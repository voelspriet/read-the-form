#!/usr/bin/env bash
# Drive Claude Code with GLM-5.3-Flash instead of Claude, through Z.ai's
# Anthropic-compatible endpoint.
#
# Run this in a SEPARATE terminal tab. These variables redirect the agent to a
# metered API; exporting them in a session that is on a Claude subscription
# quietly moves your work onto billing you did not intend.
set -euo pipefail

if [ -z "${ZAI_API_KEY:-}" ]; then
  if [ -f "$(dirname "$0")/.env" ]; then
    ZAI_API_KEY="$(grep -E '^ZAI_API_KEY=' "$(dirname "$0")/.env" | cut -d= -f2-)"
  fi
fi
if [ -z "${ZAI_API_KEY:-}" ] || [[ "$ZAI_API_KEY" == *paste* ]]; then
  echo "No z.ai key. Put ZAI_API_KEY in .env, or export it, then run this again." >&2
  echo "Get one at https://z.ai" >&2
  exit 1
fi

export ANTHROPIC_BASE_URL="https://api.z.ai/api/anthropic"
export ANTHROPIC_AUTH_TOKEN="$ZAI_API_KEY"
export API_TIMEOUT_MS=3000000
export ANTHROPIC_DEFAULT_OPUS_MODEL="glm-5.3-flash"
export ANTHROPIC_DEFAULT_SONNET_MODEL="glm-5.3-flash"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="glm-4.5-air"

echo "Claude Code is now driving glm-5.3-flash via $ANTHROPIC_BASE_URL"
echo "Nothing in this shell reaches Anthropic."
exec claude "$@"
