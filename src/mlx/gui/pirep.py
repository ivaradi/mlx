# Module for the detailed PIREP viewer

#------------------------------------------------------------------------------

from common import *

from mlx.const import *

import time

#------------------------------------------------------------------------------

class PIREPViewer(gtk.Dialog):
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
        frame = gtk.Frame(label = label)

        alignment = gtk.Alignment(xalign = 0.0, yalign = 0.0,
                                  xscale = 1.0, yscale = 1.0)
        frame.add(alignment)
        alignment.set_padding(padding_top = 4, padding_bottom = 4,
                              padding_left = 4, padding_right = 4)
        box = gtk.VBox()
        alignment.add(box)
        
        return (frame, box)

    @staticmethod
    def getLabel(text):
        """Get a bold label with the given text."""
        label = gtk.Label("<b>" + text + "</b>")
        label.set_use_markup(True)
        label.set_alignment(0.0, 0.5)
        return label

    @staticmethod
    def getDataLabel(width = None, xAlignment = 0.0):
        """Get a bold label with the given text."""
        label = gtk.Label()
        if width is not None:
            label.set_width_chars(width)
        label.set_alignment(xAlignment, 0.5)
        return label

    @staticmethod
    def getTextWindow(heightRequest = 40):
        """Get a scrollable text window.
        
        Returns a tuple of the following items:
        - the window,
        - the text view."""
        scrolledWindow = gtk.ScrolledWindow()
        scrolledWindow.set_shadow_type(SHADOW_IN)
        scrolledWindow.set_policy(POLICY_AUTOMATIC, POLICY_AUTOMATIC)

        textView = gtk.TextView()
        textView.set_wrap_mode(WRAP_WORD)
        textView.set_editable(False)
        textView.set_cursor_visible(False)
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
        dataBox = gtk.HBox()
        table.attach(dataBox, column, column+1, row, row+1)
        
        dataLabel = PIREPViewer.addLabeledData(dataBox, labelText,
                                               width = width)
        dataLabel.set_alignment(dataLabelXAlignment, 0.5)

        return dataLabel

    @staticmethod
    def addLabeledData(hBox, labelText, width = None, dataPadding = 8):
        """Add a label and a data label to the given HBox.
        
        Returnsd the data label."""
        label = PIREPViewer.getLabel(labelText)
        hBox.pack_start(label, False, False, 0)
                
        dataLabel = PIREPViewer.getDataLabel(width = width)
        hBox.pack_start(dataLabel, False, False, dataPadding)

        return dataLabel

    @staticmethod
    def addVFiller(vBox, height = 4):
        """Add a filler eventbox to the given vertical box."""
        filler = gtk.EventBox()
        filler.set_size_request(-1, height)
        vBox.pack_start(filler, False, False, 0)
        
    @staticmethod
    def timestamp2text(label, timestamp):
        """Convert the given timestamp into a text containing the hour
        and minute in UTC and put that text into the given label."""
        tm = time.gmtime(timestamp)
        label.set_text("%02d:%02d" % (tm.tm_hour, tm.tm_min))

    def __init__(self, gui):
        """Construct the PIREP viewer."""
        super(PIREPViewer, self).__init__(title = WINDOW_TITLE_BASE +
                                          " - " +
                                          xstr("pirepView_title"),
                                          parent = gui.mainWindow)
                                          
        self.set_resizable(False)

        self._gui = gui
        
        contentArea = self.get_content_area()

        self._notebook = gtk.Notebook()
        contentArea.pack_start(self._notebook, False, False, 4)
        
        dataTab = self._buildDataTab()
        label = gtk.Label(xstr("pirepView_tab_data"))
        label.set_use_underline(True)
        label.set_tooltip_text(xstr("pirepView_tab_data_tooltip"))
        self._notebook.append_page(dataTab, label)
        
        commentsTab = self._buildCommentsTab()
        label = gtk.Label(xstr("pirepView_tab_comments"))
        label.set_use_underline(True)
        label.set_tooltip_text(xstr("pirepView_tab_comments_tooltip"))
        self._notebook.append_page(commentsTab, label)
        
        logTab = self._buildLogTab()
        label = gtk.Label(xstr("pirepView_tab_log"))
        label.set_use_underline(True)
        label.set_tooltip_text(xstr("pirepView_tab_log_tooltip"))
        self._notebook.append_page(logTab, label)

        self._okButton = self.add_button(xstr("button_ok"), RESPONSETYPE_OK)
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

        self._numPassengers.set_text(str(bookedFlight.numPassengers))
        self._numCrew.set_text(str(bookedFlight.numCrew))
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

        self._flownCargoWeight.set_text("%.0f" % (pirep.cargoWeight,))
        self._flightType.set_text(xstr("flighttype_" + 
                                       flightType2string(pirep.flightType)))
        self._online.set_text(xstr("pirepView_" +
                                   ("yes" if pirep.online else "no")))

        delayCodes = ""
        for code in pirep.delayCodes:
            if delayCodes: delayCodes += ", "
            delayCodes += PIREP.delayCodes[code]
        
        self._delayCodes.get_buffer().set_text(delayCodes)        

        self._comments.get_buffer().set_text(pirep.comments)
        self._flightDefects.get_buffer().set_text(pirep.flightDefects)

        logBuffer = self._log.get_buffer()
        logBuffer.set_text("")
        for (timeStr, line) in pirep.logLines:
            logBuffer.insert(logBuffer.get_end_iter(), 
                             formatFlightLogLine(timeStr, line))

        self._notebook.set_current_page(0)
        self._okButton.grab_default()

    def _buildDataTab(self):
        """Build the data tab of the viewer."""
        table = gtk.Table(1, 2)
        table.set_row_spacings(4)
        table.set_col_spacings(16)
        table.set_homogeneous(True)

        box1 = gtk.VBox()
        table.attach(box1, 0, 1, 0, 1)
        
        box2 = gtk.VBox()
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
        
        dataBox = gtk.HBox()
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

        dataBox = gtk.HBox()
        mainBox.pack_start(dataBox, False, False, 0)

        self._aircraftType = \
            PIREPViewer.addLabeledData(dataBox,
                                       xstr("pirepView_aircraftType"),
                                       width = 25)

        PIREPViewer.addVFiller(mainBox)

        table = gtk.Table(3, 2)
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

        table = gtk.Table(3, 2)
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

        levelBox = gtk.HBox()
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

        dataBox = gtk.HBox()
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

        table = gtk.Table(2, 2)
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

        table = gtk.Table(4, 2)
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
        
        dataBox = gtk.HBox()
        mainBox.pack_start(dataBox, False, False, 0)
        
        self._flownCargoWeight = \
            PIREPViewer.addLabeledData(dataBox,
                                       xstr("pirepView_cargoWeight"),
                                       width = 6)

        self._flightType = \
            PIREPViewer.addLabeledData(dataBox,
                                       xstr("pirepView_flightType"),
                                       width = 10)
            
        self._online = \
            PIREPViewer.addLabeledData(dataBox,
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
        table = gtk.Table(2, 1)
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
        mainBox = gtk.VBox()

        (logWindow, self._log) = PIREPViewer.getTextWindow(heightRequest = -1)
        mainBox.pack_start(logWindow, True, True, 0)
        
        return mainBox
        
#------------------------------------------------------------------------------
