#!/bin/bash

set -e -u

scriptdir=$(cd $(dirname $0) && pwd)

sdistname="${1}"
uid="${2}"
gid="${3}"

mlxdirname=$(basename "${sdistname}" .tar.gz)
version=$(echo "${mlxdirname}" | sed "s:mlx-::")

cd "${scriptdir}"

tar xf "dist/${sdistname}"

cd "${mlxdirname}"

echo "winemakeinst.bat" | wine cmd

echo
echo "Copying the 'dist' directory..."
destdistdir="../dist/dist-${version}"

rm -rf "${destdistdir}"
cp -a dist "${destdistdir}"
chown -R ${uid}:${gid} "${destdistdir}"

echo
echo "Copying the setup program..."

cp "MAVA Logger X-${version}-Setup.exe" ../dist
chown ${uid}:${gid} "../dist/MAVA Logger X-${version}-Setup.exe"

echo
echo "Done."
