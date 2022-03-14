
from .common import *
from .dcdata import getTable
from .info import FlightInfo
from .flight import comboModel

from mlx.pirep import PIREP
from mlx.flight import Flight
from mlx.const import *

import time
import re

#------------------------------------------------------------------------------

## @package mlx.gui.pirep
#
# The detailed PIREP viewer and editor windows.
#
# The \ref PIREPViewer class is a dialog displaying all information found in a
# PIREP. It consists of three tabs. The Data tab displays the simple,
# itemizable data. The Comments & defects tab contains the flight comments and
# defects, while the Log tab contains the flight log collected by the
# \ref mlx.logger.Logger "logger".

#------------------------------------------------------------------------------

class MessageFrame(Gtk.Frame):
    """A frame containing the information about a PIREP message.

    It consists of a text view with the heading information (author, time) and
    another text view with the actual message."""
    def __init__(self, message, senderPID, senderName):
        """Construct the frame."""
        Gtk.Frame.__init__(self)

        vbox = Gtk.VBox()

        self._heading = heading = Gtk.TextView()
        heading.set_editable(False)
        heading.set_can_focus(False)
        heading.set_wrap_mode(Gtk.WrapMode.WORD)
        heading.set_size_request(-1, 16)

        buffer = heading.get_buffer()
        self._headingTag  = buffer.create_tag("heading", weight=Pango.Weight.BOLD)
        buffer.set_text("%s - %s" % (senderPID, senderName))
        buffer.apply_tag(self._headingTag,
                         buffer.get_start_iter(), buffer.get_end_iter())

        headingAlignment = Gtk.Alignment(xalign = 0.0, yalign = 0.0,
                                         xscale = 1.0, yscale = 0.0)
        headingAlignment.set_padding(padding_top = 0, padding_bottom = 0,
                                     padding_left = 2, padding_right = 2)
        headingAlignment.add(heading)
        vbox.pack_start(headingAlignment, True, True, 4)

        self._messageView = messageView = Gtk.TextView()
        messageView.set_wrap_mode(Gtk.WrapMode.WORD)
        messageView.set_editable(False)
        messageView.set_can_focus(False)
        messageView.set_accepts_tab(False)
        messageView.set_size_request(-1, 60)

        buffer = messageView.get_buffer()
        buffer.set_text(message)

        vbox.pack_start(messageView, True, True, 4)

        self.add(vbox)
        self.show_all()

        styleContext = self.get_style_context()
        color = styleContext.get_background_color(Gtk.StateFlags.NORMAL)
        heading.override_background_color(0, color)


#-------------------------------------------------------------------------------

class MessagesWidget(Gtk.Frame):
    """The widget for the messages."""
    @staticmethod
    def getFaultFrame(alignment):
        """Get the fault frame from the given alignment."""
        return alignment.get_children()[0]

    def __init__(self, gui):
        Gtk.Frame.__init__(self)

        self._gui = gui
        self.set_label(xstr("pirep_messages"))
        label = self.get_label_widget()
        label.set_use_underline(True)

        alignment = Gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 1.0, yscale = 1.0)
        alignment.set_padding(padding_top = 4, padding_bottom = 4,
                              padding_left = 4, padding_right = 4)

        self._outerBox = outerBox = Gtk.EventBox()
        outerBox.add(alignment)

        self._innerBox = innerBox = Gtk.EventBox()
        alignment.add(self._innerBox)

        alignment = Gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 1.0, yscale = 1.0)
        alignment.set_padding(padding_top = 0, padding_bottom = 0,
                              padding_left = 0, padding_right = 0)

        innerBox.add(alignment)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroller.set_shadow_type(Gtk.ShadowType.NONE)

        self._messages = Gtk.VBox()
        self._messages.set_homogeneous(False)
        scroller.add_with_viewport(self._messages)

        alignment.add(scroller)

        self._messageWidgets = []

        self.add(outerBox)
        self.show_all()

    def addMessage(self, message):
        """Add a message from the given sender."""

        alignment = Gtk.Alignment(xalign = 0.0, yalign = 0.0,
                                      xscale = 1.0, yscale = 0.0)
        alignment.set_padding(padding_top = 2, padding_bottom = 2,
                              padding_left = 4, padding_right = 4)

        messageFrame = MessageFrame(message.message,
                                    message.senderPID,
                                    message.senderName)

        alignment.add(messageFrame)
        self._messages.pack_start(alignment, False, False, 4)
        self._messages.show_all()

        self._messageWidgets.append((alignment, messageFrame))

    def reset(self):
        """Reset the widget by removing all messages."""
        for (alignment, messageFrame) in self._messageWidgets:
            self._messages.remove(alignment)
        self._messages.show_all()

        self._messageWidgets = []

#------------------------------------------------------------------------------

