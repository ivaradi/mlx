#!/bin/sh

SET scriptdir=%~dp0
scriptdir=`dirname $0`

echo %* > %TEMP%\mlxcef.args.secondary.tmp
move %TEMP%\mlxcef.args.secondary.tmp %TEMP%\mlxcef.args.secondary
