# The main program

from .gui.gui import GUI

from config import Config

import os
import sys

if os.name=="nt":
    import win32api

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

def main():
    """The main operation of the program."""
    programDirectory = os.path.dirname(sys.argv[0])

    config = Config()
    gui = GUI(programDirectory, config)
    
    sys.stdout = StdIOHandler(gui)
    sys.stderr = StdIOHandler(gui)

    try:
        gui.build(programDirectory)
        
        gui.run()
    finally:
        gui.flushStdIO()
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

    if gui.toRestart:
        programPath = os.path.join(os.path.dirname(sys.argv[0]),
                                   "runmlx.exe" if os.name=="nt" else "runmlx.sh")
        if os.name=="nt":
            programPath = win32api.GetShortPathName(programPath)

        os.execl(programPath, programPath)

#--------------------------------------------------------------------------------------

if __name__ == "__main__":
    main()
