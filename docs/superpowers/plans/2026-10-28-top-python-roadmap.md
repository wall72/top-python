# top-python 개선 로드맵 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `system_monitor.py`의 알려진 버그 4개를 고치고, 단일 파일을 `top_python/` 패키지로 재구성하며, 핵심 순수 함수에 단위 테스트를 추가하고, 4개의 신규 기능(갱신 주기 조작, cmdline 토글, 코어별 CPU 표시, CLI 인자)을 추가한 뒤 `pyproject.toml`과 `--version`으로 마무리한다.

**Architecture:** 현재 `SystemMonitor` 한 클래스에 몰려 있는 책임(색상/포맷팅/정렬/수집/렌더링/입력)을 `top_python/` 아래 역할별 모듈로 분리한다. 순수 로직(포맷팅, 정렬, 색상 계산, EMA 계산)은 인스턴스 상태 없는 free function으로 뽑아 `pytest`로 직접 테스트하고, 상태가 필요한 부분(프로세스 캐시, 로드 평균 추적, 메인 루프)만 작은 클래스로 유지한다. 저장소 루트의 `system_monitor.py`는 최종적으로 `top_python.cli:main`을 호출하는 얇은 하위호환 shim이 된다.

**Tech Stack:** Python 3.10+, `psutil>=5.9.0`, `pytest`(dev 전용 의존성), 표준 라이브러리(`argparse`, `dataclasses`, `heapq`, `math`).

**Spec:** `docs/superpowers/specs/2026-10-28-top-python-roadmap-design.md`

## Global Constraints

- 새 필수 의존성을 추가하지 않는다 — 실행 시 의존성은 `psutil>=5.9.0`만 유지한다 (`pytest`는 dev 전용).
- Windows 호환 분기(`os.name == "nt"`에서 ANSI 활성화, `msvcrt` 입력)를 깨뜨리지 않는다.
- `enable_color`가 꺼진 경우(파이프/리다이렉트, `--no-color`) 출력은 색상 코드 없이 정상적으로 렌더링되어야 한다.
- 메모리 값은 항상 MiB 단위로 다룬다(`to_mib` 변환 후).
- 실행 방법은 계속 단순해야 한다 — `python system_monitor.py`가 끝까지 동작해야 한다.
- 문서·커밋 메시지·코드 주석은 한글을 유지한다(`.github/copilot-instructions.md` 지침).
- 저장소에 CI가 없으므로 각 태스크의 검증은 로컬 `pytest`/수동 실행으로 확인한다.
- 범위에서 제외된 것: 프로세스 필터링/검색(`/` 키, 별도 스펙), `psutil` 모킹 테스트.

## Review Focus

- **코어 수가 1개이거나 4의 배수가 아닐 때** 코어별 CPU 표시의 줄 분배(`ceil(n/4)`)가 틀려 마지막 줄이 깨지거나 코어가 누락될 수 있다 — Task 16에서 1코어·5코어 등 경계값 테스트로 고정한다.
- **`nice` 값이 극단(-20, 19)일 때** `pr` 계산(`20 + nice`)이 범위를 벗어나는 문자열을 만들지 않는지 — Task 1에서 경계값 테스트로 고정한다.
- **`update_interval`을 계속 내려서 0 이하로 만들려는 입력**(`-` 키 반복)이 틱 루프를 바쁜 대기(busy loop)로 만들 수 있다 — Task 14에서 하한값 테스트로 고정한다.
- **`--interval` CLI 인자에 0 이하나 숫자가 아닌 값**이 들어오면 루프가 즉시 100% CPU를 소모하거나 크래시할 수 있다 — Task 17에서 argparse 유효성 검사 테스트로 고정한다.
- **색상이 꺼진 상태에서 `bar()`/`color()`가 호출될 때** ANSI 코드가 섞여 나오면 `--no-color`/파이프 출력이 깨진다 — Task 6에서 `enabled=False` 케이스를 테스트로 고정한다.

---

## 파일 구조

새로 만들거나 수정할 파일과 각각의 책임:

- `top_python/__init__.py` — 패키지 진입점, `__version__` 노출 (Task 18).
- `top_python/formatting.py` — `format_uptime`, `format_time_plus`, `to_mib`, `priority_label`, `ema_step` (순수 함수).
- `top_python/colors.py` — ANSI 상수, `color()`, `metric_color()`, `state_color()`, `bar()` (순수 함수, `enabled` 인자로 활성화 여부 제어).
- `top_python/models.py` — `ProcCacheEntry`, `ProcessRow` 데이터클래스.
- `top_python/sorting.py` — `sort_rows()` (순수 함수).
- `top_python/collectors.py` — `ProcessCollector`(프로세스 캐시+수집), `cpu_breakdown()`, `memory_snapshot()`, `LoadAverageTracker`(EMA 상태 유지).
- `top_python/render.py` — `render_header`, `render_cpu_section`, `render_mem_section`, `render_process_table`, `build_screen`, `core_rows`(코어별 막대 줄 분배).
- `top_python/input_handling.py` — `read_key()`, `raw_stdin()` (플랫폼 분기, 자동 테스트 불가 — 수동 검증).
- `top_python/app.py` — `SystemMonitor` 클래스(메인 루프, 상태, `handle_key`).
- `top_python/cli.py` — `parse_args()`, `main(argv=None) -> int`.
- `system_monitor.py` — `top_python.cli:main`을 호출하는 하위호환 shim으로 축소.
- `pyproject.toml` — 신규, 패키지 메타데이터 + console script.
- `tests/test_formatting.py`, `tests/test_colors.py`, `tests/test_sorting.py`, `tests/test_collectors.py`, `tests/test_render.py`, `tests/test_app.py`, `tests/test_cli.py` — 각 모듈별 단위 테스트.
- `requirements-dev.txt` — 신규, `pytest`만 명시.

---