class PIREPViewer(Gtk.Dialog):
    """The dialog for PIREP viewing."""
    @staticmethod
    def createFrame(label):
        """Create a frame with the given label.

        The frame will contain an alignment to properly distance the
        insides. The alignment will contain a VBox to contain the real
        contents.

        The function returns a tuple with the following items:
        - the frame,
        - the inner VBox."""
        frame = Gtk.Frame(label = label)

        alignment = Gtk.Alignment(xalign = 0.0, yalign = 0.0,
                                  xscale = 1.0, yscale = 1.0)
        frame.add(alignment)
        alignment.set_padding(padding_top = 4, padding_bottom = 4,
                              padding_left = 4, padding_right = 4)
        box = Gtk.VBox()
        alignment.add(box)

        return (frame, box)

    @staticmethod
    def getLabel(text, extraText = ""):
        """Get a bold label with the given text."""
        label = Gtk.Label("<b>" + text + "</b>" + extraText)
        label.set_use_markup(True)
        label.set_alignment(0.0, 0.5)
        return label

    @staticmethod
    def getDataLabel(width = None, xAlignment = 0.0):
        """Get a bold label with the given text."""
        label = Gtk.Label()
        if width is not None:
            label.set_width_chars(width)
        label.set_alignment(xAlignment, 0.5)
        return label

    @staticmethod
    def getTextWindow(heightRequest = 40, editable = False):
        """Get a scrollable text window.

        Returns a tuple of the following items:
        - the window,
        - the text view."""
        scrolledWindow = Gtk.ScrolledWindow()
        scrolledWindow.set_shadow_type(Gtk.ShadowType.IN)
        scrolledWindow.set_policy(Gtk.PolicyType.AUTOMATIC,
                                  Gtk.PolicyType.AUTOMATIC)

        textView = Gtk.TextView()
        textView.set_wrap_mode(Gtk.WrapMode.WORD)
        textView.set_editable(editable)
        textView.set_cursor_visible(editable)
        textView.set_size_request(-1, heightRequest)
        scrolledWindow.add(textView)

        return (scrolledWindow, textView)

    @staticmethod
    def tableAttach(table, column, row, labelText, width = None,
                    dataLabelXAlignment = 0.0):
        """Attach a labeled data to the given column and row of the
        table.

        If width is given, that will be the width of the data
        label.

        Returns the data label attached."""
        dataBox = Gtk.HBox()
        table.attach(dataBox, column, column+1, row, row+1)

        dataLabel = PIREPViewer.addLabeledData(dataBox, labelText,
                                               width = width)
        dataLabel.set_alignment(dataLabelXAlignment, 0.5)

        return dataLabel

    @staticmethod
    def addLabeledData(hBox, labelText, width = None, dataPadding = 8):
        """Add a label and a data label to the given HBox.

        Returns the data label."""
        label = PIREPViewer.getLabel(labelText)
        hBox.pack_start(label, False, False, 0)

        dataLabel = PIREPViewer.getDataLabel(width = width)
        hBox.pack_start(dataLabel, False, False, dataPadding)

        return dataLabel

    @staticmethod
    def addHFiller(hBox, width = 8):
        """Add a filler to the given horizontal box."""
        filler = Gtk.Alignment(xalign = 0.0, yalign = 0.0,
                               xscale = 1.0, yscale = 1.0)
        filler.set_size_request(width, -1)
        hBox.pack_start(filler, False, False, 0)

    @staticmethod
    def addVFiller(vBox, height = 4):
        """Add a filler to the given vertical box."""
        filler = Gtk.Alignment(xalign = 0.0, yalign = 0.0,
                               xscale = 1.0, yscale = 1.0)
        filler.set_size_request(-1, height)
        vBox.pack_start(filler, False, False, 0)

    @staticmethod
    def timestamp2text(label, timestamp):
        """Convert the given timestamp into a text containing the hour
        and minute in UTC and put that text into the given label."""
        tm = time.gmtime(timestamp)
        label.set_text("%02d:%02d" % (tm.tm_hour, tm.tm_min))

    def __init__(self, gui, showMessages = False):
        """Construct the PIREP viewer."""
        super(PIREPViewer, self).__init__(title = WINDOW_TITLE_BASE +
                                          " - " +
                                          xstr("pirepView_title"),
                                          parent = gui.mainWindow)

        self.set_resizable(False)

        self._gui = gui

        contentArea = self.get_content_area()

        self._notebook = Gtk.Notebook()
        contentArea.pack_start(self._notebook, False, False, 4)

        dataTab = self._buildDataTab()
        label = Gtk.Label(xstr("pirepView_tab_data"))
        label.set_use_underline(True)
        label.set_tooltip_text(xstr("pirepView_tab_data_tooltip"))
        self._notebook.append_page(dataTab, label)

        commentsTab = self._buildCommentsTab()
        label = Gtk.Label(xstr("pirepView_tab_comments"))
        label.set_use_underline(True)
        label.set_tooltip_text(xstr("pirepView_tab_comments_tooltip"))
        self._notebook.append_page(commentsTab, label)

        logTab = self._buildLogTab()
        label = Gtk.Label(xstr("pirepView_tab_log"))
        label.set_use_underline(True)
        label.set_tooltip_text(xstr("pirepView_tab_log_tooltip"))
        self._notebook.append_page(logTab, label)

        self._showMessages = showMessages
        if showMessages:
            messagesTab = self._buildMessagesTab()
            label = Gtk.Label(xstr("pirepView_tab_messages"))
            label.set_use_underline(True)
            label.set_tooltip_text(xstr("pirepView_tab_messages_tooltip"))
            self._notebook.append_page(messagesTab, label)

        self._okButton = self.add_button(xstr("button_ok"), Gtk.ResponseType.OK)
        self._okButton.set_can_default(True)

    def setPIREP(self, pirep):
        """Setup the data in the dialog from the given PIREP."""
        bookedFlight = pirep.bookedFlight

        self._callsign.set_text(bookedFlight.callsign)
        self._tailNumber.set_text(bookedFlight.tailNumber)
        aircraftType = xstr("aircraft_" + icaoCodes[bookedFlight.aircraftType].lower())
        self._aircraftType.set_text(aircraftType)

        self._departureICAO.set_text(bookedFlight.departureICAO)
        self._departureTime.set_text("%02d:%02d" % \
                                     (bookedFlight.departureTime.hour,
                                      bookedFlight.departureTime.minute))

        self._arrivalICAO.set_text(bookedFlight.arrivalICAO)
        self._arrivalTime.set_text("%02d:%02d" % \
                                   (bookedFlight.arrivalTime.hour,
                                    bookedFlight.arrivalTime.minute))

        self._numPassengers.set_text(str(bookedFlight.numPassengers) + " + " +
                                     str(bookedFlight.numChildren) + " + " +
                                     str(bookedFlight.numInfants))
        self._numCrew.set_text(str(bookedFlight.numCockpitCrew) + " + " +
                               str(bookedFlight.numCabinCrew))
        self._bagWeight.set_text(str(bookedFlight.bagWeight))
        self._cargoWeight.set_text(str(bookedFlight.cargoWeight))
        self._mailWeight.set_text(str(bookedFlight.mailWeight))

        self._route.get_buffer().set_text(bookedFlight.route)

        self._filedCruiseLevel.set_text("FL" + str(pirep.filedCruiseAltitude/100))

        if pirep.cruiseAltitude != pirep.filedCruiseAltitude:
            self._modifiedCruiseLevel.set_text("FL" + str(pirep.cruiseAltitude/100))
        else:
            self._modifiedCruiseLevel.set_text("-")

        self._userRoute.get_buffer().set_text(pirep.route)

        self._departureMETAR.get_buffer().set_text(pirep.departureMETAR)

        self._arrivalMETAR.get_buffer().set_text(pirep.arrivalMETAR)
        self._departureRunway.set_text(pirep.departureRunway)
        self._sid.set_text(pirep.sid)

        self._star.set_text("-" if pirep.star is None else pirep.star)
        self._transition.set_text("-" if pirep.transition is None else pirep.transition)
        self._approachType.set_text(pirep.approachType)
        self._arrivalRunway.set_text(pirep.arrivalRunway)

        PIREPViewer.timestamp2text(self._blockTimeStart, pirep.blockTimeStart)
        PIREPViewer.timestamp2text(self._blockTimeEnd, pirep.blockTimeEnd)
        PIREPViewer.timestamp2text(self._flightTimeStart, pirep.flightTimeStart)
        PIREPViewer.timestamp2text(self._flightTimeEnd, pirep.flightTimeEnd)

        self._flownDistance.set_text("%.1f" % (pirep.flownDistance,))
        self._fuelUsed.set_text("%.0f" % (pirep.fuelUsed,))

        rating = pirep.rating
        if rating<0:
            self._rating.set_markup('<b><span foreground="red">NO GO</span></b>')
        else:
            self._rating.set_text("%.1f %%" % (rating,))

        self._flownNumCabinCrew.set_text("%d" % (pirep.numCabinCrew,))
        self._flownNumPassengers.set_text("%d" % (pirep.numPassengers,))
        self._flownBagWeight.set_text("%.0f" % (pirep.bagWeight,))
        self._flownCargoWeight.set_text("%.0f" % (pirep.cargoWeight,))
        self._flownMailWeight.set_text("%.0f" % (pirep.mailWeight,))
        self._flightType.set_text(xstr("flighttype_" +
                                       flightType2string(pirep.flightType)))
        self._online.set_text(xstr("pirepView_" +
                                   ("yes" if pirep.online else "no")))

        delayCodes = ""
        for code in pirep.delayCodes:
            if delayCodes: delayCodes += ", "
            delayCodes += code

        self._delayCodes.get_buffer().set_text(delayCodes)

        self._comments.get_buffer().set_text(pirep.comments)
        self._flightDefects.get_buffer().set_text(pirep.flightDefects)

        logBuffer = self._log.get_buffer()
        logBuffer.set_text("")
        lineIndex = 0
        for (timeStr, line) in pirep.logLines:
            isFault = lineIndex in pirep.faultLineIndexes
            appendTextBuffer(logBuffer,
                             formatFlightLogLine(timeStr, line),
                             isFault = isFault)
            lineIndex += 1

        if self._showMessages:
            self._messages.reset()
            for message in pirep.messages:
                self._messages.addMessage(message)

        self._notebook.set_current_page(0)
        self._okButton.grab_default()

    def _buildDataTab(self):
        """Build the data tab of the viewer."""
        table = Gtk.Table(1, 2)
        table.set_row_spacings(4)
        table.set_col_spacings(16)
        table.set_homogeneous(True)

        box1 = Gtk.VBox()
        table.attach(box1, 0, 1, 0, 1)

        box2 = Gtk.VBox()
        table.attach(box2, 1, 2, 0, 1)

        flightFrame = self._buildFlightFrame()
        box1.pack_start(flightFrame, False, False, 4)

        routeFrame = self._buildRouteFrame()
        box1.pack_start(routeFrame, False, False, 4)

        departureFrame = self._buildDepartureFrame()
        box2.pack_start(departureFrame, True, True, 4)

        arrivalFrame = self._buildArrivalFrame()
        box2.pack_start(arrivalFrame, True, True, 4)

        statisticsFrame = self._buildStatisticsFrame()
        box2.pack_start(statisticsFrame, False, False, 4)

        miscellaneousFrame = self._buildMiscellaneousFrame()
        box1.pack_start(miscellaneousFrame, False, False, 4)

        return table

    def _buildFlightFrame(self):
        """Build the frame for the flight data."""

        (frame, mainBox) = PIREPViewer.createFrame(xstr("pirepView_frame_flight"))

        dataBox = Gtk.HBox()
        mainBox.pack_start(dataBox, False, False, 0)

        self._callsign = \
            PIREPViewer.addLabeledData(dataBox,
                                       xstr("pirepView_callsign"),
                                       width = 8)

        self._tailNumber = \
            PIREPViewer.addLabeledData(dataBox,
                                       xstr("pirepView_tailNumber"),
                                       width = 7)

        PIREPViewer.addVFiller(mainBox)

        dataBox = Gtk.HBox()
        mainBox.pack_start(dataBox, False, False, 0)

        self._aircraftType = \
            PIREPViewer.addLabeledData(dataBox,
                                       xstr("pirepView_aircraftType"),
                                       width = 25)

        PIREPViewer.addVFiller(mainBox)

        table = Gtk.Table(3, 2)
        mainBox.pack_start(table, False, False, 0)
        table.set_row_spacings(4)
        table.set_col_spacings(8)

        self._departureICAO = \
            PIREPViewer.tableAttach(table, 0, 0,
                                    xstr("pirepView_departure"),
                                    width = 5)

        self._departureTime = \
            PIREPViewer.tableAttach(table, 1, 0,
                                    xstr("pirepView_departure_time"),
                                    width = 6)

        self._arrivalICAO = \
            PIREPViewer.tableAttach(table, 0, 1,
                                    xstr("pirepView_arrival"),
                                    width = 5)

        self._arrivalTime = \
            PIREPViewer.tableAttach(table, 1, 1,
                                    xstr("pirepView_arrival_time"),
                                    width = 6)

        table = Gtk.Table(3, 2)
        mainBox.pack_start(table, False, False, 0)
        table.set_row_spacings(4)
        table.set_col_spacings(8)

        self._numPassengers = \
            PIREPViewer.tableAttach(table, 0, 0,
                                    xstr("pirepView_numPassengers"),
                                    width = 4)

        self._numCrew = \
            PIREPViewer.tableAttach(table, 1, 0,
                                    xstr("pirepView_numCrew"),
                                    width = 3)

        self._bagWeight = \
            PIREPViewer.tableAttach(table, 0, 1,
                                    xstr("pirepView_bagWeight"),
                                    width = 5)

        self._cargoWeight = \
            PIREPViewer.tableAttach(table, 1, 1,
                                    xstr("pirepView_cargoWeight"),
                                    width = 5)

        self._mailWeight = \
            PIREPViewer.tableAttach(table, 2, 1,
                                    xstr("pirepView_mailWeight"),
                                    width = 5)

        PIREPViewer.addVFiller(mainBox)

        mainBox.pack_start(PIREPViewer.getLabel(xstr("pirepView_route")),
                           False, False, 0)

        (routeWindow, self._route) = PIREPViewer.getTextWindow()
        mainBox.pack_start(routeWindow, False, False, 0)

        return frame

    def _buildRouteFrame(self):
        """Build the frame for the user-specified route and flight
        level."""

        (frame, mainBox) = PIREPViewer.createFrame(xstr("pirepView_frame_route"))

        levelBox = Gtk.HBox()
        mainBox.pack_start(levelBox, False, False, 0)

        self._filedCruiseLevel = \
            PIREPViewer.addLabeledData(levelBox,
                                       xstr("pirepView_filedCruiseLevel"),
                                       width = 6)

        self._modifiedCruiseLevel = \
            PIREPViewer.addLabeledData(levelBox,
                                       xstr("pirepView_modifiedCruiseLevel"),
                                       width = 6)

        PIREPViewer.addVFiller(mainBox)

        (routeWindow, self._userRoute) = PIREPViewer.getTextWindow()
        mainBox.pack_start(routeWindow, False, False, 0)

        return frame

    def _buildDepartureFrame(self):
        """Build the frame for the departure data."""
        (frame, mainBox) = PIREPViewer.createFrame(xstr("pirepView_frame_departure"))

        mainBox.pack_start(PIREPViewer.getLabel("METAR:"),
                           False, False, 0)
        (metarWindow, self._departureMETAR) = \
            PIREPViewer.getTextWindow(heightRequest = -1)
        mainBox.pack_start(metarWindow, True, True, 0)

        PIREPViewer.addVFiller(mainBox)

        dataBox = Gtk.HBox()
        mainBox.pack_start(dataBox, False, False, 0)

        self._departureRunway = \
            PIREPViewer.addLabeledData(dataBox,
                                       xstr("pirepView_runway"),
                                       width = 5)

        self._sid = \
            PIREPViewer.addLabeledData(dataBox,
                                       xstr("pirepView_sid"),
                                       width = 12)

        return frame

    def _buildArrivalFrame(self):
        """Build the frame for the arrival data."""
        (frame, mainBox) = PIREPViewer.createFrame(xstr("pirepView_frame_arrival"))

        mainBox.pack_start(PIREPViewer.getLabel("METAR:"),
                           False, False, 0)
        (metarWindow, self._arrivalMETAR) = \
            PIREPViewer.getTextWindow(heightRequest = -1)
        mainBox.pack_start(metarWindow, True, True, 0)

        PIREPViewer.addVFiller(mainBox)

        table = Gtk.Table(2, 2)
        mainBox.pack_start(table, False, False, 0)
        table.set_row_spacings(4)
        table.set_col_spacings(8)

        self._star = \
            PIREPViewer.tableAttach(table, 0, 0,
                                    xstr("pirepView_star"),
                                    width = 12)

        self._transition = \
            PIREPViewer.tableAttach(table, 1, 0,
                                    xstr("pirepView_transition"),
                                    width = 12)

        self._approachType = \
            PIREPViewer.tableAttach(table, 0, 1,
                                    xstr("pirepView_approachType"),
                                    width = 7)

        self._arrivalRunway = \
            PIREPViewer.tableAttach(table, 1, 1,
                                    xstr("pirepView_runway"),
                                    width = 5)

        return frame

    def _buildStatisticsFrame(self):
        """Build the frame for the statistics data."""
        (frame, mainBox) = PIREPViewer.createFrame(xstr("pirepView_frame_statistics"))

        table = Gtk.Table(4, 2)
        mainBox.pack_start(table, False, False, 0)
        table.set_row_spacings(4)
        table.set_col_spacings(8)
        table.set_homogeneous(False)

        self._blockTimeStart = \
            PIREPViewer.tableAttach(table, 0, 0,
                                    xstr("pirepView_blockTimeStart"),
                                    width = 6)

        self._blockTimeEnd = \
            PIREPViewer.tableAttach(table, 1, 0,
                                    xstr("pirepView_blockTimeEnd"),
                                    width = 8)

        self._flightTimeStart = \
            PIREPViewer.tableAttach(table, 0, 1,
                                    xstr("pirepView_flightTimeStart"),
                                    width = 6)

        self._flightTimeEnd = \
            PIREPViewer.tableAttach(table, 1, 1,
                                    xstr("pirepView_flightTimeEnd"),
                                    width = 6)

        self._flownDistance = \
            PIREPViewer.tableAttach(table, 0, 2,
                                    xstr("pirepView_flownDistance"),
                                    width = 8)

        self._fuelUsed = \
            PIREPViewer.tableAttach(table, 1, 2,
                                    xstr("pirepView_fuelUsed"),
                                    width = 6)

        self._rating = \
            PIREPViewer.tableAttach(table, 0, 3,
                                    xstr("pirepView_rating"),
                                    width = 7)
        return frame

    def _buildMiscellaneousFrame(self):
        """Build the frame for the miscellaneous data."""
        (frame, mainBox) = PIREPViewer.createFrame(xstr("pirepView_frame_miscellaneous"))

        table = Gtk.Table(3, 2)
        mainBox.pack_start(table, False, False, 0)
        table.set_row_spacings(4)
        table.set_col_spacings(8)

        self._flownNumPassengers = \
            PIREPViewer.tableAttach(table, 0, 0,
                                    xstr("pirepView_numPassengers"),
                                    width = 4)

        self._flownNumCabinCrew = \
            PIREPViewer.tableAttach(table, 1, 0,
                                    xstr("pirepView_numCrew"),
                                    width = 3)

        self._flownBagWeight = \
            PIREPViewer.tableAttach(table, 0, 1,
                                    xstr("pirepView_bagWeight"),
                                    width = 5)

        self._flownCargoWeight = \
            PIREPViewer.tableAttach(table, 1, 1,
                                    xstr("pirepView_cargoWeight"),
                                    width = 6)

        self._flownMailWeight = \
            PIREPViewer.tableAttach(table, 2, 1,
                                    xstr("pirepView_mailWeight"),
                                    width = 5)

        self._flightType = \
            PIREPViewer.tableAttach(table, 0, 2,
                                    xstr("pirepView_flightType"),
                                    width = 15)

        self._online = \
            PIREPViewer.tableAttach(table, 1, 2,
                                    xstr("pirepView_online"),
                                    width = 5)

        PIREPViewer.addVFiller(mainBox)

        mainBox.pack_start(PIREPViewer.getLabel(xstr("pirepView_delayCodes")),
                           False, False, 0)

        (textWindow, self._delayCodes) = PIREPViewer.getTextWindow()
        mainBox.pack_start(textWindow, False, False, 0)

        return frame

    def _buildCommentsTab(self):
        """Build the tab with the comments and flight defects."""
        table = Gtk.Table(2, 1)
        table.set_col_spacings(16)

        (frame, commentsBox) = \
            PIREPViewer.createFrame(xstr("pirepView_comments"))
        table.attach(frame, 0, 1, 0, 1)

        (commentsWindow, self._comments) = \
            PIREPViewer.getTextWindow(heightRequest = -1)
        commentsBox.pack_start(commentsWindow, True, True, 0)

        (frame, flightDefectsBox) = \
            PIREPViewer.createFrame(xstr("pirepView_flightDefects"))
        table.attach(frame, 1, 2, 0, 1)

        (flightDefectsWindow, self._flightDefects) = \
            PIREPViewer.getTextWindow(heightRequest = -1)
        flightDefectsBox.pack_start(flightDefectsWindow, True, True, 0)

        return table

    def _buildLogTab(self):
        """Build the log tab."""
        mainBox = Gtk.VBox()

        (logWindow, self._log) = PIREPViewer.getTextWindow(heightRequest = -1)
        addFaultTag(self._log.get_buffer())
        mainBox.pack_start(logWindow, True, True, 0)

        return mainBox

    def _buildMessagesTab(self):
        """Build the messages tab."""
        mainBox = Gtk.VBox()

        self._messages = MessagesWidget(self._gui)
        mainBox.pack_start(self._messages, True, True, 0)

        return mainBox

