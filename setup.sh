#!/bin/bash
# Raspberry Pi Environment Setup Script

echo "Updating system packages and installing dependencies..."
sudo apt update
sudo apt install -y python3-pip python3-venv git mpv

echo "Initializing Git..."
git init
git add .
git commit -m "Initial commit for RPi TUI Launcher"

echo "Creating virtual environment (venv)..."
python3 -m venv venv

echo "Activating virtual environment and installing python packages..."
source venv/bin/activate
pip install -r requirements.txt

echo "Setup completed!"
echo "To register the Systemd service, you can run:"
echo "sudo cp rpi-launcher.service /etc/systemd/system/"
echo "sudo systemctl enable rpi-launcher.service"
echo "sudo systemctl start rpi-launcher.service"
