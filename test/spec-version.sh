#!/usr/bin/env bash
#
# Usage:
#   test/spec-version.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

source devtools/run-task.sh
source test/common.sh  # date-and-git-info
source test/spec-common.sh  # OSH_LIST

maybe-show() {
  local path=$1
  if test -f $path; then
    echo "--- $path ---"
    cat $path
    echo
  fi
}

oil-version-text() {
  date-and-git-info

  for bin in $OIL_LIST; do
    echo ---
    echo "\$ $bin --version"
    $bin --version
    echo
  done

  maybe-show /etc/alpine-release
  maybe-show /etc/debian_version
  maybe-show /etc/lsb-release
}

tea-version-text() {
  oil-version-text
}

# This has to be in test/spec because it uses $OSH_LIST, etc.
osh-version-text() {

  local -a osh_list
  if test $# -eq 0; then
    osh_list=( $OSH_LIST )  # word splitting
  else
    osh_list=( "$@" )  # explicit arguments
  fi

  date-and-git-info

  for bin in "${osh_list[@]}"; do
    echo ---
    echo "\$ $bin --version"
    $bin --version
    echo
  done

  # $BASH and $ZSH should exist

  echo ---
  bash --version | head -n 1
  ls -l $(type -p bash)
  echo

  echo ---
  zsh --version | head -n 1
  ls -l $(type -p zsh)
  echo

  # No -v or -V or --version.  TODO: Only use hermetic version on release.

  echo ---
  local my_dash
  my_dash=$(type -p dash)
  if test -f $my_dash; then
    ls -l $my_dash
  else
    dpkg -s dash | egrep '^Package|Version'
  fi
  echo

  echo ---
  local my_mksh
  my_mksh=$(type -p mksh)
  if test -f $my_mksh; then
    ls -l $my_mksh
  else
    dpkg -s mksh | egrep '^Package|Version'
  fi
  echo

  echo ---
  local my_busybox
  my_busybox=$(type -p busybox)
  if test -f $my_busybox; then
    { $my_busybox || true; } | head -n 1
    ls -l $my_busybox
  else
    # Need || true because of pipefail
    { busybox || true; } | head -n 1
  fi
  echo

  maybe-show /etc/debian_version
  maybe-show /etc/lsb-release
  maybe-show /etc/alpine-release
}

osh-minimal-version-text() {
  osh-version-text
}

interactive-version-text() {
  osh-version-text
}

needs-terminal-version-text() {
  osh-version-text
}

run-task "$@"
