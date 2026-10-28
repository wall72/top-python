#!/usr/bin/env python3
"""하위호환 엔트리포인트 — 실제 구현은 top_python 패키지에 있다."""
import sys
from top_python.cli import main

if __name__ == "__main__":
    sys.exit(main())
