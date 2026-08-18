#!/bin/bash
set -e

REPO_URL="https://github.com/justinbetabox/betabox_robotics.git"
BRANCH="feat/centralized-robot-runtime"

LIB_DIR="/opt/libs"
SDK_DIR="$LIB_DIR/betabox_robotics"

SERVICE_USER="$(id -un)"
SERVICE_GROUP="$(id -gn "$SERVICE_USER")"

echo "======================================"
echo " Betabox Robotics Bootstrap"
echo "======================================"

if [[ "$EUID" -eq 0 ]]; then
    echo "Please run this script as the Betabox service user, not with sudo."
    exit 1
fi

echo "[1/4] Installing git..."
sudo apt update
sudo apt install -y git

echo "[2/4] Preparing /opt/libs..."
sudo mkdir -p "$LIB_DIR"
sudo chown -R "$SERVICE_USER:$SERVICE_GROUP" "$LIB_DIR"

echo "[3/4] Cloning or updating SDK..."

if [[ -d "$SDK_DIR/.git" ]]; then
    cd "$SDK_DIR"

    git fetch origin "$BRANCH"
    git checkout "$BRANCH"
    git pull --ff-only origin "$BRANCH"
else
    git clone \
        --branch "$BRANCH" \
        --single-branch \
        "$REPO_URL" \
        "$SDK_DIR"
fi

echo "[4/4] Running installer..."

cd "$SDK_DIR"
chmod +x deployment/install.sh
./deployment/install.sh
