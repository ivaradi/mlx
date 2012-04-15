# The flight handling "wizard"

from mlx.gui.common import *

import mlx.const as const
import mlx.fs as fs
from mlx.checks import PayloadChecker

import datetime
import time

#------------------------------------------------------------------------------

acftTypeNames = { const.AIRCRAFT_B736: "Boeing 737-600",
                  const.AIRCRAFT_B737: "Boeing 737-700",
                  const.AIRCRAFT_B738: "Boeing 737-800",
                  const.AIRCRAFT_DH8D: "Bombardier Dash 8-Q400",
                  const.AIRCRAFT_B733: "Boeing 737-300",
                  const.AIRCRAFT_B734: "Boeing 737-400",
                  const.AIRCRAFT_B735: "Boeing 737-500",
                  const.AIRCRAFT_B762: "Boeing 767-200",
                  const.AIRCRAFT_B763: "Boeing 767-300",
                  const.AIRCRAFT_CRJ2: "Bombardier CRJ200",
                  const.AIRCRAFT_F70:  "Fokker 70",
                  const.AIRCRAFT_DC3:  "Lisunov Li-2",
                  const.AIRCRAFT_T134: "Tupolev Tu-134",
                  const.AIRCRAFT_T154: "Tupolev Tu-154",
                  const.AIRCRAFT_YK40: "Yakovlev Yak-40" }

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

        mainBox = gtk.VBox()        

        alignment = gtk.Alignment(xalign = 0.0, yalign = 0.0,
                                  xscale = 1.0, yscale = 1.0)        
        alignment.set_padding(padding_top = 16, padding_bottom = 16,
                              padding_left = 16, padding_right = 16)
        alignment.add(mainBox)
        self._vbox.pack_start(alignment, True, True, 0)
        
        alignment = gtk.Alignment(xalign = 0.5, yalign = 0.0,
                                  xscale = 0, yscale = 0.0)
        alignment.set_padding(padding_top = 0, padding_bottom = 16,
                              padding_left = 0, padding_right = 0)

        label = gtk.Label(help)
        label.set_justify(gtk.Justification.CENTER if pygobject
                          else gtk.JUSTIFY_CENTER)
        label.set_use_markup(True)
        alignment.add(label)
        mainBox.pack_start(alignment, False, False, 0)

        self._mainAlignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                            xscale = 1.0, yscale = 1.0)
        mainBox.pack_start(self._mainAlignment, True, True, 0)
                                            
        buttonAlignment =  gtk.Alignment(xalign = 1.0, xscale=0.0, yscale = 0.0)
        buttonAlignment.set_padding(padding_top = 4, padding_bottom = 10,
                                    padding_left = 16, padding_right = 16)

        self._buttonBox = gtk.HBox()
        self._buttonBox.set_homogeneous(False)
        self._defaultButton = None
        buttonAlignment.add(self._buttonBox)

        self._vbox.pack_start(buttonAlignment, False, False, 0)

        self._wizard = wizard

        self._finalized = False
        self._fromPage = None

    def setMainWidget(self, widget):
        """Set the given widget as the main one."""
        self._mainAlignment.add(widget)

    def addButton(self, label, default = False):
        """Add a button with the given label.

        Return the button object created."""
        button = gtk.Button(label)
        self._buttonBox.pack_start(button, False, False, 4)
        button.set_use_underline(True)
        if default:
            button.set_can_default(True)
            self._defaultButton = button
        return button

    def activate(self):
        """Called when this page becomes active.

        This default implementation does nothing."""
        pass

    def finalize(self):
        """Called when the page is finalized."""
        pass

    def grabDefault(self):
        """If the page has a default button, make it the default one."""
        if self._defaultButton is not None:
            self._defaultButton.grab_default()

    def reset(self):
        """Reset the page if the wizard is reset."""
        self._finalized = False
        self._fromPage = None

    def goBack(self):
        """Go to the page we were invoked from."""
        assert self._fromPage is not None
        
        self._wizard.setCurrentPage(self._fromPage, finalize = False)
    
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
        self._loginButton.set_sensitive(False)
        gui = self._wizard.gui
        gui.beginBusy("Logging in...")
        gui.webHandler.login(self._loginResultCallback,
                            self._pilotID.get_text(),
                            self._password.get_text())

    def _loginResultCallback(self, returned, result):
        """The login result callback, called in the web handler's thread."""
        gobject.idle_add(self._handleLoginResult, returned, result)

    def _handleLoginResult(self, returned, result):
        """Handle the login result."""
        self._wizard.gui.endBusy()
        self._loginButton.set_sensitive(True)
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

    def activate(self):
        """Fill the flight list."""
        self._flightList.set_sensitive(True)
        self._listStore.clear()
        for flight in self._wizard.loginResult.flights:
            self._listStore.append([str(flight.departureTime),
                                    flight.callsign,
                                    flight.departureICAO,
                                    flight.arrivalICAO])

    def finalize(self):
        """Finalize the page."""
        self._flightList.set_sensitive(False)

    def _selectionChanged(self, selection):
        """Called when the selection is changed."""
        self._button.set_sensitive(selection.count_selected_rows()==1)

    def _forwardClicked(self, button):
        """Called when the forward button was clicked."""
        if self._finalized:
            self._wizard.jumpPage(self._nextDistance, finalize = False)
        else:
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
            self._nextDistance = 2
            self._wizard.jumpPage(2)

    def _fleetRetrieved(self, fleet):
        """Called when the fleet has been retrieved."""
        if fleet is None:
            self._nextDistance = 2
            self._wizard.jumpPage(2)
        else:
            plane = fleet[self._wizard._bookedFlight.tailNumber]
            if plane is None:
                self._nextDistance = 2
                self._wizard.jumpPage(2)
            elif plane.gateNumber is not None and \
                 not fleet.isGateConflicting(plane):
                self._wizard._departureGate = plane.gateNumber
                self._nextDistance = 2
                self._wizard.jumpPage(2)
            else:
                self._nextDistance = 1
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

        button = self.addButton(gtk.STOCK_GO_BACK)
        button.set_use_stock(True)
        button.connect("clicked", self._backClicked)
        
        self._button = self.addButton(gtk.STOCK_GO_FORWARD, default = True)
        self._button.set_use_stock(True)
        self._button.set_sensitive(False)
        self._button.connect("clicked", self._forwardClicked)

    def activate(self):
        """Fill the gate list."""
        self._listStore.clear()
        self._gateList.set_sensitive(True)
        occupiedGateNumbers = self._wizard._fleet.getOccupiedGateNumbers()
        for gateNumber in const.lhbpGateNumbers:
            if gateNumber not in occupiedGateNumbers:
                self._listStore.append([gateNumber])

    def finalize(self):
        """Finalize the page."""
        self._gateList.set_sensitive(False)

    def _selectionChanged(self, selection):
        """Called when the selection is changed."""
        self._button.set_sensitive(selection.count_selected_rows()==1)

    def _backClicked(self, button):
        """Called when the Back button is pressed."""
        self.goBack()

    def _forwardClicked(self, button):
        """Called when the forward button is clicked."""
        if not self._finalized:
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
        help = "Load the aircraft below into the simulator and park it\n" \
               "at the given airport, at the gate below, if present.\n\n" \
               "Then press the Connect button to connect to the simulator."
        super(ConnectPage, self).__init__(wizard,
                                          "Connect to the simulator",
                                          help)
        
        alignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)

        table = gtk.Table(5, 2)
        table.set_row_spacings(4)
        table.set_col_spacings(16)
        table.set_homogeneous(True)
        alignment.add(table)
        self.setMainWidget(alignment)

        labelAlignment = gtk.Alignment(xalign=1.0, xscale=0.0)
        label = gtk.Label("Flight number:")
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, 0, 1)

        labelAlignment = gtk.Alignment(xalign=0.0, xscale=0.0)
        self._flightNumber = gtk.Label()
        self._flightNumber.set_width_chars(7)
        self._flightNumber.set_alignment(0.0, 0.5)
        labelAlignment.add(self._flightNumber)
        table.attach(labelAlignment, 1, 2, 0, 1)

        labelAlignment = gtk.Alignment(xalign=1.0, xscale=0.0)
        label = gtk.Label("Aircraft:")
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, 1, 2)

        labelAlignment = gtk.Alignment(xalign=0.0, xscale=0.0)
        self._aircraft = gtk.Label()
        self._aircraft.set_width_chars(25)
        self._aircraft.set_alignment(0.0, 0.5)
        labelAlignment.add(self._aircraft)
        table.attach(labelAlignment, 1, 2, 1, 2)

        labelAlignment = gtk.Alignment(xalign=1.0, xscale=0.0)
        label = gtk.Label("Tail number:")
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, 2, 3)

        labelAlignment = gtk.Alignment(xalign=0.0, xscale=0.0)
        self._tailNumber = gtk.Label()
        self._tailNumber.set_width_chars(10)
        self._tailNumber.set_alignment(0.0, 0.5)
        labelAlignment.add(self._tailNumber)
        table.attach(labelAlignment, 1, 2, 2, 3)

        labelAlignment = gtk.Alignment(xalign=1.0, xscale=0.0)
        label = gtk.Label("Airport:")
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, 3, 4)

        labelAlignment = gtk.Alignment(xalign=0.0, xscale=0.0)
        self._departureICAO = gtk.Label()
        self._departureICAO.set_width_chars(6)
        self._departureICAO.set_alignment(0.0, 0.5)
        labelAlignment.add(self._departureICAO)
        table.attach(labelAlignment, 1, 2, 3, 4)

        labelAlignment = gtk.Alignment(xalign=1.0, xscale=0.0)
        label = gtk.Label("Gate:")
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, 4, 5)

        labelAlignment = gtk.Alignment(xalign=0.0, xscale=0.0)
        self._departureGate = gtk.Label()
        self._departureGate.set_width_chars(5)
        self._departureGate.set_alignment(0.0, 0.5)
        labelAlignment.add(self._departureGate)
        table.attach(labelAlignment, 1, 2, 4, 5)

        button = self.addButton(gtk.STOCK_GO_BACK)
        button.set_use_stock(True)
        button.connect("clicked", self._backClicked)

        self._button = self.addButton("_Connect", default = True)
        self._button.set_use_underline(True)
        self._clickedID = self._button.connect("clicked", self._connectClicked)

    def activate(self):
        """Setup the departure information."""
        self._button.set_label("_Connect")
        self._button.set_use_underline(True)
        self._button.disconnect(self._clickedID)
        self._clickedID = self._button.connect("clicked", self._connectClicked)

        bookedFlight = self._wizard._bookedFlight

        self._flightNumber.set_markup("<b>" + bookedFlight.callsign + "</b>")

        aircraftType = acftTypeNames[bookedFlight.aircraftType]
        self._aircraft.set_markup("<b>" + aircraftType + "</b>")
        
        self._tailNumber.set_markup("<b>" + bookedFlight.tailNumber + "</b>")

        icao = bookedFlight.departureICAO
        self._departureICAO.set_markup("<b>" + icao + "</b>")
        gate = self._wizard._departureGate
        if gate!="-":
            gate = "<b>" + gate + "</b>"
        self._departureGate.set_markup(gate)

    def finalize(self):
        """Finalize the page."""
        self._button.set_label(gtk.STOCK_GO_FORWARD)
        self._button.set_use_stock(True)
        self._button.disconnect(self._clickedID)
        self._clickedID = self._button.connect("clicked", self._forwardClicked)

    def _backClicked(self, button):
        """Called when the Back button is pressed."""
        self.goBack()

    def _connectClicked(self, button):
        """Called when the Connect button is pressed."""
        self._wizard._connectSimulator()

    def _forwardClicked(self, button):
        """Called when the Forward button is pressed."""
        self._wizard.nextPage()

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

        self._cargoWeight = IntegerEntry(defaultValue = 0)
        self._cargoWeight.set_width_chars(6)
        self._cargoWeight.connect("integer-changed", self._cargoWeightChanged)
        self._cargoWeight.set_tooltip_text("The weight of the cargo for your flight.")
        table.attach(self._cargoWeight, 1, 2, 3, 4)
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

        self._zfwButton = gtk.Button("_ZFW from FS:")
        self._zfwButton.set_use_underline(True)
        self._zfwButton.connect("clicked", self._zfwRequested)
        table.attach(self._zfwButton, 0, 1, 6, 7)

        self._simulatorZFW = gtk.Label("-")
        self._simulatorZFW.set_width_chars(6)
        self._simulatorZFW.set_alignment(1.0, 0.5)
        table.attach(self._simulatorZFW, 1, 2, 6, 7)
        self._simulatorZFWValue = None

        table.attach(gtk.Label("kg"), 2, 3, 6, 7)

        self._backButton = self.addButton(gtk.STOCK_GO_BACK)
        self._backButton.set_use_stock(True)
        self._backButton.connect("clicked", self._backClicked)

        self._button = self.addButton(gtk.STOCK_GO_FORWARD, default = True)
        self._button.set_use_stock(True)
        self._button.connect("clicked", self._forwardClicked)

    def activate(self):
        """Setup the information."""
        bookedFlight = self._wizard._bookedFlight
        self._numCrew.set_text(str(bookedFlight.numCrew))
        self._numPassengers.set_text(str(bookedFlight.numPassengers))
        self._bagWeight.set_text(str(bookedFlight.bagWeight))
        self._cargoWeight.set_int(bookedFlight.cargoWeight)
        self._cargoWeight.set_sensitive(True)
        self._mailWeight.set_text(str(bookedFlight.mailWeight))
        self._zfwButton.set_sensitive(True)
        self._updateCalculatedZFW()

    def finalize(self):
        """Finalize the payload page."""
        self._cargoWeight.set_sensitive(False)
        self._zfwButton.set_sensitive(False)

    def calculateZFW(self):
        """Calculate the ZFW value."""
        zfw = self._wizard.gui._flight.aircraft.dow
        bookedFlight = self._wizard._bookedFlight
        zfw += (bookedFlight.numCrew + bookedFlight.numPassengers) * 82
        zfw += bookedFlight.bagWeight
        zfw += self._cargoWeight.get_int()
        zfw += bookedFlight.mailWeight
        return zfw
        
    def _updateCalculatedZFW(self):
        """Update the calculated ZFW"""
        zfw = self.calculateZFW()

        markupBegin = "<b>"
        markupEnd = "</b>"
        if self._simulatorZFWValue is not None and \
           PayloadChecker.isZFWFaulty(self._simulatorZFWValue, zfw):
            markupBegin += '<span foreground="red">'
            markupEnd = "</span>" + markupEnd
        self._calculatedZFW.set_markup(markupBegin + str(zfw) + markupEnd)

    def _cargoWeightChanged(self, entry, weight):
        """Called when the cargo weight has changed."""
        self._updateCalculatedZFW()
            
    def _zfwRequested(self, button):
        """Called when the ZFW is requested from the simulator."""
        self._zfwButton.set_sensitive(False)
        self._backButton.set_sensitive(False)
        self._button.set_sensitive(False)
        gui = self._wizard.gui
        gui.beginBusy("Querying ZFW...")
        gui.simulator.requestZFW(self._handleZFW)

    def _handleZFW(self, zfw):
        """Called when the ZFW value is retrieved."""
        gobject.idle_add(self._processZFW, zfw)

    def _processZFW(self, zfw):
        """Process the given ZFW value received from the simulator."""
        self._wizard.gui.endBusy()
        self._zfwButton.set_sensitive(True)
        self._backButton.set_sensitive(True)
        self._button.set_sensitive(True)
        self._simulatorZFWValue = zfw
        self._simulatorZFW.set_text("%.0f" % (zfw,))
        self._updateCalculatedZFW()

    def _forwardClicked(self, button):
        """Called when the forward button is clicked."""
        self._wizard.nextPage()

    def _backClicked(self, button):
        """Called when the Back button is pressed."""
        self.goBack()
        
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

        self._timeButton = gtk.Button("_Time from FS:")
        self._timeButton.set_use_underline(True)
        self._timeButton.connect("clicked", self._timeRequested)
        table.attach(self._timeButton, 0, 1, 2, 3)

        self._simulatorTime = gtk.Label("-")
        self._simulatorTime.set_alignment(0.0, 0.5)
        table.attach(self._simulatorTime, 1, 2, 2, 3)

        self._backButton = self.addButton(gtk.STOCK_GO_BACK)
        self._backButton.set_use_stock(True)
        self._backButton.connect("clicked", self._backClicked)

        self._button = self.addButton(gtk.STOCK_GO_FORWARD, default = True)
        self._button.set_use_stock(True)
        self._button.connect("clicked", self._forwardClicked)

    def activate(self):
        """Activate the page."""
        self._timeButton.set_sensitive(True)
        bookedFlight = self._wizard._bookedFlight
        self._departure.set_text(str(bookedFlight.departureTime.time()))
        self._arrival.set_text(str(bookedFlight.arrivalTime.time()))

    def finalize(self):
        """Finalize the page."""
        self._timeButton.set_sensitive(False)

    def _timeRequested(self, button):
        """Request the time from the simulator."""
        self._timeButton.set_sensitive(False)
        self._backButton.set_sensitive(False)
        self._button.set_sensitive(False)
        self._wizard.gui.beginBusy("Querying time...")
        self._wizard.gui.simulator.requestTime(self._handleTime)

    def _handleTime(self, timestamp):
        """Handle the result of a time retrieval."""
        gobject.idle_add(self._processTime, timestamp)

    def _processTime(self, timestamp):
        """Process the given time."""
        self._wizard.gui.endBusy()
        self._timeButton.set_sensitive(True)
        self._backButton.set_sensitive(True)
        self._button.set_sensitive(True)
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

    def _backClicked(self, button):
        """Called when the Back button is pressed."""
        self.goBack()
        
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

        self._backButton = self.addButton(gtk.STOCK_GO_BACK)
        self._backButton.set_use_stock(True)
        self._backButton.connect("clicked", self._backClicked)

        self._button = self.addButton(gtk.STOCK_GO_FORWARD, default = True)
        self._button.set_use_stock(True)
        self._button.connect("clicked", self._forwardClicked)

    @property
    def cruiseLevel(self):
        """Get the cruise level."""
        return self._cruiseLevel.get_value_as_int()

    def activate(self):
        """Setup the route from the booked flight."""
        self._route.set_sensitive(True)
        self._cruiseLevel.set_sensitive(True)
        self._route.get_buffer().set_text(self._wizard._bookedFlight.route)
        self._updateForwardButton()

    def finalize(self):
        """Finalize the page."""
        self._route.set_sensitive(False)
        self._cruiseLevel.set_sensitive(False)

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

    def _backClicked(self, button):
        """Called when the Back button is pressed."""
        self.goBack()
        
    def _forwardClicked(self, button):
        """Called when the Forward button is clicked."""
        if self._finalized:
            self._wizard.nextPage()
        else:
            self._backButton.set_sensitive(False)
            self._button.set_sensitive(False)
            self._cruiseLevel.set_sensitive(False)
            self._route.set_sensitive(False)

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
        self._backButton.set_sensitive(True)
        self._button.set_sensitive(True)
        self._wizard.nextPage()

