# The flight handling "wizard"

from mlx.gui.common import *

import mlx.const as const
import mlx.fs as fs
from mlx.checks import PayloadChecker

import datetime
import time

#-----------------------------------------------------------------------------

class Page(gtk.Alignment):
    """A page in the flight wizard."""
    def __init__(self, wizard, title, help):
        """Construct the page."""
        super(Page, self).__init__(xalign = 0.0, yalign = 0.0,
                                   xscale = 1.0, yscale = 1.0)
        self.set_padding(padding_top = 4, padding_bottom = 4,
                         padding_left = 12, padding_right = 12)

        frame = gtk.Frame()
        self.add(frame)

        style = self.get_style() if pygobject else self.rc_get_style()

        self._vbox = gtk.VBox()
        self._vbox.set_homogeneous(False)
        frame.add(self._vbox)

        eventBox = gtk.EventBox()
        eventBox.modify_bg(0, style.bg[3])

        alignment = gtk.Alignment(xalign = 0.0, xscale = 0.0)
        
        label = gtk.Label(title)
        label.modify_fg(0, style.fg[3])
        label.modify_font(pango.FontDescription("bold 24"))
        alignment.set_padding(padding_top = 4, padding_bottom = 4,
                              padding_left = 6, padding_right = 0)
                              
        alignment.add(label)
        eventBox.add(alignment)
        
        self._vbox.pack_start(eventBox, False, False, 0)

        table = gtk.Table(3, 1)
        table.set_homogeneous(False)

        alignment = gtk.Alignment(xalign = 0.0, yalign = 0.0,
                                  xscale = 1.0, yscale = 1.0)        
        alignment.set_padding(padding_top = 16, padding_bottom = 16,
                              padding_left = 16, padding_right = 16)
        alignment.add(table)
        self._vbox.pack_start(alignment, True, True, 0)
        
        alignment = gtk.Alignment(xalign = 0.5, yalign = 0.0,
                                  xscale = 0, yscale = 0.0)
        alignment.set_padding(padding_top = 0, padding_bottom = 16,
                              padding_left = 0, padding_right = 0)

        label = gtk.Label(help)
        label.set_justify(gtk.Justification.CENTER if pygobject
                          else gtk.JUSTIFY_CENTER)
        alignment.add(label)
        table.attach(alignment, 0, 1, 0, 1)

        self._mainAlignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                            xscale = 1.0, yscale = 1.0)
        table.attach(self._mainAlignment, 0, 1, 1, 3)
                                            
        buttonAlignment =  gtk.Alignment(xalign = 1.0, xscale=0.0, yscale = 0.0)
        buttonAlignment.set_padding(padding_top = 4, padding_bottom = 10,
                                    padding_left = 16, padding_right = 16)

        self._buttonBox = gtk.HButtonBox()
        self._defaultButton = None
        buttonAlignment.add(self._buttonBox)

        self._vbox.pack_start(buttonAlignment, False, False, 0)

        self._wizard = wizard

    def setMainWidget(self, widget):
        """Set the given widget as the main one."""
        self._mainAlignment.add(widget)

    def addButton(self, label, default = False):
        """Add a button with the given label.

        Return the button object created."""
        button = gtk.Button(label)
        self._buttonBox.add(button)
        button.set_use_underline(True)
        if default:
            button.set_can_default(True)
            self._defaultButton = button
        return button

    def activate(self):
        """Called when this page becomes active.

        This default implementation does nothing."""
        pass

    def grabDefault(self):
        """If the page has a default button, make it the default one."""
        if self._defaultButton is not None:
            self._defaultButton.grab_default()

    def reset(self):
        """Reset the page if the wizard is reset."""
        pass
    
#-----------------------------------------------------------------------------

