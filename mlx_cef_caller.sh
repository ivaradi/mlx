#!/bin/sh

scriptdir=`dirname $0`

echo "$@" > "/tmp/mlxcef.${LOGNAME}.args.tmp"
mv "/tmp/mlxcef.${LOGNAME}.args.tmp" "/tmp/mlxcef.${LOGNAME}.args"
