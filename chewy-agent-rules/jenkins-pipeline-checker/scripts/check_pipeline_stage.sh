#!/usr/bin/env bash
set -euo pipefail

PIPELINE="${1:-}"
RUN_ID="${2:-}"
STAGE_NAME="${3:-}"
BRANCH_NAME="${4:-}"

if [[ "$PIPELINE" =~ ^https?:// ]]; then
  BLUE_URL="$PIPELINE"
  STAGE_NAME="${2:-}"
  PIPELINE="$(echo "$BLUE_URL" | sed -n 's#.*blue/organizations/[^/]\\+/\\([^/]*\\)/detail/\\([^/]*\\)/\\([^/]*\\)/pipeline.*#\\1#p')"
  BRANCH_NAME="$(echo "$BLUE_URL" | sed -n 's#.*blue/organizations/[^/]\\+/\\([^/]*\\)/detail/\\([^/]*\\)/\\([^/]*\\)/pipeline.*#\\2#p')"
  RUN_ID="$(echo "$BLUE_URL" | sed -n 's#.*blue/organizations/[^/]\\+/\\([^/]*\\)/detail/\\([^/]*\\)/\\([^/]*\\)/pipeline.*#\\3#p')"
fi

if [[ -z "$PIPELINE" || -z "$RUN_ID" || -z "$STAGE_NAME" ]]; then
  echo "Usage: $0 <pipeline> <run_id> <stage_name> [branch_name]" >&2
  echo "   or: $0 <blue_ocean_url> <stage_name>" >&2
  exit 2
fi

: "${JENKINS_USERNAME:?Set JENKINS_USERNAME in the environment}"
: "${JENKINS_API_TOKEN:?Set JENKINS_API_TOKEN in the environment}"

BASE_URL="${JENKINS_BASE_URL:-https://jenkins-nonprod.shss.chewy.com}"
ORG="${JENKINS_ORG:-jenkins}"
AUTH="${JENKINS_USERNAME}:${JENKINS_API_TOKEN}"

api() {
  curl -sS -u "$AUTH" -H 'Accept: application/json' "$1"
}

if [[ -n "$BRANCH_NAME" ]]; then
  JOB_PATH="job/$PIPELINE/job/$BRANCH_NAME/$RUN_ID"
  DESCRIBE_URL="$BASE_URL/$JOB_PATH/wfapi/describe"
  DESCRIBE_JSON="$(api "$DESCRIBE_URL")"

  if ! echo "$DESCRIBE_JSON" | jq -e .id >/dev/null 2>&1; then
    echo "ERROR: Jenkins wfapi did not return JSON (auth/SSO issue?)" >&2
    echo "$DESCRIBE_JSON" | head -c 200 >&2
    exit 1
  fi

  NODE_ID="$(echo "$DESCRIBE_JSON" | jq -r --arg stage "$STAGE_NAME" '.stages[] | select(.name == $stage) | .id' | head -n 1)"

  if [[ -z "$NODE_ID" || "$NODE_ID" == "null" ]]; then
    echo "ERROR: Stage '$STAGE_NAME' not found. Available stages:" >&2
    echo "$DESCRIBE_JSON" | jq -r '.stages[].name' >&2
    exit 1
  fi

  LOG_URL="$BASE_URL/$JOB_PATH/execution/node/$NODE_ID/wfapi/log?start=0"
  LOG_JSON="$(api "$LOG_URL")"
  LOG_TEXT="$(echo "$LOG_JSON" | jq -r '.text // empty')"
  if [[ -n "$LOG_TEXT" ]]; then
    printf '%s' "$LOG_TEXT"
  else
    curl -sS -u "$AUTH" "$BASE_URL/$JOB_PATH/consoleText"
  fi
else
  RUN_URL="$BASE_URL/blue/rest/organizations/$ORG/pipelines/$PIPELINE/runs/$RUN_ID/"
  RUN_JSON="$(api "$RUN_URL")"

  if ! echo "$RUN_JSON" | jq -e .id >/dev/null 2>&1; then
    echo "ERROR: Jenkins API did not return JSON (auth/SSO issue?)" >&2
    echo "$RUN_JSON" | head -c 200 >&2
    exit 1
  fi

  NODES_URL="$RUN_URL/nodes/"
  NODES_JSON="$(api "$NODES_URL")"
  NODE_ID="$(echo "$NODES_JSON" | jq -r --arg stage "$STAGE_NAME" '.[] | select(.displayName == $stage) | .id' | head -n 1)"

  if [[ -z "$NODE_ID" || "$NODE_ID" == "null" ]]; then
    echo "ERROR: Stage '$STAGE_NAME' not found. Available stages:" >&2
    echo "$NODES_JSON" | jq -r '.[].displayName' >&2
    exit 1
  fi

  LOG_URL="$RUN_URL/nodes/$NODE_ID/log/?start=0"
  curl -sS -u "$AUTH" "$LOG_URL"
fi
