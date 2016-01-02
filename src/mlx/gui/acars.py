
from common import *

from mlx.i18n import xstr
import mlx.const as const

import cef

#------------------------------------------------------------------------------

## @package mlx.gui.acars
#
# The ACARS tab.
#
# This module implements to \ref ACRS class, which displays the MAVA ACARS in a
# browser window using CEF

#------------------------------------------------------------------------------

class ACARS(gtk.VBox):
    """The flight info tab."""
    # The URL of the ACARS map
    URL = MAVA_BASE_URL + "/acars2/show.html"

    def __init__(self, gui):
        """Construct the flight info tab."""
        super(ACARS, self).__init__()
        self._gui = gui

    def start(self):
        """Start the browser."""
        container = cef.getContainer()

        self.pack_start(container, True, True, 0)

        cef.startInContainer(container, ACARS.URL)
