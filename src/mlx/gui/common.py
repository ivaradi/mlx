# Common things for the GUI

import os

appIndicator = False

if os.name=="nt" or "FORCE_PYGTK" in os.environ:
    print "Using PyGTK"
    pygobject = False
    import pygtk
    import gtk
    import gobject
    try:
        import appindicator
        appIndicator = True
    except Exception, e:
        pass
else:
    print "Using PyGObject"
    pygobject = True
    from gi.repository import Gtk as gtk
    from gi.repository import GObject as gobject
    from gi.repository import AppIndicator3 as appindicator
    appIndicator = True

import cairo

