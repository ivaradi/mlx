#!/bin/bash

scriptdir=$(cd $(dirname $0) && pwd)

if test "$1" = "initialize"; then
    "${scriptdir}/setup.sh"
elif test "$1" = "build"; then
    shift
    "${scriptdir}/build.sh" "$@"
else
    exec "$@"
fi
