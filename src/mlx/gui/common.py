
from mlx.common import *

import mlx.const as _const
from mlx.i18n import xstr

from mlx.util import secondaryInstallation

import os

#-----------------------------------------------------------------------------

## @package mlx.gui.common
#
# Common definitions and utilities for the GUI
#
# The main purpose of this module is to provide common definitions for things
# that are named differently in Gtk+ 2 and 3. This way the other parts of the
# GUI have to check the version in use very rarely. The variable \c pygobject
# tells which version is being used. If it is \c True, Gtk+ 3 is used via the
# PyGObject interface. Otherwise Gtk+ 2 is used, which is the default on
# Windows or when the \c FORCE_PYGTK environment variable is set.
#
# Besides this there are some common utility classes and functions.

#-----------------------------------------------------------------------------

appIndicator = False

if not pygobject:
    print "Using PyGTK"
    pygobject = False
    import pygtk
    pygtk.require("2.0")
    import gtk.gdk as gdk
    import gtk
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
    JUSTIFY_LEFT = gtk.JUSTIFY_LEFT

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
    SHADOW_NONE = gtk.SHADOW_NONE

    POLICY_AUTOMATIC = gtk.POLICY_AUTOMATIC
    POLICY_NEVER = gtk.POLICY_NEVER
    POLICY_ALWAYS = gtk.POLICY_ALWAYS

    WEIGHT_NORMAL = pango.WEIGHT_NORMAL
    WEIGHT_BOLD = pango.WEIGHT_BOLD

    WINDOW_STATE_ICONIFIED = gdk.WINDOW_STATE_ICONIFIED
    WINDOW_STATE_WITHDRAWN = gdk.WINDOW_STATE_WITHDRAWN

    SORT_ASCENDING = gtk.SORT_ASCENDING
    SORT_DESCENDING = gtk.SORT_DESCENDING

    EVENT_BUTTON_PRESS = gdk.BUTTON_PRESS

    TREE_VIEW_COLUMN_FIXED = gtk.TREE_VIEW_COLUMN_FIXED

    FILL = gtk.FILL
    EXPAND = gtk.EXPAND

    UPDATE_IF_VALID = gtk.UPDATE_IF_VALID

    pixbuf_new_from_file = gdk.pixbuf_new_from_file

    def text2unicode(text):
        """Convert the given text, returned by a Gtk widget, to Unicode."""
        return unicode(text)

    def text2str(text):
        """Convert the given text, returned by xstr to a string."""
        return str(text)

else: # pygobject
    from gi.repository import Gdk as gdk
    from gi.repository import GdkPixbuf as gdkPixbuf
    from gi.repository import Gtk as gtk
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
    JUSTIFY_LEFT = gtk.Justification.LEFT

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
    SHADOW_NONE = gtk.ShadowType.NONE

    POLICY_AUTOMATIC = gtk.PolicyType.AUTOMATIC
    POLICY_NEVER = gtk.PolicyType.NEVER
    POLICY_ALWAYS = gtk.PolicyType.ALWAYS

    WEIGHT_NORMAL = pango.Weight.NORMAL
    WEIGHT_BOLD = pango.Weight.BOLD

    WINDOW_STATE_ICONIFIED = gdk.WindowState.ICONIFIED
    WINDOW_STATE_WITHDRAWN = gdk.WindowState.WITHDRAWN

    SORT_ASCENDING = gtk.SortType.ASCENDING
    SORT_DESCENDING = gtk.SortType.DESCENDING

    EVENT_BUTTON_PRESS = gdk.EventType.BUTTON_PRESS

    TREE_VIEW_COLUMN_FIXED = gtk.TreeViewColumnSizing.FIXED

    FILL = gtk.AttachOptions.FILL
    EXPAND = gtk.AttachOptions.EXPAND

    UPDATE_IF_VALID = gtk.SpinButtonUpdatePolicy.IF_VALID

    pixbuf_new_from_file = gdkPixbuf.Pixbuf.new_from_file

    import codecs
    _utf8Decoder = codecs.getdecoder("utf-8")

    def text2unicode(str):
        """Convert the given text, returned by a Gtk widget, to Unicode."""
        return _utf8Decoder(str)[0]

    def text2str(text):
        """Convert the given text, returned by xstr to a string."""
        return _utf8Decoder(text)[0]

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

    def reset(self):
        """Reset the integer."""
        self.set_int(None)

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

