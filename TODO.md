# TODO — 코드 리뷰 개선점

## 버그 / 정확도

- [ ] **`pr` (우선순위) 값 고정 문제**  
  현재 nice < 0 이면 `"rt"`, 그 외엔 항상 `"20"`으로 출력.  
  실제 Linux의 `top`은 `20 + nice` 값을 표시하므로 `str(20 + nice_value)` 로 수정 필요.

- [ ] **`_format_uptime` 복수형 처리 누락**  
  `"1 day"` 는 올바르지만 `"2 day"` 처럼 `s` 가 빠짐.  
  `days > 1` 일 때 `"days"` 로 분기 처리 필요.

- [ ] **`_loadavg` 의사(pseudo) 로드값 부정확**  
  Windows에서 `os.getloadavg` 가 없으면 1분/5분/15분 평균을 모두 동일한 현재 CPU 사용률로 채움.  
  이동 평균(exponential moving average)을 직접 계산하는 방식으로 개선 필요.

- [ ] **`_collect_process_rows` 내 `cpu_percent` 호출 위치**  
  `proc.cpu_percent(interval=None)` 가 `oneshot()` 컨텍스트 내부에서 호출되고 있어  
  실제로는 oneshot 캐시와 무관한 별도 시스템 콜이 발생할 수 있음.  
  `oneshot()` 블록 종료 후 호출하도록 이동하는 것이 바람직함.

---

## 기능 개선

- [x] **`q` 입력 시 즉시 종료되지 않는 버그 수정** ✓  
  내부 대기 루프 `break` 조건에 `q` 가 누락되어 최대 1초 지연 발생. `not self.running` 조건 추가로 해결.

- [ ] **갱신 주기(`update_interval`) 키보드 조작 미구현**  
  README 하단 키 도움말에 `interval` 이 표시되지만 실제로 증감할 키가 없음.  
  예: `+` / `-` 키로 0.5초 단위 조정 추가.

- [ ] **프로세스 필터링 / 검색**  
  `/` 키로 프로세스 이름 필터 입력 모드 진입 — 대규모 서버에서 특정 프로세스 추적에 유용.

- [ ] **전체 명령줄(cmdline) 표시 토글**  
  현재 `name` 만 표시됨. `e` 키로 `cmdline` 전체 경로 ↔ 이름 전환 지원.

- [ ] **개별 CPU 코어 사용률 표시**  
  `psutil.cpu_percent(percpu=True)` 를 활용해 헤더 영역에 코어별 막대 그래프 추가 (토글 가능).

- [ ] **`--no-color` / `--interval` CLI 인자 지원**  
  `argparse` 로 실행 시 옵션 지정 가능하도록 `main()` 개선.

---

## 코드 품질

- [ ] **`_build_screen` 함수 분리**  
  헤더 렌더링, CPU 행, 메모리 행, 프로세스 테이블 렌더링을 각각 별도 메서드로 추출하여 가독성 향상.

- [ ] **`dict` 기반 프로세스 행을 `dataclass` 로 교체**  
  `_collect_process_rows` 가 반환하는 `dict` 를 `@dataclass` 또는 `TypedDict` 로 교체하면  
  타입 검사와 자동완성 지원이 개선됨.

- [ ] **`ANSI 색상 코드` 를 `enum` 또는 별도 상수 모듈로 분리**  
  현재 클래스 속성으로 관리되고 있어, 색상 관련 로직이 `SystemMonitor` 의 책임 범위를 벗어남.

- [ ] **`_color` 의 `bold` + `color` 조합 순서 일관성**  
  일부 경우 `BOLD + COLOR + text + RESET`, 일부는 `COLOR + text + RESET` 으로 혼재.  
  공통 헬퍼로 통일 필요.

- [ ] **매직 넘버 상수화**  
  `80`, `40`, `18`, `11`, `2.0`, `0.03`, `50.0`, `80.0` 등 코드 곳곳의 숫자를  
  이름이 있는 상수로 정의하여 의도를 명확히 표현.

---

## 테스트

- [ ] **단위 테스트 없음**  
  `_format_uptime`, `_format_time_plus`, `_to_mib`, `_sort_rows`, `_bar` 등  
  순수 함수들에 대한 `pytest` 기반 단위 테스트 추가.

- [ ] **psutil 모킹 테스트**  
  `psutil` 을 mock 처리하여 `_collect_process_rows`, `_memory_snapshot`, `_cpu_breakdown` 의  
  동작을 외부 시스템 없이 검증할 수 있는 테스트 작성.

---

## 기타

- [ ] **`pyproject.toml` 추가**  
  현재 `requirements.txt` 만 존재. `pyproject.toml` (PEP 517/518) 으로 프로젝트 메타데이터 관리.

- [ ] **`--version` 플래그 및 버전 정보 추가**  
  버전 상수(`__version__`) 를 모듈 상단에 정의하고 CLI 에서 출력 가능하도록 구성.
