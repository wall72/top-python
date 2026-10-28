# Copilot 지침 — top-python

## 응답 언어

이 저장소에서 작업하는 모든 Copilot 세션은 **응답을 한국어로 작성**한다.

## 프로젝트 개요

Linux `top`/`htop` 스타일의 단일 파일 터미널 시스템 모니터(`system_monitor.py`, 약 470줄)이다. CPU/메모리 샘플링, 프로세스 캐싱, 렌더링, 키보드 입력 처리가 모두 `SystemMonitor` 클래스 안에 들어 있다. 이 저장소에는 테스트 스위트, 린터, 빌드 설정이 없다. 의도된 동작과 알려진 이슈를 파악할 때는 README.md(한글)와 TODO.md(한글, 코드 리뷰 메모)를 근거로 삼는다.

## 실행

```bash
pip install -r requirements.txt   # psutil>=5.9.0
python system_monitor.py          # q 또는 Ctrl+C로 종료
```

자동화된 테스트는 없다. 변경 사항은 모니터를 직접 실행해 렌더링 결과와 키보드 단축키(`c`/`m`/`p`/`t` 정렬, `r` 역순, `q` 종료)를 확인하여 검증한다.

## 아키텍처 — 렌더 루프

`run()`은 매 틱마다 다음 루프를 실행한다:
1. `_collect_process_rows()` — `psutil.process_iter()`를 순회하며 PID를 키로 `self.proc_cache: Dict[pid, ProcCacheEntry]`와 병합한다. 캐시는 한 번만 조회하는 `user`/`cmd`와, CPU 퍼센트 샘플링이 "프라이밍"되었는지(`entry.primed`) 여부를 유지한다. `psutil.Process.cpu_percent()`는 의미 있는 델타 값을 반환하려면 최초 기준값 호출이 먼저 필요하기 때문이다. 2초 이상 보이지 않은 캐시 항목은 매 패스마다 정리된다.
2. `_sort_rows()` — `self.sort_key`(`cpu`/`mem`/`pid`/`time`)에 따라 행을 정렬/제한한다. `run()`에서 항상 `limit`이 주어지므로, 전체 `sorted()` 대신 `heapq.nlargest/nsmallest`를 사용해 효율을 높인다.
3. `_cpu_breakdown()` / `_memory_snapshot()` — `psutil.cpu_times_percent()` / `virtual_memory()` / `swap_memory()`를 통한 시스템 전체 원샷 통계.
4. `_build_screen()` — 헤더, CPU/MEM 막대, 프로세스 테이블을 하나의 문자열 프레임으로 조립한 뒤, 깜빡임을 피하기 위해 `\033[H\033[J` 커서 이동/클리어 접두사와 함께 단 한 번의 `sys.stdout.write`로 출력한다.

키보드 처리는 논블로킹이며 틱 당 대기 구간 안에서 폴링된다(`_read_key()`는 POSIX에서 `select`, Windows에서 `msvcrt` 사용). 덕분에 정렬 키 변경이 `update_interval` 전체를 기다리지 않고 바로 반영된다.

## 컨벤션

- **크로스플랫폼 분기**는 `os.name == "nt"` 체크와 함께 플랫폼 모듈(`msvcrt`, `termios`/`tty`)을 인라인 `import`로 불러오며, `try/except Exception: pass`로 감싼다 — 실패 시(예: 색상/raw 모드 설정) 모니터가 죽지 않고 우아하게 기능이 저하되어야 한다.
- **색상**: ANSI 코드는 `SystemMonitor`의 클래스 속성(`FG_RED`, `BOLD` 등)으로 정의한다. 항상 `self._color(text, color, bold=False)`를 통해 적용해야 하며, 이 함수는 `self.enable_color`(`sys.stdout.isatty()`로 설정)도 존중하므로 출력이 파이프/리다이렉트될 때는 색상 없이 출력된다. 수치 기반 색상은 `_metric_color()`(초록 <50%, 노랑 <80%, 빨강 ≥80%)와 프로세스 상태 문자용 `_state_color()`에서 나온다.
- **단위**: 메모리 값은 `psutil`에서 읽은 직후 `_to_mib()`로 MiB 단위로 변환한다. 이후 모든 메모리 필드는 MiB 단위를 유지해야 한다(`top`의 표시 관례와 일치).
- **프로세스 행**은 dataclass가 아닌 고정 키(`pid`, `user`, `pr`, `ni`, `virt`, `res`, `shr`, `state`, `cpu`, `mem`, `timep`, `cmd`)를 가진 일반 `dict`이다. 테이블을 확장할 때는 이 구조와 일관되게 새 필드를 추가하고, `_collect_process_rows()`와 `_build_screen()`의 포맷 문자열을 함께 갱신한다.
- **실제 `top`과의 알려진 차이점**은 TODO.md에서 추적한다(예: `pr`이 `20 + nice` 대신 현재 `"20"`/`"rt"`로 하드코딩되어 있음, `_format_uptime`이 "day"를 복수형 처리하지 않음). 이상해 보이는 동작을 "고치기" 전에 TODO.md를 먼저 확인한다 — 이미 추적 중인 항목인 경우가 많으므로, 해당 항목을 참조하며 작업한다.
