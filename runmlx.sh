#!/bin/sh

scriptdir=`dirname $0`

PYTHONPATH="${scriptdir}/src:${scriptdir}:${PYTHONPATH}"
export PYTHONPATH

https_proxy=

exec python -m runmlx "$@"