### Task 1: 버그 수정 — `pr`(우선순위) 값

**Files:**
- Modify: `system_monitor.py` (`_collect_process_rows` 내 `pr` 계산부)
- Test: `tests/test_system_monitor_bugfixes.py` (신규)
- Create: `requirements-dev.txt`

**Interfaces:**
- Produces: `SystemMonitor._priority_label(nice_value: int) -> str` (staticmethod)

- [ ] **Step 1: `requirements-dev.txt` 생성, `pytest`만 기재**

```
pytest>=7.0
```

- [ ] **Step 2: 가상환경에 설치**

Run: `pip install -r requirements.txt -r requirements-dev.txt`

- [ ] **Step 3: 실패하는 테스트 작성**

```python
# tests/test_system_monitor_bugfixes.py
import pytest
from system_monitor import SystemMonitor

def test_priority_label_normal_nice():
    assert SystemMonitor._priority_label(0) == "20"

def test_priority_label_negative_nice():
    assert SystemMonitor._priority_label(-5) == "15"

def test_priority_label_min_nice():
    assert SystemMonitor._priority_label(-20) == "0"

def test_priority_label_max_nice():
    assert SystemMonitor._priority_label(19) == "39"
```

- [ ] **Step 4: 테스트 실행 — 실패 확인**

Run: `pytest tests/test_system_monitor_bugfixes.py -v`
Expected: FAIL with `AttributeError: type object 'SystemMonitor' has no attribute '_priority_label'`

- [ ] **Step 5: `SystemMonitor._priority_label(nice_value: int) -> str` staticmethod 구현**

`str(20 + nice_value)`를 반환한다. 기존의 `"rt"` 분기는 제거한다(스펙 근거: 실제 `top`은 `nice` 값과 무관하게 스케줄링 정책으로 realtime 여부를 판단하며, 이 코드베이스는 그 정보를 갖고 있지 않으므로 모든 경우에 `20 + nice`를 사용한다). `_collect_process_rows`의 `"pr": "rt" if nice_value < 0 else "20"` 줄을 `"pr": SystemMonitor._priority_label(nice_value)`로 교체한다.

- [ ] **Step 6: 테스트 실행 — 통과 확인**

Run: `pytest tests/test_system_monitor_bugfixes.py -v`
Expected: PASS (4 tests)

- [ ] **Step 7: 커밋**

```bash
git add requirements-dev.txt tests/test_system_monitor_bugfixes.py system_monitor.py
git commit -m "fix: pr 우선순위 값을 20 + nice로 계산"
```

---

### Task 2: 버그 수정 — `_format_uptime` 복수형 처리

**Files:**
- Modify: `system_monitor.py` (`_format_uptime`)
- Test: `tests/test_system_monitor_bugfixes.py` (추가)

**Interfaces:**
- Consumes: 없음
- Produces: 기존 `SystemMonitor._format_uptime(seconds: float) -> str` 시그니처 유지, 반환 문자열만 변경

- [ ] **Step 1: 실패하는 테스트 추가**

```python
def test_format_uptime_singular_day():
    assert SystemMonitor._format_uptime(90000) == "1 day, 01:00"

def test_format_uptime_plural_days():
    assert SystemMonitor._format_uptime(2 * 86400 + 3600) == "2 days, 01:00"

def test_format_uptime_no_days():
    assert SystemMonitor._format_uptime(3661) == "01:01"
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `pytest tests/test_system_monitor_bugfixes.py -k plural_days -v`
Expected: FAIL (현재는 `"2 day, 01:00"`을 반환)

- [ ] **Step 3: `_format_uptime` 수정**

`days > 1`일 때 `"day"` 대신 `"days"`를 사용하도록 분기 추가 (`days == 1`일 때만 단수).

- [ ] **Step 4: 테스트 실행 — 통과 확인**

Run: `pytest tests/test_system_monitor_bugfixes.py -v`
Expected: PASS (전체)

- [ ] **Step 5: 커밋**

```bash
git add tests/test_system_monitor_bugfixes.py system_monitor.py
git commit -m "fix: 가동시간이 2일 이상일 때 days로 복수형 처리"
```

---

### Task 3: 버그 수정 — 가상(pseudo) 로드 평균을 EMA로 계산

**Files:**
- Modify: `system_monitor.py` (`_loadavg`, `__init__`)
- Test: `tests/test_system_monitor_bugfixes.py` (추가)

**Interfaces:**
- Produces: `SystemMonitor._ema_step(prev: float, target: float, dt: float, tau: float) -> float` (staticmethod, 순수 함수)
- `SystemMonitor.__init__`에 `self._load_ema: list[float]` 초기화(3개 원소, 초기값 0.0) 추가
- `_loadavg(self, cpu_used: float) -> List[float]`는 기존 시그니처 유지, Windows/‌`getloadavg` 없는 경로에서만 `_ema_step`을 3개 시정수(tau)에 적용해 `self._load_ema`를 갱신하고 반환

- [ ] **Step 1: 실패하는 테스트 작성**

```python
def test_ema_step_moves_toward_target():
    result = SystemMonitor._ema_step(prev=0.0, target=1.0, dt=60.0, tau=60.0)
    assert 0.6 < result < 0.64  # 1 - e^-1 ≈ 0.632

def test_ema_step_zero_dt_returns_prev():
    assert SystemMonitor._ema_step(prev=0.5, target=1.0, dt=0.0, tau=60.0) == 0.5

def test_ema_step_large_dt_approaches_target():
    result = SystemMonitor._ema_step(prev=0.0, target=2.0, dt=100000.0, tau=60.0)
    assert result == pytest.approx(2.0, abs=1e-6)
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `pytest tests/test_system_monitor_bugfixes.py -k ema_step -v`
Expected: FAIL with `AttributeError`

- [ ] **Step 3: `_ema_step` 구현**

