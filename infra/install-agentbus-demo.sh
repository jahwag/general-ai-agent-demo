#!/usr/bin/env bash
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo 'install-agentbus-demo.sh must run as root' >&2
  exit 1
fi
if [[ $# -ne 3 || ! $2 =~ ^[1-9][0-9]*$ || ! $3 =~ ^[1-9][0-9]*$ ]]; then
  echo 'usage: install-agentbus-demo.sh AGENTBUS_BIN_DIR TICKET_ID OPERATOR_ID' >&2
  exit 2
fi

bin_dir=$1
ticket_id=$2
operator_id=$3
app_root=/opt/general-ai-agent
agent_user=gaidemo-copilot
operator_user=gaidemo-operator
human_user=gaidemo-human
approver_user=gaidemo-approver
bus_user=gaidemo-agentbus
proposal_group=gaidemo-proposals
proposal_root="/home/$agent_user/gaidemo"
proposal_dir="$proposal_root/artifacts"
proposal_path="$proposal_dir/proposal.json"

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
usermod --append --groups gaidemo-readers "$human_user"
getent group "$proposal_group" >/dev/null || groupadd --system "$proposal_group"
usermod --append --groups "$proposal_group" "$agent_user"
usermod --append --groups "$proposal_group" "$operator_user"
if [[ ! -d $proposal_root ]]; then
  echo "missing Clem project directory $proposal_root" >&2
  exit 2
fi
chgrp "$proposal_group" "/home/$agent_user" "$proposal_root"
chmod 0710 "/home/$agent_user" "$proposal_root"
install -d -m 2710 -o "$agent_user" -g "$proposal_group" "$proposal_dir"
if [[ -f $proposal_path ]]; then
  chgrp "$proposal_group" "$proposal_path"
  chmod 0640 "$proposal_path"
fi
getent group "$approver_user" >/dev/null || groupadd --system "$approver_user"
if ! id "$approver_user" >/dev/null 2>&1; then
  useradd --system --home-dir /var/lib/gaidemo-approver --create-home \
    --shell /usr/sbin/nologin --gid "$approver_user" "$approver_user"
fi
usermod --append --groups "gaidemo-readers,$human_user" "$approver_user"
install -d -m 0750 -o "$bus_user" -g "$bus_user" /var/lib/gaidemo-agentbus
install -d -m 0750 -o "$operator_user" -g gaidemo-operators /var/lib/gaidemo-approval
install -d -m 0750 -o "$operator_user" -g gaidemo-operators /var/lib/gaidemo-operator
install -d -m 0750 -o "$human_user" -g "$human_user" /var/lib/gaidemo-human
install -d -m 0750 -o "$approver_user" -g "$approver_user" /var/lib/gaidemo-approver
install -d -m 0700 -o "$agent_user" -g "$agent_user" "/home/$agent_user/.config/agentbus"
install -d -m 0750 -o root -g gaidemo-operators /etc/gaidemo
install -d -m 0750 -o root -g "$human_user" /etc/gaidemo-human
install -d -m 0750 -o root -g "$approver_user" /etc/gaidemo-approver
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
  gaidemo-freshservice-approval.service \
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
mint_if_missing freshservice-approval-bridge \
  /var/lib/gaidemo-approver/agentbus.token \
  "$approver_user" "$approver_user"

config_tmp=$runtime/approval.env
printf '%s\n' \
  'AGENTBUS_SERVER=http://127.0.0.1:7777' \
  'AGENTBUS_GATEWAY_TOKEN_FILE=/var/lib/gaidemo-operator/agentbus-gateway.token' \
  "DEMO_TICKET_ID=$ticket_id" \
  "DEMO_OPERATOR_ID=$operator_id" \
  "GAIDEMO_PROPOSAL_PATH=$proposal_path" \
  'GAIDEMO_APPROVAL_STATE_DIR=/var/lib/gaidemo-approval' \
  >"$config_tmp"
install -m 0640 -o root -g gaidemo-operators "$config_tmp" /etc/gaidemo/agentbus.env

config_tmp=$runtime/cockpit.env
printf '%s\n' \
  'AGENTBUS_SERVER=http://127.0.0.1:7777' \
  'AGENTBUS_HUMAN_TOKEN_FILE=/var/lib/gaidemo-human/agentbus.token' \
  "DEMO_TICKET_ID=$ticket_id" \
  'GAIDEMO_HUMAN_STATE_DIR=/var/lib/gaidemo-human' \
  'GAIDEMO_COCKPIT_HTML=/opt/general-ai-agent/democtl/live_cockpit.html' \
  >"$config_tmp"
install -m 0640 -o root -g "$human_user" "$config_tmp" /etc/gaidemo-human/cockpit.env

config_tmp=$runtime/native-approval.env
printf '%s\n' \
  'AGENTBUS_SERVER=http://127.0.0.1:7777' \
  'AGENTBUS_NATIVE_APPROVAL_TOKEN_FILE=/var/lib/gaidemo-approver/agentbus.token' \
  "DEMO_TICKET_ID=$ticket_id" \
  "DEMO_OPERATOR_ID=$operator_id" \
  'GAIDEMO_PROPOSAL_DESCRIPTOR_PATH=/var/lib/gaidemo-human/current-proposal.json' \
  'GAIDEMO_NATIVE_APPROVAL_STATE_DIR=/var/lib/gaidemo-approver' \
  >"$config_tmp"
install -m 0640 -o root -g "$approver_user" "$config_tmp" \
  /etc/gaidemo-approver/approval.env

if grep -q '^DEMO_TICKET_ID=' /etc/gaidemo/freshworks.env; then
  sed -i -E "s/^DEMO_TICKET_ID=.*/DEMO_TICKET_ID=$ticket_id/" /etc/gaidemo/freshworks.env
else
  echo 'freshworks.env lacks DEMO_TICKET_ID' >&2
  exit 2
fi

systemctl restart gaidemo-freshworks-read.service
systemctl enable gaidemo-live-cockpit.service gaidemo-freshservice-approval.service \
  gaidemo-agentbus-approval.service
systemctl restart gaidemo-live-cockpit.service gaidemo-freshservice-approval.service \
  gaidemo-agentbus-approval.service
