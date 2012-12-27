
from config import Config
from i18n import setLanguage
from sound import initializeSound
from util import secondaryInstallation
from const import VERSION

import os
import sys

#--------------------------------------------------------------------------------------

## @package mlx.mlx
#
# The main program.
#
# This module contains the main program of the logger as well as the \ref
# restart "restart" handling.

#--------------------------------------------------------------------------------------

instance = None

#--------------------------------------------------------------------------------------

class StdIOHandler(object):
    """Handler for the standard I/O messages."""
    def __init__(self, gui):
        """Construct the handler."""
        self._gui = gui

    def write(self, text):
        """Write the given text into the log."""
        self._gui.writeStdIO(text)

#--------------------------------------------------------------------------------------

def restart(args = []):
    """Restart the program with the given arguments."""
    #print "Restarting with args", args
    programPath = os.path.join(os.path.dirname(sys.argv[0]),
                               "runmlx.exe" if os.name=="nt" else "runmlx.sh")
    if os.name=="nt":
        import win32api
        try:
            programPath = win32api.GetShortPathName(programPath)
        except:
            programPath = os.path.join(os.path.dirname(sys.argv[0]),
                                       "runmlx.bat")
            programPath = win32api.GetShortPathName(programPath)

    args = [programPath] + args

    instance.close()
    os.execv(programPath, args)

#--------------------------------------------------------------------------------------

def main():
    """The main operation of the program."""
    from singleton import SingleInstance, raiseCallbackWrapper

    global instance
    instance = SingleInstance("mlx" + ("-secondary" if secondaryInstallation
                                       else ""), raiseCallbackWrapper)
    if not instance: return

    programDirectory = os.path.dirname(sys.argv[0])

    config = Config()
    config.load()

    secondaryArgs = ["secondary"] if secondaryInstallation else []
    if "usedeflang" not in sys.argv and config.setupLocale():
        restart(["usedeflang"] + secondaryArgs)

    setLanguage(programDirectory, config.getLanguage())

    from .gui.gui import GUI
    gui = GUI(programDirectory, config)

    sys.stdout = StdIOHandler(gui)
    sys.stderr = StdIOHandler(gui)

    print "MAVA Logger X " + VERSION + " debug log"
    print "The initial configuration:"
    config.log()

    initializeSound(os.path.join(programDirectory, "sounds"))

    try:
        gui.build(programDirectory)

        gui.run()
    finally:
        gui.flushStdIO()
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

    config.save()

    if gui.toRestart:
        restart(secondaryArgs)

#--------------------------------------------------------------------------------------

if __name__ == "__main__":
    if instance:
        main()
