# The flight handling "wizard"

from mlx.gui.common import *

import mlx.const as const
import mlx.fs as fs
import mlx.acft as acft
from mlx.checks import PayloadChecker
import mlx.util as util
from mlx.pirep import PIREP
from mlx.i18n import xstr
from mlx.sound import startSound

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
    def __init__(self, wizard, title, help, completedHelp = None):
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
                                  xscale = 0.0, yscale = 0.0)
        alignment.set_padding(padding_top = 0, padding_bottom = 16,
                              padding_left = 0, padding_right = 0)

        self._help = help
        self._completedHelp = completedHelp

        if self._completedHelp is None or \
           len(help.splitlines())>=len(completedHelp.splitlines()):
            longerHelp = help
        else:
            longerHelp = completedHelp
        
        self._helpLabel = gtk.Label(completedHelp)
        # FIXME: should be a constant in common
        self._helpLabel.set_justify(gtk.Justification.CENTER if pygobject
                                    else gtk.JUSTIFY_CENTER)
        self._helpLabel.set_use_markup(True)
        alignment.add(self._helpLabel)
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

        self._completed = False
        self._fromPage = None

    def setMainWidget(self, widget):
        """Set the given widget as the main one."""
        self._mainAlignment.add(widget)

    def addButton(self, label, default = False, sensitive = True,
                  tooltip = None, clicked = None):
        """Add a button with the given label.

        Return the button object created."""
        button = gtk.Button(label)
        self._buttonBox.pack_start(button, False, False, 4)
        button.set_use_underline(True)
        if default:
            button.set_can_default(True)
            self._defaultButton = button
        button.set_sensitive(sensitive)
        if tooltip is not None:
            button.set_tooltip_text(tooltip)
        if clicked is not None:
            button.connect("clicked", clicked)
        return button

    def addPreviousButton(self, sensitive = True, clicked = None):
        """Add the 'Next' button to the page."""
        return self.addButton(xstr("button_previous"),
                              sensitive = sensitive,
                              tooltip = xstr("button_previous_tooltip"),
                              clicked = clicked)

    def addNextButton(self, default = True, sensitive = True,
                      clicked = None):
        """Add the 'Next' button to the page."""
        return self.addButton(xstr("button_next"),
                              default = default,
                              sensitive = sensitive,
                              tooltip = xstr("button_next_tooltip"),
                              clicked = clicked)

    def initialize(self):
        """Initialize the page.

        It sets up the primary help, and calls the activate() function."""
        self._helpLabel.set_markup(self._help)
        self._helpLabel.set_sensitive(True)
        self.activate()

    def activate(self):
        """Called when this page becomes active.

        This default implementation does nothing."""
        pass

    def complete(self):
        """Called when the page is completed.

        It greys out/changes the help text and then calls finalize()."""
        self.finalize()
        if self._completedHelp is None:
            self._helpLabel.set_sensitive(False)
        else:
            self._helpLabel.set_markup(self._completedHelp)
        self._completed = True

    def finalize(self):
        """Called when the page is finalized."""
        pass

    def grabDefault(self):
        """If the page has a default button, make it the default one."""
        if self._defaultButton is not None:
            self._defaultButton.grab_default()

    def reset(self):
        """Reset the page if the wizard is reset."""
        self._completed = False
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
        super(LoginPage, self).__init__(wizard, xstr("login"),
                                        xstr("loginHelp"))

        alignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)

        table = gtk.Table(2, 3)
        table.set_row_spacings(4)
        table.set_col_spacings(32)
        alignment.add(table)
        self.setMainWidget(alignment)

        labelAlignment = gtk.Alignment(xalign = 1.0, yalign = 0.5,
                                       xscale = 0.0, yscale = 0.0)
        label = gtk.Label(xstr("label_pilotID"))
        label.set_use_underline(True)
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, 0, 1)

        self._pilotID = gtk.Entry()
        self._pilotID.connect("changed", self._setLoginButton)
        self._pilotID.set_tooltip_text(xstr("login_pilotID_tooltip"))
        table.attach(self._pilotID, 1, 2, 0, 1)
        label.set_mnemonic_widget(self._pilotID)

        labelAlignment = gtk.Alignment(xalign = 1.0, yalign = 0.5,
                                       xscale = 0.0, yscale = 0.0)
        label = gtk.Label(xstr("label_password"))
        label.set_use_underline(True)
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, 1, 2)

        self._password = gtk.Entry()
        self._password.set_visibility(False)
        self._password.connect("changed", self._setLoginButton)
        self._password.set_tooltip_text(xstr("login_password_tooltip"))
        table.attach(self._password, 1, 2, 1, 2)
        label.set_mnemonic_widget(self._password)

        self._rememberButton = gtk.CheckButton(xstr("remember_password"))
        self._rememberButton.set_use_underline(True)
        self._rememberButton.set_tooltip_text(xstr("login_remember_tooltip"))
        table.attach(self._rememberButton, 1, 2, 2, 3, ypadding = 8)

        self._loginButton = self.addButton(xstr("button_login"), default = True)
        self._loginButton.set_sensitive(False)
        self._loginButton.connect("clicked", self._loginClicked)
        self._loginButton.set_tooltip_text(xstr("login_button_tooltip"))        

    def activate(self):
        """Activate the page."""
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
        gui.beginBusy(xstr("login_busy"))
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
                dialog = gtk.MessageDialog(parent = self._wizard.gui.mainWindow,
                                           type = MESSAGETYPE_ERROR,
                                           message_format = xstr("login_invalid"))
                dialog.add_button(xstr("button_ok"), RESPONSETYPE_OK)
                dialog.set_title(WINDOW_TITLE_BASE)
                dialog.format_secondary_markup(xstr("login_invalid_sec"))
                dialog.run()
                dialog.hide()
        else:
            dialog = gtk.MessageDialog(parent = self._wizard.gui.mainWindow,
                                       type = MESSAGETYPE_ERROR,
                                       message_format = xstr("login_failconn"))
            dialog.add_button(xstr("button_ok"), RESPONSETYPE_OK)
            dialog.set_title(WINDOW_TITLE_BASE)
            dialog.format_secondary_markup(xstr("login_failconn_sec"))
            
            dialog.run()
            dialog.hide()

#-----------------------------------------------------------------------------

class FlightSelectionPage(Page):
    """The page to select the flight."""
    def __init__(self, wizard):
        """Construct the flight selection page."""
        help = xstr("flightsel_help") 
        completedHelp = xstr("flightsel_chelp")
        super(FlightSelectionPage, self).__init__(wizard, xstr("flightsel_title"),
                                                  help, completedHelp = completedHelp)


        self._listStore = gtk.ListStore(str, str, str, str)
        self._flightList = gtk.TreeView(self._listStore)
        column = gtk.TreeViewColumn(xstr("flightsel_no"), gtk.CellRendererText(),
                                    text = 1)
        column.set_expand(True)
        self._flightList.append_column(column)
        column = gtk.TreeViewColumn(xstr("flightsel_deptime"), gtk.CellRendererText(),
                                    text = 0)
        column.set_expand(True)
        self._flightList.append_column(column)
        column = gtk.TreeViewColumn(xstr("flightsel_from"), gtk.CellRendererText(),
                                    text = 2)
        column.set_expand(True)
        self._flightList.append_column(column)
        column = gtk.TreeViewColumn(xstr("flightsel_to"), gtk.CellRendererText(),
                                    text = 3)
        column.set_expand(True)
        self._flightList.append_column(column)

        flightSelection = self._flightList.get_selection()
        flightSelection.connect("changed", self._selectionChanged)

        scrolledWindow = gtk.ScrolledWindow()
        scrolledWindow.add(self._flightList)
        scrolledWindow.set_size_request(400, -1)
        # FIXME: these should be constants in common.py
        scrolledWindow.set_policy(gtk.PolicyType.AUTOMATIC if pygobject
                                  else gtk.POLICY_AUTOMATIC,
                                  gtk.PolicyType.AUTOMATIC if pygobject
                                  else gtk.POLICY_AUTOMATIC)
        scrolledWindow.set_shadow_type(gtk.ShadowType.IN if pygobject
                                       else gtk.SHADOW_IN)

        alignment = gtk.Alignment(xalign = 0.5, yalign = 0.0, xscale = 0.0, yscale = 1.0)
        alignment.add(scrolledWindow)

        self.setMainWidget(alignment)

        self._button = self.addNextButton(sensitive = False,
                                          clicked =  self._forwardClicked)

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
        if self._completed:
            self._wizard.jumpPage(self._nextDistance, finalize = False)
        else:
            selection = self._flightList.get_selection()
            (listStore, iter) = selection.get_selected()
            path = listStore.get_path(iter)
            [index] = path.get_indices() if pygobject else path

            flight = self._wizard.loginResult.flights[index]
            self._wizard._bookedFlight = flight
            self._wizard.gui.enableFlightInfo()

            self._updateDepartureGate()
        
    def _updateDepartureGate(self):
        """Update the departure gate for the booked flight."""
        flight = self._wizard._bookedFlight
        if self._wizard.gui.config.onlineGateSystem:
            if flight.departureICAO=="LHBP":
                self._wizard.getFleet(self._fleetRetrieved)
            else:
                self._wizard.updatePlane(self._planeUpdated,
                                         flight.tailNumber,
                                         const.PLANE_AWAY)
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

    def _planeUpdated(self, success):
        """Callback for the plane updating."""
        self._nextDistance = 2
        self._wizard.jumpPage(2)
        
