#!/bin/bash

set -e -u

echo "Building PyWin32"

cd /build

wget -O - https://github.com/mhammond/pywin32/archive/b224.tar.gz | gzip -dc | tar xf -
cd pywin32-b224
patch -p1 < ../pywin32git.patch
patch -p1 < ../pywin32.patch
python3 setup.py build
python3 setup.py install

echo "Building CEFPython"

cd /build

wget -O - http://opensource.spotify.com/cefbuilds/cef_binary_3.3359.1774.gd49d25f_windows32.tar.bz2 | bzip2 -dc | tar xf -
cd cef_binary_3.3359.1774.gd49d25f_windows32

patch -p1 < ../cef_binary_3.3359.1774.gd49d25f_windows32.patch
mv tests tests.orig

mkdir build
cd build
/usr/bin/env PATH=/mingw32/bin:/usr/local/bin::/c/Windows/System32:/c/Windows:/c/Windows/System32/Wbem:/c/Windows/System32/WindowsPowerShell/v1.0 cmake  -G "MinGW Makefiles" ..
cd libcef_dll_wrapper
mingw32-make

cd /build

wget -O - https://github.com/cztomczak/cefpython/archive/v66.0.tar.gz | gzip -dc | tar xf -
cd cefpython-66.0

patch -p1 < ../cefpython-66.0.patch

mkdir -p build
cd build

wget https://github.com/cztomczak/cefpython/releases/download/v66-upstream/cef66_3.3359.1774.gd49d25f_win32.zip
unzip cef66_3.3359.1774.gd49d25f_win32.zip
rm cef66_3.3359.1774.gd49d25f_win32.zip

cp /build/cef_binary_3.3359.1774.gd49d25f_windows32/build/libcef_dll_wrapper/libcef_dll_wrapper.a cef66_3.3359.1774.gd49d25f_win32/lib

pip3 install -r ../tools/requirements.txt

python3 ../tools/build.py --no-run-tests --no-run-examples 66.0  || true
python3 ../tools/build.py --no-run-tests --no-run-examples 66.0

echo "Building Py2EXE"

cd /build

wget -O - https://github.com/albertosottile/py2exe/archive/v0.9.3.0.tar.gz | gzip -dc | tar xf -
cd py2exe-0.9.3.0
patch -p1 < ../py2exe.patch
python3 setup.py build
python3 setup.py install

echo "Archiving msys64 directory"
cd /c
tar czf - msys64 | ssh -i /c/msys64/build/id_rsa -o StrictHostKeyChecking=no ivaradi@mises.varadiistvan.hu mlx/www/update/msys64.sh
