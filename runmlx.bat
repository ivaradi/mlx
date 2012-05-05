@echo off

set scriptdir=%~dp0

set PYTHONPATH=%scriptdir%\src;%PYTHONPATH%

python.exe -m runmlx %1 %2 %3 %4 %5 %6 %7 %8 %9
