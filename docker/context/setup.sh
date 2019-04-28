#!/bin/bash

set -e -u

cdrive="${HOME}/.wine/drive_c"
cpythondir="${cdrive}/msys64/mingw32"

if test -f "${cpythondir}/bin/python3.exe"; then
    echo "Image already configured, not doing anything!"
    exit 1
fi

echo "Preparing image to be able to build MAVA Logger X for Windows"
echo

export WINEARCH=win32

echo "exit" | wine cmd

echo "Downloading and extracting the extra packages..."

wget -O - mlx.varadiistvan.hu/update/msys64.tar.gz | tar xzf - -C "${cdrive}"
wget -O - mlx.varadiistvan.hu/update/winepkgs.tar | tar xf - nsis-2.46-setup.exe pyuipc-cpython-37m.dll xplra.py

mv  pyuipc-cpython-37m.dll xplra.py /root/.wine/drive_c/msys64/mingw32/lib/python3.7/site-packages

echo
echo "Installing extra packages..."

wine nsis-2.46-setup.exe

echo
echo "Removing extra packages..."
rm -f *.exe
echo
echo "Done."