`system_monitor.py` 상단에 `import math`를 추가한다. `alpha = 1 - math.exp(-dt / tau)`를 계산하고 `prev + alpha * (target - prev)`를 반환한다.

- [ ] **Step 4: 테스트 실행 — 통과 확인**

Run: `pytest tests/test_system_monitor_bugfixes.py -k ema_step -v`
Expected: PASS (3 tests)

- [ ] **Step 5: `_loadavg`를 `_ema_step` 기반으로 재작성**

`os.getloadavg`가 없는 분기에서: `pseudo_load = (cpu_used / 100.0) * self.cpu_count`를 목표값으로 삼아, `self._load_ema`의 세 항목을 각각 tau=60.0(1분), 300.0(5분), 900.0(15분)으로 `_ema_step(prev, pseudo_load, self.update_interval, tau)`로 갱신하고 `list(self._load_ema)`를 반환한다. `__init__`에 `self._load_ema = [0.0, 0.0, 0.0]`를 추가한다.

- [ ] **Step 6: 전체 테스트 실행**

Run: `pytest tests/test_system_monitor_bugfixes.py -v`
Expected: PASS (전체)

- [ ] **Step 7: 커밋**

```bash
git add tests/test_system_monitor_bugfixes.py system_monitor.py
git commit -m "fix: 의사 로드 평균을 지수이동평균(EMA)으로 계산"
```

---

### Task 4: 버그 수정 — `cpu_percent` 호출을 `oneshot()` 밖으로 이동

**Files:**
- Modify: `system_monitor.py` (`_collect_process_rows`)

**Interfaces:**
- 없음(내부 호출 순서 변경만, 공개 시그니처 불변)

- [ ] **Step 1: 코드 변경**

`with proc.oneshot():` 블록 안에서 호출되던 `proc.cpu_percent(interval=0.0)`/`proc.cpu_percent(interval=None)`를 블록 종료 직후로 이동한다. `entry.primed` 여부 분기 로직은 그대로 유지하되, `oneshot()` 블록 안에서는 `info = proc.info`로 나머지 필드만 읽는다.

- [ ] **Step 2: 수동 검증**

자동 테스트는 작성하지 않는다(실제 `psutil.Process` 동작을 모킹 없이 검증하기 어렵고, `psutil` 모킹 테스트는 로드맵 범위에서 제외되었다). 대신 다음을 수동으로 확인한다:

Run: `python system_monitor.py` (몇 초 관찰 후 `q`로 종료)
Expected: 콘솔에 에러 없이 프로세스 테이블이 계속 갱신되고, CPU% 값이 이전과 동일하게 합리적인 범위로 표시된다.

- [ ] **Step 3: 커밋**

```bash
git add system_monitor.py
git commit -m "fix: cpu_percent 호출을 oneshot 블록 밖으로 이동"
```

---

### Task 5: 패키지 스켈레톤 + `top_python/formatting.py`

**Files:**
- Create: `top_python/__init__.py`
- Create: `top_python/formatting.py`
- Create: `tests/test_formatting.py`
- Modify: `system_monitor.py` (아직 shim으로 바꾸지 않음 — 이 태스크에서는 새 모듈만 만든다)

**Interfaces:**
- Produces:
  - `format_uptime(seconds: float) -> str`
  - `format_time_plus(seconds: float) -> str`
  - `to_mib(value_bytes: int) -> float`
  - `priority_label(nice_value: int) -> str`
  - `ema_step(prev: float, target: float, dt: float, tau: float) -> float`

- [ ] **Step 1: `top_python/__init__.py`를 빈 파일로 생성**

- [ ] **Step 2: 실패하는 테스트 작성 (`tests/test_formatting.py`)**

```python
from top_python.formatting import format_uptime, format_time_plus, to_mib, priority_label, ema_step
import pytest

def test_format_uptime_plural_days():
    assert format_uptime(2 * 86400 + 3600) == "2 days, 01:00"

def test_format_time_plus_basic():
    assert format_time_plus(83.45) == "   1:23.45"

def test_to_mib():
    assert to_mib(1024 * 1024 * 2) == 2.0

def test_priority_label_negative_nice():
    assert priority_label(-5) == "15"

def test_ema_step_zero_dt_returns_prev():
    assert ema_step(prev=0.5, target=1.0, dt=0.0, tau=60.0) == 0.5
```

- [ ] **Step 3: 테스트 실행 — 실패 확인**

Run: `pytest tests/test_formatting.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'top_python'`

- [ ] **Step 4: `top_python/formatting.py` 구현**

Task 1~3에서 `system_monitor.py`에 구현한 `_format_uptime`(복수형 처리 포함)/`_format_time_plus`/`_to_mib`/`_priority_label`/`_ema_step`의 로직을 그대로 free function으로 옮긴다(선행 밑줄 제거).

- [ ] **Step 5: 테스트 실행 — 통과 확인**

Run: `pytest tests/test_formatting.py -v`
Expected: PASS (5 tests)

- [ ] **Step 6: 커밋**

```bash
git add top_python/__init__.py top_python/formatting.py tests/test_formatting.py
git commit -m "refactor: 포맷팅 순수 함수를 top_python.formatting으로 이동"
```

---

### Task 6: `top_python/colors.py`

**Files:**
- Create: `top_python/colors.py`
- Create: `tests/test_colors.py`

**Interfaces:**
- Consumes: 없음
- Produces:
  - 모듈 상수 `RESET, BOLD, DIM, FG_CYAN, FG_GREEN, FG_YELLOW, FG_RED, FG_BLUE, FG_MAGENTA, FG_WHITE`
  - `color(text: str, code: str, bold: bool = False, enabled: bool = True) -> str`
  - `metric_color(value: float) -> str`
  - `state_color(state: str) -> str`
  - `bar(percent: float, width: int = 24, enabled: bool = True) -> str`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
from top_python.colors import color, metric_color, state_color, bar, FG_RED, FG_GREEN

