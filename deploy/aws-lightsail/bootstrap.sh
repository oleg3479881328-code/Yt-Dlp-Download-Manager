#!/usr/bin/env bash
set -euo pipefail

exec > >(tee -a /var/log/video-review-portal-bootstrap.log) 2>&1

REPOSITORY_URL="__REPOSITORY_URL__"
REPOSITORY_BRANCH="__REPOSITORY_BRANCH__"
REVIEW_TOKEN="__REVIEW_TOKEN__"
ADMIN_TOKEN="__ADMIN_TOKEN__"
APP_ROOT="/opt/video-review-portal"
RUNTIME_ROOT="/srv/video-review-portal"
APP_USER="video-review"

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y git nginx python3 python3-venv python3-pip rsync

if ! id "$APP_USER" >/dev/null 2>&1; then
  useradd --system --home "$RUNTIME_ROOT" --shell /usr/sbin/nologin "$APP_USER"
fi

rm -rf "$APP_ROOT"
git clone --branch "$REPOSITORY_BRANCH" --single-branch "$REPOSITORY_URL" "$APP_ROOT"
python3 -m venv "$APP_ROOT/.venv"
"$APP_ROOT/.venv/bin/pip" install --upgrade pip
"$APP_ROOT/.venv/bin/pip" install -r "$APP_ROOT/review_portal/requirements.txt"

mkdir -p "$RUNTIME_ROOT/media" "$RUNTIME_ROOT/data"
chown -R "$APP_USER:$APP_USER" "$RUNTIME_ROOT"
chown -R root:root "$APP_ROOT"

cat > /etc/video-review-portal.env <<EOF
REVIEW_PORTAL_MEDIA_DIR=$RUNTIME_ROOT/media
REVIEW_PORTAL_DATA_DIR=$RUNTIME_ROOT/data
REVIEW_PORTAL_TOKEN=$REVIEW_TOKEN
REVIEW_PORTAL_ADMIN_TOKEN=$ADMIN_TOKEN
EOF
chmod 600 /etc/video-review-portal.env

cat > /etc/systemd/system/video-review-portal.service <<EOF
[Unit]
Description=VIDEO MIX Review Portal
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_ROOT
EnvironmentFile=/etc/video-review-portal.env
ExecStart=$APP_ROOT/.venv/bin/python -m uvicorn review_portal.app:app --host 127.0.0.1 --port 8770 --proxy-headers --forwarded-allow-ips=127.0.0.1
Restart=always
RestartSec=3
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=$RUNTIME_ROOT

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/nginx/sites-available/video-review-portal <<'EOF'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;

    client_max_body_size 20m;

    location / {
        proxy_pass http://127.0.0.1:8770;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Range $http_range;
        proxy_set_header If-Range $http_if_range;
        proxy_buffering off;
        add_header Cache-Control "no-store" always;
    }
}
EOF

rm -f /etc/nginx/sites-enabled/default
ln -sfn /etc/nginx/sites-available/video-review-portal /etc/nginx/sites-enabled/video-review-portal
nginx -t
systemctl daemon-reload
systemctl enable --now video-review-portal
systemctl enable --now nginx

for attempt in $(seq 1 30); do
  if curl --fail --silent http://127.0.0.1/health >/dev/null; then
    echo "VIDEO MIX Review Portal is healthy."
    exit 0
  fi
  sleep 2
done

echo "Portal health check failed."
systemctl status video-review-portal --no-pager || true
journalctl -u video-review-portal --no-pager -n 100 || true
exit 1
