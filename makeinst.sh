#!/bin/bash

#set MSVCRDIR=c:\windows\winsxs\x86_Microsoft.VC90.CRT*9.0.21022.8*
export GTKRTDIR=/mingw32
export CEFDIR=/mingw32/lib/python3.7/site-packages/cefpython3
#set CHROMEDRIVER=c:\tmp\chromedriver.exe
#set NSISDIR=C:\Program Files\NSIS

python3 setup.py py2exe

#del dist\library\selenium\webdriver\chrome\service.pyc
#copy patches\library\selenium\webdriver\chrome\service.py dist\library\selenium\webdriver\chrome\service.py
#python -m compileall dist\library\selenium\webdriver\chrome\service.py
#del dist\library\selenium\webdriver\chrome\service.py

#"%NSISDIR%\makensis" mlx.nsi
