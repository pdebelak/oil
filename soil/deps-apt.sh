#!/usr/bin/env bash
#
# Usage:
#   ./deps-apt.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

dummy() {
  # gcc: time-helper is needed
  # git: for checking out code
  # python2: for various tools
  apt-get install -y gcc git python2
}

dev-minimal() {
  local -a packages=(
    # common
    git python2

    libreadline-dev
    procps  # pgrep used by test/interactive
    gawk

    python2-dev  # for building Python extensions

    python-pip  # flake8 typing
    python3-setuptools  # mypy
    python3-pip

    # Note: osh-minimal task needs shells; not using spec-bin for now
    busybox-static mksh zsh
  )

  apt-get install -y "${packages[@]}"

}


"$@"