class LoginPage(Page):
    """The login page."""
    def __init__(self, wizard):
        """Construct the login page."""
        help = "Enter your MAVA pilot's ID and password to\n" \
        "log in to the MAVA website and download\n" \
        "your booked flights."
        super(LoginPage, self).__init__(wizard, "Login", help)

        alignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)
        
        table = gtk.Table(2, 3)
        table.set_row_spacings(4)
        table.set_col_spacings(32)
        alignment.add(table)
        self.setMainWidget(alignment)

        labelAlignment = gtk.Alignment(xalign=1.0, xscale=0.0)
        label = gtk.Label("Pilot _ID:")
        label.set_use_underline(True)
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, 0, 1)

        self._pilotID = gtk.Entry()
        self._pilotID.connect("changed", self._setLoginButton)
        self._pilotID.set_tooltip_text("Enter your MAVA pilot's ID. This "
                                       "usually starts with a "
                                       "'P' followed by 3 digits.")
        table.attach(self._pilotID, 1, 2, 0, 1)
        label.set_mnemonic_widget(self._pilotID)

        labelAlignment = gtk.Alignment(xalign=1.0, xscale=0.0)
        label = gtk.Label("_Password:")
        label.set_use_underline(True)
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, 1, 2)

        self._password = gtk.Entry()
        self._password.set_visibility(False)
        self._password.connect("changed", self._setLoginButton)
        self._password.set_tooltip_text("Enter the password for your pilot's ID")
        table.attach(self._password, 1, 2, 1, 2)
        label.set_mnemonic_widget(self._password)

        self._rememberButton = gtk.CheckButton("_Remember password")
        self._rememberButton.set_use_underline(True)
        self._rememberButton.set_tooltip_text("If checked, your password will "
                                              "be stored, so that you should "
                                              "not have to enter it every time. "
                                              "Note, however, that the password "
                                              "is stored as text, and anybody "
                                              "who can access your files will "
                                              "be able to read it.")
        table.attach(self._rememberButton, 1, 2, 2, 3, ypadding = 8)

        self._loginButton = self.addButton("_Login", default = True)
        self._loginButton.set_sensitive(False)
        self._loginButton.connect("clicked", self._loginClicked)
        self._loginButton.set_tooltip_text("Click to log in.")
        
        config = self._wizard.gui.config
        self._pilotID.set_text(config.pilotID)
        self._password.set_text(config.password)
        self._rememberButton.set_active(config.rememberPassword)

    def _setLoginButton(self, entry):
        """Set the login button's sensitivity.

        The button is sensitive only if both the pilot ID and the password
        fields contain values."""
        self._loginButton.set_sensitive(self._pilotID.get_text()!="" and
                                        self._password.get_text()!="")

    def _loginClicked(self, button):
        """Called when the login button was clicked."""
        self._wizard.gui.beginBusy("Logging in...")
        self._wizard.gui.webHandler.login(self._loginResultCallback,
                                          self._pilotID.get_text(),
                                          self._password.get_text())

    def _loginResultCallback(self, returned, result):
        """The login result callback, called in the web handler's thread."""
        gobject.idle_add(self._handleLoginResult, returned, result)

    def _handleLoginResult(self, returned, result):
        """Handle the login result."""
        self._wizard.gui.endBusy()
        if returned:
            if result.loggedIn:
                config = self._wizard.gui.config

                config.pilotID = self._pilotID.get_text()

                rememberPassword = self._rememberButton.get_active()                
                config.password = self._password.get_text() if rememberPassword  \
                                  else ""

                config.rememberPassword = rememberPassword
                
                config.save()
                self._wizard._loginResult = result
                self._wizard.nextPage()
            else:
                dialog = gtk.MessageDialog(type = MESSAGETYPE_ERROR,
                                           buttons = BUTTONSTYPE_OK,
                                           message_format =
                                           "Invalid pilot's ID or password.")
                dialog.format_secondary_markup("Check the ID and try to reenter"
                                               " the password.")
                dialog.run()
                dialog.hide()
        else:
            dialog = gtk.MessageDialog(type = MESSAGETYPE_ERROR,
                                       buttons = BUTTONSTYPE_OK,
                                       message_format = 
                                       "Failed to connect to the MAVA website.")
            dialog.format_secondary_markup("Try again in a few minutes.")
            dialog.run()
            dialog.hide()

#-----------------------------------------------------------------------------

class FlightSelectionPage(Page):
    """The page to select the flight."""
    def __init__(self, wizard):
        """Construct the flight selection page."""
        super(FlightSelectionPage, self).__init__(wizard, "Flight selection",
                                                  "Select the flight you want "
                                                  "to perform.")


        self._listStore = gtk.ListStore(str, str, str, str)
        self._flightList = gtk.TreeView(self._listStore)
        column = gtk.TreeViewColumn("Flight no.", gtk.CellRendererText(),
                                    text = 1)
        column.set_expand(True)
        self._flightList.append_column(column)
        column = gtk.TreeViewColumn("Departure time [UTC]", gtk.CellRendererText(),
                                    text = 0)
        column.set_expand(True)
        self._flightList.append_column(column)
        column = gtk.TreeViewColumn("From", gtk.CellRendererText(),
                                    text = 2)
        column.set_expand(True)
        self._flightList.append_column(column)
        column = gtk.TreeViewColumn("To", gtk.CellRendererText(),
                                    text = 3)
        column.set_expand(True)
        self._flightList.append_column(column)

        flightSelection = self._flightList.get_selection()
        flightSelection.connect("changed", self._selectionChanged)

        scrolledWindow = gtk.ScrolledWindow()
        scrolledWindow.add(self._flightList)
        scrolledWindow.set_size_request(400, -1)
        scrolledWindow.set_policy(gtk.PolicyType.AUTOMATIC if pygobject
                                  else gtk.POLICY_AUTOMATIC,
                                  gtk.PolicyType.AUTOMATIC if pygobject
                                  else gtk.POLICY_AUTOMATIC)
        scrolledWindow.set_shadow_type(gtk.ShadowType.IN if pygobject
                                       else gtk.SHADOW_IN)

        alignment = gtk.Alignment(xalign = 0.5, yalign = 0.0, xscale = 0.0, yscale = 1.0)
        alignment.add(scrolledWindow)

        self.setMainWidget(alignment)

        self._button = self.addButton(gtk.STOCK_GO_FORWARD, default = True)
        self._button.set_use_stock(True)
        self._button.set_sensitive(False)
        self._button.connect("clicked", self._forwardClicked)

        self._activated = False

    def activate(self):
        """Fill the flight list."""
        if not self._activated:
            for flight in self._wizard.loginResult.flights:
                self._listStore.append([str(flight.departureTime),
                                        flight.callsign,
                                        flight.departureICAO,
                                        flight.arrivalICAO])
            self._activated = True

    def _selectionChanged(self, selection):
        """Called when the selection is changed."""
        self._button.set_sensitive(selection.count_selected_rows()==1)

    def _forwardClicked(self, button):
        """Called when the forward button was clicked."""
        selection = self._flightList.get_selection()
        (listStore, iter) = selection.get_selected()
        path = listStore.get_path(iter)
        [index] = path.get_indices() if pygobject else path

        flight = self._wizard.loginResult.flights[index]
        self._wizard._bookedFlight = flight

        self._updateDepartureGate()
        
    def _updateDepartureGate(self):
        """Update the departure gate for the booked flight."""
        flight = self._wizard._bookedFlight
        if flight.departureICAO=="LHBP":
            self._wizard._getFleet(self._fleetRetrieved)
        else:
            self._wizard.jumpPage(2)

    def _fleetRetrieved(self, fleet):
        """Called when the fleet has been retrieved."""
        if fleet is None:
            self._wizard.jumpPage(2)
        else:
            plane = fleet[self._wizard._bookedFlight.tailNumber]
            if plane is None:
                self._wizard.jumpPage(2)
            
            if plane.gateNumber is not None and \
               not fleet.isGateConflicting(plane):
                self._wizard._departureGate = plane.gateNumber
                self._wizard.jumpPage(2)
            else:
                self._wizard.nextPage()
        
