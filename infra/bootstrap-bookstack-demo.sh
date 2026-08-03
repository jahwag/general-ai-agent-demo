#!/usr/bin/env bash
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "bootstrap-bookstack-demo.sh must run as root" >&2
  exit 1
fi

app_root=/opt/general-ai-agent
stack_root=/etc/gaidemo-bookstack
stack_env="$stack_root/compose.env"
stack_compose="$stack_root/compose.yaml"
admin_password_file="$stack_root/admin-password"
knowledge_env=/etc/gaidemo-knowledge/bookstack.env
seed_result=/var/lib/gaidemo-knowledge/seed-result.json
bootstrap_env="$(mktemp /run/gaidemo-bookstack-bootstrap.XXXXXX)"
bootstrap_token_id="$(openssl rand -hex 16)"
bootstrap_token_secret="$(openssl rand -hex 16)"

compose() {
  docker compose --env-file "$stack_env" --file "$stack_compose" "$@"
}

database_sql() {
  compose exec -T database sh -c \
    'exec mariadb -uroot -p"$MARIADB_ROOT_PASSWORD" bookstackapp'
}

cleanup() {
  if [[ -n ${bootstrap_token_id:-} ]]; then
    printf "DELETE FROM api_tokens WHERE token_id='%s';\n" \
      "$bootstrap_token_id" | database_sql >/dev/null 2>&1 || true
  fi
  if [[ $bootstrap_env == /run/gaidemo-bookstack-bootstrap.* ]]; then
    rm -f -- "$bootstrap_env"
  fi
}
trap cleanup EXIT HUP INT TERM

if [[ ! -s $stack_env || ! -s $stack_compose ]]; then
  echo "BookStack stack is not installed" >&2
  exit 2
fi
if [[ ! -d /etc/gaidemo-knowledge ]]; then
  echo "BookStack connector is not installed" >&2
  exit 2
fi

if [[ ! -s $admin_password_file ]]; then
  admin_password="$(openssl rand -base64 24 | tr -d '\n')"
  printf '%s\n' "$admin_password" | \
    install -m 0600 -o root -g root /dev/stdin "$admin_password_file"
fi

bootstrap_hash="$(
  printf '%s' "$bootstrap_token_secret" | \
    compose exec -T bookstack php -r \
      'echo password_hash(trim(stream_get_contents(STDIN)), PASSWORD_DEFAULT);'
)"
bootstrap_hash_base64="$(printf '%s' "$bootstrap_hash" | base64 -w0)"
printf \
  "INSERT INTO api_tokens (name, token_id, secret, user_id, expires_at, created_at, updated_at) VALUES ('Temporary demo bootstrap', '%s', FROM_BASE64('%s'), 1, DATE_ADD(CURDATE(), INTERVAL 1 DAY), NOW(), NOW());\n" \
  "$bootstrap_token_id" "$bootstrap_hash_base64" | database_sql

{
  printf 'BOOKSTACK_BASE_URL=http://127.0.0.1:6875\n'
  printf 'BOOKSTACK_TOKEN_ID=%s\n' "$bootstrap_token_id"
  printf 'BOOKSTACK_TOKEN_SECRET=%s\n' "$bootstrap_token_secret"
} >"$bootstrap_env"
chmod 0600 "$bootstrap_env"

set -a
# shellcheck source=/dev/null
source "$bootstrap_env"
set +a
install -d -m 0750 -o gaidemo-knowledge -g gaidemo-knowledge-secrets \
  /var/lib/gaidemo-knowledge
/opt/general-ai-agent/.venv/bin/python -I -m democtl.bookstack_seed \
  --manifest "$app_root/fixtures/bookstack/manifest.json" \
  --kb-dir "$app_root/fixtures/kb" \
  --admin-password-file "$admin_password_file" \
  --output "$seed_result"
chown gaidemo-knowledge:gaidemo-knowledge-secrets "$seed_result"
chmod 0640 "$seed_result"

reader_user_id="$(jq -er '.reader_user_id' "$seed_result")"
if [[ ! $reader_user_id =~ ^[1-9][0-9]*$ ]]; then
  echo "BookStack seed did not return a valid reader user ID" >&2
  exit 2
fi
reader_token_id="$(openssl rand -hex 16)"
reader_token_secret="$(openssl rand -hex 16)"
reader_hash="$(
  printf '%s' "$reader_token_secret" | \
    compose exec -T bookstack php -r \
      'echo password_hash(trim(stream_get_contents(STDIN)), PASSWORD_DEFAULT);'
)"
reader_hash_base64="$(printf '%s' "$reader_hash" | base64 -w0)"
printf \
  "DELETE FROM api_tokens WHERE user_id=%s AND name='Cora demo connector'; INSERT INTO api_tokens (name, token_id, secret, user_id, expires_at, created_at, updated_at) VALUES ('Cora demo connector', '%s', FROM_BASE64('%s'), %s, DATE_ADD(CURDATE(), INTERVAL 1 YEAR), NOW(), NOW());\n" \
  "$reader_user_id" "$reader_token_id" "$reader_hash_base64" \
  "$reader_user_id" | database_sql

knowledge_tmp="$(mktemp /run/gaidemo-bookstack-reader.XXXXXX)"
{
  printf 'KNOWLEDGE_SOURCE=bookstack\n'
  printf 'BOOKSTACK_BASE_URL=http://127.0.0.1:6875\n'
  printf 'BOOKSTACK_TOKEN_ID=%s\n' "$reader_token_id"
  printf 'BOOKSTACK_TOKEN_SECRET=%s\n' "$reader_token_secret"
} >"$knowledge_tmp"
install -m 0640 -o root -g gaidemo-knowledge-secrets \
  "$knowledge_tmp" "$knowledge_env"
rm -f -- "$knowledge_tmp"

systemctl enable gaidemo-bookstack-read.service
systemctl restart gaidemo-bookstack-read.service