class CredentialsDialog(gtk.Dialog):
    """A dialog window to ask for a user name and a password."""
    def __init__(self, gui, userName, password,
                 titleLabel, cancelButtonLabel, okButtonLabel,
                 userNameLabel, userNameTooltip,
                 passwordLabel, passwordTooltip,
                 infoText = None,
                 rememberPassword = None,
                 rememberLabel = None, rememberTooltip = None):
        """Construct the dialog."""
        super(CredentialsDialog, self).__init__(WINDOW_TITLE_BASE + " - " +
                                                titleLabel,
                                                gui.mainWindow,
                                                DIALOG_MODAL)
        self.add_button(cancelButtonLabel, RESPONSETYPE_CANCEL)
        self.add_button(okButtonLabel, RESPONSETYPE_OK)

        contentArea = self.get_content_area()

        contentAlignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                         xscale = 0.0, yscale = 0.0)
        contentAlignment.set_padding(padding_top = 4, padding_bottom = 16,
                                     padding_left = 8, padding_right = 8)

        contentArea.pack_start(contentAlignment, False, False, 0)

        contentVBox = gtk.VBox()
        contentAlignment.add(contentVBox)

        if infoText is not None:
            label = gtk.Label(infoText)
            label.set_alignment(0.0, 0.0)

            contentVBox.pack_start(label, False, False, 0)

        tableAlignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                       xscale = 0.0, yscale = 0.0)
        tableAlignment.set_padding(padding_top = 24, padding_bottom = 0,
                                   padding_left = 0, padding_right = 0)

        table = gtk.Table(3, 2)
        table.set_row_spacings(4)
        table.set_col_spacings(16)
        table.set_homogeneous(False)

        tableAlignment.add(table)
        contentVBox.pack_start(tableAlignment, True, True, 0)

        label = gtk.Label(userNameLabel)
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, 0, 1)

        self._userName = gtk.Entry()
        self._userName.set_width_chars(16)
        # FIXME: enabled the OK button only when there is something in thr
        # user name and password fields
        #self._userName.connect("changed",
        #                       lambda button: self._updateForwardButton())
        self._userName.set_tooltip_text(userNameTooltip)
        self._userName.set_text(userName)
        table.attach(self._userName, 1, 2, 0, 1)
        label.set_mnemonic_widget(self._userName)

        label = gtk.Label(passwordLabel)
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, 1, 2)

        self._password = gtk.Entry()
        self._password.set_visibility(False)
        #self._password.connect("changed",
        #                       lambda button: self._updateForwardButton())
        self._password.set_tooltip_text(passwordTooltip)
        self._password.set_text(password)
        table.attach(self._password, 1, 2, 1, 2)
        label.set_mnemonic_widget(self._password)

        if rememberPassword is not None:
            self._rememberButton = gtk.CheckButton(rememberLabel)
            self._rememberButton.set_use_underline(True)
            self._rememberButton.set_tooltip_text(rememberTooltip)
            self._rememberButton.set_active(rememberPassword)
            table.attach(self._rememberButton, 1, 2, 2, 3, ypadding = 8)
        else:
            self._rememberButton = None

    @property
    def userName(self):
        """Get the user name entered."""
        return self._userName.get_text()

    @property
    def password(self):
        """Get the password entered."""
        return self._password.get_text()

    @property
    def rememberPassword(self):
        """Get whether the password is to be remembered."""
        return None if self._rememberButton is None \
               else self._rememberButton.get_active()

    def run(self):
        """Run the dialog."""
        self.show_all()

        response = super(CredentialsDialog, self).run()

        self.hide()

        return response

#------------------------------------------------------------------------------

gobject.signal_new("integer-changed", IntegerEntry, gobject.SIGNAL_RUN_FIRST,
                   None, (object,))

#------------------------------------------------------------------------------

PROGRAM_NAME = "MAVA Logger X"

WINDOW_TITLE_BASE = PROGRAM_NAME + " " + _const.VERSION
if secondaryInstallation:
    WINDOW_TITLE_BASE += " (" + xstr("secondary") + ")"

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
                  _const.AIRCRAFT_YK40  : xstr("aircraft_yk40"),
                  _const.AIRCRAFT_B462  : xstr("aircraft_b462") }

#------------------------------------------------------------------------------

def formatFlightLogLine(timeStr, line):
    """Format the given flight log line."""
    """Format the given line for flight logging."""
    if timeStr is not None:
        line = timeStr + ": " + line
    return line + "\n"

#------------------------------------------------------------------------------

def addFaultTag(buffer):
    """Add a tag named 'fault' to the given buffer."""
    buffer.create_tag("fault", foreground="red", weight=WEIGHT_BOLD)

#------------------------------------------------------------------------------

def appendTextBuffer(buffer, text, isFault = False):
    """Append the given line at the end of the given text buffer.

    If isFault is set, use the tag named 'fault'."""
    insertTextBuffer(buffer, buffer.get_end_iter(), text, isFault)

#------------------------------------------------------------------------------

def insertTextBuffer(buffer, iter, text, isFault = False):
    """Insert the given line into the given text buffer at the given iterator.

    If isFault is set, use the tag named 'fault' else use the tag named
    'normal'."""
    line = iter.get_line()

    buffer.insert(iter, text)

    iter0 = buffer.get_iter_at_line(line)
    iter1 = buffer.get_iter_at_line(line+1)
    if isFault:
        buffer.apply_tag_by_name("fault", iter0, iter1)
    else:
        buffer.remove_all_tags(iter0, iter1)

#------------------------------------------------------------------------------
