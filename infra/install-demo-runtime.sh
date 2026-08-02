#!/usr/bin/env bash
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "install-demo-runtime.sh must run as root" >&2
  exit 1
fi

app_root=/opt/general-ai-agent
agent_user=gaidemo-copilot
operator_user=gaidemo-operator
reader_group=gaidemo-readers
operator_group=gaidemo-operators

if ! id "$agent_user" >/dev/null 2>&1; then
  echo "missing $agent_user; run clem provision first" >&2
  exit 1
fi

getent group "$reader_group" >/dev/null || groupadd --system "$reader_group"
getent group "$operator_group" >/dev/null || groupadd --system "$operator_group"
if ! id "$operator_user" >/dev/null 2>&1; then
  useradd \
    --system \
    --home-dir /var/lib/gaidemo-operator \
    --create-home \
    --shell /usr/sbin/nologin \
    --gid "$operator_group" \
    "$operator_user"
fi
usermod --append --groups "$reader_group" "$agent_user"
usermod --gid "$operator_group" --append --groups "$reader_group" "$operator_user"

install -d -m 0755 -o root -g root "$app_root"
python3 -m venv "$app_root/.venv"
"$app_root/.venv/bin/pip" install \
  --disable-pip-version-check \
  "setuptools>=68"
"$app_root/.venv/bin/pip" install \
  --disable-pip-version-check \
  --no-build-isolation \
  --no-deps \
  "$app_root"

install -m 0755 -o root -g root \
  "$app_root/infra/bin/gaidemo-ticket-read" \
  /usr/local/bin/gaidemo-ticket-read
install -m 0755 -o root -g root \
  "$app_root/infra/bin/gaidemo-ticket-seed" \
  /usr/local/bin/gaidemo-ticket-seed
install -m 0755 -o root -g root \
  "$app_root/infra/bin/gaidemo-proposal-apply" \
  /usr/local/bin/gaidemo-proposal-apply
install -m 0644 -o root -g root \
  "$app_root/infra/systemd/gaidemo-freshworks-read.service" \
  /etc/systemd/system/gaidemo-freshworks-read.service

install -d -m 0750 -o root -g "$operator_group" /etc/gaidemo
if [[ ! -e /etc/gaidemo/freshworks.env ]]; then
  install -m 0640 -o root -g "$operator_group" /dev/null /etc/gaidemo/freshworks.env
fi
chown root:"$operator_group" /etc/gaidemo/freshworks.env
chmod 0640 /etc/gaidemo/freshworks.env

chown -R root:root "$app_root"
chmod -R u=rwX,go=rX "$app_root"
systemctl daemon-reload
systemctl enable gaidemo-freshworks-read.service
