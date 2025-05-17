#!/bin/bash

# build-cefpython.sh <builddir>
#
# Build CEF Python (the latest compatible version with the MAVA Logger X)
# for Linux in the given build directory.

set -e -u -x

CEF_VERSION_MAJOR="108"
CEF_VERSION_MINOR="4"
CEF_VERSION_SHORT="${CEF_VERSION_MAJOR}.${CEF_VERSION_MINOR}"
CEF_VERSION="${CEF_VERSION_SHORT}.13"
CEF_FULL_VERSION="${CEF_VERSION}+ga98cd4c+chromium-108.0.5359.125"

CEF_NAME="cef_binary_${CEF_FULL_VERSION}_linux64"
CEFPYTHON_CEF_DIRNAME="cef${CEF_VERSION_MAJOR}_${CEF_FULL_VERSION}_linux64"
CEFPYTHON_SHA="393ba30d4455246d284b448259bc8e0e1dfc0f0c"
MAKEJOBS="16"

builddir="${1}"

mkdir -p "${builddir}"

cd "${builddir}"
rm  -rf "${CEF_NAME}"
if test -f "${HOME}/sources/mlx/${CEF_NAME}.tar.bz2"; then
    tar xf "${HOME}/sources/mlx/${CEF_NAME}.tar.bz2"
else
    wget -O - "https://cef-builds.spotifycdn.com/${CEF_NAME}.tar.bz2" | bzip2 -dc | tar xf -
fi

cd "${CEF_NAME}"
mv tests tests.orig
mkdir build
cd build
cmake -G "Unix Makefiles" ..
cd libcef_dll_wrapper
make -j${MAKEJOBS}

cd "${builddir}"
rm -rf "cefpython-${CEFPYTHON_SHA}"

wget -O - https://github.com/ivaradi/cefpython/archive/${CEFPYTHON_SHA}.tar.gz | gzip -dc | tar xf -

cd "cefpython-${CEFPYTHON_SHA}"
mkdir build
cd build

mkdir -p "${CEFPYTHON_CEF_DIRNAME}/bin"
mv "${builddir}/${CEF_NAME}/Release/"* "${CEFPYTHON_CEF_DIRNAME}/bin"
mv "${builddir}/${CEF_NAME}/Resources/"* "${CEFPYTHON_CEF_DIRNAME}/bin"

mkdir -p "${CEFPYTHON_CEF_DIRNAME}/lib"
mv "${builddir}/${CEF_NAME}/build/libcef_dll_wrapper/libcef_dll_wrapper.a" "${CEFPYTHON_CEF_DIRNAME}/lib"

mv "${builddir}/${CEF_NAME}/LICENSE.txt" "${CEFPYTHON_CEF_DIRNAME}"

pip3 install --break-system-packages -r ../tools/requirements.txt

python3 ../tools/build.py "${CEF_VERSION}" || true
python3 ../tools/make_installer.py "${CEF_VERSION_SHORT}"

cd "cefpython3_${CEF_VERSION_SHORT}_linux64"
python3 setup.py bdist_wheel
mv "dist/cefpython3-${CEF_VERSION_SHORT}-"*".whl" "${builddir}"
