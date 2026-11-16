#!/usr/bin/env bash
# Run check.py every 5 minutes until LOOP_MINUTES have passed.
#
# GitHub's cron scheduler proved unreliable for this account (hours with no
# scheduled runs), so one long job does the checking and the workflow starts
# its own successor when this loop ends. The repo is public, so the minutes
# are free.
#
# Once a day it also starts the factory's digest-data workflow (GitHub was
# dropping that schedule too), if FACTORY_DISPATCH_TOKEN is set.
set -uo pipefail

LOOP_MINUTES="${LOOP_MINUTES:-330}"
INTERVAL=300
DIGEST_REPO="atibbs/factory"
DIGEST_WORKFLOW="digest-data.yml"
# Window in UTC (HHMM) for starting digest-data: after 14:17, before the
# Claude routine reads the data at 15:00.
DIGEST_FROM=1417
DIGEST_UNTIL=1455

deadline=$(( $(date +%s) + LOOP_MINUTES * 60 ))

maybe_start_digest() {
  [ -n "${FACTORY_DISPATCH_TOKEN:-}" ] || return 0
  local hhmm today count
  hhmm=$((10#$(date -u +%H%M)))
  (( hhmm >= DIGEST_FROM && hhmm < DIGEST_UNTIL )) || return 0
  today=$(date -u +%F)
  count=$(GH_TOKEN="$FACTORY_DISPATCH_TOKEN" gh api \
    "repos/$DIGEST_REPO/actions/workflows/$DIGEST_WORKFLOW/runs?created=>=$today" \
    -q '.total_count' 2>/dev/null) || { echo "digest-data: could not list runs"; return 0; }
  if [ "${count:-0}" -gt 0 ]; then
    return 0
  fi
  if GH_TOKEN="$FACTORY_DISPATCH_TOKEN" gh workflow run "$DIGEST_WORKFLOW" \
       --repo "$DIGEST_REPO" --ref main; then
    echo "digest-data: started for $today"
  else
    echo "::warning::digest-data: dispatch failed"
  fi
}

while :; do
  started=$(date +%s)
  echo "::group::check $(date -u +'%F %H:%M UTC')"
  python3 check.py ${CHECK_ARGS:-} || echo "::warning::check.py failed (exit $?)"
  echo "::endgroup::"
  maybe_start_digest

  # Sleep to the next 5-minute mark measured from this check's start.
  next=$(( started + INTERVAL ))
  if (( next >= deadline )); then
    break
  fi
  now=$(date +%s)
  (( next > now )) && sleep $(( next - now ))
done
echo "loop finished; the workflow starts the next one"
