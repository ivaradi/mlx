#!/bin/sh

scriptdir=`dirname $0`

echo "$@" > "/tmp/mlxcef.${LOGNAME}.args.secondary.tmp"
mv "/tmp/mlxcef.${LOGNAME}.args.secondary.tmp" "/tmp/mlxcef.${LOGNAME}.args.secondary"
