#!/usr/bin/env bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)" || exit 1

exec "${SCRIPT_DIR}/../run.sh" phonebook "$@"
