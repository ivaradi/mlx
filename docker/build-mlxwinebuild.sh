#!/bin/bash

set -e -u

sdistfile="${1}"
sdistdir=$(cd $(dirname "${sdistfile}") && pwd)

docker run --rm -v "${sdistdir}:/root/dist" mlxwinebuild-py3 build $(basename "${sdistfile}") $(id -u) $(id -g)
#docker run -it --rm -v "${sdistdir}:/root/dist" mlxwinebuild-py3 bash