#------------------------------------------------------------------------------

class PIREPEditor(Gtk.Dialog):
    """A PIREP editor dialog."""
    _delayCodeRE = re.compile("([0-9]{2,3})( \([^\)]*\))")

    @staticmethod
    def tableAttachWidget(table, column, row, labelText, widget):
        """Attach the given widget with the given label to the given table.

        The label will got to cell (column, row), the widget to cell
        (column+1, row)."""
        label = Gtk.Label("<b>" + labelText + "</b>")
        label.set_use_markup(True)
        alignment = Gtk.Alignment(xalign = 0.0, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)
        alignment.add(label)
        table.attach(alignment, column, column + 1, row, row + 1)

        table.attach(widget, column + 1, column + 2, row, row + 1)

    @staticmethod
    def tableAttachSpinButton(table, column, row, labelText, maxValue,
                              minValue = 0, stepIncrement = 1,
                              pageIncrement = 10, numeric = True,
                              width = 3):
        """Attach a spin button with the given label to the given table.

        The label will got to cell (column, row), the spin button to cell
        (column+1, row)."""
        button = Gtk.SpinButton()
        button.set_range(min = minValue, max = maxValue)
        button.set_increments(step = stepIncrement, page = pageIncrement)
        button.set_numeric(True)
        button.set_width_chars(width)
        button.set_alignment(1.0)

        PIREPEditor.tableAttachWidget(table, column, row, labelText, button)

        return button

    @staticmethod
    def tableAttachTimeEntry(table, column, row, labelText):
        """Attach a time entry widget with the given label to the given table.

        The label will got to cell (column, row), the spin button to cell
        (column+1, row)."""
        entry = TimeEntry()
        entry.set_width_chars(5)
        entry.set_alignment(1.0)

        PIREPEditor.tableAttachWidget(table, column, row, labelText, entry)

        return entry

    def __init__(self, gui):
        """Construct the PIREP viewer."""
        super(PIREPEditor, self).__init__(title = WINDOW_TITLE_BASE +
                                          " - " +
                                          xstr("pirepEdit_title"),
                                          parent = gui.mainWindow)

        self.set_resizable(False)

        self._gui = gui

        self._pirep = None

        contentArea = self.get_content_area()

        self._notebook = Gtk.Notebook()
        contentArea.pack_start(self._notebook, False, False, 4)

        dataTab = self._buildDataTab()
        label = Gtk.Label(xstr("pirepView_tab_data"))
        label.set_use_underline(True)
        label.set_tooltip_text(xstr("pirepView_tab_data_tooltip"))
        self._notebook.append_page(dataTab, label)

        self._flightInfo = self._buildCommentsTab()
        label = Gtk.Label(xstr("pirepView_tab_comments"))
        label.set_use_underline(True)
        label.set_tooltip_text(xstr("pirepView_tab_comments_tooltip"))
        self._notebook.append_page(self._flightInfo, label)

        logTab = self._buildLogTab()
        label = Gtk.Label(xstr("pirepView_tab_log"))
        label.set_use_underline(True)
        label.set_tooltip_text(xstr("pirepView_tab_log_tooltip"))
        self._notebook.append_page(logTab, label)

        self.add_button(xstr("button_cancel"), Gtk.ResponseType.CANCEL)

        self._okButton = self.add_button(xstr("button_save"), Gtk.ResponseType.NONE)
        self._okButton.connect("clicked", self._okClicked)
        self._okButton.set_can_default(True)
        self._modified = False
        self._toSave = False

    def setPIREP(self, pirep):
        """Setup the data in the dialog from the given PIREP."""
        self._pirep = pirep

        bookedFlight = pirep.bookedFlight

        self._callsign.set_text(bookedFlight.callsign)
        self._tailNumber.set_text(bookedFlight.tailNumber)
        aircraftType = xstr("aircraft_" + icaoCodes[bookedFlight.aircraftType].lower())
        self._aircraftType.set_text(aircraftType)

        self._departureICAO.set_text(bookedFlight.departureICAO)
        self._departureTime.set_text("%02d:%02d" % \
                                     (bookedFlight.departureTime.hour,
                                      bookedFlight.departureTime.minute))

        self._arrivalICAO.set_text(bookedFlight.arrivalICAO)
        self._arrivalTime.set_text("%02d:%02d" % \
                                   (bookedFlight.arrivalTime.hour,
                                    bookedFlight.arrivalTime.minute))

        self._numPassengers.set_text(str(bookedFlight.numPassengers) + " + " +
                                     str(bookedFlight.numChildren) + " + " +
                                     str(bookedFlight.numInfants))
        self._numCrew.set_text(str(bookedFlight.numCockpitCrew) + " + " +
                               str(bookedFlight.numCabinCrew))
        self._bagWeight.set_text(str(bookedFlight.bagWeight))
        self._cargoWeight.set_text(str(bookedFlight.cargoWeight))
        self._mailWeight.set_text(str(bookedFlight.mailWeight))

        self._route.get_buffer().set_text(bookedFlight.route)

        self._filedCruiseLevel.set_value(pirep.filedCruiseAltitude/100)
        self._modifiedCruiseLevel.set_value(pirep.cruiseAltitude/100)

        self._userRoute.get_buffer().set_text(pirep.route)

        self._departureMETAR.get_buffer().set_text(pirep.departureMETAR)

        self._arrivalMETAR.get_buffer().set_text(pirep.arrivalMETAR)
        self._departureRunway.set_text(pirep.departureRunway)
        self._sid.get_child().set_text(pirep.sid)

        if not pirep.star:
            self._star.set_active(0)
        else:
            self._star.get_child().set_text(pirep.star)

        if not pirep.transition:
            self._transition.set_active(0)
        else:
            self._transition.get_child().set_text(pirep.transition)
        self._approachType.set_text(pirep.approachType)
        self._arrivalRunway.set_text(pirep.arrivalRunway)

        self._blockTimeStart.setTimestamp(pirep.blockTimeStart)
        self._blockTimeEnd.setTimestamp(pirep.blockTimeEnd)
        self._flightTimeStart.setTimestamp(pirep.flightTimeStart)
        self._flightTimeEnd.setTimestamp(pirep.flightTimeEnd)

        self._flownDistance.set_text("%.1f" % (pirep.flownDistance,))
        self._fuelUsed.set_value(int(pirep.fuelUsed))

        rating = pirep.rating
        if rating<0:
            self._rating.set_markup('<b><span foreground="red">NO GO</span></b>')
        else:
            self._rating.set_text("%.1f %%" % (rating,))

        self._flownNumCabinCrew.set_value(pirep.numCabinCrew)
        self._flownNumPassengers.set_value(pirep.numPassengers)
        self._flownNumChildren.set_value(pirep.numChildren)
        self._flownNumInfants.set_value(pirep.numInfants)
        self._flownBagWeight.set_value(pirep.bagWeight)
        self._flownCargoWeight.set_value(pirep.cargoWeight)
        self._flownMailWeight.set_value(pirep.mailWeight)
        self._flightType.set_active(flightType2index(pirep.flightType))
        self._online.set_active(pirep.online)

        self._flightInfo.reset()
        self._flightInfo.enable(bookedFlight.aircraftType)

        delayCodes = ""
        for code in pirep.delayCodes:
            if delayCodes: delayCodes += ", "
            delayCodes += code
            m = PIREPEditor._delayCodeRE.match(code)
            if m:
                self._flightInfo.activateDelayCode(m.group(1))

        self._delayCodes.get_buffer().set_text(delayCodes)

        self._flightInfo.comments = pirep.comments
        if pirep.flightDefects.find("<br/></b>")!=-1:
            flightDefects = pirep.flightDefects.split("<br/></b>")
            caption = flightDefects[0]
            index = 0
            for defect in flightDefects[1:]:
                if defect.find("<b>")!=-1:
                    (explanation, nextCaption) = defect.split("<b>")
                else:
                    explanation = defect
                    nextCaption = None
                self._flightInfo.addFault(index, caption)
                self._flightInfo.setExplanation(index, explanation)
                index += 1
                caption = nextCaption

        # self._comments.get_buffer().set_text(pirep.comments)
        # self._flightDefects.get_buffer().set_text(pirep.flightDefects)

        logBuffer = self._log.get_buffer()
        logBuffer.set_text("")
        lineIndex = 0
        for (timeStr, line) in pirep.logLines:
            isFault = lineIndex in pirep.faultLineIndexes
            appendTextBuffer(logBuffer,
                             formatFlightLogLine(timeStr, line),
                             isFault = isFault)
            lineIndex += 1

        self._notebook.set_current_page(0)
        self._okButton.grab_default()

        self._modified = False
        self._updateButtons()
        self._modified = True
        self._toSave = False

    def delayCodesChanged(self):
        """Called when the delay codes have changed."""
        self._updateButtons()

    def commentsChanged(self):
        """Called when the comments have changed."""
        self._updateButtons()

    def faultExplanationsChanged(self):
        """Called when the fault explanations have changed."""
        self._updateButtons()

    def _buildDataTab(self):
        """Build the data tab of the viewer."""
        table = Gtk.Table(1, 2)
        table.set_row_spacings(4)
        table.set_col_spacings(16)
        table.set_homogeneous(True)

        box1 = Gtk.VBox()
        table.attach(box1, 0, 1, 0, 1)

        box2 = Gtk.VBox()
        table.attach(box2, 1, 2, 0, 1)

        flightFrame = self._buildFlightFrame()
        box1.pack_start(flightFrame, False, False, 4)

        routeFrame = self._buildRouteFrame()
        box1.pack_start(routeFrame, False, False, 4)

        departureFrame = self._buildDepartureFrame()
        box2.pack_start(departureFrame, True, True, 4)

        arrivalFrame = self._buildArrivalFrame()
        box2.pack_start(arrivalFrame, True, True, 4)

        statisticsFrame = self._buildStatisticsFrame()
        box2.pack_start(statisticsFrame, False, False, 4)

        miscellaneousFrame = self._buildMiscellaneousFrame()
        box1.pack_start(miscellaneousFrame, False, False, 4)

        return table

    def _buildFlightFrame(self):
        """Build the frame for the flight data."""

        (frame, mainBox) = PIREPViewer.createFrame(xstr("pirepView_frame_flight"))

        dataBox = Gtk.HBox()
        mainBox.pack_start(dataBox, False, False, 0)

        self._callsign = \
            PIREPViewer.addLabeledData(dataBox,
                                       xstr("pirepView_callsign"),
                                       width = 8)

        self._tailNumber = \
            PIREPViewer.addLabeledData(dataBox,
                                       xstr("pirepView_tailNumber"),
                                       width = 7)

        PIREPViewer.addVFiller(mainBox)

        dataBox = Gtk.HBox()
        mainBox.pack_start(dataBox, False, False, 0)

        self._aircraftType = \
            PIREPViewer.addLabeledData(dataBox,
                                       xstr("pirepView_aircraftType"),
                                       width = 25)

        PIREPViewer.addVFiller(mainBox)

        table = Gtk.Table(3, 2)
        mainBox.pack_start(table, False, False, 0)
        table.set_row_spacings(4)
        table.set_col_spacings(8)

        self._departureICAO = \
            PIREPViewer.tableAttach(table, 0, 0,
                                    xstr("pirepView_departure"),
                                    width = 5)

        self._departureTime = \
            PIREPViewer.tableAttach(table, 1, 0,
                                    xstr("pirepView_departure_time"),
                                    width = 6)

        self._arrivalICAO = \
            PIREPViewer.tableAttach(table, 0, 1,
                                    xstr("pirepView_arrival"),
                                    width = 5)

        self._arrivalTime = \
            PIREPViewer.tableAttach(table, 1, 1,
                                    xstr("pirepView_arrival_time"),
                                    width = 6)

        table = Gtk.Table(3, 2)
        mainBox.pack_start(table, False, False, 0)
        table.set_row_spacings(4)
        table.set_col_spacings(8)

        self._numPassengers = \
            PIREPViewer.tableAttach(table, 0, 0,
                                    xstr("pirepView_numPassengers"),
                                    width = 4)
        self._numCrew = \
            PIREPViewer.tableAttach(table, 1, 0,
                                    xstr("pirepView_numCrew"),
                                    width = 3)

        self._bagWeight = \
            PIREPViewer.tableAttach(table, 0, 1,
                                    xstr("pirepView_bagWeight"),
                                    width = 5)

        self._cargoWeight = \
            PIREPViewer.tableAttach(table, 1, 1,
                                    xstr("pirepView_cargoWeight"),
                                    width = 5)

        self._mailWeight = \
            PIREPViewer.tableAttach(table, 2, 1,
                                    xstr("pirepView_mailWeight"),
                                    width = 5)

        PIREPViewer.addVFiller(mainBox)

        mainBox.pack_start(PIREPViewer.getLabel(xstr("pirepView_route")),
                           False, False, 0)

        (routeWindow, self._route) = PIREPViewer.getTextWindow()
        mainBox.pack_start(routeWindow, False, False, 0)

        return frame

    def _buildRouteFrame(self):
        """Build the frame for the user-specified route and flight
        level."""

        (frame, mainBox) = PIREPViewer.createFrame(xstr("pirepView_frame_route"))

        levelBox = Gtk.HBox()
        mainBox.pack_start(levelBox, False, False, 0)

        label = PIREPViewer.getLabel(xstr("pirepView_filedCruiseLevel"),
                                     xstr("pirepEdit_FL"))
        levelBox.pack_start(label, False, False, 0)

        self._filedCruiseLevel = Gtk.SpinButton()
        self._filedCruiseLevel.set_increments(step = 10, page = 100)
        self._filedCruiseLevel.set_range(min = 0, max = 500)
        self._filedCruiseLevel.set_tooltip_text(xstr("route_level_tooltip"))
        self._filedCruiseLevel.set_numeric(True)
        self._filedCruiseLevel.connect("value-changed", self._updateButtons)

        levelBox.pack_start(self._filedCruiseLevel, False, False, 0)

        PIREPViewer.addHFiller(levelBox)

        label = PIREPViewer.getLabel(xstr("pirepView_modifiedCruiseLevel"),
                                     xstr("pirepEdit_FL"))
        levelBox.pack_start(label, False, False, 0)

        self._modifiedCruiseLevel = Gtk.SpinButton()
        self._modifiedCruiseLevel.set_increments(step = 10, page = 100)
        self._modifiedCruiseLevel.set_range(min = 0, max = 500)
        self._modifiedCruiseLevel.set_tooltip_text(xstr("pirepEdit_modified_route_level_tooltip"))
        self._modifiedCruiseLevel.set_numeric(True)
        self._modifiedCruiseLevel.connect("value-changed", self._updateButtons)

        levelBox.pack_start(self._modifiedCruiseLevel, False, False, 0)

        PIREPViewer.addVFiller(mainBox)

        (routeWindow, self._userRoute) = \
          PIREPViewer.getTextWindow(editable = True)
        mainBox.pack_start(routeWindow, False, False, 0)
        self._userRoute.get_buffer().connect("changed", self._updateButtons)
        self._userRoute.set_tooltip_text(xstr("route_route_tooltip"))

        return frame

    def _buildDepartureFrame(self):
        """Build the frame for the departure data."""
        (frame, mainBox) = PIREPViewer.createFrame(xstr("pirepView_frame_departure"))

        mainBox.pack_start(PIREPViewer.getLabel("METAR:"),
                           False, False, 0)
        (metarWindow, self._departureMETAR) = \
            PIREPViewer.getTextWindow(heightRequest = -1,
                                      editable = True)
        self._departureMETAR.get_buffer().connect("changed", self._updateButtons)
        self._departureMETAR.set_tooltip_text(xstr("takeoff_metar_tooltip"))
        mainBox.pack_start(metarWindow, True, True, 0)

        PIREPViewer.addVFiller(mainBox)

        dataBox = Gtk.HBox()
        mainBox.pack_start(dataBox, False, False, 0)

        label = Gtk.Label("<b>" + xstr("pirepView_runway") + "</b>")
        label.set_use_markup(True)
        dataBox.pack_start(label, False, False, 0)

        # FIXME: quite the same as the runway entry boxes in the wizard
        self._departureRunway = Gtk.Entry()
        self._departureRunway.set_width_chars(5)
        self._departureRunway.set_tooltip_text(xstr("takeoff_runway_tooltip"))
        self._departureRunway.connect("changed", self._upperChanged)
        dataBox.pack_start(self._departureRunway, False, False, 8)

        label = Gtk.Label("<b>" + xstr("pirepView_sid") + "</b>")
        label.set_use_markup(True)
        dataBox.pack_start(label, False, False, 0)

        # FIXME: quite the same as the SID combo box in
        # the flight wizard
        self._sid = Gtk.ComboBox.new_with_model_and_entry(comboModel)

        self._sid.set_entry_text_column(0)
        self._sid.get_child().set_width_chars(10)
        self._sid.set_tooltip_text(xstr("takeoff_sid_tooltip"))
        self._sid.connect("changed", self._upperChangedComboBox)

        dataBox.pack_start(self._sid, False, False, 8)

        return frame

    def _buildArrivalFrame(self):
        """Build the frame for the arrival data."""
        (frame, mainBox) = PIREPViewer.createFrame(xstr("pirepView_frame_arrival"))

        mainBox.pack_start(PIREPViewer.getLabel("METAR:"),
                           False, False, 0)
        (metarWindow, self._arrivalMETAR) = \
            PIREPViewer.getTextWindow(heightRequest = -1,
                                      editable = True)
        self._arrivalMETAR.get_buffer().connect("changed", self._updateButtons)
        self._arrivalMETAR.set_tooltip_text(xstr("landing_metar_tooltip"))
        mainBox.pack_start(metarWindow, True, True, 0)

        PIREPViewer.addVFiller(mainBox)

        table = Gtk.Table(2, 4)
        mainBox.pack_start(table, False, False, 0)
        table.set_row_spacings(4)
        table.set_col_spacings(8)

        # FIXME: quite the same as in the wizard
        self._star = Gtk.ComboBox.new_with_model_and_entry(comboModel)

        self._star.set_entry_text_column(0)
        self._star.get_child().set_width_chars(10)
        self._star.set_tooltip_text(xstr("landing_star_tooltip"))
        self._star.connect("changed", self._upperChangedComboBox)

        PIREPEditor.tableAttachWidget(table, 0, 0,
                                      xstr("pirepView_star"),
                                      self._star)

        # FIXME: quite the same as in the wizard
        self._transition = Gtk.ComboBox.new_with_model_and_entry(comboModel)

        self._transition.set_entry_text_column(0)
        self._transition.get_child().set_width_chars(10)
        self._transition.set_tooltip_text(xstr("landing_transition_tooltip"))
        self._transition.connect("changed", self._upperChangedComboBox)

        PIREPEditor.tableAttachWidget(table, 2, 0,
                                      xstr("pirepView_transition"),
                                      self._transition)


        # FIXME: quite the same as in the wizard
        self._approachType = Gtk.Entry()
        self._approachType.set_width_chars(10)
        self._approachType.set_tooltip_text(xstr("landing_approach_tooltip"))
        self._approachType.connect("changed", self._upperChanged)

        PIREPEditor.tableAttachWidget(table, 0, 1,
                                      xstr("pirepView_approachType"),
                                      self._approachType)

        # FIXME: quite the same as in the wizard
        self._arrivalRunway = Gtk.Entry()
        self._arrivalRunway.set_width_chars(10)
        self._arrivalRunway.set_tooltip_text(xstr("landing_runway_tooltip"))
        self._arrivalRunway.connect("changed", self._upperChanged)

        PIREPEditor.tableAttachWidget(table, 2, 1,
                                      xstr("pirepView_runway"),
                                      self._arrivalRunway)

        return frame

    def _buildStatisticsFrame(self):
        """Build the frame for the statistics data."""
        (frame, mainBox) = PIREPViewer.createFrame(xstr("pirepView_frame_statistics"))

        table = Gtk.Table(4, 4)
        mainBox.pack_start(table, False, False, 0)
        table.set_row_spacings(4)
        table.set_col_spacings(8)
        table.set_homogeneous(False)

        self._blockTimeStart = \
            PIREPEditor.tableAttachTimeEntry(table, 0, 0,
                                             xstr("pirepView_blockTimeStart"))
        self._blockTimeStart.connect("changed", self._updateButtons)
        self._blockTimeStart.set_tooltip_text(xstr("pirepEdit_block_time_start_tooltip"))

        self._blockTimeEnd = \
            PIREPEditor.tableAttachTimeEntry(table, 2, 0,
                                             xstr("pirepView_blockTimeEnd"))
        self._blockTimeEnd.connect("changed", self._updateButtons)
        self._blockTimeEnd.set_tooltip_text(xstr("pirepEdit_block_time_end_tooltip"))

        self._flightTimeStart = \
            PIREPEditor.tableAttachTimeEntry(table, 0, 1,
                                             xstr("pirepView_flightTimeStart"))
        self._flightTimeStart.connect("changed", self._updateButtons)
        self._flightTimeStart.set_tooltip_text(xstr("pirepEdit_flight_time_start_tooltip"))

        self._flightTimeEnd = \
            PIREPEditor.tableAttachTimeEntry(table, 2, 1,
                                             xstr("pirepView_flightTimeEnd"))
        self._flightTimeEnd.connect("changed", self._updateButtons)
        self._flightTimeEnd.set_tooltip_text(xstr("pirepEdit_flight_time_end_tooltip"))

        self._flownDistance = PIREPViewer.getDataLabel(width = 3)
        PIREPEditor.tableAttachWidget(table, 0, 2,
                                      xstr("pirepView_flownDistance"),
                                      self._flownDistance)

        self._fuelUsed = \
            PIREPEditor.tableAttachSpinButton(table, 2, 2,
                                              xstr("pirepView_fuelUsed"),
                                              1000000)
        self._fuelUsed.connect("value-changed", self._updateButtons)
        self._fuelUsed.set_tooltip_text(xstr("pirepEdit_fuel_used_tooltip"))

        self._rating = PIREPViewer.getDataLabel(width = 3)
        PIREPEditor.tableAttachWidget(table, 0, 3,
                                      xstr("pirepView_rating"),
                                      self._rating)
        return frame

    def _buildMiscellaneousFrame(self):
        """Build the frame for the miscellaneous data."""
        (frame, mainBox) = PIREPViewer.createFrame(xstr("pirepView_frame_miscellaneous"))

        table = Gtk.Table(6, 2)
        mainBox.pack_start(table, False, False, 0)
        table.set_row_spacings(4)
        table.set_col_spacings(8)
        table.set_homogeneous(False)

        label = Gtk.Label("<b>" + xstr("pirepView_numPassengers") + "</b>")
        label.set_use_markup(True)
        alignment = Gtk.Alignment(xalign = 0.0, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)
        alignment.add(label)
        table.attach(alignment, 0, 1, 0, 1)



        self._flownNumPassengers = button = Gtk.SpinButton()
        button.set_range(min = 0, max = 300)
        button.set_increments(step = 1, page = 10)
        button.set_numeric(True)
        button.set_width_chars(2)
        button.set_alignment(1.0)
        button.connect("value-changed", self._updateButtons)
        button.set_tooltip_text(xstr("payload_pax_tooltip"))

        self._flownNumChildren = button = Gtk.SpinButton()
        button.set_range(min = 0, max = 300)
        button.set_increments(step = 1, page = 10)
        button.set_numeric(True)
        button.set_width_chars(2)
        button.set_alignment(1.0)
        button.connect("value-changed", self._updateButtons)
        button.set_tooltip_text(xstr("payload_pax_children_tooltip"))

        self._flownNumInfants = button = Gtk.SpinButton()
        button.set_range(min = 0, max = 300)
        button.set_increments(step = 1, page = 10)
        button.set_numeric(True)
        button.set_width_chars(2)
        button.set_alignment(1.0)
        button.connect("value-changed", self._updateButtons)
        button.set_tooltip_text(xstr("payload_pax_infants_tooltip"))

        paxBox = Gtk.HBox()
        paxBox.pack_start(self._flownNumPassengers, False, False, 0)
        paxBox.pack_start(Gtk.Label("+"), False, False, 4)
        paxBox.pack_start(self._flownNumChildren, False, False, 0)
        paxBox.pack_start(Gtk.Label("+"), False, False, 4)
        paxBox.pack_start(self._flownNumInfants, False, False, 0)
        paxBox.set_halign(Gtk.Align.END)

        table.attach(paxBox, 1, 4, 0, 1)

        self._flownNumCabinCrew = \
            PIREPEditor.tableAttachSpinButton(table, 4, 0,
                                              xstr("pirepView_numCrew"),
                                              10)
        self._flownNumCabinCrew.connect("value-changed", self._updateButtons)
        self._flownNumCabinCrew.set_tooltip_text(xstr("payload_crew_tooltip"))

        self._flownBagWeight = \
            PIREPEditor.tableAttachSpinButton(table, 0, 1,
                                              xstr("pirepView_bagWeight"),
                                              100000, width = 6)
        self._flownBagWeight.connect("value-changed", self._updateButtons)
        self._flownBagWeight.set_tooltip_text(xstr("payload_bag_tooltip"))

        self._flownCargoWeight = \
            PIREPEditor.tableAttachSpinButton(table, 2, 1,
                                              xstr("pirepView_cargoWeight"),
                                              100000, width = 6)
        self._flownCargoWeight.connect("value-changed", self._updateButtons)
        self._flownCargoWeight.set_tooltip_text(xstr("payload_cargo_tooltip"))

        self._flownMailWeight = \
            PIREPEditor.tableAttachSpinButton(table, 4, 1,
                                              xstr("pirepView_mailWeight"),
                                              100000, width = 6)
        self._flownMailWeight.connect("value-changed", self._updateButtons)
        self._flownMailWeight.set_tooltip_text(xstr("payload_mail_tooltip"))

        self._flightType = createFlightTypeComboBox()
        PIREPEditor.tableAttachWidget(table, 0, 2,
                                      xstr("pirepView_flightType"),
                                      self._flightType)
        self._flightType.connect("changed", self._updateButtons)
        self._flightType.set_tooltip_text(xstr("pirepEdit_flight_type_tooltip"))

        self._online = Gtk.CheckButton(xstr("pirepEdit_online"))
        table.attach(self._online, 2, 3, 2, 3)
        self._online.connect("toggled", self._updateButtons)
        self._online.set_tooltip_text(xstr("pirepEdit_online_tooltip"))

        PIREPViewer.addVFiller(mainBox)

        mainBox.pack_start(PIREPViewer.getLabel(xstr("pirepView_delayCodes")),
                           False, False, 0)

        (textWindow, self._delayCodes) = PIREPViewer.getTextWindow()
        mainBox.pack_start(textWindow, False, False, 0)
        self._delayCodes.set_tooltip_text(xstr("pirepEdit_delayCodes_tooltip"))

        return frame

    def _buildCommentsTab(self):
        """Build the tab with the comments and flight defects."""
        return FlightInfo(self._gui, callbackObject = self)

    def _buildLogTab(self):
        """Build the log tab."""
        mainBox = Gtk.VBox()

        (logWindow, self._log) = PIREPViewer.getTextWindow(heightRequest = -1)
        addFaultTag(self._log.get_buffer())
        mainBox.pack_start(logWindow, True, True, 0)

        return mainBox

    def _upperChanged(self, entry, arg = None):
        """Called when the value of some entry widget has changed and the value
        should be converted to uppercase."""
        entry.set_text(entry.get_text().upper())
        self._updateButtons()
        #self._valueChanged(entry, arg)

    def _upperChangedComboBox(self, comboBox):
        """Called for combo box widgets that must be converted to uppercase."""
        entry = comboBox.get_child()
        if comboBox.get_active()==-1:
            entry.set_text(entry.get_text().upper())
        self._updateButtons()
        #self._valueChanged(entry)

    def _updateButtons(self, *kwargs):
        """Update the activity state of the buttons."""
        pirep = self._pirep
        bookedFlight = pirep.bookedFlight

        departureMinutes = \
            bookedFlight.departureTime.hour*60 + bookedFlight.departureTime.minute
        departureDifference = abs(Flight.getMinutesDifference(self._blockTimeStart.minutes,
                                                              departureMinutes))
        flightStartDifference = \
            Flight.getMinutesDifference(self._flightTimeStart.minutes,
                                        self._blockTimeStart.minutes)
        arrivalMinutes = \
            bookedFlight.arrivalTime.hour*60 + bookedFlight.arrivalTime.minute
        arrivalDifference = abs(Flight.getMinutesDifference(self._blockTimeEnd.minutes,
                                                            arrivalMinutes))
        flightEndDifference = \
            Flight.getMinutesDifference(self._blockTimeEnd.minutes,
                                        self._flightTimeEnd.minutes)

        timesOK = self._flightInfo.hasComments or \
                  self._flightInfo.hasDelayCode or \
                  (departureDifference<=Flight.TIME_ERROR_DIFFERENCE and
                   arrivalDifference<=Flight.TIME_ERROR_DIFFERENCE and
                   flightStartDifference>=0 and flightStartDifference<30 and
                   flightEndDifference>=0 and flightEndDifference<30)

        text = self._sid.get_child().get_text()
        sid = text if self._sid.get_active()!=0 and text and text!="N/A" \
               else None

        text = self._star.get_child().get_text()
        star = text if self._star.get_active()!=0 and text and text!="N/A" \
               else None

        text = self._transition.get_child().get_text()
        transition = text if self._transition.get_active()!=0 \
                     and text and text!="N/A" else None


        buffer = self._userRoute.get_buffer()
        route =  buffer.get_text(buffer.get_start_iter(),
                                 buffer.get_end_iter(), True)

        numPassengers = \
            self._flownNumPassengers.get_value_as_int() + \
            self._flownNumChildren.get_value_as_int() + \
            self._flownNumInfants.get_value_as_int()

        minCabinCrew = 0 if numPassengers==0 else \
            (bookedFlight.maxPassengers // 50) + 1

        self._okButton.set_sensitive(self._modified and timesOK and
                                     self._flightInfo.faultsFullyExplained and
                                     numPassengers<=bookedFlight.maxPassengers and
                                     self._flownNumCabinCrew.get_value_as_int()>=minCabinCrew and
                                     self._fuelUsed.get_value_as_int()>0 and
                                     self._departureRunway.get_text_length()>0 and
                                     self._arrivalRunway.get_text_length()>0 and
                                     self._departureMETAR.get_buffer().get_char_count()>0 and
                                     self._arrivalMETAR.get_buffer().get_char_count()>0 and
                                     self._filedCruiseLevel.get_value_as_int()>=50 and
                                     self._modifiedCruiseLevel.get_value_as_int()>=50 and
                                     sid is not None and (star is not None or
                                     transition is not None) and route!="" and
                                     self._approachType.get_text()!="")

    def _okClicked(self, button):
        """Called when the OK button has been clicked.

        The PIREP is updated from the data in the window."""
        if not askYesNo(xstr("pirepEdit_save_question"), parent = self):
            self.response(Gtk.ResponseType.CANCEL)

        pirep = self._pirep

        pirep.filedCruiseAltitude = \
          self._filedCruiseLevel.get_value_as_int() * 100
        pirep.cruiseAltitude = \
          self._modifiedCruiseLevel.get_value_as_int() * 100

        pirep.route = getTextViewText(self._userRoute)

        pirep.departureMETAR = getTextViewText(self._departureMETAR)
        pirep.departureRunway = self._departureRunway.get_text()
        pirep.sid = self._sid.get_child().get_text()

        pirep.arrivalMETAR = getTextViewText(self._arrivalMETAR)
        pirep.star = None if self._star.get_active()==0 \
          else self._star.get_child().get_text()
        pirep.transition = None if self._transition.get_active()==0 \
          else self._transition.get_child().get_text()
        pirep.approachType = self._approachType.get_text()
        pirep.arrivalRunway = self._arrivalRunway.get_text()

        pirep.blockTimeStart = \
          self._blockTimeStart.getTimestampFrom(pirep.blockTimeStart)
        pirep.blockTimeEnd = \
          self._blockTimeEnd.getTimestampFrom(pirep.blockTimeEnd)
        pirep.flightTimeStart = \
          self._flightTimeStart.getTimestampFrom(pirep.flightTimeStart)
        pirep.flightTimeEnd = \
          self._flightTimeEnd.getTimestampFrom(pirep.flightTimeEnd)

        pirep.fuelUsed = self._fuelUsed.get_value()

        pirep.numCabinCrew = self._flownNumCabinCrew.get_value()
        pirep.numPassengers = self._flownNumPassengers.get_value()
        pirep.bagWeight = self._flownBagWeight.get_value()
        pirep.cargoWeight = self._flownCargoWeight.get_value()
        pirep.mailWeight = self._flownMailWeight.get_value()

        pirep.flightType = flightTypes[self._flightType.get_active()]
        pirep.online = self._online.get_active()

        pirep.delayCodes = self._flightInfo.delayCodes
        pirep.comments = self._flightInfo.comments
        pirep.flightDefects = self._flightInfo.faultsAndExplanations

        self.response(Gtk.ResponseType.OK)


#------------------------------------------------------------------------------
