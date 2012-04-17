#!/bin/bash

scriptdir=`dirname $0`
sim="${scriptdir}/../src/mlx/pyuipc_sim.py"

oldIFS="${IFS}"
IFS=$'\n'
for line in `cat $1`; do
    read -p "$line"
    echo $line | python "${sim}" >/dev/null
done
IFS="${oldIFS}"
