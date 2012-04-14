# Common things for the GUI

import os

appIndicator = False

if os.name=="nt" or "FORCE_PYGTK" in os.environ:
    print "Using PyGTK"
    pygobject = False
    import pygtk
    import gtk.gdk as gdk
    import gtk
    import gobject
    import pango
    try:
        import appindicator
        appIndicator = True
    except Exception, e:
        pass

    MESSAGETYPE_ERROR = gtk.MESSAGE_ERROR
    MESSAGETYPE_QUESTION = gtk.MESSAGE_QUESTION
    BUTTONSTYPE_OK = gtk.BUTTONS_OK
    BUTTONSTYPE_YES_NO = gtk.BUTTONS_YES_NO
    RESPONSETYPE_YES = gtk.RESPONSE_YES
else:
    print "Using PyGObject"
    pygobject = True
    from gi.repository import Gdk as gdk
    from gi.repository import Gtk as gtk
    from gi.repository import GObject as gobject
    from gi.repository import AppIndicator3 as appindicator
    from gi.repository import Pango as pango
    appIndicator = True
    
    MESSAGETYPE_ERROR = gtk.MessageType.ERROR
    MESSAGETYPE_QUESTION = gtk.MessageType.QUESTION
    BUTTONSTYPE_OK = gtk.ButtonsType.OK
    BUTTONSTYPE_YES_NO = gtk.ButtonsType.YES_NO
    RESPONSETYPE_YES = gtk.ResponseType.YES

import cairo

#------------------------------------------------------------------------------

class FlightStatusHandler(object):
    """Base class for objects that handle the flight status in some way."""
    def __init__(self):
        self._stage = None
        self._rating = 100
        self._noGoReason = None

    def resetFlightStatus(self):
        """Reset the flight status."""
        self._stage = None
        self._rating = 100
        self._noGoReason = None
        self._updateFlightStatus()
        
    def setStage(self, stage):
        """Set the stage of the flight."""
        if stage!=self._stage:
            self._stage = stage
            self._updateFlightStatus()

    def setRating(self, rating):
        """Set the rating to the given value."""
        if rating!=self._rating:
            self._rating = rating
            if self._noGoReason is None:
                self._updateFlightStatus()

    def setNoGo(self, reason):
        """Set a No-Go condition with the given reason."""
        if self._noGoReason is None:
            self._noGoReason = reason
            self._updateFlightStatus()

#------------------------------------------------------------------------------
