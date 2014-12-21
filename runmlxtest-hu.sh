#!/bin/sh

scriptdir=`dirname $0`

exec /usr/bin/env FORCE_PYUIPC_SIM=yes FORCE_SELECT_SIM=yes "${scriptdir}/runmlx-hu.sh" "$@"
