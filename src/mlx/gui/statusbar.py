
from .common import *

import mlx.const as const
from mlx.i18n import xstr

import math
import time

#-------------------------------------------------------------------------------

## @package mlx.gui.statusbar
#
# The status bar.
#
# This module implements the status bar seen at the lower part of the main
# window. It contains the icon depicting the status of the connection to the
# simulator, the current flight stage, rating and the simulator time.

#-------------------------------------------------------------------------------

class Statusbar(Gtk.Frame, FlightStatusHandler):
    """A status bar for the logger."""
    def __init__(self, iconDirectory):
        """Construct the status bar."""
        Gtk.Frame.__init__(self)
        FlightStatusHandler.__init__(self)

        self._connecting = False
        self._connected = False
        
        self.set_shadow_type(Gtk.ShadowType.NONE)

        frameAlignment = Gtk.Alignment(xscale = 1.0, yscale = 1.0)

        frameAlignment.set_padding(padding_top = 2, padding_bottom = 2,
                                   padding_left = 16, padding_right = 16)
        self.add(frameAlignment)

        statusBox = Gtk.HBox()
        frameAlignment.add(statusBox)

        iconPath = os.path.join(iconDirectory, "conn_grey.png")
        self._connGreyIcon = pixbuf_new_from_file(iconPath)

        iconPath = os.path.join(iconDirectory, "conn_red.png")
        self._connRedIcon = pixbuf_new_from_file(iconPath)

        iconPath = os.path.join(iconDirectory, "conn_green.png")
        self._connGreenIcon = pixbuf_new_from_file(iconPath)

        self._connStateArea = Gtk.DrawingArea()
        self._connStateArea.set_size_request(18, 18)
        self._connStateArea.set_tooltip_markup(xstr("statusbar_conn_tooltip"))

        self._connStateArea.connect("draw", self._drawConnState)

        alignment = Gtk.Alignment(xalign = 0.5, yalign = 0.5)
        alignment.add(self._connStateArea)        

        statusBox.pack_start(alignment, False, False, 8)

        statusBox.pack_start(Gtk.VSeparator(), False, False, 8)

        self._stageLabel = Gtk.Label()
        longestStage = xstr("flight_stage_" +
                            const.stage2string(const.STAGE_PUSHANDTAXI))
        self._stageLabel.set_width_chars(len(longestStage) + 3)
        self._stageLabel.set_tooltip_text(xstr("statusbar_stage_tooltip"))
        self._stageLabel.set_alignment(0.0, 0.5)
        
        statusBox.pack_start(self._stageLabel, False, False, 8)

        statusBox.pack_start(Gtk.VSeparator(), False, False, 8)

        self._timeLabel = Gtk.Label("--:--:--")
        self._timeLabel.set_width_chars(8)
        self._timeLabel.set_tooltip_text(xstr("statusbar_time_tooltip"))
        self._timeLabel.set_alignment(1.0, 0.5)
        
        statusBox.pack_start(self._timeLabel, False, False, 8)

        statusBox.pack_start(Gtk.VSeparator(), False, False, 8)

        self._ratingLabel = Gtk.Label()
        self._ratingLabel.set_width_chars(20)
        self._ratingLabel.set_tooltip_text(xstr("statusbar_rating_tooltip"))
        self._ratingLabel.set_alignment(0.0, 0.5)
        
        statusBox.pack_start(self._ratingLabel, False, False, 8)

        self._busyLabel = Gtk.Label()
        self._busyLabel.set_width_chars(30)
        self._busyLabel.set_tooltip_text(xstr("statusbar_busy_tooltip"))
        self._busyLabel.set_alignment(1.0, 0.5)
        statusBox.pack_start(self._busyLabel, True, True, 8)
        
        self._updateFlightStatus()
        self.updateTime()

    def updateConnection(self, connecting, connected):
        """Update the connection status."""
        self._connecting = connecting
        self._connected = connected
        self._connStateArea.queue_draw()

    def updateBusyState(self, message):
        """Update the busy state."""
        self._busyLabel.set_text("" if message is None else message)

    def updateTime(self, t = None):
        """Update the time"""
        timeStr = "--:--:--" if t is None \
                  else time.strftime("%H:%M:%S", time.gmtime(t))
        
        self._timeLabel.set_text(timeStr)

    def _drawConnState(self, connStateArea, eventOrContext):
        """Draw the connection state."""
        if self._connecting:
            if self._connected:
                icon = self._connGreenIcon
            else:
                icon = self._connRedIcon
        else:
            icon = self._connGreyIcon

        gdk.cairo_set_source_pixbuf(eventOrContext, icon, 0, 0)
        eventOrContext.paint()

    def _updateFlightStatus(self):
        """Update the flight status information."""
        if self._stage is None:
            text = "-"
        else:
            text = xstr("flight_stage_" + const.stage2string(self._stage)).upper()
        self._stageLabel.set_text(text)
    
        if self._noGoReason is None:
            rating = "%.1f%%" % (self._rating,)
        else:
            rating = '<span foreground="red">' + self._noGoReason + '</span>'
        self._ratingLabel.set_markup(rating)
