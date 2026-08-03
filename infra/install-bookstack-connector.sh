#!/usr/bin/env bash
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "install-bookstack-connector.sh must run as root" >&2
  exit 1
fi

app_root=/opt/general-ai-agent
agent_user=gaidemo-copilot
operator_user=gaidemo-operator
knowledge_user=gaidemo-knowledge
reader_group=gaidemo-readers
secret_group=gaidemo-knowledge-secrets

for required_user in "$agent_user" "$operator_user"; do
  if ! id "$required_user" >/dev/null 2>&1; then
    echo "missing $required_user; install the demo runtime first" >&2
    exit 2
  fi
done

getent group "$reader_group" >/dev/null || groupadd --system "$reader_group"
getent group "$secret_group" >/dev/null || groupadd --system "$secret_group"
if ! id "$knowledge_user" >/dev/null 2>&1; then
  useradd \
    --system \
    --home-dir /var/lib/gaidemo-knowledge \
    --create-home \
    --shell /usr/sbin/nologin \
    --gid "$secret_group" \
    "$knowledge_user"
fi
usermod --append --groups "$reader_group" "$agent_user"
usermod --append --groups "$reader_group,$secret_group" "$knowledge_user"
usermod --append --groups "$secret_group" "$operator_user"

install -m 0755 -o root -g root \
  "$app_root/infra/bin/gaidemo-kb-search" \
  /usr/local/bin/gaidemo-kb-search
install -m 0755 -o root -g root \
  "$app_root/infra/bin/gaidemo-kb-read" \
  /usr/local/bin/gaidemo-kb-read
install -m 0755 -o root -g root \
  "$app_root/infra/bin/gaidemo-proposal-validate" \
  /usr/local/bin/gaidemo-proposal-validate
install -m 0755 -o root -g root \
  "$app_root/infra/bin/gaidemo-proposal-apply" \
  /usr/local/bin/gaidemo-proposal-apply
install -m 0644 -o root -g root \
  "$app_root/infra/systemd/gaidemo-bookstack-read.service" \
  /etc/systemd/system/gaidemo-bookstack-read.service

install -d -m 0750 -o root -g "$secret_group" /etc/gaidemo-knowledge
if [[ ! -e /etc/gaidemo-knowledge/bookstack.env ]]; then
  install -m 0640 -o root -g "$secret_group" \
    /dev/null /etc/gaidemo-knowledge/bookstack.env
fi
chown root:"$secret_group" /etc/gaidemo-knowledge/bookstack.env
chmod 0640 /etc/gaidemo-knowledge/bookstack.env

systemctl daemon-reload
if systemctl is-active --quiet gaidemo-agentbus-approval.service; then
  systemctl restart gaidemo-agentbus-approval.service
fi
