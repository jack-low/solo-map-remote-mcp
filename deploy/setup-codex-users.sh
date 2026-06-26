#!/usr/bin/env bash
set -euo pipefail

APP_OPS_USER="${APP_OPS_USER:-appops}"
APP_INFRA_USER="${APP_INFRA_USER:-appinfra}"
SOURCE_AUTHORIZED_KEYS="${SOURCE_AUTHORIZED_KEYS:-$HOME/.ssh/authorized_keys}"
SUDOERS_FILE="/etc/sudoers.d/90-${APP_INFRA_USER}"

for user in "$APP_OPS_USER" "$APP_INFRA_USER"; do
  if ! id "$user" >/dev/null 2>&1; then
    useradd -m -s /bin/bash "$user"
  fi
  passwd -l "$user" >/dev/null || true
  install -d -m 700 -o "$user" -g "$user" "/home/$user/.ssh"
  if [ -f "$SOURCE_AUTHORIZED_KEYS" ]; then
    install -m 600 -o "$user" -g "$user" "$SOURCE_AUTHORIZED_KEYS" "/home/$user/.ssh/authorized_keys"
  fi
  install -d -m 755 -o "$user" -g "$user" "/home/$user/work"
done

usermod -aG sudo "$APP_INFRA_USER"
cat > "$SUDOERS_FILE" <<EOF
Defaults:${APP_INFRA_USER} !requiretty
${APP_INFRA_USER} ALL=(root) NOPASSWD: /usr/bin/systemctl, /usr/sbin/nginx, /usr/bin/certbot, /usr/bin/cp, /usr/bin/ln, /usr/bin/install, /usr/bin/mkdir, /usr/bin/chown, /usr/bin/chmod, /usr/bin/tee, /usr/bin/loginctl, /usr/bin/apt, /usr/bin/apt-get, /usr/sbin/service
EOF
chmod 440 "$SUDOERS_FILE"
visudo -cf "$SUDOERS_FILE"

id "$APP_OPS_USER"
id "$APP_INFRA_USER"