#-----------------------------------------------------------------------------

class GateSelectionPage(Page):
    """Page to select a free gate at LHBP.
    This page should be displayed only if we have fleet information!."""
    def __init__(self, wizard):
        """Construct the gate selection page."""
        super(GateSelectionPage, self).__init__(wizard, xstr("gatesel_title"),
                                                xstr("gatesel_help"))
        
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

        self.addPreviousButton(clicked = self._backClicked)
        
        self._button = self.addNextButton(sensitive = False,
                                          clicked = self._forwardClicked)

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
        if not self._completed:
            selection = self._gateList.get_selection()
            (listStore, iter) = selection.get_selected()
            (gateNumber,) = listStore.get(iter, 0)

            self._wizard._departureGate = gateNumber

            self._wizard.updatePlane(self._planeUpdated,
                                     self._wizard._bookedFlight.tailNumber,
                                     const.PLANE_HOME, gateNumber)
        else:
            self._wizard.nextPage()

    def _planeUpdated(self, success):
        """Callback for the plane updating call."""
        if success is None or success:
            self._wizard.nextPage()
        else:
            dialog = gtk.MessageDialog(parent = self._wizard.gui.mainWindow,
                                       type = MESSAGETYPE_ERROR,
                                       message_format = xstr("gatesel_conflict"))
            dialog.add_button(xstr("button_ok"), RESPONSETYPE_OK)
            dialog.set_title(WINDOW_TITLE_BASE)
            dialog.format_secondary_markup(xstr("gatesel_conflict_sec"))
            dialog.run()
            dialog.hide()

            self._wizard.getFleet(self._fleetRetrieved)

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
        completedHelp = "The basic data of your flight can be read below."
        super(ConnectPage, self).__init__(wizard, xstr("connect_title"),
                                          xstr("connect_help"),
                                          completedHelp = xstr("connect_chelp"))
        
        alignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)

        table = gtk.Table(5, 2)
        table.set_row_spacings(4)
        table.set_col_spacings(16)
        table.set_homogeneous(True)
        alignment.add(table)
        self.setMainWidget(alignment)

        labelAlignment = gtk.Alignment(xalign=1.0, xscale=0.0)
        label = gtk.Label(xstr("connect_flightno"))
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, 0, 1)

        labelAlignment = gtk.Alignment(xalign=0.0, xscale=0.0)
        self._flightNumber = gtk.Label()
        self._flightNumber.set_width_chars(7)
        self._flightNumber.set_alignment(0.0, 0.5)
        labelAlignment.add(self._flightNumber)
        table.attach(labelAlignment, 1, 2, 0, 1)

        labelAlignment = gtk.Alignment(xalign=1.0, xscale=0.0)
        label = gtk.Label(xstr("connect_acft"))
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, 1, 2)

        labelAlignment = gtk.Alignment(xalign=0.0, xscale=0.0)
        self._aircraft = gtk.Label()
        self._aircraft.set_width_chars(25)
        self._aircraft.set_alignment(0.0, 0.5)
        labelAlignment.add(self._aircraft)
        table.attach(labelAlignment, 1, 2, 1, 2)

        labelAlignment = gtk.Alignment(xalign=1.0, xscale=0.0)
        label = gtk.Label(xstr("connect_tailno"))
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, 2, 3)

        labelAlignment = gtk.Alignment(xalign=0.0, xscale=0.0)
        self._tailNumber = gtk.Label()
        self._tailNumber.set_width_chars(10)
        self._tailNumber.set_alignment(0.0, 0.5)
        labelAlignment.add(self._tailNumber)
        table.attach(labelAlignment, 1, 2, 2, 3)

        labelAlignment = gtk.Alignment(xalign=1.0, xscale=0.0)
        label = gtk.Label(xstr("connect_airport"))
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, 3, 4)

        labelAlignment = gtk.Alignment(xalign=0.0, xscale=0.0)
        self._departureICAO = gtk.Label()
        self._departureICAO.set_width_chars(6)
        self._departureICAO.set_alignment(0.0, 0.5)
        labelAlignment.add(self._departureICAO)
        table.attach(labelAlignment, 1, 2, 3, 4)

        labelAlignment = gtk.Alignment(xalign=1.0, xscale=0.0)
        label = gtk.Label(xstr("connect_gate"))
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, 4, 5)

        labelAlignment = gtk.Alignment(xalign=0.0, xscale=0.0)
        self._departureGate = gtk.Label()
        self._departureGate.set_width_chars(5)
        self._departureGate.set_alignment(0.0, 0.5)
        labelAlignment.add(self._departureGate)
        table.attach(labelAlignment, 1, 2, 4, 5)

        self.addPreviousButton(clicked = self._backClicked)

        self._button = self.addButton(xstr("button_connect"), default = True,
                                      tooltip = xstr("button_connect_tooltip"))
        self._clickedID = self._button.connect("clicked", self._connectClicked)

    def activate(self):
        """Setup the departure information."""
        self._button.set_label(xstr("button_connect"))
        self._button.set_use_underline(True)
        self._button.set_tooltip_text(xstr("button_connect_tooltip"))
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
        self._button.set_label(xstr("button_next"))
        self._button.set_use_underline(True)
        self._button.set_tooltip_text(xstr("button_next_tooltip"))
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
        super(PayloadPage, self).__init__(wizard, xstr("payload_title"),
                                          xstr("payload_help"),
                                          completedHelp = xstr("payload_chelp"))

        alignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)

        table = gtk.Table(7, 3)
        table.set_row_spacings(4)
        table.set_col_spacings(16)
        table.set_homogeneous(False)
        alignment.add(table)
        self.setMainWidget(alignment)

        label = gtk.Label(xstr("payload_crew"))
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, 0, 1)

        self._numCrew = gtk.Label()
        self._numCrew.set_width_chars(6)
        self._numCrew.set_alignment(1.0, 0.5)
        table.attach(self._numCrew, 1, 2, 0, 1)
        
        label = gtk.Label(xstr("payload_pax"))
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, 1, 2)

        self._numPassengers = gtk.Label()
        self._numPassengers.set_width_chars(6)
        self._numPassengers.set_alignment(1.0, 0.5)
        table.attach(self._numPassengers, 1, 2, 1, 2)
        
        label = gtk.Label(xstr("payload_bag"))
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, 2, 3)

        self._bagWeight = gtk.Label()
        self._bagWeight.set_width_chars(6)
        self._bagWeight.set_alignment(1.0, 0.5)
        table.attach(self._bagWeight, 1, 2, 2, 3)

        table.attach(gtk.Label("kg"), 2, 3, 2, 3)
        
        label = gtk.Label(xstr("payload_cargo"))
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, 3, 4)

        self._cargoWeight = IntegerEntry(defaultValue = 0)
        self._cargoWeight.set_width_chars(6)
        self._cargoWeight.connect("integer-changed", self._cargoWeightChanged)
        self._cargoWeight.set_tooltip_text(xstr("payload_cargo_tooltip"))
        table.attach(self._cargoWeight, 1, 2, 3, 4)
        label.set_mnemonic_widget(self._cargoWeight)

        table.attach(gtk.Label("kg"), 2, 3, 3, 4)
        
        label = gtk.Label(xstr("payload_mail"))
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, 4, 5)

        self._mailWeight = gtk.Label()
        self._mailWeight.set_width_chars(6)
        self._mailWeight.set_alignment(1.0, 0.5)
        table.attach(self._mailWeight, 1, 2, 4, 5)

        table.attach(gtk.Label("kg"), 2, 3, 4, 5)
        
        label = gtk.Label("<b>" + xstr("payload_zfw") + "</b>")
        label.set_alignment(0.0, 0.5)
        label.set_use_markup(True)
        table.attach(label, 0, 1, 5, 6)

        self._calculatedZFW = gtk.Label()
        self._calculatedZFW.set_width_chars(6)
        self._calculatedZFW.set_alignment(1.0, 0.5)
        table.attach(self._calculatedZFW, 1, 2, 5, 6)

        table.attach(gtk.Label("kg"), 2, 3, 5, 6)

        self._zfwButton = gtk.Button(xstr("payload_fszfw"))
        self._zfwButton.set_use_underline(True)
        self._zfwButton.connect("clicked", self._zfwRequested)
        self._zfwButton.set_tooltip_text(xstr("payload_fszfw_tooltip"))
        table.attach(self._zfwButton, 0, 1, 6, 7)

        self._simulatorZFW = gtk.Label("-")
        self._simulatorZFW.set_width_chars(6)
        self._simulatorZFW.set_alignment(1.0, 0.5)
        table.attach(self._simulatorZFW, 1, 2, 6, 7)
        self._simulatorZFWValue = None

        table.attach(gtk.Label("kg"), 2, 3, 6, 7)

        self._backButton = self.addPreviousButton(clicked = self._backClicked)
        self._button = self.addNextButton(clicked = self._forwardClicked)

    @property
    def cargoWeight(self):
        """Get the cargo weight entered."""
        return self._cargoWeight.get_int()

    def activate(self):
        """Setup the information."""
        bookedFlight = self._wizard._bookedFlight
        self._numCrew.set_text(str(bookedFlight.numCrew))
        self._numPassengers.set_text(str(bookedFlight.numPassengers))
        self._bagWeight.set_text(str(bookedFlight.bagWeight))
        self._cargoWeight.set_int(bookedFlight.cargoWeight)
        self._cargoWeight.set_sensitive(True)
        self._mailWeight.set_text(str(bookedFlight.mailWeight))
        self._simulatorZFW.set_text("-")
        self._simulatorZFWValue = None
        self._zfwButton.set_sensitive(True)
        self._updateCalculatedZFW()

    def finalize(self):
        """Finalize the payload page."""
        self._cargoWeight.set_sensitive(False)
        self._wizard.gui.initializeWeightHelp()

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
        gui.beginBusy(xstr("payload_zfw_busy"))
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
        super(TimePage, self).__init__(wizard, xstr("time_title"),
                                       xstr("time_help"),
                                       completedHelp = xstr("time_chelp"))

        alignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)

        table = gtk.Table(3, 2)
        table.set_row_spacings(4)
        table.set_col_spacings(16)
        table.set_homogeneous(False)
        alignment.add(table)
        self.setMainWidget(alignment)

        label = gtk.Label(xstr("time_departure"))
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, 0, 1)

        self._departure = gtk.Label()
        self._departure.set_alignment(0.0, 0.5)
        table.attach(self._departure, 1, 2, 0, 1)
        
        label = gtk.Label(xstr("time_arrival"))
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, 1, 2)

        self._arrival = gtk.Label()
        self._arrival.set_alignment(0.0, 0.5)
        table.attach(self._arrival, 1, 2, 1, 2)

        self._timeButton = gtk.Button(xstr("time_fs"))
        self._timeButton.set_use_underline(True)
        self._timeButton.set_tooltip_text(xstr("time_fs_tooltip"))
        self._timeButton.connect("clicked", self._timeRequested)
        table.attach(self._timeButton, 0, 1, 2, 3)

        self._simulatorTime = gtk.Label("-")
        self._simulatorTime.set_alignment(0.0, 0.5)
        table.attach(self._simulatorTime, 1, 2, 2, 3)

        self._backButton = self.addPreviousButton(clicked = self._backClicked)
        self._button = self.addNextButton(clicked = self._forwardClicked)

    def activate(self):
        """Activate the page."""
        self._timeButton.set_sensitive(True)
        bookedFlight = self._wizard._bookedFlight
        self._departure.set_text(str(bookedFlight.departureTime.time()))
        self._arrival.set_text(str(bookedFlight.arrivalTime.time()))
        self._simulatorTime.set_text("-")

    def _timeRequested(self, button):
        """Request the time from the simulator."""
        self._timeButton.set_sensitive(False)
        self._backButton.set_sensitive(False)
        self._button.set_sensitive(False)
        self._wizard.gui.beginBusy(xstr("time_busy"))
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
        if not self._completed:
            gui = self._wizard.gui
            gui.beginBusy(xstr("fuel_get_busy"))
            
            gui.simulator.getFuel(gui.flight.aircraft.fuelTanks,
                                  self._handleFuel)
        else:
            self._wizard.nextPage()

    def _handleFuel(self, fuelData):
        """Callback for the fuel query operation."""
        gobject.idle_add(self._processFuel, fuelData)

    def _processFuel(self, fuelData):
        """Process the given fuel data."""
        self._wizard.gui.endBusy()
        self._wizard._fuelData = fuelData
        self._wizard.nextPage()
        
