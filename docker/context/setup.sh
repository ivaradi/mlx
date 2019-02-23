#!/bin/bash

set -e -u

cdrive="${HOME}/.wine/drive_c"
ctmpdir="${cdrive}/tmp"
cpythondir="${cdrive}/Python27"
cwinsysdir="${cdrive}/windows/system32"

if test -f "${cpythondir}/python.exe"; then
    echo "Image already configured, not doing anything!"
    exit 1
fi

echo "Preparing image to be able to build MAVA Logger X for Windows"
echo

echo "Downloading and extracting the extra packages..."

wget -O - mlx.varadiistvan.hu/update/winepkgs.tar | tar xf -

echo
echo "Installing extra packages..."

export WINEARCH=win32

echo "exit" | wine cmd
wine msiexec /i python-2.7.15.msi
wine msiexec /i cefpython3-31.2.py2.7-win32.msi
wine msiexec /i pygtk-all-in-one-2.24.1.win32-py2.7.msi
wine msiexec /i pyuipc-0.4.win32-py2.7.msi
wine msiexec /i xplra-0.2.win32.msi

wine pywin32-217.win32-py2.7.exe
wine py2exe-0.6.9.win32-py2.7.exe
wine nsis-2.46-setup.exe

mkdir "${ctmpdir}"
cp chromedriver.exe "${ctmpdir}"

tar xzf Python27.extra.tar.gz -C "${cpythondir}"

echo
echo "Removing extra packages..."
rm -f *.msi *.exe Python27.extra.tar.gz python27.dll WINHTTP.dll
echo
echo "Done."
