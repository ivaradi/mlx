set scriptdir=%~dp0

set PYTHONPATH=%scriptdir%\src;%PYTHONPATH%

python.exe -m runmlx