#-----------------------------------------------------------------------------

class FuelTank(gtk.VBox):
    """Widget for the fuel tank."""
    def __init__(self, fuelTank, name, capacity, currentWeight):
        """Construct the widget for the tank with the given name."""
        super(FuelTank, self).__init__()

        self._enabled = True
        self.fuelTank = fuelTank
        self.capacity = capacity
        self.currentWeight = currentWeight
        self.expectedWeight = currentWeight

        label = gtk.Label("<b>" + name + "</b>")
        label.set_use_markup(True)
        label.set_use_underline(True)
        label.set_justify(JUSTIFY_CENTER)
        label.set_alignment(0.5, 1.0)
        self.pack_start(label, False, False, 4)

        self._tankFigure = gtk.EventBox()
        self._tankFigure.set_size_request(38, -1)
        self._tankFigure.set_visible_window(False)
        self._tankFigure.set_tooltip_markup(xstr("fuel_tank_tooltip"))

        if pygobject:
            self._tankFigure.connect("draw", self._drawTankFigure)
        else:
            self._tankFigure.connect("expose_event", self._drawTankFigure)
        self._tankFigure.connect("button_press_event", self._buttonPressed)
        self._tankFigure.connect("motion_notify_event", self._motionNotify)
        self._tankFigure.connect("scroll-event", self._scrolled)
        
        alignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 0.0, yscale = 1.0)
        alignment.add(self._tankFigure)

        self.pack_start(alignment, True, True, 4)

        self._expectedButton = gtk.SpinButton()
        self._expectedButton.set_numeric(True)
        self._expectedButton.set_range(0, self.capacity)
        self._expectedButton.set_increments(10, 100)
        self._expectedButton.set_value(currentWeight)
        self._expectedButton.set_alignment(1.0)
        self._expectedButton.set_width_chars(5)
        self._expectedButton.connect("value-changed", self._expectedChanged)

        label.set_mnemonic_widget(self._expectedButton)

        alignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 0.0, yscale = 1.0)
        alignment.add(self._expectedButton) 
        self.pack_start(alignment, False, False, 4)

    def setCurrent(self, currentWeight):
        """Set the current weight."""
        self.currentWeight = currentWeight
        self._redraw()

    def isCorrect(self):
        """Determine if the contents of the fuel tank are as expected"""
        return abs(self.expectedWeight - self.currentWeight)<=1

    def disable(self):
        """Disable the fuel tank."""
        self._expectedButton.set_sensitive(False)
        self._enabled = False

    def _redraw(self):
        """Redraw the tank figure."""
        self._tankFigure.queue_draw()

    def _drawTankFigure(self, tankFigure, eventOrContext):
        """Draw the tank figure."""
        triangleSize = 5

        context = eventOrContext if pygobject else tankFigure.window.cairo_create()
        (xOffset, yOffset) = (0, 0) if pygobject \
                             else (tankFigure.allocation.x, tankFigure.allocation.y)
        
        width = tankFigure.get_allocated_width() if pygobject \
                else tankFigure.allocation.width
        height = tankFigure.get_allocated_height() if pygobject \
                 else tankFigure.allocation.height

        rectangleX0 = triangleSize
        rectangleY0 = triangleSize
        rectangleX1 = width - 1 - triangleSize
        rectangleY1 = height - 1 - triangleSize
        rectangleLineWidth = 2.0

        context.set_source_rgb(0.0, 0.0, 0.0)
        context.set_line_width(rectangleLineWidth)
        context.rectangle(xOffset + rectangleX0 + rectangleLineWidth/2,
                          yOffset + rectangleY0 + rectangleLineWidth/2,
                          rectangleX1 - rectangleX0 - rectangleLineWidth,
                          rectangleY1 - rectangleY0 - rectangleLineWidth)
        context.stroke()

        rectangleInnerLeft   = rectangleX0 + rectangleLineWidth
        rectangleInnerRight  = rectangleX1 - rectangleLineWidth
        self._rectangleInnerTop = rectangleInnerTop = rectangleY0 + rectangleLineWidth
        self._rectangleInnerBottom = rectangleInnerBottom = rectangleY1 - rectangleLineWidth

        rectangleInnerWidth = rectangleInnerRight - rectangleInnerLeft
        rectangleInnerHeight = rectangleInnerBottom - rectangleInnerTop

        context.set_source_rgb(1.0, 0.9, 0.6)
        currentHeight = self.currentWeight * rectangleInnerHeight / self.capacity
        currentX = rectangleInnerTop + rectangleInnerHeight - currentHeight
        context.rectangle(xOffset + rectangleInnerLeft,
                          yOffset + rectangleInnerTop +
                          rectangleInnerHeight - currentHeight,
                          rectangleInnerWidth, currentHeight)
        context.fill()

        expectedHeight = self.expectedWeight * rectangleInnerHeight / self.capacity
        expectedY = rectangleInnerTop + rectangleInnerHeight - expectedHeight

        context.set_line_width(1.5)
        context.set_source_rgb(0.0, 0.85, 0.85)
        context.move_to(xOffset + rectangleX0, yOffset + expectedY)
        context.line_to(xOffset + rectangleX1, yOffset + expectedY)
        context.stroke()

        context.set_line_width(0.0)
        context.move_to(xOffset + 0, yOffset + expectedY - triangleSize)
        context.line_to(xOffset + 0, yOffset + expectedY + triangleSize)
        context.line_to(xOffset + rectangleX0 + 1, yOffset + expectedY)
        context.line_to(xOffset + 0, yOffset + expectedY - triangleSize)
        context.fill()

        context.set_line_width(0.0)
        context.move_to(xOffset + width, yOffset + expectedY - triangleSize)
        context.line_to(xOffset + width, yOffset + expectedY + triangleSize)
        context.line_to(xOffset + rectangleX1 - 1, yOffset + expectedY)
        context.line_to(xOffset + width, yOffset + expectedY - triangleSize)
        context.fill()

        return True

    def _setExpectedFromY(self, y):
        """Set the expected weight from the given Y-coordinate."""
        level = (self._rectangleInnerBottom - y) / \
                (self._rectangleInnerBottom - self._rectangleInnerTop)
        level = min(1.0, max(0.0, level))
        self._expectedButton.set_value(level * self.capacity)
        
    def _buttonPressed(self, tankFigure, event):
        """Called when a button is pressed in the figure.

        The expected level will be set there."""
        if self._enabled and event.button==1:
            self._setExpectedFromY(event.y)
        
    def _motionNotify(self, tankFigure, event):
        """Called when the mouse pointer moves within the area of a tank figure."""
        if self._enabled and event.state==BUTTON1_MASK:            
            self._setExpectedFromY(event.y)

    def _scrolled(self, tankFigure, event):
        """Called when a scroll event is received."""
        if self._enabled:
            increment = 1 if event.state==CONTROL_MASK \
                        else 100 if event.state==SHIFT_MASK \
                        else 10 if event.state==0 else 0
            if increment!=0:
                if event.direction==SCROLL_DOWN:
                    increment *= -1
                self._expectedButton.spin(SPIN_USER_DEFINED, increment)
        
    def _expectedChanged(self, spinButton):
        """Called when the expected value has changed."""
        self.expectedWeight = spinButton.get_value_as_int()
        self._redraw()        

