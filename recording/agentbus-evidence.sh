#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "$0")/.." && pwd)
agentbus_repo=${AGENTBUS_REPO:-/home/jahwag/IdeaProjects/agentbus}
port=${AGENTBUS_EVIDENCE_PORT:-17779}
server="http://127.0.0.1:${port}"
runtime=$(mktemp -d "$repo_root/tmp/agentbus-evidence.XXXXXX")
server_pid=""

cleanup() {
  if [[ -n $server_pid ]] && kill -0 "$server_pid" 2>/dev/null; then
    kill "$server_pid"
    wait "$server_pid" 2>/dev/null || true
  fi
  if [[ $runtime == "$repo_root"/tmp/agentbus-evidence.* ]]; then
    rm -rf -- "$runtime"
  fi
}
trap cleanup EXIT HUP INT TERM

if [[ ! -f $agentbus_repo/go.mod ]]; then
  echo "AgentBus source not found: $agentbus_repo" >&2
  exit 2
fi

(
  cd "$agentbus_repo"
  CGO_ENABLED=0 go build -trimpath -o "$runtime/agentbusd" ./cmd/agentbusd
  CGO_ENABLED=0 go build -trimpath -o "$runtime/agentbus" ./cmd/agentbus
)

openssl rand -hex -out "$runtime/admin.token" 32
chmod 0600 "$runtime/admin.token"
"$runtime/agentbusd" \
  --listen "127.0.0.1:${port}" \
  --db "$runtime/bus.db" \
  --admin-token-file "$runtime/admin.token" \
  --ui=true \
  >"$runtime/daemon.log" 2>&1 &
server_pid=$!

for _ in {1..80}; do
  if curl --fail --silent --show-error "$server/readyz" >/dev/null 2>&1; then
    break
  fi
  if ! kill -0 "$server_pid" 2>/dev/null; then
    echo "AgentBus stopped before becoming ready" >&2
    exit 2
  fi
  sleep 0.1
done
curl --fail --silent --show-error "$server/readyz" >/dev/null

for name in cora approval-gateway human-approval-bridge; do
  "$runtime/agentbus" mint \
    --server "$server" \
    --admin-token-file "$runtime/admin.token" \
    --name "$name" \
    --token-out "$runtime/$name.token" \
    >/dev/null
done

send() {
  local token=$1
  local to=$2
  local client_id=$3
  local body=$4
  local reply_to=${5:-}
  local reply_args=()
  if [[ -n $reply_to ]]; then
    reply_args=(--reply-to "$reply_to")
  fi
  "$runtime/agentbus" send \
    --server "$server" \
    --token-file "$runtime/$token.token" \
    --to "$to" \
    --client-message-id "$client_id" \
    --body "$body" \
    "${reply_args[@]}" \
    | jq -r .message_id
}

proposal_hash=$(sha256sum "$repo_root/artifacts/proposal.json" | cut -c1-12)
root=$(send cora approval-gateway fs1-intake \
  "Ticket #1 detected. I will read only this ticket, search governed knowledge, and prepare a proposal. I cannot write to Freshservice.")
research=$(send cora approval-gateway fs1-research \
  "Research complete. Likely linked replacement-device enrolment and stale MFA registration. Evidence: kb://mfa-recovery.md, kb://device-reenrollment.md, kb://wifi-managed-device.md." \
  "$root")
proposal=$(send cora approval-gateway fs1-proposal \
  "Proposal $proposal_hash is ready: private troubleshooting note, proposed category, and audit tags ai-assisted and human-approved." \
  "$research")
gate=$(send approval-gateway cora fs1-gate \
  "No mutation performed. Exact human phrase APPROVE is required. Ticket timestamp and proposal hash will be revalidated by the operator-owned gateway." \
  "$proposal")
human=$(send human-approval-bridge approval-gateway fs1-human-approval \
  "APPROVE ticket=1 proposal=$proposal_hash" \
  "$gate")
applied=$(send approval-gateway cora fs1-applied \
  "Approval bound to ticket #1 and proposal $proposal_hash. Stale-ticket check passed. Operator gateway applied the allowlisted private note and tags." \
  "$human")
send cora approval-gateway fs1-done \
  "Freshservice confirms one private note plus ai-assisted and human-approved. Delivery acknowledged." \
  "$applied" \
  >/dev/null

node "$repo_root/recording/capture-agentbus-evidence.mjs" \
  "$runtime/agentbus" \
  "$server" \
  "$runtime/admin.token" \
  "$repo_root/artifacts/agentbus-conversation.png" \
  "$repo_root/artifacts/agentbus-conversation-late.png"

stat -c '%n %s bytes' \
  "$repo_root/artifacts/agentbus-conversation.png" \
  "$repo_root/artifacts/agentbus-conversation-late.png"