#-----------------------------------------------------------------------------

class GateSelectionPage(Page):
    """Page to select a free gate at LHBP.

    This page should be displayed only if we have fleet information!."""
    def __init__(self, wizard):
        """Construct the gate selection page."""
        help = "The airplane's gate position is invalid.\n\n" \
               "Select the gate from which you\n" \
               "would like to begin the flight."
        super(GateSelectionPage, self).__init__(wizard,
                                                "LHBP gate selection",
                                                help)

        self._listStore = gtk.ListStore(str)
        self._gateList = gtk.TreeView(self._listStore)
        column = gtk.TreeViewColumn(None, gtk.CellRendererText(),
                                    text = 0)
        column.set_expand(True)
        self._gateList.append_column(column)
        self._gateList.set_headers_visible(False)

        gateSelection = self._gateList.get_selection()
        gateSelection.connect("changed", self._selectionChanged)

        scrolledWindow = gtk.ScrolledWindow()
        scrolledWindow.add(self._gateList)
        scrolledWindow.set_size_request(50, -1)
        scrolledWindow.set_policy(gtk.PolicyType.AUTOMATIC if pygobject
                                  else gtk.POLICY_AUTOMATIC,
                                  gtk.PolicyType.AUTOMATIC if pygobject
                                  else gtk.POLICY_AUTOMATIC)
        scrolledWindow.set_shadow_type(gtk.ShadowType.IN if pygobject
                                       else gtk.SHADOW_IN)

        alignment = gtk.Alignment(xalign = 0.5, yalign = 0.0, xscale = 0.0, yscale = 1.0)
        alignment.add(scrolledWindow)

        self.setMainWidget(alignment)        

        self._button = self.addButton(gtk.STOCK_GO_FORWARD, default = True)
        self._button.set_use_stock(True)
        self._button.set_sensitive(False)
        self._button.connect("clicked", self._forwardClicked)

    def activate(self):
        """Fill the gate list."""
        self._listStore.clear()
        occupiedGateNumbers = self._wizard._fleet.getOccupiedGateNumbers()
        for gateNumber in const.lhbpGateNumbers:
            if gateNumber not in occupiedGateNumbers:
                self._listStore.append([gateNumber])

    def _selectionChanged(self, selection):
        """Called when the selection is changed."""
        self._button.set_sensitive(selection.count_selected_rows()==1)

    def _forwardClicked(self, button):
        """Called when the forward button is clicked."""
        selection = self._gateList.get_selection()
        (listStore, iter) = selection.get_selected()
        (gateNumber,) = listStore.get(iter, 0)

        self._wizard._departureGate = gateNumber

        #self._wizard._updatePlane(self._planeUpdated,
        #                          self._wizard._bookedFlight.tailNumber,
        #                          const.PLANE_HOME,
        #                          gateNumber)
        self._wizard.nextPage()

    def _planeUpdated(self, success):
        """Callback for the plane updating call."""
        if success is None or success:
            self._wizard.nextPage()
        else:
            dialog = gtk.MessageDialog(type = MESSAGETYPE_ERROR,
                                       buttons = BUTTONSTYPE_OK,
                                       message_format = "Gate conflict detected again")
            dialog.format_secondary_markup("Try to select a different gate.")
            dialog.run()
            dialog.hide()

            self._wizard._getFleet(self._fleetRetrieved)

    def _fleetRetrieved(self, fleet):
        """Called when the fleet has been retrieved."""
        if fleet is None:
            self._wizard.nextPage()
        else:
            self.activate()
            
#-----------------------------------------------------------------------------