#-----------------------------------------------------------------------------

class FuelPage(Page):
    """The page containing the fuel tank filling."""
    _pumpStep = 0.02
    
    def __init__(self, wizard):
        """Construct the page."""
        super(FuelPage, self).__init__(wizard, xstr("fuel_title"),
                                       xstr("fuel_help"),
                                       completedHelp = xstr("fuel_chelp"))

        self._fuelTanks = []
        self._fuelTable = None
        self._fuelAlignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                            xscale = 0.0, yscale = 1.0)
        self.setMainWidget(self._fuelAlignment)

        tanks = acft.MostFuelTankAircraft.fuelTanks
        tankData = ((2500, 3900),) * len(tanks)
        self._setupTanks(tanks, tankData)

        self._backButton = self.addPreviousButton(clicked = self._backClicked)
        self._button = self.addNextButton(clicked = self._forwardClicked)

        self._pumpIndex = 0

    def activate(self):
        """Activate the page."""
        gui = self._wizard.gui

        self._setupTanks(gui.flight.aircraft.fuelTanks,
                         self._wizard._fuelData)

    def finalize(self):
        """Finalize the page."""
        for fuelTank in self._fuelTanks:
            fuelTank.disable()

    def _backClicked(self, button):
        """Called when the Back button is pressed."""
        self.goBack()
        
    def _forwardClicked(self, button):
        """Called when the forward button is clicked."""
        if not self._completed:
            self._pumpIndex = 0
            self._wizard.gui.beginBusy(xstr("fuel_pump_busy"))
            self._pump()
        else:
            self._wizard.nextPage()        

    def _setupTanks(self, tanks, tankData):
        """Setup the tanks for the given data."""
        numTanks = len(tanks)
        if self._fuelTable is not None:
            self._fuelAlignment.remove(self._fuelTable)

        self._fuelTanks = []
        self._fuelTable = gtk.Table(numTanks, 1)
        self._fuelTable.set_col_spacings(16)
        for i in range(0, numTanks):
            tank = tanks[i]
            (current, capacity) = tankData[i]

            fuelTank = FuelTank(tank,
                                xstr("fuel_tank_" +
                                     const.fuelTank2string(tank)),
                                capacity, current)
            self._fuelTable.attach(fuelTank, i, i+1, 0, 1)
            self._fuelTanks.append(fuelTank)
            
        self._fuelAlignment.add(self._fuelTable)
        self.show_all()

    def _pump(self):
        """Perform one step of pumping.

        It is checked, if the current tank's contents are of the right
        quantity. If not, it is filled one step further to the desired
        contents. Otherwise the next tank is started. If all tanks are are
        filled, the next page is selected."""
        numTanks = len(self._fuelTanks)

        fuelTank = None
        while self._pumpIndex < numTanks:
            fuelTank = self._fuelTanks[self._pumpIndex]
            if fuelTank.isCorrect():
                self._pumpIndex += 1
                fuelTank = None
            else:
                break

        if fuelTank is None:
            self._wizard.gui.endBusy()
            self._wizard.nextPage()
        else:
            currentLevel = fuelTank.currentWeight / fuelTank.capacity
            expectedLevel = fuelTank.expectedWeight / fuelTank.capacity
            if currentLevel<expectedLevel:
                currentLevel += FuelPage._pumpStep
                if currentLevel>expectedLevel: currentLevel = expectedLevel
            else:
                currentLevel -= FuelPage._pumpStep
                if currentLevel<expectedLevel: currentLevel = expectedLevel
            fuelTank.setCurrent(currentLevel * fuelTank.capacity)
            self._wizard.gui.simulator.setFuelLevel([(fuelTank.fuelTank,
                                                      currentLevel)])
            gobject.timeout_add(50, self._pump)
        
#-----------------------------------------------------------------------------

