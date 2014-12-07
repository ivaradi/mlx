#!/bin/sh

scriptdir=`dirname $0`

PYTHONPATH="${scriptdir}/src:${scriptdir}:${PYTHONPATH}"
export PYTHONPATH

exec python -m runmlx "$@"