def test_color_disabled_returns_plain_text():
    assert color("hi", FG_RED, enabled=False) == "hi"

def test_color_enabled_wraps_with_code():
    assert color("hi", FG_RED, enabled=True) == f"{FG_RED}hi\033[0m"

def test_metric_color_thresholds():
    assert metric_color(10.0) == FG_GREEN
    assert metric_color(90.0) == FG_RED

def test_state_color_running_is_green():
    assert state_color("R") == FG_GREEN

def test_bar_disabled_has_no_escape_codes():
    result = bar(50.0, width=10, enabled=False)
    assert "\033" not in result
    assert result.count("#") == 5
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `pytest tests/test_colors.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: `top_python/colors.py` 구현**

`system_monitor.py`의 ANSI 상수와 `_color`/`_metric_color`/`_state_color`/`_bar` 로직을 옮기되, `_color`와 `_bar`는 인스턴스의 `self.enable_color` 대신 `enabled` 매개변수를 받도록 바꾼다.

- [ ] **Step 4: 테스트 실행 — 통과 확인**

Run: `pytest tests/test_colors.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: 커밋**

```bash
git add top_python/colors.py tests/test_colors.py
git commit -m "refactor: ANSI 색상 로직을 top_python.colors로 분리"
```

---

### Task 7: `top_python/models.py`

**Files:**
- Create: `top_python/models.py`
- Create: `tests/test_models.py`

**Interfaces:**
- Consumes: 없음
- Produces:
  - `ProcCacheEntry` dataclass: `proc: psutil.Process`, `primed: bool = False`, `last_seen: float = 0.0`, `user: str = "?"`, `cmd: str = "?"`, `cmdline_full: str | None = None`
  - `ProcessRow` dataclass: `pid: int, user: str, pr: str, ni: int, virt: float, res: float, shr: float, state: str, cpu: float, mem: float, timep: float, cmd: str`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
from top_python.models import ProcessRow, ProcCacheEntry

def test_process_row_field_access():
    row = ProcessRow(pid=1, user="root", pr="20", ni=0, virt=1.0, res=2.0,
                      shr=0.5, state="R", cpu=10.0, mem=5.0, timep=1.5, cmd="init")
    assert row.pid == 1
    assert row.cmd == "init"

def test_proc_cache_entry_defaults():
    entry = ProcCacheEntry(proc=None)
    assert entry.primed is False
    assert entry.user == "?"
    assert entry.cmdline_full is None
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `pytest tests/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: `top_python/models.py` 구현**

기존 `ProcCacheEntry`에 `cmdline_full: str | None = None` 필드를 추가해 옮기고, 지금까지 `dict`로 다루던 프로세스 행을 `ProcessRow` 데이터클래스로 정의한다(필드는 기존 dict 키와 동일).

- [ ] **Step 4: 테스트 실행 — 통과 확인**

Run: `pytest tests/test_models.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: 커밋**

```bash
git add top_python/models.py tests/test_models.py
git commit -m "refactor: 프로세스 행을 dict 대신 ProcessRow 데이터클래스로 정의"
```

---

### Task 8: `top_python/sorting.py`

**Files:**
- Create: `top_python/sorting.py`
- Create: `tests/test_sorting.py`

**Interfaces:**
- Consumes: `top_python.models.ProcessRow`
- Produces: `sort_rows(rows: list[ProcessRow], sort_key: str, reverse: bool, limit: int | None = None) -> list[ProcessRow]`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
from top_python.models import ProcessRow
from top_python.sorting import sort_rows

def _row(pid, cpu, mem, timep):
    return ProcessRow(pid=pid, user="u", pr="20", ni=0, virt=0, res=0, shr=0,
                       state="R", cpu=cpu, mem=mem, timep=timep, cmd="x")

ROWS = [_row(1, 10.0, 1.0, 5.0), _row(2, 50.0, 2.0, 1.0), _row(3, 5.0, 9.0, 9.0)]

def test_sort_by_cpu_descending():
    result = sort_rows(ROWS, "cpu", reverse=True)
    assert [r.pid for r in result] == [2, 1, 3]

def test_sort_by_pid_ascending():
    result = sort_rows(ROWS, "pid", reverse=False)
    assert [r.pid for r in result] == [1, 2, 3]

def test_sort_with_limit_uses_top_n():
    result = sort_rows(ROWS, "mem", reverse=True, limit=2)
    assert [r.pid for r in result] == [3, 2]

def test_sort_unknown_key_defaults_to_cpu():
    result = sort_rows(ROWS, "bogus", reverse=True)
    assert [r.pid for r in result] == [2, 1, 3]
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `pytest tests/test_sorting.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: `sort_rows` 구현**

기존 `_sort_rows`의 `key_map`/`heapq.nlargest`/`heapq.nsmallest`/`sorted` 로직을 그대로 옮기되 `rows`, `sort_key`, `reverse`, `limit`을 인자로 받는 free function으로 만든다.

- [ ] **Step 4: 테스트 실행 — 통과 확인**

Run: `pytest tests/test_sorting.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: 커밋**

```bash
git add top_python/sorting.py tests/test_sorting.py
git commit -m "refactor: 정렬 로직을 top_python.sorting 순수 함수로 분리"
```

---

### Task 9: `top_python/collectors.py`

**Files:**
- Create: `top_python/collectors.py`
- Create: `tests/test_collectors.py`

**Interfaces:**
- Consumes: `top_python.models.ProcCacheEntry`, `top_python.models.ProcessRow`, `top_python.formatting.to_mib`, `top_python.formatting.ema_step`
- Produces:
  - `class ProcessCollector`: `__init__(self)`, `collect(self, show_cmdline: bool = False) -> tuple[list[ProcessRow], dict]`
  - `cpu_breakdown() -> dict`
  - `memory_snapshot() -> dict`
  - `class LoadAverageTracker`: `__init__(self, cpu_count: int)`, `update(self, cpu_used: float, dt: float) -> list[float]`

