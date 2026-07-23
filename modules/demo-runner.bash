#!/usr/bin/env bash

# Shared implementation for the module demo launchers.
run_demo() {
  local demo_dir="$1"
  shift

  local source_dir
  local modules_dir
  local current_main
  local module_main
  local existing_pythonpath
  local joined_pythonpath
  local python_bin
  local selector
  local demo_path
  local relative_path
  local base_name
  local stem
  local package_name
  local package_base
  local label
  local selected
  local demo_workdir
  local demo_file
  local -a python_paths
  local -a demos
  local -a matches

  source_dir="$(cd "${demo_dir}/.." && pwd -P)" || return 1
  modules_dir="$(cd "${source_dir}/../.." && pwd -P)" || return 1
  current_main="${source_dir}/main"

  # Run against the monorepo sources while retaining any caller-supplied paths.
  python_paths=("${current_main}" "${demo_dir}")
  for module_main in "${modules_dir}"/*/src/main; do
    if [[ -d "${module_main}" && "${module_main}" != "${current_main}" ]]; then
      python_paths+=("${module_main}")
    fi
  done

  printf -v joined_pythonpath '%s:' "${python_paths[@]}"
  joined_pythonpath="${joined_pythonpath%:}"
  existing_pythonpath="${PYTHONPATH-}"
  export PYTHONPATH="${joined_pythonpath}${existing_pythonpath:+:${existing_pythonpath}}"

  demos=()
  while IFS= read -r demo_path; do
    demos+=("${demo_path}")
  done < <(
    find "${demo_dir}" -type f \
      \( -name '*_demo.py' -o -name '__main__.py' \) -print |
      LC_ALL=C sort
  )

  if [[ ${#demos[@]} -eq 0 ]]; then
    echo "No demos found under ${demo_dir}" >&2
    return 1
  fi

  if [[ $# -eq 0 || "$1" == "--list" ]]; then
    echo "Available demos:"
    for demo_path in "${demos[@]}"; do
      relative_path="${demo_path#"${demo_dir}/"}"
      if [[ "${relative_path##*/}" == "__main__.py" ]]; then
        label="${relative_path%/__main__.py}"
      else
        label="${relative_path}"
      fi
      printf '  %s\n' "${label}"
    done
    printf '\nUsage: %s <demo> [arguments ...]\n' "$0"
    return 0
  fi

  selector="$1"
  shift
  matches=()

  for demo_path in "${demos[@]}"; do
    relative_path="${demo_path#"${demo_dir}/"}"
    base_name="${demo_path##*/}"
    stem="${base_name%.py}"

    if [[ "${base_name}" == "__main__.py" ]]; then
      package_name="${relative_path%/__main__.py}"
      package_base="${package_name##*/}"
      if [[ "${selector}" == "${package_name}" ||
            "${selector}" == "${package_base}" ||
            "${selector}" == "${relative_path}" ||
            "${selector}" == "${demo_path}" ]]; then
        matches+=("${demo_path}")
      fi
    elif [[ "${selector}" == "${relative_path}" ||
            "${selector}" == "${relative_path%.py}" ||
            "${selector}" == "${base_name}" ||
            "${selector}" == "${stem}" ||
            "${selector}" == "${demo_path}" ]]; then
      matches+=("${demo_path}")
    fi
  done

  if [[ ${#matches[@]} -eq 0 ]]; then
    printf 'Unknown demo: %s\nRun "%s --list" to see the available demos.\n' \
      "${selector}" "$0" >&2
    return 2
  fi

  if [[ ${#matches[@]} -gt 1 ]]; then
    printf 'Ambiguous demo name: %s\nMatches:\n' "${selector}" >&2
    for demo_path in "${matches[@]}"; do
      relative_path="${demo_path#"${demo_dir}/"}"
      printf '  %s\n' "${relative_path}" >&2
    done
    return 2
  fi

  python_bin="${PYTHON_BIN:-python3}"
  if ! command -v "${python_bin}" >/dev/null 2>&1; then
    printf 'Python interpreter not found: %s\n' "${python_bin}" >&2
    return 127
  fi
  if ! "${python_bin}" -c \
    'import sys; raise SystemExit(sys.version_info < (3, 10))' >/dev/null 2>&1; then
    printf 'Python 3.10 or newer is required (%s is incompatible; set PYTHON_BIN to choose another interpreter).\n' \
      "${python_bin}" >&2
    return 2
  fi

  selected="${matches[0]}"
  demo_workdir="${selected%/*}"
  demo_file="${selected##*/}"

  (
    cd "${demo_workdir}" || exit 1
    exec "${python_bin}" "${demo_file}" "$@"
  )
}
