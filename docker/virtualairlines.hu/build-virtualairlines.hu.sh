#!/bin/bash

scriptdir=$(cd $(dirname $0) && pwd)

docker build -t virtualairlines.hu "${scriptdir}/context"
