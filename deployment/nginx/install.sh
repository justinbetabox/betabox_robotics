
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SOURCE="$SCRIPT_DIR/betabox.conf"
AVAILABLE="/etc/nginx/sites-available/betabox"
ENABLED="/etc/nginx/sites-enabled/betabox"
DEFAULT="/etc/nginx/sites-enabled/default"

if [[ ! -f "$SOURCE" ]]; then
    echo "ERROR: Missing Betabox Nginx configuration." >&2
    exit 1
fi

if ! command -v nginx >/dev/null 2>&1; then
    echo "ERROR: Nginx is not installed." >&2
    exit 1
fi

# Run the helper with sudo so backup and restore operations
# have consistent permissions.
if [[ "$EUID" -ne 0 ]]; then
    echo "ERROR: Run this script as root." >&2
    exit 1
fi

BACKUP_DIR="$(mktemp -d)"
COMMITTED=false

cleanup() {
    if [[ "$COMMITTED" != true ]]; then
        echo "Restoring previous Nginx configuration..."

        rm -f "$ENABLED" "$DEFAULT"

        rm -f "$AVAILABLE"

        if [[ -e "$BACKUP_DIR/available" || -L "$BACKUP_DIR/available" ]]; then
            cp -a "$BACKUP_DIR/available" "$AVAILABLE"
        fi

        if [[ -L "$BACKUP_DIR/enabled" || -e "$BACKUP_DIR/enabled" ]]; then
            cp -a "$BACKUP_DIR/enabled" "$ENABLED"
        fi

        if [[ -L "$BACKUP_DIR/default" || -e "$BACKUP_DIR/default" ]]; then
            cp -a "$BACKUP_DIR/default" "$DEFAULT"
        fi

        nginx -t || true
        systemctl reload-or-restart nginx || true
    fi

    rm -rf "$BACKUP_DIR"
}

# Record the original state before changing anything.
if [[ -e "$AVAILABLE" || -L "$AVAILABLE" ]]; then
    cp -a "$AVAILABLE" "$BACKUP_DIR/available"
fi

if [[ -L "$ENABLED" || -e "$ENABLED" ]]; then
    cp -a "$ENABLED" "$BACKUP_DIR/enabled"
fi

if [[ -L "$DEFAULT" || -e "$DEFAULT" ]]; then
    cp -a "$DEFAULT" "$BACKUP_DIR/default"
fi

trap cleanup EXIT

echo "Installing Betabox Nginx configuration..."

install -o root -g root -m 0644 "$SOURCE" "$AVAILABLE"

rm -f "$ENABLED" "$DEFAULT"
ln -s "$AVAILABLE" "$ENABLED"

echo "Validating Nginx configuration..."
nginx -t

echo "Activating Nginx..."
systemctl enable nginx
systemctl reload-or-restart nginx

COMMITTED=true

echo "Betabox Nginx configuration installed successfully."
