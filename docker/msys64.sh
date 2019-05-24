#!/bin/bash

# Script to receive the msys64.tar.gz file on the server

set -e -u

scriptdir=$(cd $(dirname $0) && pwd)

msys64path="${scriptdir}/msys64.tar.gz"

echo "Receiving msys64.tar.gz.new ..."
cat > "${msys64path}.new"

echo "Replacing old version"
mv "${msys64path}.new" "${msys64path}"