class ConnectPage(Page):
    """Page which displays the departure airport and gate (if at LHBP)."""
    def __init__(self, wizard):
        """Construct the connect page."""
        help = "The flight begins at the airport given below.\n" \
               "Park your aircraft there, at the gate below, if given.\n\n" \
               "Then press the Connect button to connect to the simulator."
        super(ConnectPage, self).__init__(wizard,
                                          "Connect to the simulator",
                                          help)
        
        alignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)

        table = gtk.Table(2, 2)
        table.set_row_spacings(4)
        table.set_col_spacings(16)
        table.set_homogeneous(True)
        alignment.add(table)
        self.setMainWidget(alignment)

        labelAlignment = gtk.Alignment(xalign=1.0, xscale=0.0)
        label = gtk.Label("ICAO code:")
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, 0, 1)

        labelAlignment = gtk.Alignment(xalign=0.0, xscale=0.0)
        self._departureICAO = gtk.Label()
        self._departureICAO.set_width_chars(5)
        self._departureICAO.set_alignment(0.0, 0.5)
        labelAlignment.add(self._departureICAO)
        table.attach(labelAlignment, 1, 2, 0, 1)

        labelAlignment = gtk.Alignment(xalign=1.0, xscale=0.0)
        label = gtk.Label("Gate:")
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, 1, 2)

        labelAlignment = gtk.Alignment(xalign=0.0, xscale=0.0)
        self._departureGate = gtk.Label()
        self._departureGate.set_width_chars(5)
        self._departureGate.set_alignment(0.0, 0.5)
        labelAlignment.add(self._departureGate)
        table.attach(labelAlignment, 1, 2, 1, 2)

        self._button = self.addButton("_Connect", default = True)
        self._button.set_use_underline(True)
        self._button.connect("clicked", self._connectClicked)

    def activate(self):
        """Setup the departure information."""
        icao = self._wizard._bookedFlight.departureICAO
        self._departureICAO.set_markup("<b>" + icao + "</b>")
        gate = self._wizard._departureGate
        if gate!="-":
            gate = "<b>" + gate + "</b>"
        self._departureGate.set_markup(gate)

    def _connectClicked(self, button):
        """Called when the Connect button is pressed."""
        self._wizard._connectSimulator()

#-----------------------------------------------------------------------------

class PayloadPage(Page):
    """Page to allow setting up the payload."""
    def __init__(self, wizard):
        """Construct the page."""
        help = "The briefing contains the weights below.\n" \
               "Setup the cargo weight here and the payload weight in the simulator.\n\n" \
               "You can also check here what the simulator reports as ZFW."
               
        super(PayloadPage, self).__init__(wizard, "Payload", help)

        alignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)

        table = gtk.Table(7, 3)
        table.set_row_spacings(4)
        table.set_col_spacings(16)
        table.set_homogeneous(False)
        alignment.add(table)
        self.setMainWidget(alignment)

        label = gtk.Label("Crew:")
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, 0, 1)

        self._numCrew = gtk.Label()
        self._numCrew.set_width_chars(6)
        self._numCrew.set_alignment(1.0, 0.5)
        table.attach(self._numCrew, 1, 2, 0, 1)
        
        label = gtk.Label("Passengers:")
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, 1, 2)

        self._numPassengers = gtk.Label()
        self._numPassengers.set_width_chars(6)
        self._numPassengers.set_alignment(1.0, 0.5)
        table.attach(self._numPassengers, 1, 2, 1, 2)
        
        label = gtk.Label("Baggage:")
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, 2, 3)

        self._bagWeight = gtk.Label()
        self._bagWeight.set_width_chars(6)
        self._bagWeight.set_alignment(1.0, 0.5)
        table.attach(self._bagWeight, 1, 2, 2, 3)

        table.attach(gtk.Label("kg"), 2, 3, 2, 3)
        
        label = gtk.Label("_Cargo:")
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, 3, 4)

        self._cargoWeight = gtk.Entry()
        self._cargoWeight.set_width_chars(6)
        self._cargoWeight.set_alignment(1.0)
        self._cargoWeight.connect("changed", self._cargoWeightChanged)
        self._cargoWeight.set_tooltip_text("The weight of the cargo for your flight.")
        table.attach(self._cargoWeight, 1, 2, 3, 4)
        self._cargoWeightValue = 0        
        label.set_mnemonic_widget(self._cargoWeight)

        table.attach(gtk.Label("kg"), 2, 3, 3, 4)
        
        label = gtk.Label("Mail:")
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, 4, 5)

        self._mailWeight = gtk.Label()
        self._mailWeight.set_width_chars(6)
        self._mailWeight.set_alignment(1.0, 0.5)
        table.attach(self._mailWeight, 1, 2, 4, 5)

        table.attach(gtk.Label("kg"), 2, 3, 4, 5)
        
        label = gtk.Label("<b>Calculated ZFW:</b>")
        label.set_alignment(0.0, 0.5)
        label.set_use_markup(True)
        table.attach(label, 0, 1, 5, 6)

        self._calculatedZFW = gtk.Label()
        self._calculatedZFW.set_width_chars(6)
        self._calculatedZFW.set_alignment(1.0, 0.5)
        table.attach(self._calculatedZFW, 1, 2, 5, 6)

        table.attach(gtk.Label("kg"), 2, 3, 5, 6)

        button = gtk.Button("_ZFW from FS:")
        button.set_use_underline(True)
        button.connect("clicked", self._zfwRequested)
        table.attach(button, 0, 1, 6, 7)

        self._simulatorZFW = gtk.Label("-")
        self._simulatorZFW.set_width_chars(6)
        self._simulatorZFW.set_alignment(1.0, 0.5)
        table.attach(self._simulatorZFW, 1, 2, 6, 7)
        self._simulatorZFWValue = None

        table.attach(gtk.Label("kg"), 2, 3, 6, 7)

        self._button = self.addButton(gtk.STOCK_GO_FORWARD, default = True)
        self._button.set_use_stock(True)
        self._button.connect("clicked", self._forwardClicked)

    def activate(self):
        """Setup the information."""
        bookedFlight = self._wizard._bookedFlight
        self._numCrew.set_text(str(bookedFlight.numCrew))
        self._numPassengers.set_text(str(bookedFlight.numPassengers))
        self._bagWeight.set_text(str(bookedFlight.bagWeight))
        self._cargoWeightValue = bookedFlight.cargoWeight
        self._cargoWeight.set_text(str(bookedFlight.cargoWeight))
        self._mailWeight.set_text(str(bookedFlight.mailWeight))
        self._updateCalculatedZFW()

    def _calculateZFW(self):
        """Calculate the ZFW value."""
        zfw = self._wizard.gui._flight.aircraft.dow
        bookedFlight = self._wizard._bookedFlight
        zfw += (bookedFlight.numCrew + bookedFlight.numPassengers) * 82
        zfw += bookedFlight.bagWeight
        zfw += self._cargoWeightValue
        zfw += bookedFlight.mailWeight
        return zfw
        
    def _updateCalculatedZFW(self):
        """Update the calculated ZFW"""
        zfw = self._calculateZFW()

        markupBegin = "<b>"
        markupEnd = "</b>"
        if self._simulatorZFWValue is not None and \
           PayloadChecker.isZFWFaulty(self._simulatorZFWValue, zfw):
            markupBegin += '<span foreground="red">'
            markupEnd = "</span>" + markupEnd
        self._calculatedZFW.set_markup(markupBegin + str(zfw) + markupEnd)

    def _cargoWeightChanged(self, entry):
        """Called when the cargo weight has changed."""
        text = self._cargoWeight.get_text()
        if text=="":
            self._cargoWeightValue = 0
        else:
            try:
                self._cargoWeightValue = int(text)
            except:
                self._cargoWeight.set_text(str(self._cargoWeightValue))
        self._updateCalculatedZFW()
            
    def _zfwRequested(self, button):
        """Called when the ZFW is requested from the simulator."""
        self._wizard.gui.beginBusy("Querying ZFW...")
        self._wizard.gui.simulator.requestZFW(self._handleZFW)

    def _handleZFW(self, zfw):
        """Called when the ZFW value is retrieved."""
        gobject.idle_add(self._processZFW, zfw)

    def _processZFW(self, zfw):
        """Process the given ZFW value received from the simulator."""
        self._wizard.gui.endBusy()
        self._simulatorZFWValue = zfw
        self._simulatorZFW.set_text("%.0f" % (zfw,))
        self._updateCalculatedZFW()

    def _forwardClicked(self, button):
        """Called when the forward button is clicked."""
        self._wizard._zfw = self._calculateZFW()
        self._wizard.nextPage()
        
