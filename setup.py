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

defaultManifest="""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
  <trustInfo xmlns="urn:schemas-microsoft-com:asm.v3">
    <security>
      <requestedPrivileges>
        <requestedExecutionLevel level="asInvoker"/>
      </requestedPrivileges>
    </security>
  </trustInfo>
  <compatibility xmlns="urn:schemas-microsoft-com:compatibility.v1">
    <application>
      <!--The ID below indicates application support for Windows Vista -->
      <supportedOS Id="{e2011457-1546-43c5-a5fe-008deee3d3f0}"/>
      <!--The ID below indicates application support for Windows 7 -->
      <supportedOS Id="{35138b9a-5d96-4fbd-8e2d-a2440225f93a}"/>
      <!--The ID below indicates application support for Windows 8 -->
      <supportedOS Id="{4a2f28e3-53b9-4441-ba9c-d69d4a4a6e38}"/>
      <!--The ID below indicates application support for Windows 8.1 -->
      <supportedOS Id="{1f676c76-80e1-4239-95bb-83d0f6d0da78}"/>
      <!--The ID below indicates application support for Windows 10 -->
      <supportedOS Id="{8e0f7a12-bfb3-4fe8-b9a5-48fd50a15a9a}"/>
    </application>
  </compatibility>
</assembly>"""

adminManifest=defaultManifest.replace("asInvoker", "requireAdministrator")

RT_MANIFEST=24

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

        if gtkRuntimeDir:
            gtkBinDir = os.path.join(gtkRuntimeDir, "bin")
            data_files.append(("", [
                                os.path.join(gtkBinDir, "libatk-1.0-0.dll"),
                                os.path.join(gtkBinDir, "libbz2-1.dll"),
                                os.path.join(gtkBinDir, "libcairo-2.dll"),
                                os.path.join(gtkBinDir, "libcairo-gobject-2.dll"),
                                os.path.join(gtkBinDir, "libcroco-0.6-3.dll"),
                                os.path.join(gtkBinDir, "libcrypto-1_1.dll"),
                                os.path.join(gtkBinDir, "libdatrie-1.dll"),
                                os.path.join(gtkBinDir, "libepoxy-0.dll"),
                                os.path.join(gtkBinDir, "libexpat-1.dll"),
                                os.path.join(gtkBinDir, "libexslt-0.dll"),
                                os.path.join(gtkBinDir, "libffi-6.dll"),
                                os.path.join(gtkBinDir, "libfontconfig-1.dll"),
                                os.path.join(gtkBinDir, "libfreetype-6.dll"),
                                os.path.join(gtkBinDir, "libfribidi-0.dll"),
                                os.path.join(gtkBinDir, "libgcc_s_dw2-1.dll"),
                                os.path.join(gtkBinDir, "libgdk_pixbuf-2.0-0.dll"),
                                os.path.join(gtkBinDir, "libgio-2.0-0.dll"),
                                os.path.join(gtkBinDir, "libgirepository-1.0-1.dll"),
                                os.path.join(gtkBinDir, "libglib-2.0-0.dll"),
                                os.path.join(gtkBinDir, "libgmodule-2.0-0.dll"),
                                os.path.join(gtkBinDir, "libgobject-2.0-0.dll"),
                                os.path.join(gtkBinDir, "libgraphite2.dll"),
                                os.path.join(gtkBinDir, "libharfbuzz-0.dll"),
                                os.path.join(gtkBinDir, "libiconv-2.dll"),
                                os.path.join(gtkBinDir, "libintl-8.dll"),
                                os.path.join(gtkBinDir, "liblzma-5.dll"),
                                os.path.join(gtkBinDir, "libmpdec-2.dll"),
                                os.path.join(gtkBinDir, "libpango-1.0-0.dll"),
                                os.path.join(gtkBinDir, "libpangocairo-1.0-0.dll"),
                                os.path.join(gtkBinDir, "libpangoft2-1.0-0.dll"),
                                os.path.join(gtkBinDir, "libpangowin32-1.0-0.dll"),
                                os.path.join(gtkBinDir, "libpcre-1.dll"),
                                os.path.join(gtkBinDir, "libpixman-1-0.dll"),
                                os.path.join(gtkBinDir, "libpng16-16.dll"),
                                os.path.join(gtkBinDir, "librsvg-2-2.dll"),
                                os.path.join(gtkBinDir, "libssl-1_1.dll"),
                                os.path.join(gtkBinDir, "libssp-0.dll"),
                                os.path.join(gtkBinDir, "libstdc++-6.dll"),
                                os.path.join(gtkBinDir, "libthai-0.dll"),
                                os.path.join(gtkBinDir, "libwinpthread-1.dll"),
                                os.path.join(gtkBinDir, "libxml2-2.dll"),
                                os.path.join(gtkBinDir, "libxslt-1.dll"),
                                os.path.join(gtkBinDir, "zlib1.dll"),
                              ]))
        if cefDir:
            data_files.append(("", [
                                os.path.join(cefDir, "libcef.dll"),
                                os.path.join(cefDir, "chrome_elf.dll")
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
                   "icon_resources" : [(1, "logo.ico")],
                   "other_resources": [(RT_MANIFEST, 1, defaultManifest)]},
                 { "script" : "mlxupdate.py",
                   "other_resources": [(RT_MANIFEST, 1, adminManifest)]}],
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
