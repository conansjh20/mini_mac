#!/bin/bash
# 라즈베리파이 환경 셋업 스크립트

echo "시스템 패키지 업데이트 및 의존성 설치 중..."
sudo apt update
sudo apt install -y python3-pip python3-venv git mpv retroarch

echo "Git 초기화..."
git init
git add .
git commit -m "Initial commit for RPi TUI Launcher"

echo "가상환경(venv) 생성 중..."
python3 -m venv venv

echo "가상환경 활성화 및 파이썬 패키지 설치..."
source venv/bin/activate
pip install -r requirements.txt

echo "셋업이 완료되었습니다!"
echo "Systemd 서비스를 등록하려면 다음 명령어를 참고하세요:"
echo "sudo cp rpi-launcher.service /etc/systemd/system/"
echo "sudo systemctl enable rpi-launcher.service"
echo "sudo systemctl start rpi-launcher.service"