- [ ] **Step 1: 실패하는 테스트 작성 (실제 psutil 대상, 모킹 없음)**

```python
from top_python.collectors import ProcessCollector, cpu_breakdown, memory_snapshot, LoadAverageTracker

def test_process_collector_returns_rows_and_states():
    collector = ProcessCollector()
    rows, states = collector.collect()
    assert len(rows) > 0
    assert sum(states.values()) == len(rows)
    assert all(hasattr(r, "pid") for r in rows)

def test_cpu_breakdown_has_expected_keys():
    result = cpu_breakdown()
    assert set(result.keys()) == {"us", "sy", "ni", "id", "wa", "hi", "si", "st"}

def test_memory_snapshot_has_expected_keys():
    result = memory_snapshot()
    assert result["mem_total"] >= result["mem_used"]

def test_load_average_tracker_moves_toward_target():
    tracker = LoadAverageTracker(cpu_count=4)
    first = tracker.update(cpu_used=50.0, dt=60.0)
    second = tracker.update(cpu_used=50.0, dt=60.0)
    assert second[0] > first[0]
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `pytest tests/test_collectors.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: `top_python/collectors.py` 구현**

`system_monitor.py`의 `_collect_process_rows`(Task 4에서 고친 순서 포함, `show_cmdline` 인자 지원은 Task 15에서 추가 예정이므로 지금은 매개변수만 받아두고 무시), `_cpu_breakdown`, `_memory_snapshot`, `_loadavg`(Task 3의 `ema_step` 사용)을 각각 클래스/함수로 옮긴다. `ProcessCollector`는 내부에 `self._cache: dict[int, ProcCacheEntry]`를 유지한다. `LoadAverageTracker`는 내부에 `self._ema: list[float]`를 유지한다.

- [ ] **Step 4: 테스트 실행 — 통과 확인**

Run: `pytest tests/test_collectors.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: 커밋**

```bash
git add top_python/collectors.py tests/test_collectors.py
git commit -m "refactor: 수집 로직을 top_python.collectors로 분리"
```

---

### Task 10: `top_python/render.py`

**Files:**
- Create: `top_python/render.py`
- Create: `tests/test_render.py`

**Interfaces:**
- Consumes: `top_python.colors.*`, `top_python.formatting.*`, `top_python.models.ProcessRow`
- Produces:
  - `render_header(now: str, uptime: str, loads: tuple[float, float, float], enabled: bool) -> str`
  - `render_cpu_section(cpu: dict, enabled: bool) -> list[str]`
  - `render_mem_section(mem: dict, enabled: bool) -> list[str]`
  - `render_process_table(rows: list[ProcessRow], width: int, enabled: bool) -> list[str]`
  - `core_rows(percpu_values: list[float], per_row: int = 4, enabled: bool = True) -> list[str]`
  - `build_screen(...) -> str` (나머지 조립, 기존 `_build_screen`과 동일한 인자 + `show_percpu: bool`, `percpu_values: list[float] | None`)

- [ ] **Step 1: 실패하는 테스트 작성**

```python
from top_python.render import render_header, render_process_table, core_rows
from top_python.models import ProcessRow

def test_render_header_contains_load_average():
    result = render_header("12:00:00", "01:00", (1.0, 0.5, 0.2), enabled=False)
    assert "load average: 1.00, 0.50, 0.20" in result

def test_render_process_table_contains_pid():
    row = ProcessRow(pid=1234, user="u", pr="20", ni=0, virt=1, res=1, shr=1,
                      state="R", cpu=1.0, mem=1.0, timep=1.0, cmd="x")
    lines = render_process_table([row], width=80, enabled=False)
    assert any("1234" in line for line in lines)

def test_core_rows_single_core():
    result = core_rows([42.0], per_row=4, enabled=False)
    assert len(result) == 1

def test_core_rows_five_cores_wraps_to_two_lines():
    result = core_rows([10.0] * 5, per_row=4, enabled=False)
    assert len(result) == 2
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `pytest tests/test_render.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: `top_python/render.py` 구현**

기존 `_build_screen`을 섹션별 함수로 쪼갠다. `core_rows`는 `percpu_values`를 `per_row`개씩 묶어 각 줄에 `bar()`를 호출해 문자열을 만든다(한 코어당 좁은 막대, 예: width=10). `build_screen`은 `show_percpu`가 True면 `core_rows` 결과를 CPU 섹션 뒤에 삽입하고, `max_proc_rows` 계산 시 `height - 11 - len(core_lines)`로 코어 줄 수만큼 줄여 프로세스 테이블 공간을 확보한다.

- [ ] **Step 4: 테스트 실행 — 통과 확인**

Run: `pytest tests/test_render.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: 커밋**

```bash
git add top_python/render.py tests/test_render.py
git commit -m "refactor: 화면 렌더링을 top_python.render 섹션별 함수로 분리"
```

---

### Task 11: `top_python/input_handling.py`

**Files:**
- Create: `top_python/input_handling.py`

**Interfaces:**
- Produces: `read_key() -> str | None`, `raw_stdin()` (contextmanager)

- [ ] **Step 1: `system_monitor.py`의 `_read_key`/`_raw_stdin` 로직을 그대로 옮겨 free function/contextmanager로 구현**

(이 모듈은 플랫폼 종속 터미널 I/O이므로 자동 테스트를 작성하지 않는다 — 스펙의 테스트 범위는 순수 함수로 한정되어 있다.)

- [ ] **Step 2: 수동 검증**

Run: `python -c "from top_python.input_handling import read_key, raw_stdin; print('import ok')"`
Expected: `import ok` 출력, 에러 없음

- [ ] **Step 3: 커밋**

