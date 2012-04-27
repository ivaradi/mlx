# Implementation of the status bar.

#-------------------------------------------------------------------------------

from common import *

import mlx.const as const
from mlx.i18n import xstr

import math
import time

#-------------------------------------------------------------------------------

class Statusbar(gtk.Frame, FlightStatusHandler):
    """A status bar for the logger."""
    def __init__(self):
        """Construct the status bar."""
        gtk.Frame.__init__(self)
        FlightStatusHandler.__init__(self)

        self._connecting = False
        self._connected = False
        
        self.set_shadow_type(gtk.ShadowType.NONE if pygobject
                             else gtk.SHADOW_NONE)

        frameAlignment = gtk.Alignment(xscale = 1.0, yscale = 1.0)

        frameAlignment.set_padding(padding_top = 2, padding_bottom = 2,
                                   padding_left = 16, padding_right = 16)
        self.add(frameAlignment)

        statusBox = gtk.HBox()
        frameAlignment.add(statusBox)

        self._connStateArea = gtk.DrawingArea()
        self._connStateArea.set_size_request(16, 16)
        self._connStateArea.set_tooltip_markup(xstr("statusbar_conn_tooltip"))

        if pygobject:
            self._connStateArea.connect("draw", self._drawConnState)
        else:
            self._connStateArea.connect("expose_event", self._drawConnState)

        alignment = gtk.Alignment(xalign = 0.5, yalign = 0.5)
        alignment.add(self._connStateArea)        

        statusBox.pack_start(alignment, False, False, 8)

        statusBox.pack_start(gtk.VSeparator(), False, False, 8)

        self._stageLabel = gtk.Label()
        longestStage = xstr("flight_stage_" +
                            const.stage2string(const.STAGE_PUSHANDTAXI))
        self._stageLabel.set_width_chars(len(longestStage) + 3)
        self._stageLabel.set_tooltip_text(xstr("statusbar_stage_tooltip"))
        self._stageLabel.set_alignment(0.0, 0.5)
        
        statusBox.pack_start(self._stageLabel, False, False, 8)

        statusBox.pack_start(gtk.VSeparator(), False, False, 8)

        self._timeLabel = gtk.Label("--:--:--")
        self._timeLabel.set_width_chars(8)
        self._timeLabel.set_tooltip_text(xstr("statusbar_time_tooltip"))
        self._timeLabel.set_alignment(1.0, 0.5)
        
        statusBox.pack_start(self._timeLabel, False, False, 8)

        statusBox.pack_start(gtk.VSeparator(), False, False, 8)

        self._ratingLabel = gtk.Label()
        self._ratingLabel.set_width_chars(12)
        self._ratingLabel.set_tooltip_text(xstr("statusbar_rating_tooltip"))
        self._ratingLabel.set_alignment(0.0, 0.5)
        
        statusBox.pack_start(self._ratingLabel, False, False, 8)

        self._busyLabel = gtk.Label()
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
        context = eventOrContext if pygobject else connStateArea.window.cairo_create()

        if self._connecting:
            if self._connected:
                context.set_source_rgb(0.0, 1.0, 0.0)
            else:
                context.set_source_rgb(1.0, 0.0, 0.0)
        else:
            context.set_source_rgb(0.75, 0.75, 0.75)

        width = connStateArea.get_allocated_width() if pygobject \
                else connStateArea.allocation.width
        height = connStateArea.get_allocated_height() if pygobject \
                 else connStateArea.allocation.height
        context.arc(width/2, height/2, width/2, 0, 2*math.pi)

        context.fill()

    def _updateFlightStatus(self):
        """Update the flight status information."""
        if self._stage is None:
            text = "-"
        else:
            text = xstr("flight_stage_" + const.stage2string(self._stage)).upper()
        self._stageLabel.set_text(text)
    
        if self._noGoReason is None:
            rating = "%.0f%%" % (self._rating,)
        else:
            rating = '<span foreground="red">' + self._noGoReason + '</span>'
        self._ratingLabel.set_markup(rating)
