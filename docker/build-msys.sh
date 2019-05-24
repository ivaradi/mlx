#!/bin/bash

set -e -u

scriptdir=$(cd $(dirname $0) && pwd)

VMDOMAIN=win10

MSYSDIR="${scriptdir}/msys"

DOCKER_IP=192.168.122.21
DOCKER_PORT=2375

DOCKER_HOST=tcp://${DOCKER_IP}:${DOCKER_PORT}
export DOCKER_HOST

set +e
if virsh start "${VMDOMAIN}"; then
    echo "Sleeping five minutes to wait for Windows to pull itself together..."
    sleep 300
else
    echo "Could not start the Windows VM, maybe it is already up."
fi

echo "Waiting for the Docker port to be available..."
count=0
while ! socat /dev/null TCP4:${DOCKER_IP}:${DOCKER_PORT},connect-timeout=2; do
    if test ${count} -gt 15; then
        echo "Docker port is not available!"
        exit 1
    fi
    count=$(expr ${count} + 1)
    sleep 2
done

echo "Waiting for Docker to be available..."
count=0
while ! docker info; do
    if test ${count} -gt 5; then
        echo "Docker is not available!"
        exit 1
    fi
    count=$(expr ${count} + 1)
    sleep 2
done

set -e

echo "Docker available, executing MSYS image build"
docker build -t msys -f "${MSYSDIR}/Dockerfile" "${MSYSDIR}"

echo "Building the MSYS distribution"
docker run -it --rm msys c:\\msys64\\build\\build.bat

echo "Shutting down the Windows VM"
virsh shutdown --mode acpi "${VMDOMAIN}"
