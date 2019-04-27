#!/bin/sh

scriptdir=`dirname $0`

PYTHONPATH="${scriptdir}/src:${scriptdir}:${PYTHONPATH}"
export PYTHONPATH

https_proxy=

FORCE_PYGOBJECT=true
export FORCE_PYGOBJECT

exec python3 -m runmlx "$@"
