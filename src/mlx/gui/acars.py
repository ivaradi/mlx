
from .common import *

from mlx.i18n import xstr
import mlx.const as const

from . import cef

#------------------------------------------------------------------------------

## @package mlx.gui.acars
#
# The ACARS tab.
#
# This module implements to \ref ACARS class, which displays the MAVA ACARS in a
# browser window using CEF

#------------------------------------------------------------------------------

class ACARS(Gtk.VBox):
    """The flight info tab."""
    # The URL of the ACARS map
    URL = MAVA_BASE_URL + "/acars2/show.html"

    def __init__(self, gui):
        """Construct the flight info tab."""
        super(ACARS, self).__init__()
        self._gui = gui
        self._browser = None

    def start(self):
        """Start the browser."""
        container = cef.getContainer()

        self.pack_start(container, True, True, 0)

        self._browser = cef.startInContainer(container, ACARS.URL)

    def stop(self):
        """Close the browser."""
        if self._browser is not None:
            self._browser.CloseBrowser(False)
            self._browser = None
