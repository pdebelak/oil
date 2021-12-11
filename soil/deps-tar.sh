#!/usr/bin/env bash
#
# Usage:
#   ./deps-tar.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

main() {
  echo 'Hello from deps-tar.sh'
}

"$@"
