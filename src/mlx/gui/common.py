# Common things for the GUI

import mlx.const as _const
from mlx.i18n import xstr

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

    RESPONSETYPE_OK = gtk.RESPONSE_OK
    RESPONSETYPE_YES = gtk.RESPONSE_YES
    RESPONSETYPE_NO = gtk.RESPONSE_NO
    RESPONSETYPE_ACCEPT = gtk.RESPONSE_ACCEPT
    RESPONSETYPE_REJECT = gtk.RESPONSE_REJECT
    RESPONSETYPE_CANCEL = gtk.RESPONSE_CANCEL

    ACCEL_VISIBLE = gtk.ACCEL_VISIBLE
    CONTROL_MASK = gdk.CONTROL_MASK
    DIALOG_MODAL = gtk.DIALOG_MODAL
    WRAP_WORD = gtk.WRAP_WORD
    JUSTIFY_CENTER = gtk.JUSTIFY_CENTER

    CONTROL_MASK = gdk.CONTROL_MASK
    SHIFT_MASK = gdk.SHIFT_MASK
    BUTTON1_MASK = gdk.BUTTON1_MASK

    SCROLL_UP = gdk.SCROLL_UP
    SCROLL_DOWN = gdk.SCROLL_DOWN

    SPIN_USER_DEFINED = gtk.SPIN_USER_DEFINED

    FILE_CHOOSER_ACTION_SELECT_FOLDER = gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER
    FILE_CHOOSER_ACTION_OPEN = gtk.FILE_CHOOSER_ACTION_OPEN
    FILE_CHOOSER_ACTION_SAVE = gtk.FILE_CHOOSER_ACTION_SAVE

    SELECTION_MULTIPLE = gtk.SELECTION_MULTIPLE

    SHADOW_IN = gtk.SHADOW_IN

    POLICY_AUTOMATIC = gtk.POLICY_AUTOMATIC

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
    RESPONSETYPE_OK = gtk.ResponseType.OK
    RESPONSETYPE_YES = gtk.ResponseType.YES
    RESPONSETYPE_NO = gtk.ResponseType.NO
    RESPONSETYPE_ACCEPT = gtk.ResponseType.ACCEPT
    RESPONSETYPE_REJECT = gtk.ResponseType.REJECT
    RESPONSETYPE_CANCEL = gtk.ResponseType.CANCEL
    ACCEL_VISIBLE = gtk.AccelFlags.VISIBLE
    CONTROL_MASK = gdk.ModifierType.CONTROL_MASK
    DIALOG_MODAL = gtk.DialogFlags.MODAL
    WRAP_WORD = gtk.WrapMode.WORD
    JUSTIFY_CENTER = gtk.Justification.CENTER

    CONTROL_MASK = gdk.ModifierType.CONTROL_MASK
    SHIFT_MASK = gdk.ModifierType.SHIFT_MASK
    BUTTON1_MASK = gdk.ModifierType.BUTTON1_MASK

    SCROLL_UP = gdk.ScrollDirection.UP
    SCROLL_DOWN = gdk.ScrollDirection.DOWN

    SPIN_USER_DEFINED = gtk.SpinType.USER_DEFINED

    FILE_CHOOSER_ACTION_SELECT_FOLDER = gtk.FileChooserAction.SELECT_FOLDER
    FILE_CHOOSER_ACTION_OPEN = gtk.FileChooserAction.OPEN
    FILE_CHOOSER_ACTION_SAVE = gtk.FileChooserAction.SAVE

    SELECTION_MULTIPLE = gtk.SelectionMode.MULTIPLE

    SHADOW_IN = gtk.ShadowType.IN

    POLICY_AUTOMATIC = gtk.PolicyType.AUTOMATIC

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

# A mapping of aircraft types to their screen names
aircraftNames = { _const.AIRCRAFT_B736  : xstr("aircraft_b736"),
                  _const.AIRCRAFT_B737  : xstr("aircraft_b737"),
                  _const.AIRCRAFT_B738  : xstr("aircraft_b738"),
                  _const.AIRCRAFT_B738C : xstr("aircraft_b738c"),
                  _const.AIRCRAFT_B733  : xstr("aircraft_b733"),
                  _const.AIRCRAFT_B734  : xstr("aircraft_b734"),
                  _const.AIRCRAFT_B735  : xstr("aircraft_b735"),
                  _const.AIRCRAFT_DH8D  : xstr("aircraft_dh8d"),
                  _const.AIRCRAFT_B762  : xstr("aircraft_b762"),
                  _const.AIRCRAFT_B763  : xstr("aircraft_b763"),
                  _const.AIRCRAFT_CRJ2  : xstr("aircraft_crj2"),
                  _const.AIRCRAFT_F70   : xstr("aircraft_f70"),
                  _const.AIRCRAFT_DC3   : xstr("aircraft_dc3"),
                  _const.AIRCRAFT_T134  : xstr("aircraft_t134"),
                  _const.AIRCRAFT_T154  : xstr("aircraft_t154"),
                  _const.AIRCRAFT_YK40  : xstr("aircraft_yk40") }

#------------------------------------------------------------------------------

def formatFlightLogLine(timeStr, line):
    """Format the given flight log line."""
    """Format the given line for flight logging."""
    if timeStr is not None:
        line = timeStr + ": " + line
    return line + "\n"

#------------------------------------------------------------------------------
