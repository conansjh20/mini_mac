#!/bin/bash
# Raspberry Pi TUI Launcher Run Script

# 스크립트가 위치한 디렉터리로 이동
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

# 가상환경 활성화 및 프로그램 실행
source venv/bin/activate
python main.py