```bash
git add top_python/input_handling.py
git commit -m "refactor: 키보드 입력 처리를 top_python.input_handling으로 분리"
```

---

### Task 12: `top_python/app.py` — `SystemMonitor` 재조립

**Files:**
- Create: `top_python/app.py`
- Create: `tests/test_app.py`

**Interfaces:**
- Consumes: `ProcessCollector`, `cpu_breakdown`, `memory_snapshot`, `LoadAverageTracker` (Task 9), `sort_rows` (Task 8), `build_screen` (Task 10), `read_key`/`raw_stdin` (Task 11)
- Produces: `class SystemMonitor`: `__init__(self, enable_color: bool | None = None, update_interval: float = 1.0)`, `handle_key(self, key: str) -> None`, `run(self) -> None`
  - 공개 상태 속성: `self.running`, `self.sort_key`, `self.sort_reverse`, `self.update_interval`, `self.show_cmdline`, `self.show_percpu`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
from top_python.app import SystemMonitor

def test_handle_key_c_sets_cpu_sort():
    monitor = SystemMonitor()
    monitor.sort_key = "mem"
    monitor.handle_key("c")
    assert monitor.sort_key == "cpu"
    assert monitor.sort_reverse is True

def test_handle_key_q_stops_running():
    monitor = SystemMonitor()
    monitor.handle_key("q")
    assert monitor.running is False

def test_handle_key_r_toggles_reverse():
    monitor = SystemMonitor()
    before = monitor.sort_reverse
    monitor.handle_key("r")
    assert monitor.sort_reverse is not before
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `pytest tests/test_app.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: `top_python/app.py` 구현**

기존 `SystemMonitor`의 `__init__`/`run`/`_handle_key`(→`handle_key`로 공개)를 Task 5~11에서 만든 모듈들을 사용하도록 재작성한다. 생성자는 `enable_color`(기본값 `None`이면 `sys.stdout.isatty()`로 결정)와 `update_interval`(기본 `1.0`)을 받는다. `self.show_cmdline = False`, `self.show_percpu = False`를 추가한다(Task 15·16에서 사용).

- [ ] **Step 4: 테스트 실행 — 통과 확인**

Run: `pytest tests/test_app.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: 커밋**

```bash
git add top_python/app.py tests/test_app.py
git commit -m "refactor: SystemMonitor를 top_python.app으로 재조립"
```

---

### Task 13: `system_monitor.py`를 하위호환 shim으로 축소 + 전체 회귀 검증

**Files:**
- Modify: `system_monitor.py` (전체 교체)
- Delete: `tests/test_system_monitor_bugfixes.py` (Task 1~3 테스트는 이미 Task 5의 `tests/test_formatting.py`로 이관됨)

**Interfaces:**
- Consumes: `top_python.app.SystemMonitor`

- [ ] **Step 1: `system_monitor.py`를 다음 내용으로 교체**

```python
#!/usr/bin/env python3
"""하위호환 엔트리포인트 — 실제 구현은 top_python 패키지에 있다."""
import sys
from top_python.app import SystemMonitor


def main() -> None:
    try:
        SystemMonitor().run()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 중복된 `tests/test_system_monitor_bugfixes.py` 삭제**

(해당 테스트들은 Task 5에서 `tests/test_formatting.py`로 이미 이관되어 중복됨)

- [ ] **Step 3: 전체 테스트 스위트 실행**

Run: `pytest -v`
Expected: PASS (전체 — formatting/colors/models/sorting/collectors/render/app)

- [ ] **Step 4: 수동 회귀 검증**

Run: `python system_monitor.py`
Expected: 기존과 동일한 화면이 출력되고, `c`/`m`/`p`/`t`/`r`/`q` 키가 모두 정상 동작한다.

- [ ] **Step 5: 커밋**

```bash
git add system_monitor.py tests/test_system_monitor_bugfixes.py
git commit -m "refactor: system_monitor.py를 top_python 패키지 호출 shim으로 축소"
```

---

### Task 14: 기능 — 갱신 주기(`update_interval`) 키보드 조작

**Files:**
- Modify: `top_python/app.py` (`handle_key`)
- Modify: `tests/test_app.py`

**Interfaces:**
- 변경 없음(`handle_key`에 `"+"`/`"-"` 분기 추가)

- [ ] **Step 1: 실패하는 테스트 작성**

```python
def test_handle_key_plus_increases_interval():
    monitor = SystemMonitor()
    monitor.update_interval = 1.0
    monitor.handle_key("+")
    assert monitor.update_interval == 1.5

def test_handle_key_minus_decreases_interval():
    monitor = SystemMonitor()
    monitor.update_interval = 1.0
    monitor.handle_key("-")
    assert monitor.update_interval == 0.5

def test_handle_key_minus_does_not_go_below_half_second():
    monitor = SystemMonitor()
    monitor.update_interval = 0.5
    monitor.handle_key("-")
    assert monitor.update_interval == 0.5
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `pytest tests/test_app.py -k interval -v`
Expected: FAIL (분기 없음)

- [ ] **Step 3: `handle_key`에 추가**

`"+"`는 `update_interval += 0.5`, `"-"`는 `update_interval = max(0.5, update_interval - 0.5)`. 하한값 `0.5`는 틱 루프가 바쁜 대기(busy loop)로 빠지는 것을 막기 위한 설계 결정이다.

- [ ] **Step 4: 테스트 실행 — 통과 확인**

Run: `pytest tests/test_app.py -k interval -v`
Expected: PASS (3 tests)

- [ ] **Step 5: 커밋**

```bash
git add top_python/app.py tests/test_app.py
git commit -m "feat: +/- 키로 갱신 주기 조정 (하한 0.5초)"
```

---

### Task 15: 기능 — cmdline 표시 토글 (`e` 키)

**Files:**
- Modify: `top_python/app.py` (`handle_key`, `run`)
- Modify: `top_python/collectors.py` (`ProcessCollector.collect`)
- Modify: `tests/test_app.py`, `tests/test_collectors.py`

