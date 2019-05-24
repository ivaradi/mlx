#!/bin/bash

set -e -u

echo "Installing extra packages..."

pacman -S --noconfirm mc patch unzip openssh ca-certificates mingw-w64-i686-python3 mingw-w64-i686-python3-setuptools mingw-w64-i686-gcc  mingw-w64-i686-gtk3 mingw-w64-i686-python3-lxml mingw-w64-i686-cmake mingw-w64-i686-make mingw-w64-i686-python3-pip mingw-w64-i686-python3-pillow mingw-w64-i686-python3-gobject mingw-w64-i686-python3-cffi
pacman -Scc --noconfirm

pip3 install jsonrpclib-pelix