class RoutePage(Page):
    """The page containing the route and the flight level."""
    def __init__(self, wizard):
        """Construct the page."""
        super(RoutePage, self).__init__(wizard, xstr("route_title"),
                                        xstr("route_help"),
                                        completedHelp = xstr("route_chelp"))

        alignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)

        mainBox = gtk.VBox()
        alignment.add(mainBox)
        self.setMainWidget(alignment)

        levelBox = gtk.HBox()

        label = gtk.Label(xstr("route_level"))
        label.set_use_underline(True)
        levelBox.pack_start(label, True, True, 0)

        self._cruiseLevel = gtk.SpinButton()
        self._cruiseLevel.set_increments(step = 10, page = 100)
        self._cruiseLevel.set_range(min = 50, max = 500)
        self._cruiseLevel.set_tooltip_text(xstr("route_level_tooltip"))
        self._cruiseLevel.set_numeric(True)
        self._cruiseLevel.connect("value-changed", self._cruiseLevelChanged)
        label.set_mnemonic_widget(self._cruiseLevel)
        self._filedCruiseLevel = 240

        levelBox.pack_start(self._cruiseLevel, False, False, 8)

        alignment = gtk.Alignment(xalign = 0.0, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)
        alignment.add(levelBox)

        mainBox.pack_start(alignment, False, False, 0)


        routeBox = gtk.VBox()

        alignment = gtk.Alignment(xalign = 0.0, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)
        label = gtk.Label(xstr("route_route"))
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

        self._uppercasingRoute = False

        self._route = gtk.TextView()
        self._route.set_tooltip_text(xstr("route_route_tooltip"))
        self._route.set_wrap_mode(WRAP_WORD)
        self._route.get_buffer().connect("changed", self._routeChanged)
        self._route.get_buffer().connect_after("insert-text", self._routeInserted)
        routeWindow.add(self._route)

        label.set_mnemonic_widget(self._route)
        routeBox.pack_start(routeWindow, True, True, 0)        

        mainBox.pack_start(routeBox, True, True, 8)

        self._backButton = self.addPreviousButton(clicked = self._backClicked)        
        self._button = self.addNextButton(clicked = self._forwardClicked)

    @property
    def filedCruiseLevel(self):
        """Get the filed cruise level."""
        return self._filedCruiseLevel

    @property
    def cruiseLevel(self):
        """Get the cruise level."""
        return self._cruiseLevel.get_value_as_int()

    @property
    def route(self):
        """Get the route."""
        return self._getRoute()

    def activate(self):
        """Setup the route from the booked flight."""
        self._cruiseLevel.set_value(240)
        self._filedCruiseLevel = 240
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
        if not self._uppercasingRoute:
            self._updateForwardButton()

    def _routeInserted(self, textBuffer, iter, text, length):
        """Called when new characters are inserted into the route.

        It uppercases all characters."""
        if not self._uppercasingRoute:
            self._uppercasingRoute = True

            iter1 = iter.copy()
            iter1.backward_chars(length)
            textBuffer.delete(iter, iter1)

            textBuffer.insert(iter, text.upper())

            self._uppercasingRoute = False

    def _backClicked(self, button):
        """Called when the Back button is pressed."""
        self.goBack()
        
    def _forwardClicked(self, button):
        """Called when the Forward button is clicked."""
        if self._completed:
            self._wizard.nextPage()
        else:
            bookedFlight = self._wizard._bookedFlight
            self._filedCruiseLevel = self.cruiseLevel
            self._wizard.gui.beginBusy(xstr("route_down_notams"))
            self._wizard.gui.webHandler.getNOTAMs(self._notamsCallback,
                                                  bookedFlight.departureICAO,
                                                  bookedFlight.arrivalICAO)
            startSound(const.SOUND_NOTAM)

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
        self._wizard.gui.beginBusy(xstr("route_down_metars"))
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
        
        title = xstr("briefing_title") % (1 if departure else 2,
                                          xstr("briefing_departure")
                                          if departure
                                          else xstr("briefing_arrival"))
        super(BriefingPage, self).__init__(wizard, title, xstr("briefing_help"),
                                           completedHelp = xstr("briefing_chelp"))

        alignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 1.0, yscale = 1.0)

        mainBox = gtk.VBox()
        alignment.add(mainBox)
        self.setMainWidget(alignment)

        self._notamsFrame = gtk.Frame()
        self._notamsFrame.set_label(xstr("briefing_notams_init"))
        scrolledWindow = gtk.ScrolledWindow()
        scrolledWindow.set_size_request(-1, 128)
        # FIXME: these constants should be in common
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
        self._metarFrame.set_label(xstr("briefing_metar_init"))
        scrolledWindow = gtk.ScrolledWindow()
        scrolledWindow.set_size_request(-1, 32)
        scrolledWindow.set_policy(gtk.PolicyType.AUTOMATIC if pygobject
                                  else gtk.POLICY_AUTOMATIC,
                                  gtk.PolicyType.AUTOMATIC if pygobject
                                  else gtk.POLICY_AUTOMATIC)

        self._uppercasingMETAR = False

        self._metar = gtk.TextView()
        self._metar.set_accepts_tab(False)
        self._metar.set_wrap_mode(gtk.WrapMode.WORD if pygobject else gtk.WRAP_WORD)
        self._metar.get_buffer().connect("changed", self._metarChanged)
        self._metar.get_buffer().connect_after("insert-text", self._metarInserted)
        scrolledWindow.add(self._metar)
        alignment = gtk.Alignment(xalign = 0.0, yalign = 0.0,
                                  xscale = 1.0, yscale = 1.0)
        alignment.set_padding(padding_top = 4, padding_bottom = 0,
                              padding_left = 0, padding_right = 0)
        alignment.add(scrolledWindow)
        self._metarFrame.add(alignment)
        mainBox.pack_start(self._metarFrame, True, True, 4)
        self.metarEdited = False

        self.addPreviousButton(clicked = self._backClicked)
        self._button = self.addNextButton(clicked = self._forwardClicked)

    @property
    def metar(self):
        """Get the METAR on the page."""
        buffer = self._metar.get_buffer()
        return buffer.get_text(buffer.get_start_iter(),
                               buffer.get_end_iter(), True)        

    def setMETAR(self, metar):
        """Set the metar."""
        self._metar.get_buffer().set_text(metar)
        self.metarEdited = False

    def activate(self):
        """Activate the page."""
        if not self._departure:
            self._button.set_label(xstr("briefing_button"))
            self._button.set_has_tooltip(False)
            self._button.set_use_stock(False)

        bookedFlight = self._wizard._bookedFlight

        icao = bookedFlight.departureICAO if self._departure \
               else bookedFlight.arrivalICAO
        notams = self._wizard._departureNOTAMs if self._departure \
                 else self._wizard._arrivalNOTAMs
        metar = self._wizard._departureMETAR if self._departure \
                 else self._wizard._arrivalMETAR

        self._notamsFrame.set_label(xstr("briefing_notams_template") % (icao,))
        buffer = self._notams.get_buffer()
        if notams is None:
            buffer.set_text(xstr("briefing_notams_failed"))
        elif not notams:
            buffer.set_text(xstr("briefing_notams_missing"))
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

        self._metarFrame.set_label(xstr("briefing_metar_template") % (icao,))
        buffer = self._metar.get_buffer()
        if metar is None:
            buffer.set_text(xstr("briefing_metar_failed"))
        else:
            buffer.set_text(metar)

        label = self._metarFrame.get_label_widget()
        label.set_use_underline(True)
        label.set_mnemonic_widget(self._metar)

        self.metarEdited = False

    def _backClicked(self, button):
        """Called when the Back button is pressed."""
        self.goBack()
        
    def _forwardClicked(self, button):
        """Called when the forward button is clicked."""
        if not self._departure:
            if not self._completed:
                self._wizard.gui.startMonitoring()
                self._button.set_label(xstr("button_next"))
                self._button.set_tooltip_text(xstr("button_next_tooltip"))
                self.complete()

        self._wizard.nextPage()

    def _metarChanged(self, buffer):
        """Called when the METAR has changed."""
        if not self._uppercasingMETAR:
            self.metarEdited = True
            self._button.set_sensitive(buffer.get_text(buffer.get_start_iter(),
                                                       buffer.get_end_iter(),
                                                       True)!="")

    def _metarInserted(self, textBuffer, iter, text, length):
        """Called when new characters are inserted into the METAR.

        It uppercases all characters."""
        if not self._uppercasingMETAR:
            self._uppercasingMETAR = True

            iter1 = iter.copy()
            iter1.backward_chars(length)
            textBuffer.delete(iter, iter1)

            textBuffer.insert(iter, text.upper())

            self._uppercasingMETAR = False

#-----------------------------------------------------------------------------

