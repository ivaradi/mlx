
from mlx.common import *

import mlx.const as _const
from mlx.i18n import xstr

from mlx.util import secondaryInstallation

import os
import time
import calendar

#-----------------------------------------------------------------------------

## @package mlx.gui.common
#
# Common definitions and utilities for the GUI

#-----------------------------------------------------------------------------

appIndicator = False

import gi
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk
from gi.repository import GdkPixbuf
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
try:
    gi.require_version("AppIndicator3", "0.1")
    from gi.repository import AppIndicator3
    appIndicator = True
except:
    pass
from gi.repository import Pango
gi.require_version("PangoCairo", "1.0")
from gi.repository import PangoCairo
from gi.repository import GLib

import codecs
_utf8Decoder = codecs.getdecoder("utf-8")

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

class IntegerEntry(Gtk.Entry):
    """An entry that allows only either an empty value, or an integer."""
    def __init__(self, defaultValue = None):
        """Construct the entry."""
        Gtk.Entry.__init__(self)

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

class TimeEntry(Gtk.Entry):
    """Widget to display and edit a time value in HH:MM format."""
    def __init__(self):
        """Construct the entry"""
        super(TimeEntry, self).__init__()
        self.set_max_width_chars(5)

        self.connect("insert-text", self._insertText)
        self.connect("delete-text", self._deleteText)
        self.connect("focus-out-event", self._focusOutEvent)

    @property
    def hour(self):
        """Get the hour from the current text"""
        text = self.get_text()
        if not text or text==":":
            return 0

        words = text.split(":")
        if len(words)==1:
            return 0
        elif len(words)>=2:
            return 0 if len(words[0])==0 else int(words[0])
        else:
            return 0

    @property
    def minute(self):
        """Get the hour from the current text"""
        text = self.get_text()
        if not text or text==":":
            return 0

        words = text.split(":")
        if len(words)==1:
            return 0 if len(words[0])==0 else int(words[0])
        elif len(words)>=2:
            return 0 if len(words[1])==0 else int(words[1])
        else:
            return 0

    @property
    def minutes(self):
        """Get the time in minutes, i.e. hour*60+minute."""
        return self.hour * 60 + self.minute

    def setTimestamp(self, timestamp):
        """Set the hour and minute from the given timestamp in UTC."""
        tm = time.gmtime(timestamp)
        self.set_text("%02d:%02d" % (tm.tm_hour, tm.tm_min))

    def getTimestampFrom(self, timestamp):
        """Get the timestamp by replacing the hour and minute from the given
        timestamp with what is set in this widget."""
        tm = time.gmtime(timestamp)
        ts = calendar.timegm((tm.tm_year, tm.tm_mon, tm.tm_mday,
                              self.hour, self.minute, 0,
                              tm.tm_wday, tm.tm_yday, tm.tm_isdst))

        if ts > (timestamp + (16*60*60)):
            ts -= 24*60*60
        elif (ts + 16*60*60) < timestamp:
            ts += 24*60*60

        return ts

    def _focusOutEvent(self, widget, event):
        """Reformat the text to match pattern HH:MM"""
        text = "%02d:%02d" % (self.hour, self.minute)
        if text!=self.get_text():
            self.set_text(text)

    def _insertText(self, entry, text, length, position):
        """Called when some text is inserted into the entry."""
        text=text[:length]
        currentText = self.get_text()
        position = self.get_position()
        newText = currentText[:position] + text + currentText[position:]
        self._checkText(newText, "insert-text")

    def _deleteText(self, entry, start, end):
        """Called when some text is erased from the entry."""
        currentText = self.get_text()
        newText = currentText[:start] + currentText[end:]
        self._checkText(newText, "delete-text")

    def _checkText(self, newText, signal):
        """Check the given text.

        If it is not suitable, stop the emission of the signal to prevent the
        change from appearing."""
        if not newText or newText==":":
            return

        words = newText.split(":")
        if (len(words)==1 and
            len(words[0])<=2 and (len(words[0])==0 or
                                  (words[0].isdigit() and int(words[0])<60))) or \
           (len(words)==2 and
            len(words[0])<=2 and (len(words[0])==0 or
                                  (words[0].isdigit() and int(words[0])<24)) and
            len(words[1])<=2 and (len(words[1])==0 or
                                  (words[1].isdigit() and int(words[1])<60))):
            pass
        else:
            Gtk.gdk.display_get_default().beep()
            self.stop_emission(signal)

#------------------------------------------------------------------------------

