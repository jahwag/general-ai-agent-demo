#!/usr/bin/env bash
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "install-bookstack-demo.sh must run as root" >&2
  exit 1
fi

app_root=/opt/general-ai-agent
stack_root=/etc/gaidemo-bookstack
stack_env="$stack_root/compose.env"
stack_compose="$stack_root/compose.yaml"

if [[ ! -f $app_root/infra/bookstack/compose.yaml ]]; then
  echo "BookStack compose file is missing from $app_root" >&2
  exit 2
fi

if ! command -v docker >/dev/null 2>&1; then
  apt-get update
  apt-get install -y --no-install-recommends docker.io docker-compose-v2
  apt-get clean
fi

systemctl enable --now docker.service
install -d -m 0750 -o root -g root "$stack_root"
install -m 0644 -o root -g root \
  "$app_root/infra/bookstack/compose.yaml" \
  "$stack_compose"

if [[ ! -s $stack_env ]]; then
  bookstack_app_key="base64:$(openssl rand -base64 32)"
  bookstack_db_password="$(openssl rand -hex 24)"
  bookstack_db_root_password="$(openssl rand -hex 24)"
  stack_tmp="$(mktemp /run/gaidemo-bookstack-env.XXXXXX)"
  cleanup() {
    if [[ $stack_tmp == /run/gaidemo-bookstack-env.* ]]; then
      rm -f -- "$stack_tmp"
    fi
  }
  trap cleanup EXIT HUP INT TERM
  {
    printf 'BOOKSTACK_APP_URL=http://127.0.0.1:6875\n'
    printf 'BOOKSTACK_APP_KEY=%s\n' "$bookstack_app_key"
    printf 'BOOKSTACK_DB_PASSWORD=%s\n' "$bookstack_db_password"
    printf 'BOOKSTACK_DB_ROOT_PASSWORD=%s\n' "$bookstack_db_root_password"
  } >"$stack_tmp"
  install -m 0600 -o root -g root "$stack_tmp" "$stack_env"
fi

docker compose \
  --env-file "$stack_env" \
  --file "$stack_compose" \
  pull
docker compose \
  --env-file "$stack_env" \
  --file "$stack_compose" \
  up --detach

for _bookstack_attempt in $(seq 1 60); do
  if curl --fail --silent --show-error \
    http://127.0.0.1:6875/status >/dev/null 2>&1; then
    exit 0
  fi
  sleep 2
done

echo "BookStack did not become healthy within 120 seconds" >&2
docker compose \
  --env-file "$stack_env" \
  --file "$stack_compose" \
  ps >&2
exit 1