class TakeoffPage(Page):
    """Page for entering the takeoff data."""
    def __init__(self, wizard):
        """Construct the takeoff page."""
        super(TakeoffPage, self).__init__(wizard, xstr("takeoff_title"),
                                          xstr("takeoff_help"),
                                          completedHelp = xstr("takeoff_chelp"))

        self._forwardAllowed = False

        alignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)

        table = gtk.Table(5, 4)
        table.set_row_spacings(4)
        table.set_col_spacings(16)
        table.set_homogeneous(False)
        alignment.add(table)
        self.setMainWidget(alignment)

        label = gtk.Label(xstr("takeoff_runway"))
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, 0, 1)

        self._runway = gtk.Entry()
        self._runway.set_width_chars(10)
        self._runway.set_tooltip_text(xstr("takeoff_runway_tooltip"))
        self._runway.connect("changed", self._upperChanged)
        table.attach(self._runway, 1, 3, 0, 1)
        label.set_mnemonic_widget(self._runway)
        
        label = gtk.Label(xstr("takeoff_sid"))
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, 1, 2)

        self._sid = gtk.Entry()
        self._sid.set_width_chars(10)
        self._sid.set_tooltip_text(xstr("takeoff_sid_tooltip"))
        self._sid.connect("changed", self._upperChanged)
        table.attach(self._sid, 1, 3, 1, 2)
        label.set_mnemonic_widget(self._sid)
        
        label = gtk.Label(xstr("takeoff_v1"))
        label.set_use_markup(True)
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, 2, 3)

        self._v1 = IntegerEntry()
        self._v1.set_width_chars(4)
        self._v1.set_tooltip_markup(xstr("takeoff_v1_tooltip"))
        self._v1.connect("integer-changed", self._valueChanged)
        table.attach(self._v1, 2, 3, 2, 3)
        label.set_mnemonic_widget(self._v1)
        
        table.attach(gtk.Label(xstr("label_knots")), 3, 4, 2, 3)
        
        label = gtk.Label(xstr("takeoff_vr"))
        label.set_use_markup(True)
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, 3, 4)

        self._vr = IntegerEntry()
        self._vr.set_width_chars(4)
        self._vr.set_tooltip_markup(xstr("takeoff_vr_tooltip"))
        self._vr.connect("integer-changed", self._valueChanged)
        table.attach(self._vr, 2, 3, 3, 4)
        label.set_mnemonic_widget(self._vr)
        
        table.attach(gtk.Label(xstr("label_knots")), 3, 4, 3, 4)
        
        label = gtk.Label(xstr("takeoff_v2"))
        label.set_use_markup(True)
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, 4, 5)

        self._v2 = IntegerEntry()
        self._v2.set_width_chars(4)
        self._v2.set_tooltip_markup(xstr("takeoff_v2_tooltip"))
        self._v2.connect("integer-changed", self._valueChanged)
        table.attach(self._v2, 2, 3, 4, 5)
        label.set_mnemonic_widget(self._v2)
        
        table.attach(gtk.Label(xstr("label_knots")), 3, 4, 4, 5)

        self.addPreviousButton(clicked = self._backClicked)

        self._button = self.addNextButton(clicked = self._forwardClicked)

    @property
    def runway(self):
        """Get the runway."""
        return self._runway.get_text()

    @property
    def sid(self):
        """Get the SID."""
        return self._sid.get_text()

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
        
    def finalize(self):
        """Finalize the page."""
        self._runway.set_sensitive(False)
        self._sid.set_sensitive(False)
        self._v1.set_sensitive(False)
        self._vr.set_sensitive(False)
        self._v2.set_sensitive(False)
        self._wizard.gui.flight.aircraft.updateV1R2()

    def allowForward(self):
        """Allow going to the next page."""
        self._forwardAllowed = True
        self._updateForwardButton()

    def _updateForwardButton(self):
        """Update the sensitivity of the forward button based on some conditions."""
        sensitive = self._forwardAllowed and \
                    self._runway.get_text()!="" and \
                    self._sid.get_text()!="" and \
                    self.v1 is not None and \
                    self.vr is not None and \
                    self.v2 is not None and \
                    self.v1 <= self.vr and \
                    self.vr <= self.v2
        self._button.set_sensitive(sensitive)

    def _valueChanged(self, widget, arg = None):
        """Called when the value of some widget has changed."""
        self._updateForwardButton()
        
    def _upperChanged(self, entry, arg = None):
        """Called when the value of some entry widget has changed and the value
        should be converted to uppercase."""
        entry.set_text(entry.get_text().upper())
        self._valueChanged(entry, arg)
        
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
        super(LandingPage, self).__init__(wizard, xstr("landing_title"),
                                          xstr("landing_help"),
                                          completedHelp = xstr("landing_chelp"))

        self._flightEnded = False

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

        label = gtk.Label(xstr("landing_star"))
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 1, 2, 0, 1)

        self._star = gtk.Entry()
        self._star.set_width_chars(10)
        self._star.set_tooltip_text(xstr("landing_star_tooltip"))
        self._star.connect("changed", self._upperChanged)
        self._star.set_sensitive(False)
        table.attach(self._star, 2, 4, 0, 1)
        label.set_mnemonic_widget(self._starButton)

        self._transitionButton = gtk.CheckButton()
        self._transitionButton.connect("clicked", self._transitionButtonClicked)
        table.attach(self._transitionButton, 0, 1, 1, 2)

        label = gtk.Label(xstr("landing_transition"))
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 1, 2, 1, 2)

        self._transition = gtk.Entry()
        self._transition.set_width_chars(10)
        self._transition.set_tooltip_text(xstr("landing_transition_tooltip"))
        self._transition.connect("changed", self._upperChanged)
        self._transition.set_sensitive(False)
        table.attach(self._transition, 2, 4, 1, 2)
        label.set_mnemonic_widget(self._transitionButton)

        label = gtk.Label(xstr("landing_runway"))
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 1, 2, 2, 3)

        self._runway = gtk.Entry()
        self._runway.set_width_chars(10)
        self._runway.set_tooltip_text(xstr("landing_runway_tooltip"))
        self._runway.connect("changed", self._upperChanged)
        table.attach(self._runway, 2, 4, 2, 3)
        label.set_mnemonic_widget(self._runway)

        label = gtk.Label(xstr("landing_approach"))
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 1, 2, 3, 4)

        self._approachType = gtk.Entry()
        self._approachType.set_width_chars(10)
        self._approachType.set_tooltip_text(xstr("landing_approach_tooltip"))
        self._approachType.connect("changed", self._upperChanged)
        table.attach(self._approachType, 2, 4, 3, 4)
        label.set_mnemonic_widget(self._approachType)

        label = gtk.Label(xstr("landing_vref"))
        label.set_use_markup(True)
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 1, 2, 5, 6)

        self._vref = IntegerEntry()
        self._vref.set_width_chars(5)
        self._vref.set_tooltip_markup(xstr("landing_vref_tooltip"))
        self._vref.connect("integer-changed", self._vrefChanged)
        table.attach(self._vref, 3, 4, 5, 6)
        label.set_mnemonic_widget(self._vref)
        
        table.attach(gtk.Label(xstr("label_knots")), 4, 5, 5, 6)

        self.addPreviousButton(clicked = self._backClicked)

        self._button = self.addNextButton(clicked = self._forwardClicked)

        # These are needed for correct size calculations
        self._starButton.set_active(True)
        self._transitionButton.set_active(True)

    @property
    def star(self):
        """Get the STAR or None if none entered."""
        return self._star.get_text() if self._starButton.get_active() else None

    @property
    def transition(self):
        """Get the transition or None if none entered."""
        return self._transition.get_text() \
               if self._transitionButton.get_active() else None

    @property
    def approachType(self):
        """Get the approach type."""
        return self._approachType.get_text()

    @property
    def runway(self):
        """Get the runway."""
        return self._runway.get_text()

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

    def flightEnded(self):
        """Called when the flight has ended."""
        self._flightEnded = True
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
        self._wizard.gui.flight.aircraft.updateVRef()
        # FIXME: Perhaps a separate initialize() call which would set up
        # defaults? -> use reset()
        self._flightEnded = False

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

    def _updateForwardButton(self):
        """Update the sensitivity of the forward button."""
        sensitive = self._flightEnded and \
                    (self._starButton.get_active() or \
                     self._transitionButton.get_active()) and \
                    (self._star.get_text()!="" or
                     not self._starButton.get_active()) and \
                    (self._transition.get_text()!="" or
                     not self._transitionButton.get_active()) and \
                    self._runway.get_text()!="" and \
                    self._approachType.get_text()!="" and \
                    self.vref is not None
        self._button.set_sensitive(sensitive)

    def _upperChanged(self, entry):
        """Called for entry widgets that must be converted to uppercase."""
        entry.set_text(entry.get_text().upper())
        self._updateForwardButton()

    def _vrefChanged(self, widget, value):
        """Called when the Vref has changed."""
        self._updateForwardButton()

    def _backClicked(self, button):
        """Called when the Back button is pressed."""
        self.goBack()
        
    def _forwardClicked(self, button):
        """Called when the forward button is clicked."""
        if self._wizard.gui.config.onlineGateSystem and \
           not self._completed and \
           self._wizard.bookedFlight.arrivalICAO=="LHBP":
            self._wizard.getFleet(callback = self._fleetRetrieved,
                                  force = True)
        else:
            self._wizard.nextPage()

    def _fleetRetrieved(self, fleet):
        """Callback for the fleet retrieval."""
        self._wizard.nextPage()

#-----------------------------------------------------------------------------

