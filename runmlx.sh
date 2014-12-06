#!/bin/sh

scriptdir=`dirname $0`

PYTHONPATH="${scriptdir}/src:${scriptdir}:${PYTHONPATH}"
export PYTHONPATH

LD_LIBRARY_PATH="${HOME}/local/opt/OpenAL/lib:${LD_LIBRARY_PATH}"
export LD_LIBRARY_PATH

exec python -m runmlx "$@"
