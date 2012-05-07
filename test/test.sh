#!/bin/bash

scriptdir=`dirname $0`
sim="${scriptdir}/../src/mlx/pyuipc_sim.py"

host="localhost"
if test $# -gt 1; then
    host=$2
fi

oldIFS="${IFS}"
IFS=$'\n'
for line in `cat $1`; do
    read -p "$line"
    echo $line | python "${sim}" "${host}" >/dev/null
done
IFS="${oldIFS}"
