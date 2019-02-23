#!/bin/bash

set -e -u

scriptdir=`dirname $0`
scriptdir=`cd "${scriptdir}" && pwd`

docker build -t mlxwinebuild-base "${scriptdir}/context"

if test -z "${XAUTHORITY:-}"; then
    XAUTHORITY="${HOME}/.Xauthority"
fi

docker run -it --name mlxwinebuildinit -v /tmp/.X11-unix:/tmp/.X11-unix -v "${XAUTHORITY}":/root/.Xauthority -v /usr/lib/x86_64-linux-gnu/vdpau:/usr/lib/x86_64-linux-gnu/vdpau --device /dev/nvidiactl --device /dev/nvidia0 --security-opt=apparmor:unconfined  --env DISPLAY mlxwinebuild-base initialize

echo "Committing new image..."

docker commit --change='CMD ["bash"]' mlxwinebuildinit mlxwinebuild

echo "Removing container..."
docker rm mlxwinebuildinit

echo "Done."