**Interfaces:**
- `ProcessCollector.collect(self, show_cmdline: bool = False)`의 `show_cmdline=True` 동작 확정: 캐시에 `cmdline_full`이 아직 없으면(`entry.cmdline_full is None`) 그 프로세스에 한해 `proc.cmdline()`을 호출해 `" ".join(...)`으로 캐싱하고, 이후 틱에서는 캐시된 값을 재사용한다. `show_cmdline=False`일 때는 `proc.cmdline()`을 호출하지 않는다.

- [ ] **Step 1: 실패하는 테스트 작성 (`tests/test_collectors.py`에 추가)**

```python
def test_collect_without_show_cmdline_never_caches_full_command():
    collector = ProcessCollector()
    collector.collect(show_cmdline=False)
    assert all(entry.cmdline_full is None for entry in collector._cache.values())

def test_collect_with_show_cmdline_populates_at_least_one_entry():
    collector = ProcessCollector()
    collector.collect(show_cmdline=True)
    assert any(entry.cmdline_full is not None for entry in collector._cache.values())
```

(참고: `psutil` 모킹이 범위 밖이므로, 이 테스트는 실제 실행 중인 프로세스(테스트를 실행하는 프로세스 자신 포함)를 대상으로 한다. `show_cmdline=False`일 때 어떤 캐시 항목에도 `cmdline_full`이 채워지지 않는다는 것, `show_cmdline=True`일 때 최소 한 개는 채워진다는 것을 검증한다.)

```python
def test_handle_key_e_toggles_show_cmdline():
    monitor = SystemMonitor()
    assert monitor.show_cmdline is False
    monitor.handle_key("e")
    assert monitor.show_cmdline is True
    monitor.handle_key("e")
    assert monitor.show_cmdline is False
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `pytest tests/test_app.py -k cmdline -v && pytest tests/test_collectors.py -k show_cmdline -v`
Expected: 둘 다 FAIL (분기/매개변수 없음)

- [ ] **Step 3: 구현**

`handle_key`에 `"e"` → `self.show_cmdline = not self.show_cmdline` 추가. `ProcessCollector.collect`에 `show_cmdline` 매개변수를 추가하고 위 캐싱 규칙을 구현해 `ProcessRow.cmd`에 `entry.cmdline_full or entry.cmd`를 담는다. `run()`에서 `collector.collect(show_cmdline=self.show_cmdline)`로 호출하도록 수정.

- [ ] **Step 4: 테스트 실행 — 통과 확인**

Run: `pytest tests/test_app.py tests/test_collectors.py -v`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add top_python/app.py top_python/collectors.py tests/test_app.py tests/test_collectors.py
git commit -m "feat: e 키로 cmdline 전체 표시 토글 (온디맨드 캐싱)"
```

---

### Task 16: 기능 — 코어별 CPU 사용률 표시 (`1` 키)

**Files:**
- Modify: `top_python/app.py` (`handle_key`, `run`)
- Modify: `top_python/render.py` (`build_screen`에 `show_percpu`/`percpu_values` 배선 — `core_rows`는 Task 10에서 이미 구현됨)
- Modify: `tests/test_app.py`

**Interfaces:**
- 변경 없음(기존 `core_rows`/`build_screen` 시그니처 사용)

- [ ] **Step 1: 실패하는 테스트 작성**

```python
def test_handle_key_1_toggles_show_percpu():
    monitor = SystemMonitor()
    assert monitor.show_percpu is False
    monitor.handle_key("1")
    assert monitor.show_percpu is True
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `pytest tests/test_app.py -k percpu -v`
Expected: FAIL (분기 없음)

- [ ] **Step 3: 구현**

`handle_key`에 `"1"` → `self.show_percpu = not self.show_percpu` 추가. `run()`에서 `self.show_percpu`가 True면 `psutil.cpu_percent(percpu=True, interval=None)`을 호출해 `build_screen`에 `percpu_values`로 전달한다.

- [ ] **Step 4: 테스트 실행 — 통과 확인**

Run: `pytest tests/test_app.py -v`
Expected: PASS (전체)

- [ ] **Step 5: 수동 검증**

Run: `python system_monitor.py` → `1` 키 입력
Expected: 코어별 막대가 CPU 섹션 아래 추가로 표시되고, 프로세스 테이블이 잘리지 않는다.

- [ ] **Step 6: 커밋**

```bash
git add top_python/app.py tests/test_app.py
git commit -m "feat: 1 키로 코어별 CPU 사용률 표시 토글"
```

---

### Task 17: 기능 — `top_python/cli.py` (`--no-color` / `--interval`)

**Files:**
- Create: `top_python/cli.py`
- Create: `tests/test_cli.py`
- Modify: `system_monitor.py` (`top_python.cli.main` 호출로 변경)

**Interfaces:**
- Consumes: `top_python.app.SystemMonitor`
- Produces: `parse_args(argv: list[str] | None) -> argparse.Namespace` (필드: `no_color: bool`, `interval: float`), `main(argv: list[str] | None = None) -> int`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
from top_python.cli import parse_args
import pytest

def test_parse_args_defaults():
    args = parse_args([])
    assert args.no_color is False
    assert args.interval == 1.0

def test_parse_args_no_color_flag():
    args = parse_args(["--no-color"])
    assert args.no_color is True

def test_parse_args_interval_value():
    args = parse_args(["--interval", "2.5"])
    assert args.interval == 2.5

def test_parse_args_rejects_non_positive_interval():
    with pytest.raises(SystemExit):
        parse_args(["--interval", "0"])
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: `top_python/cli.py` 구현**

`argparse.ArgumentParser`에 `--no-color`(`store_true`, 기본 `False`)와 `--interval`(`type=float`, 기본 `1.0`)을 추가한다. `--interval`에 0 이하 값이 들어오면 `parser.error(...)`로 `SystemExit`을 발생시키는 커스텀 `type` 함수(`positive_float`)를 사용한다. `main(argv=None) -> int`는 `parse_args`로 파싱한 뒤 `SystemMonitor(enable_color=not args.no_color, update_interval=args.interval).run()`을 호출하고 `0`을 반환한다(예외 시 `sys.stderr`에 출력 후 `1` 반환).

- [ ] **Step 4: 테스트 실행 — 통과 확인**

Run: `pytest tests/test_cli.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: `system_monitor.py`를 `top_python.cli.main` 호출로 변경**