#-----------------------------------------------------------------------------

class TimePage(Page):
    """Page displaying the departure and arrival times and allows querying the
    current time from the flight simulator."""
    def __init__(self, wizard):
        help = "The departure and arrival times are displayed below in UTC.\n\n" \
               "You can also query the current UTC time from the simulator.\n" \
               "Ensure that you have enough time to properly prepare for the flight."
               
        super(TimePage, self).__init__(wizard, "Time", help)

        alignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)

        table = gtk.Table(3, 2)
        table.set_row_spacings(4)
        table.set_col_spacings(16)
        table.set_homogeneous(False)
        alignment.add(table)
        self.setMainWidget(alignment)

        label = gtk.Label("Departure:")
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, 0, 1)

        self._departure = gtk.Label()
        self._departure.set_alignment(0.0, 0.5)
        table.attach(self._departure, 1, 2, 0, 1)
        
        label = gtk.Label("Arrival:")
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, 1, 2)

        self._arrival = gtk.Label()
        self._arrival.set_alignment(0.0, 0.5)
        table.attach(self._arrival, 1, 2, 1, 2)

        button = gtk.Button("_Time from FS:")
        button.set_use_underline(True)
        button.connect("clicked", self._timeRequested)
        table.attach(button, 0, 1, 2, 3)

        self._simulatorTime = gtk.Label("-")
        self._simulatorTime.set_alignment(0.0, 0.5)
        table.attach(self._simulatorTime, 1, 2, 2, 3)

        self._button = self.addButton(gtk.STOCK_GO_FORWARD, default = True)
        self._button.set_use_stock(True)
        self._button.connect("clicked", self._forwardClicked)

    def activate(self):
        """Activate the page."""
        bookedFlight = self._wizard._bookedFlight
        self._departure.set_text(str(bookedFlight.departureTime.time()))
        self._arrival.set_text(str(bookedFlight.arrivalTime.time()))

    def _timeRequested(self, button):
        """Request the time from the simulator."""
        self._wizard.gui.beginBusy("Querying time...")
        self._wizard.gui.simulator.requestTime(self._handleTime)

    def _handleTime(self, timestamp):
        """Handle the result of a time retrieval."""
        gobject.idle_add(self._processTime, timestamp)

    def _processTime(self, timestamp):
        """Process the given time."""
        self._wizard.gui.endBusy()
        tm = time.gmtime(timestamp)
        t = datetime.time(tm.tm_hour, tm.tm_min, tm.tm_sec)
        self._simulatorTime.set_text(str(t))

        ts = tm.tm_hour * 3600 + tm.tm_min * 60 + tm.tm_sec
        dt = self._wizard._bookedFlight.departureTime.time()
        dts = dt.hour * 3600 + dt.minute * 60 + dt.second
        diff = dts-ts

        markupBegin = ""
        markupEnd = ""
        if diff < 0:
            markupBegin = '<b><span foreground="red">'
            markupEnd = '</span></b>'
        elif diff < 3*60 or diff > 30*60:
            markupBegin = '<b><span foreground="orange">'
            markupEnd = '</span></b>'

        self._departure.set_markup(markupBegin + str(dt) + markupEnd)

    def _forwardClicked(self, button):
        """Called when the forward button is clicked."""
        self._wizard.nextPage()
        
