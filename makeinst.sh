#!/bin/bash

#set MSVCRDIR=c:\windows\winsxs\x86_Microsoft.VC90.CRT*9.0.21022.8*
if test "${WINE}" = "yes"; then
    cdrive="/root/.wine/drive_c/"
    MINGW32DIR="c:/msys64/mingw32"

    export GTKRTDIR="${MINGW32DIR}"
    export CEFDIR="${MINGW32DIR}/lib/python3.7/site-packages/cefpython3"

    export PYTHONHASHSEED=1234
    export PYTHONIOENCODING=utf8
    export PYTHONUTF8=1

    wine "${cdrive}/msys64/mingw32/bin/python3.exe" setup.py py2exe

    wine "${cdrive}/Program Files/NSIS/makensis.exe" mlx.nsi
else
    export GTKRTDIR=/mingw32
    export CEFDIR=/mingw32/lib/python3.7/site-packages/cefpython3
#set CHROMEDRIVER=c:\tmp\chromedriver.exe
    export NSISDIR=/c/Program Files/NSIS

    python3 setup.py py2exe
    "$NSISDIR/makensis.exe" mlx.nsi
fi

#del dist\library\selenium\webdriver\chrome\service.pyc
#copy patches\library\selenium\webdriver\chrome\service.py dist\library\selenium\webdriver\chrome\service.py
#python -m compileall dist\library\selenium\webdriver\chrome\service.py
#del dist\library\selenium\webdriver\chrome\service.py
