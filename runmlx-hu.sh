#!/bin/sh

scriptdir=`dirname $0`

exec /usr/bin/env LANGUAGE=hu_HU LANG=hu_HU.UTF-8 LC_MESSAGES=hu_HU.UTF-8 LC_COLLATE=hu_HU.UTF8 LC_CTYPE=hu_HU.UTF8 "${scriptdir}/runmlx.sh" "$@"
