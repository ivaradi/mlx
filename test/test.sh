#!/bin/bash

scriptdir=`dirname $0`

PYTHONPATH="${scriptdir}/../src"
export PYTHONPATH

sim="mlx.pyuipc_sim"

host="localhost"
if test $# -gt 1; then
    host=$2
fi

oldIFS="${IFS}"
IFS=$'\n'
for line in `cat $1`; do
    read -p "$line"
    echo $line | python3 -m "${sim}" "${host}" >/dev/null
done
IFS="${oldIFS}"