#-----------------------------------------------------------------------------

class BriefingPage(Page):
    """Page for the briefing."""
    def __init__(self, wizard, departure):
        """Construct the briefing page."""
        self._departure = departure
        
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

        button = self.addButton(gtk.STOCK_GO_BACK)
        button.set_use_stock(True)
        button.connect("clicked", self._backClicked)

        self._button = self.addButton(gtk.STOCK_GO_FORWARD, default = True)
        self._button.set_use_stock(True)
        self._button.connect("clicked", self._forwardClicked)

    def activate(self):
        """Activate the page."""
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

    def _backClicked(self, button):
        """Called when the Back button is pressed."""
        self.goBack()
        
    def _forwardClicked(self, button):
        """Called when the forward button is clicked."""
        if not self._departure:
            if not self._finalized:
                self._wizard.gui.startMonitoring()
                self._button.set_use_stock(True)
                self._button.set_label(gtk.STOCK_GO_FORWARD)
                self._finalized = True

        self._wizard.nextPage()

#-----------------------------------------------------------------------------

class TakeoffPage(Page):
    """Page for entering the takeoff data."""
    def __init__(self, wizard):
        """Construct the takeoff page."""
        help = "Enter the runway and SID used, as well as the speeds."

        super(TakeoffPage, self).__init__(wizard, "Takeoff", help)

        alignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)

        table = gtk.Table(5, 4)
        table.set_row_spacings(4)
        table.set_col_spacings(16)
        table.set_homogeneous(False)
        alignment.add(table)
        self.setMainWidget(alignment)

        label = gtk.Label("Run_way:")
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, 0, 1)

        self._runway = gtk.Entry()
        self._runway.set_width_chars(10)
        self._runway.set_tooltip_text("The runway the takeoff is performed from.")
        table.attach(self._runway, 1, 3, 0, 1)
        label.set_mnemonic_widget(self._runway)
        
        label = gtk.Label("_SID:")
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, 1, 2)

        self._sid = gtk.Entry()
        self._sid.set_width_chars(10)
        self._sid.set_tooltip_text("The name of the Standard Instrument Deparature procedure followed.")
        table.attach(self._sid, 1, 3, 1, 2)
        label.set_mnemonic_widget(self._sid)
        
        label = gtk.Label("V<sub>_1</sub>:")
        label.set_use_markup(True)
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, 2, 3)

        self._v1 = IntegerEntry()
        self._v1.set_width_chars(4)
        self._v1.set_tooltip_markup("The takeoff decision speed in knots.")
        table.attach(self._v1, 2, 3, 2, 3)
        label.set_mnemonic_widget(self._v1)
        
        table.attach(gtk.Label("knots"), 3, 4, 2, 3)
        
        label = gtk.Label("V<sub>_R</sub>:")
        label.set_use_markup(True)
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, 3, 4)

        self._vr = IntegerEntry()
        self._vr.set_width_chars(4)
        self._vr.set_tooltip_markup("The takeoff rotation speed in knots.")
        table.attach(self._vr, 2, 3, 3, 4)
        label.set_mnemonic_widget(self._vr)
        
        table.attach(gtk.Label("knots"), 3, 4, 3, 4)
        
        label = gtk.Label("V<sub>_2</sub>:")
        label.set_use_markup(True)
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, 4, 5)

        self._v2 = IntegerEntry()
        self._v2.set_width_chars(4)
        self._v2.set_tooltip_markup("The takeoff safety speed in knots.")
        table.attach(self._v2, 2, 3, 4, 5)
        label.set_mnemonic_widget(self._v2)
        
        table.attach(gtk.Label("knots"), 3, 4, 4, 5)
        
        button = self.addButton(gtk.STOCK_GO_BACK)
        button.set_use_stock(True)
        button.connect("clicked", self._backClicked)

        self._button = self.addButton(gtk.STOCK_GO_FORWARD, default = True)
        self._button.set_use_stock(True)
        self._button.connect("clicked", self._forwardClicked)

    @property
    def v1(self):
        """Get the v1 speed."""
        return self._v1.get_int()

    @property
    def vr(self):
        """Get the vr speed."""
        return self._vr.get_int()

    @property
    def v2(self):
        """Get the v2 speed."""
        return self._v2.get_int()

    def activate(self):
        """Activate the page."""
        self._runway.set_text("")
        self._runway.set_sensitive(True)
        self._sid.set_text("")
        self._sid.set_sensitive(True)
        self._v1.set_int(None)
        self._v1.set_sensitive(True)
        self._vr.set_int(None)
        self._vr.set_sensitive(True)
        self._v2.set_int(None)
        self._v2.set_sensitive(True)
        self._button.set_sensitive(False)
        
    def freezeValues(self):
        """Freeze the values on the page, and enable the forward button."""
        self._runway.set_sensitive(False)
        self._sid.set_sensitive(False)
        self._v1.set_sensitive(False)
        self._vr.set_sensitive(False)
        self._v2.set_sensitive(False)
        self._button.set_sensitive(True)
        
    def _backClicked(self, button):
        """Called when the Back button is pressed."""
        self.goBack()
        
    def _forwardClicked(self, button):
        """Called when the forward button is clicked."""
        self._wizard.nextPage()