class CredentialsDialog(Gtk.Dialog):
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
                                                Gtk.DialogFlags.MODAL)
        self.add_button(cancelButtonLabel, Gtk.ResponseType.CANCEL)
        self.add_button(okButtonLabel, Gtk.ResponseType.OK)

        contentArea = self.get_content_area()

        contentAlignment = Gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                         xscale = 0.0, yscale = 0.0)
        contentAlignment.set_padding(padding_top = 4, padding_bottom = 16,
                                     padding_left = 8, padding_right = 8)

        contentArea.pack_start(contentAlignment, False, False, 0)

        contentVBox = Gtk.VBox()
        contentAlignment.add(contentVBox)

        if infoText is not None:
            label = Gtk.Label(infoText)
            label.set_alignment(0.0, 0.0)

            contentVBox.pack_start(label, False, False, 0)

        tableAlignment = Gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                       xscale = 0.0, yscale = 0.0)
        tableAlignment.set_padding(padding_top = 24, padding_bottom = 0,
                                   padding_left = 0, padding_right = 0)

        table = Gtk.Table(3, 2)
        table.set_row_spacings(4)
        table.set_col_spacings(16)
        table.set_homogeneous(False)

        tableAlignment.add(table)
        contentVBox.pack_start(tableAlignment, True, True, 0)

        label = Gtk.Label(userNameLabel)
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, 0, 1)

        self._userName = Gtk.Entry()
        self._userName.set_width_chars(16)
        # FIXME: enabled the OK button only when there is something in thr
        # user name and password fields
        #self._userName.connect("changed",
        #                       lambda button: self._updateForwardButton())
        self._userName.set_tooltip_text(userNameTooltip)
        self._userName.set_text(userName)
        table.attach(self._userName, 1, 2, 0, 1)
        label.set_mnemonic_widget(self._userName)

        label = Gtk.Label(passwordLabel)
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, 1, 2)

        self._password = Gtk.Entry()
        self._password.set_visibility(False)
        #self._password.connect("changed",
        #                       lambda button: self._updateForwardButton())
        self._password.set_tooltip_text(passwordTooltip)
        self._password.set_text(password)
        table.attach(self._password, 1, 2, 1, 2)
        label.set_mnemonic_widget(self._password)

        if rememberPassword is not None:
            self._rememberButton = Gtk.CheckButton(rememberLabel)
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

GObject.signal_new("integer-changed", IntegerEntry, GObject.SIGNAL_RUN_FIRST,
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
                  _const.AIRCRAFT_B732  : xstr("aircraft_b732"),
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

aircraftFamilyNames = {
    _const.AIRCRAFT_FAMILY_B737NG: xstr("aircraft_family_b737ng"),

    _const.AIRCRAFT_FAMILY_B737CL: xstr("aircraft_family_b737cl"),

    _const.AIRCRAFT_FAMILY_DH8D: xstr("aircraft_family_dh8d"),

    _const.AIRCRAFT_FAMILY_B767: xstr("aircraft_family_b767"),

    _const.AIRCRAFT_FAMILY_CRJ2: xstr("aircraft_family_crj2"),

    _const.AIRCRAFT_FAMILY_F70: xstr("aircraft_family_f70"),

    _const.AIRCRAFT_FAMILY_DC3: xstr("aircraft_family_dc3"),

    _const.AIRCRAFT_FAMILY_T134: xstr("aircraft_family_t134"),

    _const.AIRCRAFT_FAMILY_T154: xstr("aircraft_family_t154"),

    _const.AIRCRAFT_FAMILY_YK40: xstr("aircraft_family_yk40"),

    _const.AIRCRAFT_FAMILY_B462: xstr("aircraft_family_b462")
}

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
    buffer.create_tag("fault", foreground="red", weight=Pango.Weight.BOLD)

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

def askYesNo(question, parent = None, title = WINDOW_TITLE_BASE):
    """Ask a Yes/No question.

    Return a boolean indicating the answer."""
    dialog = Gtk.MessageDialog(parent = parent,
                               type = Gtk.MessageType.QUESTION,
                               message_format = question)

    dialog.add_button(xstr("button_no"), Gtk.ResponseType.NO)
    dialog.add_button(xstr("button_yes"), Gtk.ResponseType.YES)

    dialog.set_title(title)
    result = dialog.run()
    dialog.hide()

    return result==Gtk.ResponseType.YES

#------------------------------------------------------------------------------

def errorDialog(message, parent = None, secondary = None,
                title = WINDOW_TITLE_BASE):
    """Display an error dialog box with the given message."""
    dialog = Gtk.MessageDialog(parent = parent,
                               type = Gtk.MessageType.ERROR,
                               message_format = message)
    dialog.add_button(xstr("button_ok"), Gtk.ResponseType.OK)
    dialog.set_title(title)
    if secondary is not None:
        dialog.format_secondary_markup(secondary)

    dialog.run()
    dialog.hide()

#------------------------------------------------------------------------------

def communicationErrorDialog(parent = None, title = WINDOW_TITLE_BASE):
    """Display a communication error dialog."""
    errorDialog(xstr("error_communication"), parent = parent,
                secondary = xstr("error_communication_secondary"),
                title = title)

#------------------------------------------------------------------------------

def createFlightTypeComboBox():
        flightTypeModel = Gtk.ListStore(str, int)
        for type in _const.flightTypes:
            name = "flighttype_" + _const.flightType2string(type)
            flightTypeModel.append([xstr(name), type])

        flightType = Gtk.ComboBox(model = flightTypeModel)
        renderer = Gtk.CellRendererText()
        flightType.pack_start(renderer, True)
        flightType.add_attribute(renderer, "text", 0)

        return flightType

#------------------------------------------------------------------------------

def getTextViewText(textView):
    """Get the text from the given text view."""
    buffer = textView.get_buffer()
    return buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), True)

#------------------------------------------------------------------------------
