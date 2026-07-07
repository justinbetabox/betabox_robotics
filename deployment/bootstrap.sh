#!/bin/bash
set -e

REPO_URL="https://github.com/justinbetabox/betabox_robotics.git"
LIB_DIR="/opt/libs"
SDK_DIR="$LIB_DIR/betabox_robotics"

echo "======================================"
echo " Betabox Robotics Bootstrap"
echo "======================================"

if [[ "$EUID" -eq 0 ]]; then
    echo "Please run this script as pi, not with sudo."
    exit 1
fi

echo "[1/4] Installing git..."
sudo apt update
sudo apt install -y git

echo "[2/4] Preparing /opt/libs..."
sudo mkdir -p "$LIB_DIR"
sudo chown -R "$USER:$USER" "$LIB_DIR"

echo "[3/4] Cloning or updating SDK..."
if [[ -d "$SDK_DIR/.git" ]]; then
    cd "$SDK_DIR"
    git pull
else
    git clone "$REPO_URL" "$SDK_DIR"
fi

echo "[4/4] Running installer..."
cd "$SDK_DIR"
chmod +x deployment/install.sh
./deployment/install.sh
