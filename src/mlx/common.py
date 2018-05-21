import os

#-----------------------------------------------------------------------------

## @package mlx.common
#
# Common definitions to be used by both the GUI and possible other parts
#
# The main purpose of this module is to import Gtk+2 or 3 and related modules
# and provide common names for them. There is a similator module in the GUI
# part (\ref mlx.gui.common), which contains the GUI-specific names. This one
# contains only what is used by other modules as well.
# The variable \c pygobject tells which version of Gtk is being used. If it is
# \c True, Gtk+ 3 is used via the PyGObject interface. Otherwise Gtk+ 2 is
# used, which is the default on Windows or when the \c FORCE_PYGTK environment
# variable is set.

#---------------------------------------------------------------------------------------

#MAVA_BASE_URL = os.environ.get("MAVA_BASE_URL", "http://virtualairlines.hu")
MAVA_BASE_URL = os.environ.get("MAVA_BASE_URL", "http://oldmava.mavasystems.hu")

#-------------------------------------------------------------------------------

# Due to CEF, PyGTK is the default
if "FORCE_PYGOBJECT" not in os.environ:
    print "Using PyGTK"
    pygobject = False
    import gobject
else:
    print "Using PyGObject"
    pygobject = True

    from gi.repository import GObject as gobject
