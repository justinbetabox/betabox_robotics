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

echo "[1/11] Installing system packages..."
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

echo "[2/11] Creating directories..."
sudo mkdir -p "$LIB_DIR" "$BETABOX_DIR"
sudo chown -R "$USER:$USER" "$LIB_DIR" "$BETABOX_DIR"

echo "[3/11] Creating Python virtual environment..."
if [[ ! -d "$VENV_DIR" ]]; then
    python3 -m venv --system-site-packages "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

echo "[4/11] Installing Python dependencies..."
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
    aiohttp-jinja2 \
    aiortc \
    pamela \
    smbus2 \
    gpiozero

echo "[5/11] Installing Betabox Robotics SDK..."
python -m pip install -e "$SDK_DIR" --no-deps

echo "[6/11] Installing JupyterHub..."
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
echo "[7/11] Provisioning platform..."

cd "$SDK_DIR"

sudo "$VENV_DIR/bin/python" \
    -m deployment.provision \
    --service-user "$USER"

echo "[8/11] Checking boot configuration..."
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

echo "Ensuring Wi-Fi radio is enabled..."

if command -v rfkill >/dev/null 2>&1; then
    sudo rfkill unblock wifi
fi

sudo nmcli radio wifi on

if [[ "$(nmcli -t -f WIFI general 2>/dev/null)" != "enabled" ]]; then
    echo "ERROR: Unable to enable the Wi-Fi radio." >&2
    exit 1
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

echo "[9/11] Installing Betabox privilege policies..."

SUDOERS_DIR="$SDK_DIR/deployment/sudoers"

if [[ ! -d "$SUDOERS_DIR" ]]; then
    echo "ERROR: Missing sudoers policy directory:"
    echo "  $SUDOERS_DIR"
    exit 1
fi

shopt -s nullglob
SUDOERS_POLICIES=("$SUDOERS_DIR"/*)
shopt -u nullglob

if [[ "${#SUDOERS_POLICIES[@]}" -eq 0 ]]; then
    echo "ERROR: No sudoers policies found in:"
    echo "  $SUDOERS_DIR"
    exit 1
fi

for policy in "${SUDOERS_POLICIES[@]}"; do
    if [[ ! -f "$policy" ]]; then
        continue
    fi

    name="$(basename "$policy")"
    target="/etc/sudoers.d/$name"

    echo "Validating sudoers policy: $name"

    if ! sudo visudo --check --file="$policy"; then
        echo "ERROR: Invalid sudoers policy:"
        echo "  $policy"
        exit 1
    fi

    echo "Installing sudoers policy: $name"

    sudo install \
        -o root \
        -g root \
        -m 0440 \
        "$policy" \
        "$target"

    if ! sudo visudo --check --file="$target"; then
        echo "ERROR: Installed sudoers policy is invalid:"
        echo "  $target"
        sudo rm -f "$target"
        exit 1
    fi
done

echo "[10/11] Installing systemd services..."

SYSTEMD_SOURCE="$SDK_DIR/deployment/systemd"
SYSTEMD_TARGET="/etc/systemd/system"

AVAHI_OVERRIDE_SOURCE="$SYSTEMD_SOURCE/avahi-daemon.service.d/override.conf"
AVAHI_OVERRIDE_DIR="$SYSTEMD_TARGET/avahi-daemon.service.d"
AVAHI_OVERRIDE_TARGET="$AVAHI_OVERRIDE_DIR/override.conf"

SERVICES=(
    betabox-boot-announce.service
    betabox-monitor.service
    jupyterhub.service
    set-hostname-from-serial.service
    wifi-fallback.service
    betabox-video.service
    betabox-guest-reset.service
    betabox-launchpad.service
)

sudo mkdir -p "$SYSTEMD_TARGET"

for service in "${SERVICES[@]}"; do
    echo "Installing $service..."

    sudo install \
        -m 0644 \
        "$SYSTEMD_SOURCE/$service" \
        "$SYSTEMD_TARGET/$service"
done

echo "Installing Avahi startup-order override..."

if [[ ! -f "$AVAHI_OVERRIDE_SOURCE" ]]; then
    echo "ERROR: Missing Avahi systemd override:"
    echo "  $AVAHI_OVERRIDE_SOURCE"
    exit 1
fi

sudo install \
    -d \
    -o root \
    -g root \
    -m 0755 \
    "$AVAHI_OVERRIDE_DIR"

sudo install \
    -o root \
    -g root \
    -m 0644 \
    "$AVAHI_OVERRIDE_SOURCE" \
    "$AVAHI_OVERRIDE_TARGET"

echo "Reloading systemd..."
sudo systemctl daemon-reload

for service in "${SERVICES[@]}"; do
    echo "Enabling $service..."

    sudo systemctl enable "$service"
done

echo "[11/11] Running install check..."
sudo "$VENV_DIR/bin/betabox" \
    install-check \
    --service-user "$USER"

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
echo
echo "Launchpad:"
echo "  http://$(hostname).local:8088"
echo "  http://$(hostname -I | awk '{print $1}'):8088"
echo
echo "Robot API example:"
echo "  python -m betabox_robotics.examples.robots.betabox_car.basic_robot_demo"
