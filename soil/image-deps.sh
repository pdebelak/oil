#!/usr/bin/env bash
#
# Usage:
#   ./image-deps.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

#
# Common Helpers
#

download-re2c() {
  mkdir -p _deps
  wget --directory _deps \
    https://github.com/skvadrik/re2c/releases/download/1.0.3/re2c-1.0.3.tar.gz
}

install-re2c() {
  cd _deps
  tar -x -z < re2c-1.0.3.tar.gz
  cd re2c-1.0.3
  ./configure
  make
}

#
# Image definitions: dummy, dev-minimal, other-tests, ovm-tarball, cpp
#

cpp-source-deps() {
  # Uh this doesn't work because it's created in the directory we're mounting!
  # At runtime we mount the newly cloned repo.
  #
  # Should we create _deps in a different place?  And them symlink it?
  # build/dev-shell won't be able to find it
  #
  # Problem: during the build step, our WORKDIR is /app
  #
  # Should it be /app/oil ?  But then the bind mount will hide it?
  #
  # Maybe we need ../_oil-deps or ~/oil-deps/{re2c,spec-bin,R}
  # It should be parallel to the repo though

  echo TODO
  #download-re2c
  #install-re2c

  # TODO: Remove these from runtime:
  #
  # mycpp-pip
  # mycpp-git
}

ovm-tarball-source-deps() {
  # I think building Python needs this
  ln -s /usr/bin/python2 /usr/bin/python

  # Run it LOCALLY with the tasks that are failing

  # Remove these from runtime:
  #
  # spec-deps
  # tarball-deps
}

"$@"
