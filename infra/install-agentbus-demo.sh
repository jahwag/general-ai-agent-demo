#!/usr/bin/env bash
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo 'install-agentbus-demo.sh must run as root' >&2
  exit 1
fi
if [[ $# -ne 2 || ! $2 =~ ^[1-9][0-9]*$ ]]; then
  echo 'usage: install-agentbus-demo.sh AGENTBUS_BIN_DIR TICKET_ID' >&2
  exit 2
fi

bin_dir=$1
ticket_id=$2
app_root=/opt/general-ai-agent
agent_user=gaidemo-copilot
operator_user=gaidemo-operator
human_user=gaidemo-human
bus_user=gaidemo-agentbus

for binary in agentbus agentbusd; do
  if [[ ! -x $bin_dir/$binary ]]; then
    echo "missing executable $bin_dir/$binary" >&2
    exit 2
  fi
  install -m 0755 -o root -g root "$bin_dir/$binary" "/usr/local/bin/$binary"
done

if ! id "$bus_user" >/dev/null 2>&1; then
  useradd --system --home-dir /var/lib/gaidemo-agentbus --create-home \
    --shell /usr/sbin/nologin "$bus_user"
fi
getent group "$human_user" >/dev/null || groupadd --system "$human_user"
if ! id "$human_user" >/dev/null 2>&1; then
  useradd --system --home-dir /var/lib/gaidemo-human --create-home \
    --shell /usr/sbin/nologin --gid "$human_user" "$human_user"
fi
install -d -m 0750 -o "$bus_user" -g "$bus_user" /var/lib/gaidemo-agentbus
install -d -m 0750 -o "$operator_user" -g gaidemo-operators /var/lib/gaidemo-approval
install -d -m 0750 -o "$operator_user" -g gaidemo-operators /var/lib/gaidemo-operator
install -d -m 0750 -o "$human_user" -g "$human_user" /var/lib/gaidemo-human
install -d -m 0700 -o "$agent_user" -g "$agent_user" "/home/$agent_user/.config/agentbus"
install -d -m 0750 -o root -g gaidemo-operators /etc/gaidemo
install -d -m 0750 -o root -g "$human_user" /etc/gaidemo-human
install -d -m 0750 -o root -g "$bus_user" /etc/gaidemo-agentbus

if [[ ! -s /etc/gaidemo-agentbus/admin.token ]]; then
  openssl rand -hex -out /etc/gaidemo-agentbus/admin.token 32
fi
chown "$bus_user":"$bus_user" /etc/gaidemo-agentbus/admin.token
chmod 0600 /etc/gaidemo-agentbus/admin.token

install -m 0755 -o root -g root \
  "$app_root/infra/bin/gaidemo-agentbus-send" \
  /usr/local/bin/gaidemo-agentbus-send
for service in \
  gaidemo-agentbus.service \
  gaidemo-live-cockpit.service \
  gaidemo-agentbus-approval.service; do
  install -m 0644 -o root -g root \
    "$app_root/infra/systemd/$service" "/etc/systemd/system/$service"
done

systemctl daemon-reload
systemctl enable --now gaidemo-agentbus.service

runtime=$(mktemp -d /run/gaidemo-agentbus-install.XXXXXX)
cleanup() {
  if [[ $runtime == /run/gaidemo-agentbus-install.* ]]; then
    rm -rf -- "$runtime"
  fi
}
trap cleanup EXIT HUP INT TERM

mint_if_missing() {
  local name=$1
  local target=$2
  local owner=$3
  local group=$4
  if [[ -s $target ]]; then
    return
  fi
  /usr/local/bin/agentbus mint \
    --server http://127.0.0.1:7777 \
    --admin-token-file /etc/gaidemo-agentbus/admin.token \
    --name "$name" \
    --token-out "$runtime/$name.token" \
    >/dev/null
  install -m 0600 -o "$owner" -g "$group" "$runtime/$name.token" "$target"
}

mint_if_missing cora "/home/$agent_user/.config/agentbus/token" "$agent_user" "$agent_user"
mint_if_missing approval-gateway /var/lib/gaidemo-operator/agentbus-gateway.token \
  "$operator_user" gaidemo-operators
mint_if_missing human-approval-bridge /var/lib/gaidemo-human/agentbus.token \
  "$human_user" "$human_user"

config_tmp=$runtime/approval.env
printf '%s\n' \
  'AGENTBUS_SERVER=http://127.0.0.1:7777' \
  'AGENTBUS_GATEWAY_TOKEN_FILE=/var/lib/gaidemo-operator/agentbus-gateway.token' \
  "DEMO_TICKET_ID=$ticket_id" \
  'GAIDEMO_PROPOSAL_PATH=/home/gaidemo-copilot/gaidemo/artifacts/proposal.json' \
  'GAIDEMO_APPROVAL_STATE_DIR=/var/lib/gaidemo-approval' \
  >"$config_tmp"
install -m 0640 -o root -g gaidemo-operators "$config_tmp" /etc/gaidemo/agentbus.env

config_tmp=$runtime/cockpit.env
printf '%s\n' \
  'AGENTBUS_SERVER=http://127.0.0.1:7777' \
  'AGENTBUS_HUMAN_TOKEN_FILE=/var/lib/gaidemo-human/agentbus.token' \
  "DEMO_TICKET_ID=$ticket_id" \
  'GAIDEMO_COCKPIT_HTML=/opt/general-ai-agent/democtl/live_cockpit.html' \
  >"$config_tmp"
install -m 0640 -o root -g "$human_user" "$config_tmp" /etc/gaidemo-human/cockpit.env

if grep -q '^DEMO_TICKET_ID=' /etc/gaidemo/freshworks.env; then
  sed -i -E "s/^DEMO_TICKET_ID=.*/DEMO_TICKET_ID=$ticket_id/" /etc/gaidemo/freshworks.env
else
  echo 'freshworks.env lacks DEMO_TICKET_ID' >&2
  exit 2
fi

systemctl restart gaidemo-freshworks-read.service
systemctl enable gaidemo-live-cockpit.service gaidemo-agentbus-approval.service
systemctl restart gaidemo-live-cockpit.service gaidemo-agentbus-approval.service
