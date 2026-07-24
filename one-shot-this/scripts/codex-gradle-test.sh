#!/usr/bin/env bash
set -euo pipefail

export GRADLE_USER_HOME="${CODEX_SHARED_GRADLE_USER_HOME:-${PWD}/.gradle-user-home}"
mkdir -p "${GRADLE_USER_HOME}"
GIT_COMMON_DIR="$(git rev-parse --git-common-dir)"
GIT_ROOT="$(cd "${GIT_COMMON_DIR}/.." && pwd)"

./gradlew -Pgit.root="${GIT_ROOT}" "$@"
