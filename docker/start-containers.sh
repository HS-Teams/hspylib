#!/usr/bin/env bash

# shellcheck disable=SC1091
source "docker-tools-inc.sh"

CONTAINERS_DIR=${CONTAINERS_DIR:-./containers}
pushd "${CONTAINERS_DIR}" &> /dev/null || exit 1
# shellcheck disable=SC2206
CONTAINERS=(${1:-$(find . -maxdepth 1 ! -path . -type d | cut -c3-)})
popd &> /dev/null || exit 1
[[ "${#CONTAINERS[@]}" -eq 0 ]] && exit 0

DOCKER_FLAGS=('--detach' '--wait' '--wait-timeout' '180')

# @purpose: Start all docker-compose.yml
# -param $1: if the execution is on an interactive console or not
startContainers() {
  local all=() container

  if [[ ${#CONTAINERS[@]} -gt 1 ]]; then
    for container in "${CONTAINERS[@]}"; do
      read -r -n 1 -p "Start container ${container} (y/[n]): " ANS
      test -n "${ANS}" && echo ''
      if [[ "${ANS}" =~ ^[yY]$ ]]; then
        all+=("${container}")
      fi
    done
  else
    all+=("${CONTAINERS[0]}")
  fi
  echo ''

  for container in "${all[@]}"; do
    echo -e "${BLUE}⠿ Starting container ${container} ${NC}"
    pushd "${CONTAINERS_DIR}/${container}" &>/dev/null || exit 1
    if docker compose up "${DOCKER_FLAGS[@]}"; then
      echo ''
    else
      echo -e "${RED}⠿ Docker (docker compose up) command failed! ${NC}\n"
      popd &>/dev/null || exit 1
      return 1
    fi
    popd &>/dev/null || exit 1
  done

}

echo ''
startContainers
