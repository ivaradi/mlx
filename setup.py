# -*- coding: iso-8859-2 -*-

import sys
import os
from glob import glob
from distutils.core import setup

sys.path.insert(0, os.path.join(os.path.dirname(sys.argv[0]), "src"))

import mlx.const

data_files = []
if os.name=="nt":
    import py2exe

    data_files.append(("", ["logo.ico"]))

    msvcrDir = os.environ["MSVCRDIR"] if "MSVCRDIR" in os.environ else None
    if msvcrDir:
        data_files.append(("Microsoft.VC90.CRT",  glob(os.path.join(msvcrDir, "*.*"))))

    gtkRuntimeDir = os.environ["GTKRTDIR"] if "GTKRTDIR" in os.environ else None
    if gtkRuntimeDir:
        path = os.path.join("lib", "gtk-2.0", "2.10.0", "engines")
        data_files.append((path, [os.path.join(gtkRuntimeDir, path, "libwimp.dll")]))

        path = os.path.join("share", "themes", "MS-Windows", "gtk-2.0")
        data_files.append((path, glob(os.path.join(gtkRuntimeDir, path, "*"))))
        
    with open("mlx-common.nsh", "wt") as f:
            print >>f, '!define MLX_VERSION "%s"' % (mlx.const.VERSION)
            f.close()

long_description="""MAVA Logger X

This is a program to log and evaluate the actions
of a pilot flying a virtual Malév flight operated
by MAVA."""

setup(name = "mlx",
      version = mlx.const.VERSION,
      description = "MAVA Logger X",
      long_description = long_description,
      author = "István Váradi",
      author_email = "ivaradi@gmail.com",
      url = "http://mlx.varadiistvan.hu",
      package_dir = { "" : "src" },
      packages = ["mlx", "mlx.gui"],
      requires = ["pyuipc"],
      windows = [{ "script" : "runmlx.py",
                   "icon_resources" : [(1, "logo.ico")]}],
      options = { "py2exe" : { "includes": "gio, pango, atk, pangocairo"} },
      data_files = data_files,
      platforms = ["Win32", "Linux"],
      license = "Public Domain"
      )
