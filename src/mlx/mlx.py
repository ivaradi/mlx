# The main program

from .gui.gui import GUI

from config import Config

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

def main():
    """The main operation of the program."""
    programDirectory = os.path.dirname(sys.argv[0])

    config = Config()
    gui = GUI(programDirectory, config)

    sys.stdout = StdIOHandler(gui)
    sys.stderr = StdIOHandler(gui)

    gui.build(programDirectory)

    gui.run()

#--------------------------------------------------------------------------------------

if __name__ == "__main__":
    main()
