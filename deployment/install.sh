#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SDK_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LIB_DIR="/opt/libs"
BETABOX_DIR="/opt/betabox"
VENV_DIR="$BETABOX_DIR/venv"

JUPYTERHUB_DIR="/opt/jupyterhub"
JUPYTERHUB_VENV_DIR="$JUPYTERHUB_DIR/venv"

SUDOERS_SOURCE="$SDK_DIR/deployment/sudoers/betabox-guest"
SUDOERS_TARGET="/etc/sudoers.d/betabox-guest"

STUDENT_ACCOUNTS=(
    student
    student1
    student2
    student3
)

STUDENT_PASSWORD="learnbydoing"

provision_student_accounts() {
    echo "Provisioning student accounts..."

    local username
    local home
    local group

    for username in "${STUDENT_ACCOUNTS[@]}"; do
        home="/home/$username"

        if id "$username" >/dev/null 2>&1; then
            echo "Student account already exists: $username"
        else
            echo "Creating student account: $username"

            sudo useradd \
                --create-home \
                --shell /bin/bash \
                --user-group \
                "$username"
        fi

        echo "${username}:${STUDENT_PASSWORD}" \
            | sudo chpasswd

        # Disable password expiration for classroom accounts.
        sudo chage \
            --maxdays -1 \
            "$username"

        group="$(id -gn "$username")"

        sudo usermod \
            -aG "$group" \
            "$USER"

        sudo install \
            -d \
            -o "$username" \
            -g "$group" \
            -m 2770 \
            "$home" \
            "$home/curriculum" \
            "$home/media" \
            "$home/media/pictures" \
            "$home/media/videos" \
            "$home/media/sounds" \
            "$home/preferences"
    done
}

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

provision_student_accounts

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

echo "[9/11] Installing Betabox privilege policy..."

if [[ ! -f "$SUDOERS_SOURCE" ]]; then
    echo "ERROR: Missing sudoers policy:"
    echo "  $SUDOERS_SOURCE"
    exit 1
fi

if ! sudo visudo \
    --check \
    --file="$SUDOERS_SOURCE"
then
    echo "ERROR: Invalid Betabox sudoers policy."
    exit 1
fi

sudo install \
    -o root \
    -g root \
    -m 0440 \
    "$SUDOERS_SOURCE" \
    "$SUDOERS_TARGET"

if ! sudo visudo \
    --check \
    --file="$SUDOERS_TARGET"
then
    echo "ERROR: Installed sudoers policy is invalid."
    sudo rm -f "$SUDOERS_TARGET"
    exit 1
fi

echo "[10/11] Installing systemd services..."

SYSTEMD_SOURCE="$SDK_DIR/deployment/systemd"
SYSTEMD_TARGET="/etc/systemd/system"

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

echo "Reloading systemd..."
sudo systemctl daemon-reload

for service in "${SERVICES[@]}"; do
    echo "Enabling $service..."

    sudo systemctl enable "$service"
done

echo "[11/11] Running install check..."
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
echo
echo "Launchpad:"
echo "  http://$(hostname).local:8088"
echo "  http://$(hostname -I | awk '{print $1}'):8088"
echo
echo "Robot API example:"
echo "  python -m betabox_robotics.examples.robots.betabox_car.basic_robot_demo"
