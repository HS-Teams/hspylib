#!/usr/bin/env bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)" || exit 1

# shellcheck source=../../../demo-runner.bash
source "${SCRIPT_DIR}/../../../demo-runner.bash"

run_demo "${SCRIPT_DIR}" "$@"