```python
#!/usr/bin/env python3
"""하위호환 엔트리포인트 — 실제 구현은 top_python 패키지에 있다."""
import sys
from top_python.cli import main

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: 수동 검증**

Run: `python system_monitor.py --no-color --interval 2`
Expected: 색상 없이, 2초 간격으로 화면이 갱신된다.

- [ ] **Step 7: 커밋**

```bash
git add top_python/cli.py tests/test_cli.py system_monitor.py
git commit -m "feat: --no-color/--interval CLI 인자 지원"
```

---

### Task 18: 폴리시 — `pyproject.toml`

**Files:**
- Create: `pyproject.toml`

**Interfaces:**
- 없음(패키징 메타데이터)

- [ ] **Step 1: `pyproject.toml` 작성**

```toml
[build-system]
requires = ["setuptools>=65"]
build-backend = "setuptools.build_meta"

[project]
name = "top-python"
version = "0.1.0"
description = "Linux top/htop 스타일의 터미널 시스템 모니터"
requires-python = ">=3.10"
dependencies = ["psutil>=5.9.0"]

[project.scripts]
top-python = "top_python.cli:main"

[tool.setuptools.packages.find]
include = ["top_python*"]
```

- [ ] **Step 2: 설치 후 콘솔 스크립트 동작 확인**

Run: `pip install -e . && top-python --interval 2` (수동으로 몇 초 관찰 후 `q`)
Expected: 에러 없이 모니터가 실행된다.

- [ ] **Step 3: 커밋**

```bash
git add pyproject.toml
git commit -m "chore: pyproject.toml 추가 (PEP 517/518, top-python 콘솔 스크립트)"
```

---

### Task 19: 폴리시 — `--version` 플래그

**Files:**
- Modify: `top_python/__init__.py` (`__version__ = "0.1.0"`)
- Modify: `top_python/cli.py` (`parse_args`, `main`)
- Modify: `tests/test_cli.py`

**Interfaces:**
- Produces: `top_python.__version__: str`; `parse_args`는 `--version` 플래그를 받으면 `argparse`가 버전 문자열을 출력하고 `SystemExit(0)`을 던진다(`action="version"` 사용)

- [ ] **Step 1: 실패하는 테스트 작성**

```python
import pytest
from top_python import __version__
from top_python.cli import parse_args

def test_version_flag_exits_zero(capsys):
    with pytest.raises(SystemExit) as exc_info:
        parse_args(["--version"])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert __version__ in captured.out
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `pytest tests/test_cli.py -k version -v`
Expected: FAIL (`--version` 인자 없음)

- [ ] **Step 3: 구현**

`top_python/__init__.py`에 `__version__ = "0.1.0"` 추가(Task 18의 `pyproject.toml` 버전과 동일한 값 유지). `parse_args`의 파서에 `parser.add_argument("--version", action="version", version=f"top-python {__version__}")` 추가.

- [ ] **Step 4: 테스트 실행 — 통과 확인**

Run: `pytest tests/test_cli.py -v`
Expected: PASS (전체)

- [ ] **Step 5: 전체 스위트 최종 실행**

Run: `pytest -v`
Expected: PASS (전체, 로드맵의 모든 모듈 포함)

- [ ] **Step 6: 커밋**

```bash
git add top_python/__init__.py top_python/cli.py tests/test_cli.py
git commit -m "feat: --version 플래그 추가"
```

---

## Self-Review 메모

- **스펙 커버리지**: 설계 문서 8절의 로드맵 12개 항목(1~12) 모두 Task 1~4(버그), Task 5~13(패키지 전환+테스트), Task 14~17(기능), Task 18~19(폴리시)에 1:1 또는 다대일로 매핑됨. 9절 "builder에게 맡기는 부분"의 각 항목(엔트리포인트 이름 `top-python`, dataclass 선택, 상수 모듈 형태, EMA 평활계수 tau=60/300/900, CLI 플래그 이름, 버전 `0.1.0`, PR 분할 단위=태스크당 1커밋)은 각 태스크에서 구체적 값으로 확정함.
- **완료 기준(10절)**: "기존과 동일 동작" → Task 13 Step 4, "pytest 통과" → Task 19 Step 5, "README 키 도움말과 실제 동작 일치" → Task 14(interval 조작 구현으로 기존 불일치 해소); README 자체 문구 업데이트는 범위에 없었으므로 별도 태스크로 추가하지 않되, 실행 시 변경 전 README 점검이 필요하면 손으로 확인.
- **타입 일관성**: `ProcessRow` 필드명(Task 7)이 Task 8(`sorting`)·Task 9(`collectors`)·Task 10(`render`)·Task 12(`app`) 전체에서 동일하게 사용됨. `ProcCacheEntry.cmdline_full`은 Task 7에서 정의되고 Task 15에서만 쓰임(Task 9에서는 존재는 하되 미사용 — 문제 없음).
- **Review Focus 반영**: 코어 수 경계값(Task 16은 Task 10의 `core_rows` 테스트에 이미 커버됨), `nice` 극단값(Task 1), interval 하한(Task 14), `--interval` 비정상 입력(Task 17), `enabled=False` 색상(Task 6) — 모두 해당 태스크의 테스트로 고정됨.
