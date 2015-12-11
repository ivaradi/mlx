set MSVCRDIR=c:\windows\winsxs\x86_Microsoft.VC90.CRT*9.0.21022.8*
set GTKRTDIR=c:\Python27\Lib\site-packages\gtk-2.0\runtime
set CEFDIR=c:\Python27\Lib\site-packages\cefpython3
set CHROMEDRIVER=c:\tmp\chromedriver.exe
set NSISDIR=C:\Program Files\NSIS

python setup.py py2exe

del dist\library\selenium\webdriver\chrome\service.pyc
copy patches\library\selenium\webdriver\chrome\service.py dist\library\selenium\webdriver\chrome\service.py
python -m compileall dist\library\selenium\webdriver\chrome\service.py
del dist\library\selenium\webdriver\chrome\service.py

"%NSISDIR%\makensis" mlx.nsi
