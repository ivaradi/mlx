#!/bin/sh

scriptdir=`dirname $0`

PYTHONPATH="${scriptdir}/src:${PYTHONPATH}"
export PYTHONPATH

exec python "${scriptdir}/diffdist.py" "$@"
