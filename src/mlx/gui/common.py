# Common things for the GUI

import mlx.const as _const

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
    MESSAGETYPE_INFO = gtk.MESSAGE_INFO
    BUTTONSTYPE_OK = gtk.BUTTONS_OK
    BUTTONSTYPE_YES_NO = gtk.BUTTONS_YES_NO
    RESPONSETYPE_YES = gtk.RESPONSE_YES
    ACCEL_VISIBLE = gtk.ACCEL_VISIBLE
    CONTROL_MASK = gdk.CONTROL_MASK

    def text2unicode(text):
        """Convert the given text, returned by a Gtk widget, to Unicode."""
        return unicode(text)
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
    MESSAGETYPE_INFO = gtk.MessageType.INFO
    BUTTONSTYPE_OK = gtk.ButtonsType.OK
    BUTTONSTYPE_YES_NO = gtk.ButtonsType.YES_NO
    RESPONSETYPE_YES = gtk.ResponseType.YES
    ACCEL_VISIBLE = gtk.AccelFlags.VISIBLE
    CONTROL_MASK = gdk.ModifierType.CONTROL_MASK

    import codecs
    _utf8Decoder = codecs.getdecoder("utf-8")
    
    def text2unicode(str):
        """Convert the given text, returned by a Gtk widget, to Unicode."""
        return _utf8Decoder(str)[0]

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

class IntegerEntry(gtk.Entry):
    """An entry that allows only either an empty value, or an integer."""
    def __init__(self, defaultValue = None):
        """Construct the entry."""
        gtk.Entry.__init__(self)

        self.set_alignment(1.0)

        self._defaultValue = defaultValue
        self._currentInteger = defaultValue
        self._selfSetting = False
        self._set_text()

        self.connect("changed", self._handle_changed)

    def get_int(self):
        """Get the integer."""
        return self._currentInteger

    def set_int(self, value):
        """Set the integer."""
        if value!=self._currentInteger:
            self._currentInteger = value
            self.emit("integer-changed", self._currentInteger)
        self._set_text()
    
    def _handle_changed(self, widget):
        """Handle the changed signal."""
        if self._selfSetting:
            return
        text = self.get_text()
        if text=="":
            self.set_int(self._defaultValue)
        else:
            try:
                self.set_int(int(text))
            except:
                self._set_text()

    def _set_text(self):
        """Set the text value from the current integer."""
        self._selfSetting = True
        self.set_text("" if self._currentInteger is None
                      else str(self._currentInteger))
        self._selfSetting = False
                
#------------------------------------------------------------------------------

gobject.signal_new("integer-changed", IntegerEntry, gobject.SIGNAL_RUN_FIRST,
                   None, (object,))

#------------------------------------------------------------------------------

WINDOW_TITLE_BASE = "MAVA Logger X " + _const.VERSION

#------------------------------------------------------------------------------
