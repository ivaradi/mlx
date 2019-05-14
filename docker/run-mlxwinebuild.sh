#!/bin/bash

set -e -u

docker run -it --rm -v "${HOME}:${HOME}" -w "${PWD}" mlxwinebuild-py3 "$@"
