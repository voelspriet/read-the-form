#!/usr/bin/env bash
# Which Z.ai endpoints does this key actually open?
#
# The docs do not settle whether the Anthropic-compatible endpoint that Claude
# Code uses needs a paid Coding Plan or works on an ordinary pay-as-you-go key.
# Rather than believe either answer, ask the API.
set -uo pipefail
KEY="${1:-${ZAI_API_KEY:-}}"
[ -z "$KEY" ] && { echo "usage: ./check-key.sh <zai-api-key>" >&2; exit 1; }

echo
echo "1. Standard API  (what app.py uses)"
code=$(curl -s -o /tmp/z1.json -w '%{http_code}' --max-time 60 \
  -X POST "https://api.z.ai/api/paas/v4/chat/completions" \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"model":"glm-5.3-flash","messages":[{"role":"user","content":"reply with the single word: ok"}],"max_tokens":8}')
echo "   POST /api/paas/v4/chat/completions -> HTTP $code"
[ "$code" = "200" ] && echo "   reply: $(python3 -c "import json;print(json.load(open('/tmp/z1.json'))['choices'][0]['message']['content'][:40])" 2>/dev/null)" \
                    || echo "   $(head -c 220 /tmp/z1.json)"

echo
echo "2. Anthropic-compatible API  (what Claude Code uses)"
code=$(curl -s -o /tmp/z2.json -w '%{http_code}' --max-time 60 \
  -X POST "https://api.z.ai/api/anthropic/v1/messages" \
  -H "x-api-key: $KEY" -H "anthropic-version: 2023-06-01" -H "Content-Type: application/json" \
  -d '{"model":"glm-5.3-flash","max_tokens":8,"messages":[{"role":"user","content":"reply with the single word: ok"}]}')
echo "   POST /api/anthropic/v1/messages -> HTTP $code"
[ "$code" = "200" ] && echo "   reply: $(python3 -c "import json;print(json.load(open('/tmp/z2.json'))['content'][0]['text'][:40])" 2>/dev/null)" \
                    || echo "   $(head -c 220 /tmp/z2.json)"

echo
echo "3. Vision  (the whole point of the tool)"
code=$(curl -s -o /tmp/z3.json -w '%{http_code}' --max-time 90 \
  -X POST "https://api.z.ai/api/paas/v4/chat/completions" \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d "{\"model\":\"glm-5.3-flash\",\"max_tokens\":40,\"messages\":[{\"role\":\"user\",\"content\":[{\"type\":\"text\",\"text\":\"What single word is written here? Answer with that word only.\"},{\"type\":\"image_url\",\"image_url\":{\"url\":\"data:image/jpeg;base64,$(base64 < static/demo-form.jpeg | tr -d '\n')\"}}]}]}")
echo "   image input -> HTTP $code"
[ "$code" = "200" ] && echo "   reply: $(python3 -c "import json;print(json.load(open('/tmp/z3.json'))['choices'][0]['message']['content'][:60])" 2>/dev/null)" \
                    || echo "   $(head -c 220 /tmp/z3.json)"
echo
echo "Read it like this:"
echo "  1 works, 2 fails  ->  pay-as-you-go is enough for the tool; add a Coding Plan for Claude Code"
echo "  1 and 2 both work ->  no Coding Plan needed at all"
echo "  1 fails           ->  no credit on the account yet"
