#!/usr/bin/env bash

# shellcheck disable=SC1091
source "docker-tools-inc.sh"

# shellcheck disable=SC2206,SC2207
CONTAINERS=(${1:-$(docker ps --format '{{.Names}}' | tr '\n' ' ')})
[[ ${#CONTAINERS[@]} -eq 0 ]] && exit 0

# @purpose: Stop all docker-compose.yml
# -param $1: if the execution is on an interactive console or not
stopContainers() {
  local all=() container count

  if [[ ${#CONTAINERS[@]} -gt 1 ]]; then
    for container in "${CONTAINERS[@]}"; do
      read -r -n 1 -p "Stop container ${container} (y/[n]): " ANS
      test -n "${ANS}" && echo ''
      if [[ "${ANS}" =~ ^[yY]$ ]]; then
        all+=("${container}")
      fi
    done
  else
    all+=("${CONTAINERS[0]}")
  fi
  echo ''

  count=${#all[@]}
  [[ "${count}" -gt 0 ]] && timeout $$ $((count * 60))

  for container in "${all[@]}"; do
    status=$(getStatus "${container}")
    if [[ "${status}" == "\"running\"" ]]; then
      echo -en "${BLUE}⠿ Stopping container ${container} ${NC}"
      if docker stop "${container}" &>/dev/null; then
        assertStatus "${container}" "exited"
        echo -e "${GREEN}⠿ OK ⠿"
      else
        echo -e ' ⠿ FAILED ⠿'
      fi
    else
      echo -e "${ORANGE}⠿ Container \"${container}\" is not up"
    fi
  done
  echo -e "${NC}"
}

stopContainers
