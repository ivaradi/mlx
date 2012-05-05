# The main program

from config import Config
from i18n import setLanguage
from sound import initializeSound

import os
import sys

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
    print "Restarting with args", args
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

    os.execv(programPath, args)    

#--------------------------------------------------------------------------------------

def main():
    """The main operation of the program."""
    programDirectory = os.path.dirname(sys.argv[0])

    config = Config()
    config.load()

    if (len(sys.argv)<=1 or sys.argv[1]!="usedeflang") and config.setupLocale():
        restart(["usedeflang"])

    setLanguage(config.getLanguage())
    
    from .gui.gui import GUI
    gui = GUI(programDirectory, config)
    
    sys.stdout = StdIOHandler(gui)
    sys.stderr = StdIOHandler(gui)

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
        restart()

#--------------------------------------------------------------------------------------

if __name__ == "__main__":
    main()
