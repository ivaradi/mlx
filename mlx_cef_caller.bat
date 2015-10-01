#!/bin/sh

SET scriptdir=%~dp0
scriptdir=`dirname $0`

echo %* > %TEMP%\mlxcef.args.tmp
move %TEMP%\mlxcef.args.tmp %TEMP%\mlxcef.args
