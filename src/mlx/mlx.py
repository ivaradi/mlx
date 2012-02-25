# The main program

from .gui.gui import GUI
from .gui.common import *

import os

def main(iconDirectory):
    """The main operation of the program."""
    gui = GUI()

    gui.build(iconDirectory)

    gui.run()

if __name__ == "__main__":
    main(os.path.dirname(__file__))