#-----------------------------------------------------------------------------

class RoutePage(Page):
    """The page containing the route and the flight level."""
    def __init__(self, wizard):
        help = "Set your cruise flight level below, and\n" \
               "if necessary, edit the flight plan."
               
        super(RoutePage, self).__init__(wizard, "Route", help)

        alignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)

        mainBox = gtk.VBox()
        alignment.add(mainBox)
        self.setMainWidget(alignment)

        levelBox = gtk.HBox()

        label = gtk.Label("_Cruise level")
        label.set_use_underline(True)
        levelBox.pack_start(label, True, True, 0)

        self._cruiseLevel = gtk.SpinButton()
        self._cruiseLevel.set_increments(step = 10, page = 100)
        self._cruiseLevel.set_range(min = 50, max = 500)
        self._cruiseLevel.set_value(240)
        self._cruiseLevel.set_tooltip_text("The cruise flight level.")
        self._cruiseLevel.set_numeric(True)
        self._cruiseLevel.connect("value-changed", self._cruiseLevelChanged)
        label.set_mnemonic_widget(self._cruiseLevel)        

        levelBox.pack_start(self._cruiseLevel, False, False, 8)

        alignment = gtk.Alignment(xalign = 0.0, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)
        alignment.add(levelBox)

        mainBox.pack_start(alignment, False, False, 0)


        routeBox = gtk.VBox()

        alignment = gtk.Alignment(xalign = 0.0, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)
        label = gtk.Label("_Route")
        label.set_use_underline(True)
        alignment.add(label)
        routeBox.pack_start(alignment, True, True, 0)

        routeWindow = gtk.ScrolledWindow()
        routeWindow.set_size_request(400, 80)
        routeWindow.set_shadow_type(gtk.ShadowType.IN if pygobject
                                    else gtk.SHADOW_IN)
        routeWindow.set_policy(gtk.PolicyType.AUTOMATIC if pygobject
                               else gtk.POLICY_AUTOMATIC,
                               gtk.PolicyType.AUTOMATIC if pygobject
                               else gtk.POLICY_AUTOMATIC)

        self._route = gtk.TextView()
        self._route.set_tooltip_text("The planned flight route.")
        self._route.get_buffer().connect("changed", self._routeChanged)
        routeWindow.add(self._route)

        label.set_mnemonic_widget(self._route)
        routeBox.pack_start(routeWindow, True, True, 0)        

        mainBox.pack_start(routeBox, True, True, 8)

        self._button = self.addButton(gtk.STOCK_GO_FORWARD, default = True)
        self._button.set_use_stock(True)
        self._button.connect("clicked", self._forwardClicked)

    def activate(self):
        """Setup the route from the booked flight."""
        self._route.get_buffer().set_text(self._wizard._bookedFlight.route)
        self._updateForwardButton()

    def _getRoute(self):
        """Get the text of the route."""
        buffer = self._route.get_buffer()
        return buffer.get_text(buffer.get_start_iter(),
                               buffer.get_end_iter(), True)

    def _updateForwardButton(self):
        """Update the sensitivity of the forward button."""
        self._button.set_sensitive(self._cruiseLevel.get_value_as_int()>=50 and \
                                   self._getRoute()!="")
                                   
    def _cruiseLevelChanged(self, spinButton):
        """Called when the cruise level has changed."""
        self._updateForwardButton()

    def _routeChanged(self, textBuffer):
        """Called when the route has changed."""
        self._updateForwardButton()

    def _forwardClicked(self, button):
        """Called when the Forward button is clicked."""
        self._wizard._cruiseAltitude = self._cruiseLevel.get_value_as_int() * 100
        self._wizard._route = self._getRoute()

        bookedFlight = self._wizard._bookedFlight
        self._wizard.gui.beginBusy("Downloading NOTAMs...")
        self._wizard.gui.webHandler.getNOTAMs(self._notamsCallback,
                                              bookedFlight.departureICAO,
                                              bookedFlight.arrivalICAO)

    def _notamsCallback(self, returned, result):
        """Callback for the NOTAMs."""
        gobject.idle_add(self._handleNOTAMs, returned, result)

    def _handleNOTAMs(self, returned, result):
        """Handle the NOTAMs."""
        if returned:
            self._wizard._departureNOTAMs = result.departureNOTAMs
            self._wizard._arrivalNOTAMs = result.arrivalNOTAMs
        else:
            self._wizard._departureNOTAMs = None
            self._wizard._arrivalNOTAMs = None

        bookedFlight = self._wizard._bookedFlight
        self._wizard.gui.beginBusy("Downloading METARs...")
        self._wizard.gui.webHandler.getMETARs(self._metarsCallback,
                                              [bookedFlight.departureICAO,
                                               bookedFlight.arrivalICAO])

    def _metarsCallback(self, returned, result):
        """Callback for the METARs."""
        gobject.idle_add(self._handleMETARs, returned, result)

    def _handleMETARs(self, returned, result):
        """Handle the METARs."""
        self._wizard._departureMETAR = None
        self._wizard._arrivalMETAR = None
        bookedFlight = self._wizard._bookedFlight
        if returned:
            if bookedFlight.departureICAO in result.metars:
                self._wizard._departureMETAR = result.metars[bookedFlight.departureICAO]
            if bookedFlight.arrivalICAO in result.metars:
                self._wizard._arrivalMETAR = result.metars[bookedFlight.arrivalICAO]

        self._wizard.gui.endBusy()
        self._wizard.nextPage()