#-----------------------------------------------------------------------------

class LandingPage(Page):
    """Page for entering landing data."""
    def __init__(self, wizard):
        """Construct the landing page."""
        help = "Enter the STAR and/or transition, runway,\n" \
               "approach type and V<sub>Ref</sub> used."

        super(LandingPage, self).__init__(wizard, "Landing", help)

        alignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)

        table = gtk.Table(5, 5)
        table.set_row_spacings(4)
        table.set_col_spacings(16)
        table.set_homogeneous(False)
        alignment.add(table)
        self.setMainWidget(alignment)

        self._starButton = gtk.CheckButton()
        self._starButton.connect("clicked", self._starButtonClicked)
        table.attach(self._starButton, 0, 1, 0, 1)

        label = gtk.Label("_STAR:")
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 1, 2, 0, 1)

        self._star = gtk.Entry()
        self._star.set_width_chars(10)
        self._star.set_tooltip_text("The name of Standard Terminal Arrival Route followed.")
        self._star.connect("changed", self._updateForwardButton)
        self._star.set_sensitive(False)
        table.attach(self._star, 2, 4, 0, 1)
        label.set_mnemonic_widget(self._starButton)

        self._transitionButton = gtk.CheckButton()
        self._transitionButton.connect("clicked", self._transitionButtonClicked)
        table.attach(self._transitionButton, 0, 1, 1, 2)

        label = gtk.Label("_Transition:")
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 1, 2, 1, 2)

        self._transition = gtk.Entry()
        self._transition.set_width_chars(10)
        self._transition.set_tooltip_text("The name of transition executed or VECTORS if vectored by ATC.")
        self._transition.connect("changed", self._updateForwardButton)
        self._transition.set_sensitive(False)
        table.attach(self._transition, 2, 4, 1, 2)
        label.set_mnemonic_widget(self._transitionButton)

        label = gtk.Label("Run_way:")
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 1, 2, 2, 3)

        self._runway = gtk.Entry()
        self._runway.set_width_chars(10)
        self._runway.set_tooltip_text("The runway the landing is performed on.")
        self._runway.connect("changed", self._updateForwardButton)
        table.attach(self._runway, 2, 4, 2, 3)
        label.set_mnemonic_widget(self._runway)

        label = gtk.Label("_Approach type:")
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 1, 2, 3, 4)

        self._approachType = gtk.Entry()
        self._approachType.set_width_chars(10)
        self._approachType.set_tooltip_text("The type of the approach, e.g. ILS or VISUAL.")
        self._approachType.connect("changed", self._updateForwardButton)
        table.attach(self._approachType, 2, 4, 3, 4)
        label.set_mnemonic_widget(self._approachType)

        label = gtk.Label("V<sub>_Ref</sub>:")
        label.set_use_markup(True)
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 1, 2, 5, 6)

        self._vref = IntegerEntry()
        self._vref.set_width_chars(5)
        self._vref.set_tooltip_markup("The approach reference speed in knots.")
        self._vref.connect("integer-changed", self._vrefChanged)
        table.attach(self._vref, 3, 4, 5, 6)
        label.set_mnemonic_widget(self._vref)
        
        table.attach(gtk.Label("knots"), 4, 5, 5, 6)
        
        button = self.addButton(gtk.STOCK_GO_BACK)
        button.set_use_stock(True)
        button.connect("clicked", self._backClicked)

        self._button = self.addButton(gtk.STOCK_GO_FORWARD, default = True)
        self._button.set_use_stock(True)
        self._button.connect("clicked", self._forwardClicked)

        # These are needed for correct size calculations
        self._starButton.set_active(True)
        self._transitionButton.set_active(True)

    @property
    def vref(self):
        """Return the landing reference speed."""
        return self._vref.get_int()

    def activate(self):
        """Called when the page is activated."""
        self._starButton.set_sensitive(True)
        self._starButton.set_active(False)
        self._star.set_text("")

        self._transitionButton.set_sensitive(True)
        self._transitionButton.set_active(False)
        self._transition.set_text("")

        self._runway.set_text("")
        self._runway.set_sensitive(True)

        self._approachType.set_text("")
        self._approachType.set_sensitive(True)

        self._vref.set_int(None)
        self._vref.set_sensitive(True)

        self._updateForwardButton()

    def finalize(self):
        """Finalize the page."""
        self._starButton.set_sensitive(False)
        self._star.set_sensitive(False)

        self._transitionButton.set_sensitive(False)
        self._transition.set_sensitive(False)

        self._runway.set_sensitive(False)

        self._approachType.set_sensitive(False)

        self._vref.set_sensitive(False)

    def _starButtonClicked(self, button):
        """Called when the STAR button is clicked."""
        active = button.get_active()
        self._star.set_sensitive(active)
        if active:
            self._star.grab_focus()
        self._updateForwardButton()

    def _transitionButtonClicked(self, button):
        """Called when the Transition button is clicked."""
        active = button.get_active()
        self._transition.set_sensitive(active)
        if active:
            self._transition.grab_focus()        
        self._updateForwardButton()    

    def _updateForwardButton(self, widget = None):
        """Update the sensitivity of the forward button."""
        sensitive = (self._starButton.get_active() or \
                     self._transitionButton.get_active()) and \
                    (self._star.get_text()!="" or
                     not self._starButton.get_active()) and \
                    (self._transition.get_text()!="" or
                     not self._transitionButton.get_active()) and \
                    self._runway.get_text()!="" and \
                    self._approachType.get_text()!="" and \
                    self.vref is not None
        self._button.set_sensitive(sensitive)

    def _vrefChanged(self, widget, value):
        """Called when the Vref has changed."""
        self._updateForwardButton()

    def _backClicked(self, button):
        """Called when the Back button is pressed."""
        self.goBack()
        
    def _forwardClicked(self, button):
        """Called when the forward button is clicked."""
        #self._wizard.nextPage()
        self.finalize()

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
        self._payloadPage = PayloadPage(self) 
        self._pages.append(self._payloadPage)
        self._pages.append(TimePage(self))
        self._routePage = RoutePage(self)
        self._pages.append(self._routePage)
        self._pages.append(BriefingPage(self, True))
        self._pages.append(BriefingPage(self, False))
        self._takeoffPage = TakeoffPage(self) 
        self._pages.append(self._takeoffPage)
        self._landingPage = LandingPage(self) 
        self._pages.append(self._landingPage)
        
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

    def setCurrentPage(self, index, finalize = False):
        """Set the current page to the one with the given index."""
        assert index < len(self._pages)

        fromPage = self._currentPage
        if fromPage is not None:
            page = self._pages[fromPage]
            if finalize and not page._finalized:
                page.finalize()
                page._finalized = True
            self.remove(page)

        self._currentPage = index
        page = self._pages[index]
        self.add(page)
        if page._fromPage is None:
            page._fromPage = fromPage
            page.activate()
        self.show_all()
        if fromPage is not None:
            self.grabDefault()

    @property
    def zfw(self):
        """Get the calculated ZFW value."""
        return 0 if self._bookedFlight is None \
               else self._payloadPage.calculateZFW()

    @property
    def cruiseAltitude(self):
        """Get the cruise altitude."""
        return self._routePage.cruiseLevel * 100

    @property
    def v1(self):
        """Get the V1 speed."""
        return self._takeoffPage.v1

    @property
    def vr(self):
        """Get the Vr speed."""
        return self._takeoffPage.vr

    @property
    def v2(self):
        """Get the V2 speed."""
        return self._takeoffPage.v2

    @property
    def vref(self):
        """Get the Vref speed."""
        return self._landingPage.vref

    def nextPage(self, finalize = True):
        """Go to the next page."""
        self.jumpPage(1, finalize)

    def jumpPage(self, count, finalize = True):
        """Go to the page which is 'count' pages after the current one."""
        self.setCurrentPage(self._currentPage + count, finalize = finalize)

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

    def setStage(self, stage):
        """Set the flight stage to the given one."""
        if stage==const.STAGE_TAKEOFF:
            self._takeoffPage.freezeValues()

    def _initialize(self):
        """Initialize the wizard."""
        self._fleet = None
        self._fleetCallback = None
        self._updatePlaneCallback = None
        
        self._loginResult = None
        self._bookedFlight = None
        self._departureGate = "-"
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

