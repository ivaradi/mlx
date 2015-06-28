from common import *

import platform
import json

from cefpython3 import cefpython

import os
import re

#------------------------------------------------------------------------------

## @package mlx.gui.cef
#
# Some helper stuff related to the Chrome Embedded Framework

#------------------------------------------------------------------------------

# Indicate if we should quit
_toQuit = False

#------------------------------------------------------------------------------

def initialize():
    """Initialize the Chrome Embedded Framework."""
    global _toQuit
    _toQuit = False

    gobject.threads_init()

    settings = {
        "debug": True, # cefpython debug messages in console and in log_file
        "log_severity": cefpython.LOGSEVERITY_VERBOSE, # LOGSEVERITY_VERBOSE
        "log_file": "", # Set to "" to disable
        "release_dcheck_enabled": True, # Enable only when debugging
        # This directories must be set on Linux
        "locales_dir_path": os.path.join(cefpython.GetModuleDirectory(), "locales"),
        "resources_dir_path": cefpython.GetModuleDirectory(),
        "browser_subprocess_path": "%s/%s" % \
            (cefpython.GetModuleDirectory(), "subprocess"),
    }

    cefpython.Initialize(settings, {})

    gobject.timeout_add(10, _handleTimeout)

#------------------------------------------------------------------------------

def getContainer():
    """Get a container object suitable for running a browser instance
    within."""
    if os.name=="nt":
        container = gtk.DrawingArea()
        container.set_property("can-focus", True)
        container.connect("size-allocate", _handleSizeAllocate)
    else:
        container = gtk.VBox(True, 0)

    container.show()

    return container

#------------------------------------------------------------------------------

def startInContainer(container, url, browserSettings = {}):
    """Start a browser instance in the given container with the given URL."""
    if os.name=="nt":
        windowID = container.get_window().handle
    else:
        m = re.search("GtkVBox at 0x(\w+)", str(container))
        hexID = m.group(1)
        windowID = int(hexID, 16)

    windowInfo = cefpython.WindowInfo()
    windowInfo.SetAsChild(windowID)

    return cefpython.CreateBrowserSync(windowInfo,
                                       browserSettings = browserSettings,
                                       navigateUrl = url)

#------------------------------------------------------------------------------

def finalize():
    """Finalize the Chrome Embedded Framework."""
    global _toQuit
    toQuit = True
    cefpython.Shutdown()

#------------------------------------------------------------------------------

def _handleTimeout():
    """Handle the timeout by running the CEF message loop."""
    if _toQuit:
        return False
    else:
        cefpython.MessageLoopWork()
        return True

#------------------------------------------------------------------------------

def _handleSizeAllocate(widget, sizeAlloc):
    """Handle the size-allocate event."""
    cefpython.WindowUtils.OnSize(widget.get_window().handle, 0, 0, 0)
