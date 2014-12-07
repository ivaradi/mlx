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

#-------------------------------------------------------------------------------

if os.name=="nt" or "FORCE_PYGTK" in os.environ:
    print "Using PyGTK"
    pygobject = False
    import gobject
    try:
        import pygst
        pygst.require('0.10')
        import gst

        def gst_element_factory_make(what):
            return gst.element_factory_make(what)

        GST_STATE_PLAYING=gst.STATE_PLAYING
        GST_MESSAGE_EOS=gst.MESSAGE_EOS
    except:
        pass
else:
    print "Using PyGObject"
    pygobject = True

    from gi.repository import GObject as gobject

    try:
        from gi.repository import Gst as gst

        def gst_element_factory_make(what):
            return gst.ElementFactory.make(what)

        GST_STATE_PLAYING=gst.State.PLAYING
        GST_MESSAGE_EOS=gst.MessageType.EOS
    except:
        import traceback
        traceback.print_exc()
        pass