class FinishPage(Page):
    """Flight finish page."""
    _flightTypes = [ ("flighttype_scheduled", const.FLIGHTTYPE_SCHEDULED),
                     ("flighttype_ot", const.FLIGHTTYPE_OLDTIMER),
                     ("flighttype_vip", const.FLIGHTTYPE_VIP),
                     ("flighttype_charter", const.FLIGHTTYPE_CHARTER) ]
    
    def __init__(self, wizard):
        """Construct the finish page."""
        super(FinishPage, self).__init__(wizard, xstr("finish_title"),
                                         xstr("finish_help"))
        
        alignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)

        table = gtk.Table(8, 2)
        table.set_row_spacings(4)
        table.set_col_spacings(16)
        table.set_homogeneous(False)
        alignment.add(table)
        self.setMainWidget(alignment)

        labelAlignment = gtk.Alignment(xalign=1.0, xscale=0.0)
        label = gtk.Label(xstr("finish_rating"))
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, 0, 1)

        labelAlignment = gtk.Alignment(xalign=0.0, xscale=0.0)
        self._flightRating = gtk.Label()
        self._flightRating.set_width_chars(8)
        self._flightRating.set_alignment(0.0, 0.5)
        self._flightRating.set_use_markup(True)
        labelAlignment.add(self._flightRating)
        table.attach(labelAlignment, 1, 2, 0, 1)

        labelAlignment = gtk.Alignment(xalign=1.0, xscale=0.0)
        label = gtk.Label(xstr("finish_flight_time"))
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, 1, 2)

        labelAlignment = gtk.Alignment(xalign=0.0, xscale=0.0)
        self._flightTime = gtk.Label()
        self._flightTime.set_width_chars(10)
        self._flightTime.set_alignment(0.0, 0.5)
        self._flightTime.set_use_markup(True)
        labelAlignment.add(self._flightTime)
        table.attach(labelAlignment, 1, 2, 1, 2)

        labelAlignment = gtk.Alignment(xalign=1.0, xscale=0.0)
        label = gtk.Label(xstr("finish_block_time"))
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, 2, 3)

        labelAlignment = gtk.Alignment(xalign=0.0, xscale=0.0)
        self._blockTime = gtk.Label()
        self._blockTime.set_width_chars(10)
        self._blockTime.set_alignment(0.0, 0.5)
        self._blockTime.set_use_markup(True)
        labelAlignment.add(self._blockTime)
        table.attach(labelAlignment, 1, 2, 2, 3)

        labelAlignment = gtk.Alignment(xalign=1.0, xscale=0.0)
        label = gtk.Label(xstr("finish_distance"))
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, 3, 4)

        labelAlignment = gtk.Alignment(xalign=0.0, xscale=0.0)
        self._distanceFlown = gtk.Label()
        self._distanceFlown.set_width_chars(10)
        self._distanceFlown.set_alignment(0.0, 0.5)
        self._distanceFlown.set_use_markup(True)
        labelAlignment.add(self._distanceFlown)
        table.attach(labelAlignment, 1, 2, 3, 4)
        
        labelAlignment = gtk.Alignment(xalign=1.0, xscale=0.0)
        label = gtk.Label(xstr("finish_fuel"))
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, 4, 5)

        labelAlignment = gtk.Alignment(xalign=0.0, xscale=0.0)
        self._fuelUsed = gtk.Label()
        self._fuelUsed.set_width_chars(10)
        self._fuelUsed.set_alignment(0.0, 0.5)
        self._fuelUsed.set_use_markup(True)
        labelAlignment.add(self._fuelUsed)
        table.attach(labelAlignment, 1, 2, 4, 5)

        labelAlignment = gtk.Alignment(xalign = 1.0, xscale = 0.0,
                                       yalign = 0.5, yscale = 0.0)
        label = gtk.Label(xstr("finish_type"))
        label.set_use_underline(True)
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, 5, 6)

        flightTypeModel = gtk.ListStore(str, int)
        for (name, type) in FinishPage._flightTypes:
            flightTypeModel.append([xstr(name), type])

        self._flightType = gtk.ComboBox(model = flightTypeModel)
        renderer = gtk.CellRendererText()
        self._flightType.pack_start(renderer, True)
        self._flightType.add_attribute(renderer, "text", 0)
        self._flightType.set_tooltip_text(xstr("finish_type_tooltip"))
        self._flightType.set_active(0)
        self._flightType.connect("changed", self._flightTypeChanged)
        flightTypeAlignment = gtk.Alignment(xalign=0.0, xscale=0.0)
        flightTypeAlignment.add(self._flightType)
        table.attach(flightTypeAlignment, 1, 2, 5, 6)
        label.set_mnemonic_widget(self._flightType)        

        self._onlineFlight = gtk.CheckButton(xstr("finish_online"))
        self._onlineFlight.set_use_underline(True)
        self._onlineFlight.set_tooltip_text(xstr("finish_online_tooltip"))
        onlineFlightAlignment = gtk.Alignment(xalign=0.0, xscale=0.0)
        onlineFlightAlignment.add(self._onlineFlight)
        table.attach(onlineFlightAlignment, 1, 2, 6, 7)

        labelAlignment = gtk.Alignment(xalign = 1.0, xscale = 0.0,
                                       yalign = 0.5, yscale = 0.0)
        self._gateLabel = gtk.Label(xstr("finish_gate"))
        self._gateLabel.set_use_underline(True)
        labelAlignment.add(self._gateLabel)
        table.attach(labelAlignment, 0, 1, 7, 8)

        self._gatesModel = gtk.ListStore(str)

        self._gate = gtk.ComboBox(model = self._gatesModel)
        renderer = gtk.CellRendererText()
        self._gate.pack_start(renderer, True)
        self._gate.add_attribute(renderer, "text", 0)
        self._gate.set_tooltip_text(xstr("finish_gate_tooltip"))
        self._gate.connect("changed", self._gateChanged)               
        gateAlignment = gtk.Alignment(xalign=0.0, xscale=1.0)
        gateAlignment.add(self._gate)
        table.attach(gateAlignment, 1, 2, 7, 8)
        self._gateLabel.set_mnemonic_widget(self._gate)

        self.addPreviousButton(clicked = self._backClicked)

        self._saveButton = self.addButton(xstr("finish_save"),
                                          sensitive = False,
                                          clicked = self._saveClicked,
                                          tooltip = xstr("finish_save_tooltip"))
        self._savePIREPDialog = None
        self._lastSavePath = None
        
        self._sendButton = self.addButton(xstr("sendPIREP"), default = True,
                                          sensitive = False,
                                          clicked = self._sendClicked,
                                          tooltip = xstr("sendPIREP_tooltip"))
        
    @property
    def flightType(self):
        """Get the flight type."""
        index = self._flightType.get_active()
        return None if index<0 else self._flightType.get_model()[index][1]

    @property
    def online(self):
        """Get whether the flight was an online flight or not."""
        return self._onlineFlight.get_active()

    def activate(self):
        """Activate the page."""
        flight = self._wizard.gui._flight
        rating = flight.logger.getRating()
        if rating<0:
            self._flightRating.set_markup('<b><span foreground="red">NO GO</span></b>')
        else:
            self._flightRating.set_markup("<b>%.1f %%</b>" % (rating,))

        flightLength = flight.flightTimeEnd - flight.flightTimeStart
        self._flightTime.set_markup("<b>%s</b>" % \
                                    (util.getTimeIntervalString(flightLength),))
        
        blockLength = flight.blockTimeEnd - flight.blockTimeStart
        self._blockTime.set_markup("<b>%s</b>" % \
                                   (util.getTimeIntervalString(blockLength),))

        self._distanceFlown.set_markup("<b>%.2f NM</b>" % \
                                       (flight.flownDistance,))
        
        self._fuelUsed.set_markup("<b>%.0f kg</b>" % \
                                  (flight.startFuel - flight.endFuel,))

        self._flightType.set_active(-1)
        self._onlineFlight.set_active(True)

        self._gatesModel.clear()
        if self._wizard.gui.config.onlineGateSystem and \
           self._wizard.bookedFlight.arrivalICAO=="LHBP":
            occupiedGates = self._wizard._fleet.getOccupiedGateNumbers()
            for gateNumber in const.lhbpGateNumbers:
                if gateNumber not in occupiedGates:
                    self._gatesModel.append([gateNumber])
            self._gateLabel.set_sensitive(True)
            self._gate.set_sensitive(True)
            self._gate.set_active(-1)
        else:
            self._gateLabel.set_sensitive(False)
            self._gate.set_sensitive(False)

    def _backClicked(self, button):
        """Called when the Back button is pressed."""
        self.goBack()

    def _updateButtons(self):
        """Update the sensitivity state of the buttons."""
        sensitive = self._flightType.get_active()>=0 and \
                    (self._gatesModel.get_iter_first() is None or
                     self._gate.get_active()>=0)
        
        self._saveButton.set_sensitive(sensitive)
        self._sendButton.set_sensitive(sensitive)        

    def _flightTypeChanged(self, comboBox):
        """Called when the flight type has changed."""
        self._updateButtons()

    def _gateChanged(self, comboBox):
        """Called when the arrival gate has changed."""
        self._updateButtons()

    def _saveClicked(self, button):
        """Called when the Save PIREP button is clicked."""
        gui = self._wizard.gui

        bookedFlight = gui.bookedFlight
        tm = time.gmtime()
        
        fileName = "%s %s %02d%02d %s-%s.pirep" % \
                   (gui.loginResult.pilotID,
                    str(bookedFlight.departureTime.date()),
                    tm.tm_hour, tm.tm_min,
                    bookedFlight.departureICAO,
                    bookedFlight.arrivalICAO)

        dialog = self._getSaveDialog()

        if self._lastSavePath is None:
            pirepDirectory = gui.config.pirepDirectory
            if pirepDirectory is not None:
                dialog.set_current_folder(pirepDirectory)
        else:
            dialog.set_current_folder(os.path.dirname(self._lastSavePath))
            
        dialog.set_current_name(fileName)
        result = dialog.run()
        dialog.hide()

        if result==RESPONSETYPE_OK:
            pirep = PIREP(gui)

            self._lastSavePath = text2unicode(dialog.get_filename())
            
            if pirep.save(self._lastSavePath):
                type = MESSAGETYPE_INFO
                message = xstr("finish_save_done")
                secondary = None
            else:
                type = MESSAGETYPE_ERROR
                message = xstr("finish_save_failed")
                secondary = xstr("finish_save_failed_sec")
                
            dialog = gtk.MessageDialog(parent = gui.mainWindow,
                                       type = type, message_format = message)
            dialog.add_button(xstr("button_ok"), RESPONSETYPE_OK)
            dialog.set_title(WINDOW_TITLE_BASE)
            if secondary is not None:
                dialog.format_secondary_markup(secondary)

            dialog.run()
            dialog.hide()

    def _getSaveDialog(self):
        """Get the PIREP saving dialog.

        If it does not exist yet, create it."""
        if self._savePIREPDialog is None:
            gui = self._wizard.gui
            dialog = gtk.FileChooserDialog(title = WINDOW_TITLE_BASE + " - " +
                                           xstr("finish_save_title"),
                                           action = FILE_CHOOSER_ACTION_SAVE,
                                           buttons = (gtk.STOCK_CANCEL,
                                                      RESPONSETYPE_CANCEL,
                                                      gtk.STOCK_OK, RESPONSETYPE_OK),
                                           parent = gui.mainWindow)
            dialog.set_modal(True)
            dialog.set_do_overwrite_confirmation(True)
            
            filter = gtk.FileFilter()
            filter.set_name(xstr("loadPIREP_filter_pireps"))
            filter.add_pattern("*.pirep")
            dialog.add_filter(filter)
            
            filter = gtk.FileFilter()
            filter.set_name(xstr("loadPIREP_filter_all"))
            filter.add_pattern("*.*")
            dialog.add_filter(filter)

            self._savePIREPDialog = dialog

        return self._savePIREPDialog
        

    def _sendClicked(self, button):
        """Called when the Send button is clicked."""
        pirep = PIREP(self._wizard.gui)
        self._wizard.gui.sendPIREP(pirep,
                                   callback = self._handlePIREPSent)

    def _handlePIREPSent(self, returned, result):
        """Callback for the PIREP sending result."""
        if self._wizard.gui.config.onlineGateSystem and returned and result.success:
            bookedFlight = self._wizard.bookedFlight
            if bookedFlight.arrivalICAO=="LHBP":
                iter = self._gate.get_active_iter()                
                gateNumber = None if iter is None \
                             else self._gatesModel.get_value(iter, 0)
                
                status = const.PLANE_PARKING if gateNumber is None \
                         else const.PLANE_HOME
            else:
                gateNumber = None
                status = const.PLANE_AWAY

            self._wizard.updatePlane(self._planeUpdated,
                                     bookedFlight.tailNumber,
                                     status, gateNumber = gateNumber)

    def _planeUpdated(self, success):
        """Callback for the plane updating."""
        pass
        
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
        self._payloadIndex = len(self._pages)
        self._pages.append(TimePage(self))
        self._pages.append(FuelPage(self))
        self._routePage = RoutePage(self)
        self._pages.append(self._routePage)
        self._departureBriefingPage = BriefingPage(self, True)
        self._pages.append(self._departureBriefingPage)
        self._arrivalBriefingPage = BriefingPage(self, False)
        self._pages.append(self._arrivalBriefingPage)
        self._arrivalBriefingIndex = len(self._pages)
        self._takeoffPage = TakeoffPage(self) 
        self._pages.append(self._takeoffPage)
        self._landingPage = LandingPage(self) 
        self._pages.append(self._landingPage)
        self._finishPage = FinishPage(self)
        self._pages.append(self._finishPage)
        
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
            if finalize and not page._completed:
                page.complete()
            self.remove(page)

        self._currentPage = index
        page = self._pages[index]
        self.add(page)
        if page._fromPage is None:
            page._fromPage = fromPage
            page.initialize()
        self.show_all()
        if fromPage is not None:
            self.grabDefault()

    @property
    def bookedFlight(self):
        """Get the booked flight selected."""
        return self._bookedFlight

    @property
    def cargoWeight(self):
        """Get the calculated ZFW value."""
        return self._payloadPage.cargoWeight

    @property
    def zfw(self):
        """Get the calculated ZFW value."""
        return 0 if self._bookedFlight is None \
               else self._payloadPage.calculateZFW()

    @property
    def filedCruiseAltitude(self):
        """Get the filed cruise altitude."""
        return self._routePage.filedCruiseLevel * 100

    @property
    def cruiseAltitude(self):
        """Get the cruise altitude."""
        return self._routePage.cruiseLevel * 100

    @property
    def route(self):
        """Get the route."""
        return self._routePage.route

    @property
    def departureMETAR(self):
        """Get the METAR of the departure airport."""
        return self._departureBriefingPage.metar

    @property
    def arrivalMETAR(self):
        """Get the METAR of the arrival airport."""
        return self._arrivalBriefingPage.metar

    @property
    def departureRunway(self):
        """Get the departure runway."""
        return self._takeoffPage.runway

    @property
    def sid(self):
        """Get the SID."""
        return self._takeoffPage.sid

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
    def arrivalRunway(self):
        """Get the arrival runway."""
        return self._landingPage.runway

    @property
    def star(self):
        """Get the STAR."""
        return self._landingPage.star

    @property
    def transition(self):
        """Get the transition."""
        return self._landingPage.transition

    @property
    def approachType(self):
        """Get the approach type."""
        return self._landingPage.approachType

    @property
    def vref(self):
        """Get the Vref speed."""
        return self._landingPage.vref

    @property
    def flightType(self):
        """Get the flight type."""
        return self._finishPage.flightType

    @property
    def online(self):
        """Get whether the flight was online or not."""
        return self._finishPage.online

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

    def reset(self):
        """Resets the wizard to go back to the login page."""
        self._initialize()

    def setStage(self, stage):
        """Set the flight stage to the given one."""
        if stage==const.STAGE_TAKEOFF:
            self._takeoffPage.allowForward()
        elif stage==const.STAGE_LANDING:
            if not self._arrivalBriefingPage.metarEdited:
                print "Downloading arrival METAR again"
                self.gui.webHandler.getMETARs(self._arrivalMETARCallback,
                                              [self._bookedFlight.arrivalICAO])
            
        elif stage==const.STAGE_END:
            self._landingPage.flightEnded()

    def _initialize(self):
        """Initialize the wizard."""
        self._fleet = None
        self._fleetCallback = None
        
        self._loginResult = None
        self._bookedFlight = None
        self._departureGate = "-"
        self._fuelData = None
        self._departureNOTAMs = None
        self._departureMETAR = None
        self._arrivalNOTAMs = None
        self._arrivalMETAR = None

        for page in self._pages:
            page.reset()
        
        self.setCurrentPage(0)

    def getFleet(self, callback, force = False):
        """Get the fleet via the GUI and call the given callback."""
        self._fleetCallback = callback
        self.gui.getFleet(callback = self._fleetRetrieved, force = force)

    def _fleetRetrieved(self, fleet):
        """Callback for the fleet retrieval."""
        self._fleet = fleet
        if self._fleetCallback is not None:
            self._fleetCallback(fleet)
        self._fleetCallback = None
        
    def updatePlane(self, callback, tailNumber, status, gateNumber = None):
        """Update the given plane's gate information."""
        self.gui.updatePlane(tailNumber, status, gateNumber = gateNumber,
                             callback = callback)

    def _connectSimulator(self):
        """Connect to the simulator."""
        self.gui.connectSimulator(self._bookedFlight.aircraftType)

    def _arrivalMETARCallback(self, returned, result):
        """Called when the METAR of the arrival airport is retrieved."""
        gobject.idle_add(self._handleArrivalMETAR, returned, result)
    
    def _handleArrivalMETAR(self, returned, result):
        """Called when the METAR of the arrival airport is retrieved."""
        icao = self._bookedFlight.arrivalICAO
        if returned and icao in result.metars:
            metar = result.metars[icao]
            if metar!="":
                self._arrivalBriefingPage.setMETAR(metar)
    
#-----------------------------------------------------------------------------

