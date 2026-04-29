# top-python

Python으로 작성된 Linux `top` / `htop` 스타일의 시스템 모니터입니다.

CPU 사용률, 메모리 통계, 프로세스 목록을 터미널에서 실시간으로 표시하며, htop에서 영감을 받은 ANSI 색상을 사용합니다.

## 화면 예시

```
top - 14:32:05 up 02:14,  load average: 1.20, 0.95, 0.87
Tasks:  182 total,   2 running, 178 sleeping,   0 stopped,   2 zombie
%Cpu(s):  12.3 us,   4.1 sy,   0.0 ni,  83.1 id,   0.3 wa,   0.0 hi,   0.2 si,   0.0 st
CPU  |######.......|  16.9%
MiB Mem :  15872.0 total,   4210.3 free,   8901.2 used,   2760.5 buff/cache
MEM  |###########..|  56.1%
MiB Swap:   2048.0 total,   2048.0 free,      0.0 used

    PID USER      PR  NI    VIRT    RES    SHR S  %CPU %MEM     TIME+ COMMAND
   1234 alice      20   0  512.0  128.3    32.1 R  45.2  0.8    1:23.45 python
   5678 bob        20   0  256.0   64.0    16.0 S   2.1  0.4    0:05.12 node
```

## 주요 기능

- **프로세스 목록** — CPU, 메모리, PID, CPU 시간 기준으로 정렬
- **CPU 세부 분류** — user, system, nice, idle, iowait, irq, softirq, steal
- **메모리 및 스왑** 통계 (MiB 단위)
- **색상 코드** — 메트릭 수치(초록 / 노랑 / 빨강 임계값) 및 프로세스 상태별 색상 표시
- **낮은 오버헤드 샘플링** — `psutil` one-shot 읽기와 프로세스 캐시 활용
- **크로스플랫폼** — Linux, macOS, Windows 지원 (Windows에서 ANSI 색상 자동 활성화)
- **키보드 단축키** — 정렬 기준 및 갱신 주기 조작

## 요구 사항

- Python 3.10 이상
- `psutil >= 5.9.0`

## 설치

```bash
pip install -r requirements.txt
```

## 실행

```bash
python system_monitor.py
```

## 키보드 단축키

| 키 | 동작 |
|----|------|
| `c` | CPU 사용률 기준 정렬 (기본값) |
| `m` | 메모리 사용률 기준 정렬 |
| `p` | PID 기준 정렬 |
| `t` | CPU 시간 기준 정렬 |
| `r` | 정렬 순서 전환 (오름차순 / 내림차순) |
| `q` / `Ctrl+C` | 종료 |
