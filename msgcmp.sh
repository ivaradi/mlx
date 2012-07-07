#!/bin/sh

set -e -u

scriptdir=`dirname $0`

language="${1:-}"
if test -z "${language}"; then
    language="hu"
fi

msgcmp "${scriptdir}/locale/en/mlx.po" "${scriptdir}/locale/${language}/mlx.po"
