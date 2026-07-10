#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SDK_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LIB_DIR="/opt/libs"
BETABOX_DIR="/opt/betabox"
VENV_DIR="$BETABOX_DIR/venv"

JUPYTERHUB_DIR="/opt/jupyterhub"
JUPYTERHUB_VENV_DIR="$JUPYTERHUB_DIR/venv"

echo "======================================"
echo " Betabox Robotics SDK Installer"
echo "======================================"

if [[ "$EUID" -eq 0 ]]; then
    echo "Please run this script as pi, not with sudo."
    exit 1
fi

echo "[1/10] Installing system packages..."
sudo apt update
sudo apt install -y \
    git \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    i2c-tools \
    portaudio19-dev \
    python3-pyaudio \
    python3-opencv \
    python3-picamera2 \
    python3-lgpio \
    espeak-ng \
    libttspico-utils \
    ffmpeg \
    nodejs \
    npm \
    jq

echo "[2/10] Creating directories..."
sudo mkdir -p "$LIB_DIR" "$BETABOX_DIR"
sudo chown -R "$USER:$USER" "$LIB_DIR" "$BETABOX_DIR"

echo "[3/10] Creating Python virtual environment..."
if [[ ! -d "$VENV_DIR" ]]; then
    python3 -m venv --system-site-packages "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

echo "[4/10] Installing Python dependencies..."
python -m pip install --upgrade pip setuptools wheel

# Important:
# OpenCV is pinned to the known-good version from the working Betabox image.
# --no-deps prevents pip from replacing Debian's system NumPy, which is required
# by Picamera2/simplejpeg.
python -m pip install --no-deps \
    opencv-python==4.12.0.88 \
    opencv-python-headless==4.12.0.88

python -m pip install \
    aiohttp \
    aiortc \
    smbus2 \
    gpiozero

echo "[5/10] Installing Betabox Robotics SDK..."
python -m pip install -e "$SDK_DIR" --no-deps

echo "[6/10] Installing JupyterHub..."
sudo mkdir -p "$JUPYTERHUB_DIR"
sudo chown -R "$USER:$USER" "$JUPYTERHUB_DIR"

if [[ ! -d "$JUPYTERHUB_VENV_DIR" ]]; then
    python3 -m venv "$JUPYTERHUB_VENV_DIR"
fi

"$JUPYTERHUB_VENV_DIR/bin/python" -m pip install --upgrade pip setuptools wheel

echo "Installing configurable-http-proxy..."
sudo npm install -g configurable-http-proxy

"$JUPYTERHUB_VENV_DIR/bin/python" -m pip install -r "$SDK_DIR/deployment/jupyterhub/requirements.txt"

cp "$SDK_DIR/deployment/jupyterhub/jupyterhub_config.py" "$JUPYTERHUB_DIR/jupyterhub_config.py"

if [[ -d "$SDK_DIR/deployment/jupyterhub/theme" ]]; then
    echo "Installing JupyterHub theme..."
    rm -rf "$JUPYTERHUB_DIR/theme"
    cp -r "$SDK_DIR/deployment/jupyterhub/theme" "$JUPYTERHUB_DIR/theme"
fi

echo "Installing JupyterHub static assets..."
sudo mkdir -p "$JUPYTERHUB_VENV_DIR/share/jupyterhub/static/custom"
sudo cp "$SDK_DIR/deployment/jupyterhub/theme/static/custom/"* \
    "$JUPYTERHUB_VENV_DIR/share/jupyterhub/static/custom/"

echo "Installing Robot Car Jupyter kernel..."
python -m pip install ipykernel
python -m ipykernel install \
    --prefix="$JUPYTERHUB_VENV_DIR" \
    --name robot-car \
    --display-name "Robot Car"

echo "Removing default Python 3 Jupyter kernel..."
"$JUPYTERHUB_VENV_DIR/bin/jupyter" kernelspec remove -f python3 || true
"$JUPYTERHUB_VENV_DIR/bin/python" -m pip uninstall -y ipykernel || true
echo "[7/10] Creating media directories..."
mkdir -p \
    "$HOME/media/pictures" \
    "$HOME/media/videos" \
    "$HOME/media/sounds"

echo "Installing starter sound assets..."
cp -n "$SDK_DIR/deployment/assets/sounds/"* "$HOME/media/sounds/" 2>/dev/null || true

echo "[8/10] Checking boot configuration..."
CONFIG_FILE="/boot/firmware/config.txt"

if [[ -f "$CONFIG_FILE" ]]; then
    if ! grep -q "^dtparam=i2c_arm=on" "$CONFIG_FILE"; then
        echo "Adding I2C config..."
        echo "dtparam=i2c_arm=on" | sudo tee -a "$CONFIG_FILE" > /dev/null
    fi

    if ! grep -q "^dtparam=spi=on" "$CONFIG_FILE"; then
        echo "Adding SPI config..."
        echo "dtparam=spi=on" | sudo tee -a "$CONFIG_FILE" > /dev/null
    fi

    if ! grep -q "^dtoverlay=hifiberry-dac" "$CONFIG_FILE"; then
        echo "Adding HifiBerry DAC overlay..."
        echo "dtoverlay=hifiberry-dac" | sudo tee -a "$CONFIG_FILE" > /dev/null
    fi

    if ! grep -q "^dtoverlay=i2s-mmap" "$CONFIG_FILE"; then
        echo "Adding I2S mmap overlay..."
        echo "dtoverlay=i2s-mmap" | sudo tee -a "$CONFIG_FILE" > /dev/null
    fi
else
    echo "WARNING: $CONFIG_FILE not found. Boot config was not updated."
fi

echo "Configuring Wi-Fi fallback AP profile..."
if ! nmcli connection show PiAP >/dev/null 2>&1; then
    sudo nmcli connection add \
        type wifi \
        ifname wlan0 \
        con-name PiAP \
        autoconnect no \
        ssid Betabox

    sudo nmcli connection modify PiAP \
        802-11-wireless.mode ap \
        802-11-wireless.band bg \
        ipv4.method shared \
        ipv6.method ignore
fi

echo "[9/10] Installing systemd services..."
sudo mkdir -p /etc/systemd/system
sudo cp "$SDK_DIR/deployment/systemd/betabox-boot-announce.service" /etc/systemd/system/
sudo cp "$SDK_DIR/deployment/systemd/betabox-monitor.service" /etc/systemd/system/
sudo cp "$SDK_DIR/deployment/systemd/jupyterhub.service" /etc/systemd/system/
sudo cp "$SDK_DIR/deployment/systemd/set-hostname-from-serial.service" /etc/systemd/system/
sudo cp "$SDK_DIR/deployment/systemd/wifi-fallback.service" /etc/systemd/system/
sudo cp "$SDK_DIR/deployment/systemd/betabox-video.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable betabox-boot-announce.service
sudo systemctl enable betabox-monitor.service
sudo systemctl enable jupyterhub.service
sudo systemctl enable set-hostname-from-serial.service
sudo systemctl enable wifi-fallback.service
sudo systemctl enable betabox-video.service

echo "[10/10] Running install check..."
python -m betabox_robotics.services.install_check

echo
echo "======================================"
echo " Install complete"
echo "======================================"
echo
echo "A reboot is required before hardware validation:"
echo "  sudo reboot"
echo
echo "After reboot:"
echo "  source $VENV_DIR/bin/activate"
echo "  betabox verify"
echo "  betabox status"
echo "  betabox services"
echo "  python -m betabox_robotics.examples.robots.betabox_car.basic_robot_demo"