#-----------------------------------------------------------------------------

class BriefingPage(Page):
    """Page for the briefing."""
    def __init__(self, wizard, departure):
        """Construct the briefing page."""
        self._departure = departure
        self._activated = False
        
        title = "Briefing (%d/2): %s" % (1 if departure else 2,
                                        "departure" if departure
                                         else "arrival")
                                                                
        help = "Read carefully the NOTAMs and METAR below."

        super(BriefingPage, self).__init__(wizard, title, help)

        alignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 1.0, yscale = 1.0)

        mainBox = gtk.VBox()
        alignment.add(mainBox)
        self.setMainWidget(alignment)

        self._notamsFrame = gtk.Frame()
        self._notamsFrame.set_label("LHBP NOTAMs")
        scrolledWindow = gtk.ScrolledWindow()
        scrolledWindow.set_size_request(-1, 128)
        scrolledWindow.set_policy(gtk.PolicyType.AUTOMATIC if pygobject
                                  else gtk.POLICY_AUTOMATIC,
                                  gtk.PolicyType.AUTOMATIC if pygobject
                                  else gtk.POLICY_AUTOMATIC)
        self._notams = gtk.TextView()
        self._notams.set_editable(False)
        self._notams.set_accepts_tab(False)
        self._notams.set_wrap_mode(gtk.WrapMode.WORD if pygobject else gtk.WRAP_WORD)
        scrolledWindow.add(self._notams)
        alignment = gtk.Alignment(xalign = 0.0, yalign = 0.0,
                                  xscale = 1.0, yscale = 1.0)
        alignment.set_padding(padding_top = 4, padding_bottom = 0,
                              padding_left = 0, padding_right = 0)
        alignment.add(scrolledWindow)
        self._notamsFrame.add(alignment)
        mainBox.pack_start(self._notamsFrame, True, True, 4)
        
        self._metarFrame = gtk.Frame()
        self._metarFrame.set_label("LHBP METAR")
        scrolledWindow = gtk.ScrolledWindow()
        scrolledWindow.set_size_request(-1, 32)
        scrolledWindow.set_policy(gtk.PolicyType.AUTOMATIC if pygobject
                                  else gtk.POLICY_AUTOMATIC,
                                  gtk.PolicyType.AUTOMATIC if pygobject
                                  else gtk.POLICY_AUTOMATIC)
        self._metar = gtk.TextView()
        self._metar.set_editable(False)
        self._metar.set_accepts_tab(False)
        self._metar.set_wrap_mode(gtk.WrapMode.WORD if pygobject else gtk.WRAP_WORD)
        scrolledWindow.add(self._metar)
        alignment = gtk.Alignment(xalign = 0.0, yalign = 0.0,
                                  xscale = 1.0, yscale = 1.0)
        alignment.set_padding(padding_top = 4, padding_bottom = 0,
                              padding_left = 0, padding_right = 0)
        alignment.add(scrolledWindow)
        self._metarFrame.add(alignment)
        mainBox.pack_start(self._metarFrame, True, True, 4)

        self._button = self.addButton(gtk.STOCK_GO_FORWARD, default = True)
        self._button.set_use_stock(True)
        self._button.connect("clicked", self._forwardClicked)

    def activate(self):
        """Activate the page."""
        if self._activated:
            if not self._departure:
                self._button.set_label(gtk.STOCK_GO_FORWARD)
                self._button.set_use_stock(True)
        else:
            if not self._departure:
                self._button.set_label("I have read the briefing and am ready to fly!")
                self._button.set_use_stock(False)

            bookedFlight = self._wizard._bookedFlight

            icao = bookedFlight.departureICAO if self._departure \
                   else bookedFlight.arrivalICAO
            notams = self._wizard._departureNOTAMs if self._departure \
                     else self._wizard._arrivalNOTAMs
            metar = self._wizard._departureMETAR if self._departure \
                     else self._wizard._arrivalMETAR

            self._notamsFrame.set_label(icao + " NOTAMs")
            buffer = self._notams.get_buffer()
            if notams is None:
                buffer.set_text("Could not download NOTAMs")
            else:
                s = ""
                for notam in notams:
                    s += str(notam.begin)
                    if notam.end is not None:
                        s += " - " + str(notam.end)
                    elif notam.permanent:
                        s += " - PERMANENT"
                    s += "\n"
                    if notam.repeatCycle:
                        s += "Repeat cycle: " + notam.repeatCycle + "\n"
                    s += notam.notice + "\n"
                    s += "-------------------- * --------------------\n"
                buffer.set_text(s)

            self._metarFrame.set_label(icao + " METAR")
            buffer = self._metar.get_buffer()
            if metar is None:
                buffer.set_text("Could not download METAR")
            else:
                buffer.set_text(metar)

            self._activated = True

    def reset(self):
        """Reset the page if the wizard is reset."""
        super(BriefingPage, self).reset()
        self._activated = False

    def _forwardClicked(self, button):
        """Called when the forward button is clicked."""
        self._wizard.nextPage()

