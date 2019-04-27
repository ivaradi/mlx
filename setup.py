# -*- coding: iso-8859-2 -*-

import sys
import os
from glob import glob
from distutils.core import setup
from pathlib import Path

scriptdir=os.path.dirname(sys.argv[0])
sys.path.insert(0, os.path.join(scriptdir, "src"))

import mlx.const
import mlx.update

data_files = [("sounds", glob(os.path.join("sounds", "*.*")))]
for language in ["en", "hu"]:
    data_files.append((os.path.join("doc", "manual", language),
                       glob(os.path.join("doc", "manual", language, "*.*"))))
    data_files.append((os.path.join("locale", language, "LC_MESSAGES"),
                       [os.path.join("locale", language, "LC_MESSAGES",
                                     "mlx.mo")]))

rootFiles = ["logo.png", "conn_grey.png", "conn_red.png", "conn_green.png"]
if os.name!="nt":
    rootFiles.append("Microsoft.VC90.CRT.manifest")
data_files.append(("", rootFiles))

if os.name=="nt":
    import py2exe

    data_files.append(("", ["logo.ico"]))

    msvcrDir = os.environ["MSVCRDIR"] if "MSVCRDIR" in os.environ else None
    if msvcrDir:
        data_files.append(("Microsoft.VC90.CRT",
                           ["Microsoft.VC90.CRT.manifest"] +
                           glob(os.path.join(msvcrDir, "*.*"))))
        os.environ["PATH"] = os.environ["PATH"] + ";" + glob(os.path.join(msvcrDir))[0]


    gtkRuntimeDir = os.environ["GTKRTDIR"] if "GTKRTDIR" in os.environ else None
    if gtkRuntimeDir:
        if gtkRuntimeDir.endswith("/mingw32"):
            path = os.path.join("lib", "girepository-1.0")
            data_files.append((path,
                               glob(os.path.join(gtkRuntimeDir, path, "*"))))

            files = {}

            for components in [ ["lib", "girepository-1.0"],
                                ["lib", "gdk-pixbuf-2.0", "2.10.0"],
                                ["share", "icons"],
                                ["share", "locale", "hu"],
                                ["share", "locale", "en"],
                                ["share", "themes"],
                                ["share", "glib-2.0", "schemas"]]:
                path = os.path.join(*components)
                p = Path(os.path.join(gtkRuntimeDir, path))
                for f in p.glob("**/*"):
                    if f.is_file():
                        d = os.path.join(path, str(f.parent.relative_to(p)))
                        if d in files:
                            files[d].append(str(f))
                        else:
                            files[d] = [str(f)]

            for path in files:
                data_files.append((path, files[path]))
            data_files.append(("",
                               [os.path.join(gtkRuntimeDir, "bin", "librsvg-2-2.dll"),
                                os.path.join(gtkRuntimeDir, "bin", "libcroco-0.6-3.dll")]))
        else:
            path = os.path.join("lib", "gtk-2.0", "2.10.0", "engines")
            data_files.append((os.path.join("library", path),
                               [os.path.join(gtkRuntimeDir, path, "libwimp.dll")]))

            path = os.path.join("share", "themes", "MS-Windows", "gtk-2.0")
            data_files.append((os.path.join("library", path),
                               glob(os.path.join(gtkRuntimeDir, path, "*"))))

            path = os.path.join("share", "locale", "hu", "LC_MESSAGES")
            data_files.append((os.path.join("library", path),
                               glob(os.path.join(gtkRuntimeDir, path, "*"))))
            path = os.path.join("share", "icons", "hicolor")
            data_files.append((os.path.join("library", path),
                               glob(os.path.join(gtkRuntimeDir, path, "*"))))

    cefDir = os.environ.get("CEFDIR")
    if cefDir:
        for fileName in ["icudtl.dat", "subprocess.exe", "natives_blob.bin",
                         "snapshot_blob.bin", "v8_context_snapshot.bin",
                         "cef.pak", "cef_100_percent.pak",
                         "cef_200_percent.pak", "cef_extensions.pak"]:
            data_files.append(("", [os.path.join(cefDir, fileName)]))

        data_files.append(("locales",
                           glob(os.path.join(cefDir, "locales", "*"))))

    if os.getenv("WINE")=="yes":
        winsysdir=os.getenv("WINSYSDIR")
        data_files.append(("", [os.path.join(winsysdir, "python27.dll")]))
        data_files.append(("library", [
                            os.path.join(winsysdir, "pywintypes27.dll"),
                            os.path.join(winsysdir, "WINHTTP.dll")]))

        if gtkRuntimeDir:
            gtkBinDir = os.path.join(gtkRuntimeDir, "bin")
            data_files.append(("library", [
                                os.path.join(gtkBinDir, "freetype6.dll"),
                                os.path.join(gtkBinDir, "intl.dll"),
                                os.path.join(gtkBinDir, "zlib1.dll"),
                                os.path.join(gtkBinDir, "libglib-2.0-0.dll"),
                                os.path.join(gtkBinDir, "libatk-1.0-0.dll"),
                                os.path.join(gtkBinDir, "libcairo-2.dll"),
                                os.path.join(gtkBinDir, "libexpat-1.dll"),
                                os.path.join(gtkBinDir, "libpangowin32-1.0-0.dll"),
                                os.path.join(gtkBinDir, "libgio-2.0-0.dll"),
                                os.path.join(gtkBinDir, "libgdk-win32-2.0-0.dll"),
                                os.path.join(gtkBinDir, "libpng14-14.dll"),
                                os.path.join(gtkBinDir, "libgobject-2.0-0.dll"),
                                os.path.join(gtkBinDir, "libgdk_pixbuf-2.0-0.dll"),
                                os.path.join(gtkBinDir, "libfontconfig-1.dll"),
                                os.path.join(gtkBinDir, "libpangoft2-1.0-0.dll"),
                                os.path.join(gtkBinDir, "libgmodule-2.0-0.dll"),
                                os.path.join(gtkBinDir, "libpango-1.0-0.dll"),
                                os.path.join(gtkBinDir, "libpangocairo-1.0-0.dll"),
                                os.path.join(gtkBinDir, "libgtk-win32-2.0-0.dll"),
                                os.path.join(gtkBinDir, "libgthread-2.0-0.dll")
                              ]))
        if cefDir:
            data_files.append(("library", [
                                os.path.join(cefDir, "libcef.dll")
                              ]))

    print(data_files)

    with open("mlx-common.nsh", "wt") as f:
            print('!define MLX_VERSION "%s"' % (mlx.const.VERSION), file=f)
            f.close()
else:
    for (dirpath, dirnames, filenames) in os.walk("patches"):
        if filenames:
            filenames = [os.path.join(dirpath, filename)
                         for filename in filenames]
            data_files.append((dirpath, filenames))


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
      requires = ["pyuipc", "xplra"],
      windows = [{ "script" : "runmlx.py",
                   "icon_resources" : [(1, "logo.ico")]},
                 { "script" : "mlxupdate.py",
                   "uac_info" : "requireAdministrator"}],
      options = { "py2exe" : { "packages" : "gi, lxml",
                               "skip_archive": True} },
      zipfile = "library",
      data_files = data_files,
      platforms = ["Win32", "Linux"],
      license = "Public Domain"
      )

if os.name=="nt":
    mlx.update.buildManifest(os.path.join(scriptdir, "dist"))
    with open(os.path.join(scriptdir, "dist", "Uninstall.conf"), "wt") as f:
        print("StartMenuFolder=MAVA Logger X", file=f)
        print("LinkName=MAVA Logger X", file=f)
