set MSVCRDIR=c:\windows\winsxs\x86_Microsoft.VC90.CRT*9.0.21022.8*
set GTKRTDIR=c:\Python27\Lib\site-packages\gtk-2.0\runtime
set NSISDIR=C:\Program Files\NSIS

python setup.py py2exe

"%NSISDIR%\makensis" mlx.nsi