#-----------------------------------------------------------------------------

class Wizard(gtk.VBox):
    """The flight wizard."""
    def __init__(self, gui):
        """Construct the wizard."""
        super(Wizard, self).__init__()

        self.gui = gui

        self._pages = []
        self._currentPage = None
        
        self._pages.append(LoginPage(self))
        self._pages.append(FlightSelectionPage(self))
        self._pages.append(GateSelectionPage(self))
        self._pages.append(ConnectPage(self))
        self._pages.append(PayloadPage(self))
        self._pages.append(TimePage(self))
        self._pages.append(RoutePage(self))
        self._pages.append(BriefingPage(self, True))
        self._pages.append(BriefingPage(self, False))
        
        maxWidth = 0
        maxHeight = 0
        for page in self._pages:
            page.show_all()
            pageSizeRequest = page.size_request()
            width = pageSizeRequest.width if pygobject else pageSizeRequest[0]
            height = pageSizeRequest.height if pygobject else pageSizeRequest[1]
            maxWidth = max(maxWidth, width)
            maxHeight = max(maxHeight, height)
        maxWidth += 16
        maxHeight += 32
        self.set_size_request(maxWidth, maxHeight)

        self._initialize()
        
    @property
    def loginResult(self):
        """Get the login result."""
        return self._loginResult

    def setCurrentPage(self, index):
        """Set the current page to the one with the given index."""
        assert index < len(self._pages)
        
        if self._currentPage is not None:
            self.remove(self._pages[self._currentPage])

        self._currentPage = index
        self.add(self._pages[index])
        self._pages[index].activate()
        self.show_all()

    def nextPage(self):
        """Go to the next page."""
        self.jumpPage(1)

    def jumpPage(self, count):
        """Go to the page which is 'count' pages after the current one."""
        self.setCurrentPage(self._currentPage + count)
        self.grabDefault()

    def grabDefault(self):
        """Make the default button of the current page the default."""
        self._pages[self._currentPage].grabDefault()

    def connected(self, fsType, descriptor):
        """Called when the connection could be made to the simulator."""
        self.nextPage()

    def connectionFailed(self):
        """Called when the connection could not be made to the simulator."""
        self._initialize()

    def disconnected(self):
        """Called when we have disconnected from the simulator."""
        self._initialize()

    def _initialize(self):
        """Initialize the wizard."""
        self._fleet = None
        self._fleetCallback = None
        self._updatePlaneCallback = None
        
        self._loginResult = None
        self._bookedFlight = None
        self._departureGate = "-"
        self._zfw = None
        self._cruiseAltitude = None
        self._route = None
        self._departureNOTAMs = None
        self._departureMETAR = None
        self._arrivalNOTAMs = None
        self._arrivalMETAR = None

        for page in self._pages:
            page.reset()
        
        self.setCurrentPage(0)
        
    def _getFleet(self, callback, force = False):
        """Get the fleet, if needed.

        callback is function that will be called, when the feet is retrieved,
        or the retrieval fails. It should have a single argument that will
        receive the fleet object on success, None otherwise.
        """
        if self._fleet is not None and not force:
            callback(self._fleet)

        self.gui.beginBusy("Retrieving fleet...")
        self._fleetCallback = callback
        self.gui.webHandler.getFleet(self._fleetResultCallback)

    def _fleetResultCallback(self, returned, result):
        """Called when the fleet has been queried."""
        gobject.idle_add(self._handleFleetResult, returned, result)

    def _handleFleetResult(self, returned, result):
        """Handle the fleet result."""
        self.gui.endBusy()
        if returned:
            self._fleet = result.fleet
        else:
            self._fleet = None

            dialog = gtk.MessageDialog(type = MESSAGETYPE_ERROR,
                                       buttons = BUTTONSTYPE_OK,
                                       message_format =
                                       "Failed to retrieve the information on "
                                       "the fleet.")
            dialog.run()
            dialog.hide()

        self._fleetCallback(self._fleet)

    def _updatePlane(self, callback, tailNumber, status, gateNumber = None):
        """Update the given plane's gate information."""
        self.gui.beginBusy("Updating plane status...")
        self._updatePlaneCallback = callback
        self.gui.webHandler.updatePlane(self._updatePlaneResultCallback,
                                        tailNumber, status, gateNumber)

    def _updatePlaneResultCallback(self, returned, result):
        """Callback for the plane updating operation."""
        gobject.idle_add(self._handleUpdatePlaneResult, returned, result)

    def _handleUpdatePlaneResult(self, returned, result):
        """Handle the result of a plane update operation."""
        self.gui.endBusy()
        if returned:
            success = result.success
        else:
            success = None

            dialog = gtk.MessageDialog(type = MESSAGETYPE_ERROR,
                                       buttons = BUTTONSTYPE_OK,
                                       message_format =
                                       "Failed to update the statuis of "
                                       "the airplane.")
            dialog.run()
            dialog.hide()

        self._updatePlaneCallback(success)

    def _connectSimulator(self):
        """Connect to the simulator."""
        self.gui.connectSimulator(self._bookedFlight.aircraftType)
    
#-----------------------------------------------------------------------------

