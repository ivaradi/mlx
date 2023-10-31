# -*- encoding: utf-8 -*-

from mlx.gui.common import *
import mlx.gui.cef as cef
from mlx.gui.flightlist import ColumnDescriptor, FlightList, PendingFlightsWindow

import mlx.const as const
import mlx.fs as fs
import mlx.acft as acft
from mlx.flight import Flight
from mlx.checks import PayloadChecker
from mlx.gates import lhbpGates
import mlx.util as util
from mlx.pirep import PIREP
from mlx.i18n import xstr, getLanguage
from mlx.sound import startSound
from mlx.rpc import BookedFlight
import mlx.web as web
from mlx.gates import lhbpGates

import datetime
import time
import os
import tempfile
import threading
import re
import webbrowser
import urllib.request, urllib.error, urllib.parse
from lxml import etree
from io import StringIO
import lxml.html
import certifi

#-----------------------------------------------------------------------------

## @package mlx.gui.flight
#
# The flight "wizard".
#
# This module implements the main tab of the application, the flight
# wizard. The wizard consists of \ref Page "pages", that come one after the
# other. As some pages might be skipped, the pages dynamically store the index
# of the previous page so that going back to it is simpler. The \ref
# Page.activate "activate" function is called before a page is first shown
# during a flight. This function should initialize the page's controls and fill
# it with initial data. When a page is left for the first time, its \ref
# Page.finalize "finalize" function is called. It should set those controls
# insensitive, that will not be available if the user comes back to this page.
#
# Each page has a title at the top displayed in inverted colors and a big
# font. There is a help text below it centered, that shortly describes what is
# expected on the page. There can be two help texts: one shown when the page is
# first displayed during a flight, another shown when the user goes back to the
# page. The main content area is below this, also centered. Finally, there are
# some buttons at the bottom on the right. As some buttons occur very
# frequently, there are functions to add them (\ref Page.addCancelFlightButton
# "addCancelFlightButton", \ref Page.addPreviousButton "addPreviousButton" and
# \ref Page.addNextButton "addNextButton".
#
# The \ref Wizard class is the main class to collect the pages. It also stores
# some data passed from one page to another and provides properties to access
# data items set via the wizard pages.

#-----------------------------------------------------------------------------

comboModel = Gtk.ListStore(GObject.TYPE_STRING)
comboModel.append(("N/A",))
comboModel.append(("VECTORS",))

#-----------------------------------------------------------------------------

class Page(Gtk.Alignment):
    """A page in the flight wizard."""
    def __init__(self, wizard, id, title, help, completedHelp = None):
        """Construct the page."""
        super(Page, self).__init__(xalign = 0.0, yalign = 0.0,
                                   xscale = 1.0, yscale = 1.0)
        self.set_padding(padding_top = 4, padding_bottom = 4,
                         padding_left = 12, padding_right = 12)

        frame = Gtk.Frame()
        self.add(frame)

        self._vbox = Gtk.VBox()
        self._vbox.set_homogeneous(False)
        frame.add(self._vbox)

        eventBox = Gtk.EventBox()

        alignment = Gtk.Alignment(xalign = 0.0, xscale = 0.0)

        titleLabel = Gtk.Label(title)
        titleLabel.modify_font(Pango.FontDescription("bold 24"))
        alignment.set_padding(padding_top = 4, padding_bottom = 4,
                              padding_left = 6, padding_right = 0)

        alignment.add(titleLabel)
        eventBox.add(alignment)

        self._vbox.pack_start(eventBox, False, False, 0)

        self._titleEventBox = eventBox
        self._titleLabel = titleLabel

        mainBox = Gtk.VBox()

        alignment = Gtk.Alignment(xalign = 0.0, yalign = 0.0,
                                  xscale = 1.0, yscale = 1.0)
        alignment.set_padding(padding_top = 16, padding_bottom = 16,
                              padding_left = 16, padding_right = 16)
        alignment.add(mainBox)
        self._vbox.pack_start(alignment, True, True, 0)

        alignment = Gtk.Alignment(xalign = 0.5, yalign = 0.0,
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

        self._helpLabel = Gtk.Label(longerHelp)
        # FIXME: should be a constant in common
        self._helpLabel.set_justify(Gtk.Justification.CENTER)
        self._helpLabel.set_use_markup(True)
        alignment.add(self._helpLabel)
        mainBox.pack_start(alignment, False, False, 0)

        self._mainAlignment = Gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                            xscale = 1.0, yscale = 1.0)
        mainBox.pack_start(self._mainAlignment, True, True, 0)

        buttonAlignment =  Gtk.Alignment(xalign = 1.0, xscale=0.0, yscale = 0.0)
        buttonAlignment.set_padding(padding_top = 4, padding_bottom = 10,
                                    padding_left = 16, padding_right = 16)

        self._buttonBox = Gtk.HBox()
        self._buttonBox.set_homogeneous(False)
        self._defaultButton = None
        buttonAlignment.add(self._buttonBox)

        self._vbox.pack_start(buttonAlignment, False, False, 0)

        self._wizard = wizard
        self._id = id
        self._nextPageID = None

        self._cancelFlightButton = None

        self._completed = False
        self._fromPage = None

    @property
    def id(self):
        """Get the identifier of the page."""
        return self._id

    @property
    def nextPageID(self):
        """Get the identifier of the next page, if set."""
        return self._nextPageID

    @nextPageID.setter
    def nextPageID(self, nextPageID):
        """Set the identifier of the next page."""
        self._nextPageID = nextPageID

    def setMainWidget(self, widget):
        """Set the given widget as the main one."""
        self._mainAlignment.add(widget)

    def addButton(self, label, default = False, sensitive = True,
                  tooltip = None, clicked = None, padding = 4,
                  clickedArg = None):
        """Add a button with the given label.

        Return the button object created."""
        button = Gtk.Button(label)
        self._buttonBox.pack_start(button, False, False, padding)
        button.set_use_underline(True)
        if default:
            button.set_can_default(True)
            self._defaultButton = button
        button.set_sensitive(sensitive)
        if tooltip is not None:
            button.set_tooltip_text(tooltip)
        if clicked is not None:
            if clickedArg is None:
                button.connect("clicked", clicked)
            else:
                button.connect("clicked", clicked, clickedArg)
        return button

    def addCancelFlightButton(self):
        """Add the 'Cancel flight' button to the page."""
        self._cancelFlightButton = \
            self.addButton(xstr("button_cancelFlight"),
                           sensitive = True,
                           tooltip = xstr("button_cancelFlight_tooltip"),
                           clicked = self._cancelFlight,
                           padding = 16)
        return self._cancelFlightButton

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

    def setStyle(self):
        """Set the styles of some of the items on the page."""
        context = self.get_style_context()
        color = context.get_background_color(Gtk.StateFlags.SELECTED)
        self._titleEventBox.modify_bg(0, color.to_color())
        color = context.get_color(Gtk.StateFlags.SELECTED)
        self._titleLabel.modify_fg(0, color.to_color())

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

    def prepareShow(self):
        """Prepare the page for showing, either initially on when later
        returned to."""
        pass

    def setHelp(self, help):
        """Set the help string."""
        self._help = help
        if not self._completed:
            self._helpLabel.set_markup(self._help)
            self._helpLabel.set_sensitive(True)

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

    def prepareHide(self):
        """Prepare the page for hiding, either initially on when later
        the user returned to it and then navigates away from it."""
        pass

    def reset(self):
        """Reset the page if the wizard is reset."""
        self._completed = False
        self._fromPage = None
        if self._cancelFlightButton is not None:
            self._cancelFlightButton.set_sensitive(True)

    def goBack(self):
        """Go to the page we were invoked from."""
        assert self._fromPage is not None

        self._wizard.setCurrentPage(self._fromPage, finalize = False)

    def flightEnded(self):
        """Called when the flight has ended.

        This default implementation disables the cancel flight button."""
        if self._cancelFlightButton is not None:
            self._cancelFlightButton.set_sensitive(False)

    def _cancelFlight(self, button):
        """Called when the Cancel flight button is clicked."""
        self._wizard.gui.cancelFlight()

#-----------------------------------------------------------------------------

class LoginPage(Page):
    """The login page."""
    def __init__(self, wizard):
        """Construct the login page."""
        super(LoginPage, self).__init__(wizard, "login",
                                        xstr("login"), xstr("loginHelp"))

        alignment = Gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)

        table = Gtk.Table(3, 2)
        table.set_row_spacings(4)
        table.set_col_spacings(32)
        alignment.add(table)
        self.setMainWidget(alignment)

        labelAlignment = Gtk.Alignment(xalign = 1.0, yalign = 0.5,
                                       xscale = 0.0, yscale = 0.0)
        label = Gtk.Label(xstr("label_pilotID"))
        label.set_use_underline(True)
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, 0, 1)

        self._pilotID = Gtk.Entry()
        self._pilotID.connect("changed", self._pilotIDChanged)
        self._pilotID.set_tooltip_text(xstr("login_pilotID_tooltip"))
        table.attach(self._pilotID, 1, 2, 0, 1)
        label.set_mnemonic_widget(self._pilotID)

        labelAlignment = Gtk.Alignment(xalign = 1.0, yalign = 0.5,
                                       xscale = 0.0, yscale = 0.0)
        label = Gtk.Label(xstr("label_password"))
        label.set_use_underline(True)
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, 1, 2)

        self._password = Gtk.Entry()
        self._password.set_visibility(False)
        self._password.connect("changed", self._setControls)
        self._password.set_tooltip_text(xstr("login_password_tooltip"))
        table.attach(self._password, 1, 2, 1, 2)
        label.set_mnemonic_widget(self._password)

        self._rememberButton = Gtk.CheckButton(xstr("remember_password"))
        self._rememberButton.set_use_underline(True)
        self._rememberButton.set_tooltip_text(xstr("login_remember_tooltip"))
        table.attach(self._rememberButton, 1, 2, 2, 3, ypadding = 8)

        self.addButton(xstr("button_login_register"),
                       clicked = self._registerClicked,
                       tooltip = xstr("button_login_register_tooltip"))

        self.addButton(xstr("button_offline"),
                       clicked = self._offlineClicked,
                       tooltip = xstr("button_offline_tooltip"))

        self._loginButton = self.addButton(xstr("button_login"), default = True)
        self._loginButton.connect("clicked", self._loginClicked)
        self._loginButton.set_tooltip_text(xstr("login_button_tooltip"))


    @property
    def pilotID(self):
        """Get the pilot ID, if given."""
        return self._pilotID.get_text()

    def activate(self):
        """Activate the page."""
        config = self._wizard.gui.config
        self._pilotID.set_text(config.pilotID)
        self._password.set_text(config.password)
        self._rememberButton.set_active(config.rememberPassword)
        self._setControls(None)

    def _pilotIDChanged(self, entry):
        """Called when the pilot ID has changed.

        It sets the text to upper-case and calls _setControls to update other
        stuff."""
        entry.set_text(entry.get_text().upper())
        self._setControls(entry)

    def _setControls(self, entry = None):
        """Set the sensitivity of the various controls.

        The login button is sensitive only if both the pilot ID and the
        password fields contain values.

        The password field is sensitive only, if the entrance exam checkbox is
        not selected.

        The remember password checkbox is sensitive only, if the password field
        contains text.

        The entrance exam checkbox is sensitive only, if the pilot ID is not
        empty."""
        pilotID = self._pilotID.get_text()
        password = self._password.get_text()
        self._rememberButton.set_sensitive(password!="")
        self._loginButton.set_sensitive(pilotID!="" and password!="")

    def _registerClicked(self, button):
        """Called when the Register button was clicked."""
        self._wizard.jumpPage("register")

    def _offlineClicked(self, button):
        """Called when the offline button was clicked."""
        print("mlx.flight.LoginPage: offline flight selected")
        self._wizard.nextPage()

    def _loginClicked(self, button):
        """Called when the login button was clicked."""
        print("mlx.flight.LoginPage: logging in")
        self._wizard.login(self._handleLoginResult,
                           self._pilotID.get_text(),
                           self._password.get_text())

    def _handleLoginResult(self, returned, result):
        """Handle the login result."""
        self._loginButton.set_sensitive(True)
        if returned and result.loggedIn:
            config = self._wizard.gui.config

            config.pilotID = self._pilotID.get_text()

            rememberPassword = self._rememberButton.get_active()
            config.password = result.password if rememberPassword else ""

            config.rememberPassword = rememberPassword

            config.save()
            if result.rank=="STU":
                self._wizard.jumpPage("student")
            else:
                self._wizard.nextPage()

#-----------------------------------------------------------------------------

class FlightSelectionPage(Page):
    """The page to select the flight."""
    def __init__(self, wizard):
        """Construct the flight selection page."""
        help = xstr("flightsel_help")
        completedHelp = xstr("flightsel_chelp")
        super(FlightSelectionPage, self).__init__(wizard, "flightsel",
                                                  xstr("flightsel_title"),
                                                  help, completedHelp = completedHelp)

        mainBox = Gtk.HBox()
        mainBox.set_homogeneous(False)

        leftVBox = Gtk.VBox()

        alignment = Gtk.Alignment(xscale = 1.0)
        alignment.set_size_request(100, 0)

        leftVBox.pack_start(alignment, False, False, 0)

        mainBox.pack_start(leftVBox, True, True, 0)

        self._flightList = FlightList(popupMenuProducer =
                                      self._createListPopupMenu,
                                      widthRequest = 400)
        self._flightList.connect("row-activated", self._rowActivated)
        self._flightList.connect("selection-changed", self._selectionChanged)

        mainBox.pack_start(self._flightList, False, False, 8)

        flightButtonBox = Gtk.VBox()

        alignment = Gtk.Alignment(xscale = 1.0)
        alignment.set_size_request(100, 0)
        flightButtonBox.pack_start(alignment, False, False, 0)

        flightButtonWidthAlignment = Gtk.Alignment(xscale=1.0, yscale=0.0,
                                                   xalign=0.0, yalign=0.0)
        flightButtonWidthAlignment.set_padding(padding_top = 0,
                                               padding_bottom = 0,
                                               padding_left = 8,
                                               padding_right = 0)
        flightButtonWidthBox = Gtk.VBox()

        self._saveButton = Gtk.Button(xstr("flightsel_save"))
        self._saveButton.set_use_underline(True)
        self._saveButton.set_sensitive(False)
        self._saveButton.set_tooltip_text(xstr("flightsel_save_tooltip"))
        self._saveButton.connect("clicked", self._saveClicked)

        flightButtonWidthBox.pack_start(self._saveButton, True, True, 4)

        self._printButton = Gtk.Button(xstr("flightsel_print"))
        self._printButton.set_use_underline(True)
        self._printButton.set_sensitive(False)
        self._printButton.set_tooltip_text(xstr("flightsel_print_tooltip"))
        self._printButton.connect("clicked", self._printClicked)

        flightButtonWidthBox.pack_start(self._printButton, True, True, 4)

        self._deleteButton = Gtk.Button(xstr("flightsel_delete"))
        self._deleteButton.set_use_underline(True)
        self._deleteButton.set_sensitive(False)
        self._deleteButton.set_tooltip_text(xstr("flightsel_delete_tooltip"))
        self._deleteButton.connect("clicked", self._deleteClicked)

        flightButtonWidthBox.pack_start(self._deleteButton, True, True, 4)

        flightButtonWidthAlignment.add(flightButtonWidthBox)
        flightButtonBox.pack_start(flightButtonWidthAlignment, False, False, 0)

        mainBox.pack_start(flightButtonBox, True, True, 0)

        self.setMainWidget(mainBox)

        self._bookButton = self.addButton(xstr("flightsel_book"),
                                          sensitive = True,
                                          clicked = self._bookClicked,
                                          tooltip = xstr("flightsel_book_tooltip"))

        self._pendingButton = self.addButton(xstr("flightsel_pending"),
                                             sensitive = False,
                                             clicked = self._pendingClicked,
                                             tooltip = xstr("flightsel_pending_tooltip"))

        self._saveDialog = None

        self._refreshButton = self.addButton(xstr("flightsel_refresh"),
                                             sensitive = True,
                                             clicked = self._refreshClicked,
                                             tooltip = xstr("flightsel_refresh_tooltip"))

        self._loadButton = self.addButton(xstr("flightsel_load"),
                                          sensitive = True,
                                          tooltip = xstr("flightsel_load_tooltip"))
        self._loadButton.connect("clicked", self._loadButtonClicked)
        self._loadDialog = None

        self._button = self.addNextButton(sensitive = False,
                                          clicked =  self._forwardClicked)

        self._flights = []

        self._pendingFlightsWindow = PendingFlightsWindow(self._wizard)
        self._pendingFlightsWindowShown = False
        self._pendingFlightsWindow.connect("delete-event",
                                           self._deletePendingFlightsWindow)

        self._printSettings = None

    def activate(self):
        """Fill the flight list."""
        self._setupHelp()
        self._flightList.set_sensitive(True)
        self._loadButton.set_sensitive(True)
        self._refreshButton.set_sensitive(self._wizard.loggedIn)
        self._buildFlights()

    def finalize(self):
        """Finalize the page."""
        self._flightList.set_sensitive(False)
        self._loadButton.set_sensitive(False)
        self._refreshButton.set_sensitive(False)

    def _setupHelp(self):
        """Setup the help string"""
        help = ""

        if self._wizard.loggedIn:
            numReported = len(self._wizard.loginResult.reportedFlights)
            numRejected = len(self._wizard.loginResult.rejectedFlights)
            if numReported==0 and numRejected==0:
                help = xstr("flightsel_prehelp_nopending")
            elif numReported>0 and numRejected==0:
                help = xstr("flightsel_prehelp_rep_0rej") % (numReported,)
            elif numReported==0 and numRejected>0:
                help = xstr("flightsel_prehelp_0rep_rej") % (numRejected,)
            else:
                help = xstr("flightsel_prehelp_rep_rej") % \
                       (numReported, numRejected)

        help += xstr("flightsel_help")

        self.setHelp(help)

    def _buildFlights(self):
        """Rebuild the flights from the login result."""
        self._flights = []
        self._flightList.clear()
        self._pendingFlightsWindow.clear()
        loginResult = self._wizard.loginResult
        if self._wizard.loggedIn:
            for flight in loginResult.flights:
                self.addFlight(flight)
            for flight in loginResult.reportedFlights:
                self._pendingFlightsWindow.addReportedFlight(flight)
            for flight in loginResult.rejectedFlights:
                self._pendingFlightsWindow.addRejectedFlight(flight)

        self._updatePendingButton()

    def addFlight(self, flight):
        """Add the given file to the list of flights."""
        self._flights.append(flight)
        self._flightList.addFlight(flight)

    def _reflyFlight(self, flight):
        """Refly the given flight."""
        self.addFlight(flight)
        self._updatePending()

    def _updatePending(self):
        """Update the stuff depending on the set of pending flights."""
        self._setupHelp()
        self._updatePendingButton()

    def _bookClicked(self, button):
        """Called when the Book flights button is clicked."""
        self._wizard.gui.showTimetable()

    def _pendingClicked(self, button):
        """Called when the Pending flights button is clicked."""
        self._pendingFlightsWindow.show_all()
        self._pendingFlightsWindowShown = True
        self._updateNextButton()

    def _deletePendingFlightsWindow(self, window, event):
        """Called when the pending flights window is closed."""
        self._pendingFlightsWindow.hide()
        self._pendingFlightsWindowShown = False
        self._updateNextButton()
        return True

    def _saveClicked(self, button):
        """Called when the Save flight button is clicked."""
        self._saveSelected()

    def _saveSelected(self):
        """Save the selected flight."""
        flight = self._getSelectedFlight()
        date = flight.departureTime.date()
        name = "%04d-%02d-%02d %s %s-%s.vaflight" % \
               (date.year, date.month, date.day, flight.callsign,
                flight.departureICAO, flight.arrivalICAO)

        dialog = self._getSaveDialog()
        dialog.set_current_name(name)
        dialog.show_all()
        response = dialog.run()
        dialog.hide()

        if response==Gtk.ResponseType.OK:
            fileName = dialog.get_filename()
            print("Saving", fileName)
            try:
                with open(fileName, "wt") as f:
                    flight.writeIntoFile(f)
            except Exception as e:
                print("Failed to save flight:", util.utf2unicode(str(e)))
                dialog = Gtk.MessageDialog(parent = self._wizard.gui.mainWindow,
                                           type = Gtk.MessageType.ERROR,
                                           message_format =
                                           xstr("flightsel_save_failed"))
                dialog.add_button(xstr("button_ok"), Gtk.ResponseType.OK)
                dialog.set_title(WINDOW_TITLE_BASE)
                secondary = xstr("flightsel_save_failed_sec")
                dialog.format_secondary_markup(secondary)
                dialog.run()
                dialog.hide()

    def _printClicked(self, button):
        """Called when the Print briefing button is clicked."""
        self._printSelected()

    def _printSelected(self):
        """Print the briefing for the selected flight."""
        wizard = self._wizard
        flight = self._getSelectedFlight()

        printOperation = Gtk.PrintOperation()
        if self._printSettings is not None:
            printOperation.set_print_settings(self._printSettings)

        printOperation.set_n_pages(1)
        printOperation.set_show_progress(True)
        printOperation.connect("draw_page", self._drawBriefing)

        name = "MAVA Briefing %s %s %s" % (wizard.loginResult.pilotID,
                                           flight.callsign,
                                           flight.departureTime.strftime("%Y-%m-%d %H:%M"))
        printOperation.set_job_name(name)
        printOperation.set_export_filename(name)
        printOperation.set_use_full_page(False)

        result = printOperation.run(Gtk.PrintOperationAction.PRINT_DIALOG,
                                    wizard.gui.mainWindow)

        if result == Gtk.PrintOperationResult.APPLY:
            self._printSettings = printOperation.get_print_settings()
        elif result == Gtk.PrintOperationResult.ERROR:
            errorDialog(xstr("flightsel_print_failed",
                             wizard.gui.mainWindow,
                             secondary = printOperation.get_error()))

    def _drawBriefing(self, printOperation, context, pageNumber):
        """Draw the briefing."""
        wizard = self._wizard
        loginResult = wizard.loginResult
        flight=self._getSelectedFlight()

        print("DPI", context.get_dpi_x(), context.get_dpi_y())

        logoSurface = cairo.ImageSurface.create_from_png(
            os.path.join(wizard.gui.programDirectory, "mavalogo.png"))

        scale = context.get_dpi_x() / 72.0

        cr = context.get_cairo_context()

        cr.set_antialias(cairo.ANTIALIAS_GRAY)

        pcr = context.create_pango_context()

        delimiter = "*" * 70

        layout = Pango.Layout(pcr)

        font = Pango.FontDescription("Courier")
        font.set_size(int(12 * Pango.SCALE))
        font.set_weight(Pango.Weight.THIN)
        layout.set_font_description(font)

        fontBold = Pango.FontDescription("Courier")
        fontBold.set_size(int(12 * Pango.SCALE))
        fontBold.set_weight(Pango.Weight.BOLD)

        layout.set_text(delimiter)
        (_ink, logical) = layout.get_extents()
        width = logical.width / Pango.SCALE

        x0 = (context.get_width() - width)/2.0

        logoWidth = width / 3
        logoScale = logoSurface.get_width() / logoWidth

        y = 25 * scale

        source = cr.get_source()
        logoSurface.set_device_scale(logoScale, logoScale)
        cr.set_source_surface(logoSurface, x0, y)
        cr.rectangle(x0, y, logoSurface.get_width() / logoScale,
                     logoSurface.get_height() / logoScale)
        cr.fill()
        cr.set_source(source)

        y += logoSurface.get_height() / logoScale
        y += 12 * scale

        cr.move_to(x0, y)
        cr.set_line_width(0.1 * scale)
        PangoCairo.layout_path(cr, layout)
        cr.stroke_preserve()
        cr.fill()

        y += logical.height / Pango.SCALE
        y += 4 * scale

        layout.set_text("F L I G H T  B R I E F I N G  S H E E T")
        (_ink, logical) = layout.get_extents()
        width = logical.width / Pango.SCALE

        cr.move_to((context.get_width() - width)/2.0, y)
        cr.set_line_width(0.1 * scale)
        PangoCairo.layout_path(cr, layout)
        cr.stroke_preserve()
        cr.fill()

        y += logical.height / Pango.SCALE
        y += 4 * scale

        layout.set_text(delimiter)
        (_ink, logical) = layout.get_extents()
        width = logical.width / Pango.SCALE

        x2 = x0 + width * 0.4

        cr.move_to(x0, y)
        cr.set_line_width(0.1 * scale)
        PangoCairo.layout_path(cr, layout)
        cr.stroke_preserve()
        cr.fill()

        y += logical.height / Pango.SCALE
        y += 5 * scale

        layout.set_text("AIRCRAFT: ")
        layout.set_font_description(fontBold)
        (_ink, logical) = layout.get_extents()
        x1 = x0 + logical.width / Pango.SCALE

        layout.set_text("FLIGHT:")
        layout.set_font_description(fontBold)

        cr.move_to(x0, y)
        cr.set_line_width(0.1 * scale)
        PangoCairo.layout_path(cr, layout)
        cr.stroke_preserve()
        cr.fill()

        layout.set_text("%s %s-%s" % (flight.callsign,
                                      flight.departureICAO,
                                      flight.arrivalICAO))

        layout.set_font_description(font)

        cr.move_to(x1, y)
        cr.set_line_width(0.1 * scale)
        PangoCairo.layout_path(cr, layout)
        cr.stroke_preserve()
        cr.fill()

        layout.set_text("DATE:")
        layout.set_font_description(fontBold)
        (_ink, logical) = layout.get_extents()
        x3 = x2 + logical.width / Pango.SCALE

        cr.move_to(x2, y)
        cr.set_line_width(0.1 * scale)
        PangoCairo.layout_path(cr, layout)
        cr.stroke_preserve()
        cr.fill()

        layout.set_text(" %s" % (flight.date,))
        layout.set_font_description(font)

        cr.move_to(x3, y)
        cr.set_line_width(0.1 * scale)
        PangoCairo.layout_path(cr, layout)
        cr.stroke_preserve()
        cr.fill()

        layout.set_text("  %02d:%02d" % (flight.departureTime.hour,
                                         flight.departureTime.minute))
        (_ink, logical) = layout.get_extents()
        x5 = x0 + width - logical.width / Pango.SCALE
        cr.move_to(x5, y)
        cr.set_line_width(0.1 * scale)
        PangoCairo.layout_path(cr, layout)
        cr.stroke_preserve()
        cr.fill()

        layout.set_text("ETD (UTC):")
        layout.set_font_description(fontBold)
        (_ink, logical) = layout.get_extents()
        x4 = x5 - logical.width / Pango.SCALE
        cr.move_to(x4, y)
        cr.set_line_width(0.1 * scale)
        PangoCairo.layout_path(cr, layout)
        cr.stroke_preserve()
        cr.fill()

        y += logical.height / Pango.SCALE
        y += 4 * scale

        layout.set_text("AIRCRAFT:")
        layout.set_font_description(fontBold)
        cr.move_to(x0, y)
        cr.set_line_width(0.1 * scale)
        PangoCairo.layout_path(cr, layout)
        cr.stroke_preserve()
        cr.fill()

        layout.set_text(aircraftNames[flight.aircraftType].upper())
        layout.set_font_description(font)
        cr.move_to(x1, y)
        cr.set_line_width(0.1 * scale)
        PangoCairo.layout_path(cr, layout)
        cr.stroke_preserve()
        cr.fill()

        layout.set_text("  %02d:%02d" % (flight.arrivalTime.hour,
                                         flight.arrivalTime.minute))
        cr.move_to(x5, y)
        cr.set_line_width(0.1 * scale)
        PangoCairo.layout_path(cr, layout)
        cr.stroke_preserve()
        cr.fill()

        layout.set_text("ETA (UTC):")
        layout.set_font_description(fontBold)
        cr.move_to(x4, y)
        cr.set_line_width(0.1 * scale)
        PangoCairo.layout_path(cr, layout)
        cr.stroke_preserve()
        cr.fill()

        y += logical.height / Pango.SCALE
        y += 4 * scale

        layout.set_text("CREW:")
        layout.set_font_description(fontBold)
        cr.move_to(x0, y)
        cr.set_line_width(0.1 * scale)
        PangoCairo.layout_path(cr, layout)
        cr.stroke_preserve()
        cr.fill()

        layout.set_text("%d + %d" % (flight.numCockpitCrew,
                                     flight.numCabinCrew))
        layout.set_font_description(font)
        cr.move_to(x1, y)
        cr.set_line_width(0.1 * scale)
        PangoCairo.layout_path(cr, layout)
        cr.stroke_preserve()
        cr.fill()

        layout.set_text("DOW:")
        layout.set_font_description(fontBold)
        cr.move_to(x4, y)
        cr.set_line_width(0.1 * scale)
        PangoCairo.layout_path(cr, layout)
        cr.stroke_preserve()
        cr.fill()

        layout.set_text("%d KG" % (flight.dow,))
        layout.set_font_description(font)
        (_ink, logical) = layout.get_extents()
        x5 = x0 + width - logical.width / Pango.SCALE
        cr.move_to(x5, y)
        cr.set_line_width(0.1 * scale)
        PangoCairo.layout_path(cr, layout)
        cr.stroke_preserve()
        cr.fill()

        y += logical.height / Pango.SCALE
        y += logical.height / Pango.SCALE
        y += 4 * scale

        layout.set_text("PASSENGERS")
        layout.set_font_description(fontBold)
        cr.move_to(x0, y)
        cr.set_line_width(0.1 * scale)
        PangoCairo.layout_path(cr, layout)
        cr.stroke_preserve()
        cr.fill()

        layout.set_text("CARGO HOLDS")
        layout.set_font_description(fontBold)
        cr.move_to(x2, y)
        cr.set_line_width(0.1 * scale)
        PangoCairo.layout_path(cr, layout)
        cr.stroke_preserve()
        cr.fill()

        layout.set_text("TOTAL")
        layout.set_font_description(fontBold)
        cr.move_to(x4, y)
        cr.set_line_width(0.1 * scale)
        PangoCairo.layout_path(cr, layout)
        cr.stroke_preserve()
        cr.fill()

        y += logical.height / Pango.SCALE
        y += 4 * scale

        layout.set_text("CHILDREN:")
        layout.set_font_description(font)
        (_ink, logical) = layout.get_extents()
        x1 = x0 + logical.width / Pango.SCALE

        layout.set_text("CARGO:")
        layout.set_font_description(font)
        (_ink, logical) = layout.get_extents()
        x3 = x2 + logical.width / Pango.SCALE

        layout.set_text("ADULTS:")
        layout.set_font_description(font)
        cr.move_to(x0, y)
        cr.set_line_width(0.1 * scale)
        PangoCairo.layout_path(cr, layout)
        cr.stroke_preserve()
        cr.fill()

        layout.set_text(" %3d" % (flight.numPassengers,))
        layout.set_font_description(font)
        cr.move_to(x1, y)
        cr.set_line_width(0.1 * scale)
        PangoCairo.layout_path(cr, layout)
        cr.stroke_preserve()
        cr.fill()

        layout.set_text("BAGS:")
        layout.set_font_description(font)
        cr.move_to(x2, y)
        cr.set_line_width(0.1 * scale)
        PangoCairo.layout_path(cr, layout)
        cr.stroke_preserve()
        cr.fill()

        layout.set_text(" %5d KG" % (flight.bagWeight,))
        layout.set_font_description(font)
        cr.move_to(x3, y)
        cr.set_line_width(0.1 * scale)
        PangoCairo.layout_path(cr, layout)
        cr.stroke_preserve()
        cr.fill()

        y += logical.height / Pango.SCALE
        y += 4 * scale

        layout.set_text("CHILDREN:")
        layout.set_font_description(font)
        cr.move_to(x0, y)
        cr.set_line_width(0.1 * scale)
        PangoCairo.layout_path(cr, layout)
        cr.stroke_preserve()
        cr.fill()

        layout.set_text(" %3d" % (flight.numChildren,))
        layout.set_font_description(font)
        cr.move_to(x1, y)
        cr.set_line_width(0.1 * scale)
        PangoCairo.layout_path(cr, layout)
        cr.stroke_preserve()
        cr.fill()

        layout.set_text("MAIL:")
        layout.set_font_description(font)
        cr.move_to(x2, y)
        cr.set_line_width(0.1 * scale)
        PangoCairo.layout_path(cr, layout)
        cr.stroke_preserve()
        cr.fill()

        layout.set_text(" %5d KG" % (flight.mailWeight,))
        layout.set_font_description(font)
        cr.move_to(x3, y)
        cr.set_line_width(0.1 * scale)
        PangoCairo.layout_path(cr, layout)
        cr.stroke_preserve()
        cr.fill()

        layout.set_text("PAYLOAD:")
        layout.set_font_description(font)
        cr.move_to(x4, y)
        cr.set_line_width(0.1 * scale)
        PangoCairo.layout_path(cr, layout)
        cr.stroke_preserve()
        cr.fill()

        layout.set_text("%5d KG" % (flight.payload,))
        layout.set_font_description(font)
        (_ink, logical) = layout.get_extents()
        x5 = x0 + width - logical.width / Pango.SCALE
        cr.move_to(x5, y)
        cr.set_line_width(0.1 * scale)
        PangoCairo.layout_path(cr, layout)
        cr.stroke_preserve()
        cr.fill()

        y += logical.height / Pango.SCALE
        y += 4 * scale

        layout.set_text("INFANTS:")
        layout.set_font_description(font)
        cr.move_to(x0, y)
        cr.set_line_width(0.1 * scale)
        PangoCairo.layout_path(cr, layout)
        cr.stroke_preserve()
        cr.fill()

        layout.set_text(" %3d" % (flight.numInfants,))
        layout.set_font_description(font)
        cr.move_to(x1, y)
        cr.set_line_width(0.1 * scale)
        PangoCairo.layout_path(cr, layout)
        cr.stroke_preserve()
        cr.fill()

        layout.set_text("CARGO:")
        layout.set_font_description(font)
        cr.move_to(x2, y)
        cr.set_line_width(0.1 * scale)
        PangoCairo.layout_path(cr, layout)
        cr.stroke_preserve()
        cr.fill()

        layout.set_text(" %5d KG" % (flight.cargoWeight,))
        layout.set_font_description(font)
        cr.move_to(x3, y)
        cr.set_line_width(0.1 * scale)
        PangoCairo.layout_path(cr, layout)
        cr.stroke_preserve()
        cr.fill()

        layout.set_text("ZFW:")
        layout.set_font_description(font)
        cr.move_to(x4, y)
        cr.set_line_width(0.1 * scale)
        PangoCairo.layout_path(cr, layout)
        cr.stroke_preserve()
        cr.fill()

        layout.set_text("%5d KG" % (flight.dow + flight.payload,))
        layout.set_font_description(font)
        (_ink, logical) = layout.get_extents()
        x5 = x0 + width - logical.width / Pango.SCALE
        cr.move_to(x5, y)
        cr.set_line_width(0.1 * scale)
        PangoCairo.layout_path(cr, layout)
        cr.stroke_preserve()
        cr.fill()

        y += logical.height / Pango.SCALE
        y += logical.height / Pango.SCALE
        y += 4 * scale

        layout.set_text("ROUTE:")
        layout.set_font_description(fontBold)
        (_ink, logical) = layout.get_extents()
        x1 = x0 + logical.width / Pango.SCALE
        cr.move_to(x0, y)
        cr.set_line_width(0.1 * scale)
        PangoCairo.layout_path(cr, layout)
        cr.stroke_preserve()
        cr.fill()

        routeWords = flight.route.split(" ")
        layout.set_font_description(font)

        startWord = 0
        textWidth = width - (x1 - x0)
        while startWord<len(routeWords):
            endWord = startWord + 1
            while endWord<=len(routeWords):
                layout.set_text(" %s" % (" ".join(routeWords[startWord:endWord]),))
                (_ink, logical) = layout.get_extents()
                if textWidth<logical.width / Pango.SCALE:
                    endWord -= 1
                    if endWord<=startWord:
                        endWord = startWord + 1
                    break
                endWord += 1

            layout.set_text(" %s" % (" ".join(routeWords[startWord:endWord]),))
            cr.move_to(x1, y)
            cr.set_line_width(0.1 * scale)
            PangoCairo.layout_path(cr, layout)
            cr.stroke_preserve()
            cr.fill()

            startWord = endWord

            y += logical.height / Pango.SCALE
            y += 4 * scale

        y += logical.height / Pango.SCALE

        layout.set_text(delimiter)
        layout.set_font_description(font)
        cr.move_to(x0, y)
        cr.set_line_width(0.1 * scale)
        PangoCairo.layout_path(cr, layout)
        cr.stroke_preserve()
        cr.fill()

    def _deleteClicked(self, button):
        """Called when the Delete flight button is clicked."""
        self._deleteSelected()

    def _deleteSelected(self):
        """Delete the selected flight."""
        if askYesNo(xstr("flightsel_delete_confirm"),
                    parent = self._wizard.gui.mainWindow):
            flight = self._getSelectedFlight()
            gui = self._wizard.gui
            gui.beginBusy(xstr("flightsel_delete_busy"))

            gui.webHandler.deleteFlights(self._deleteResultCallback,
                                         [flight.id])

    def _deleteResultCallback(self, returned, result):
        """Called when the deletion result is available."""
        GObject.idle_add(self._handleDeleteResult, returned, result)

    def _handleDeleteResult(self, returned, result):
        """Handle the delete result."""
        gui = self._wizard.gui
        gui.endBusy()

        if returned:
            indexes = self._flightList.selectedIndexes

            flights = [self._flights[index] for index in indexes]

            self._flightList.removeFlights(indexes)
            for index in indexes[::-1]:
                del self._flights[index]
        else:
            communicationErrorDialog()


    def _refreshClicked(self, button):
        """Called when the refresh button is clicked."""
        self._wizard.reloadFlights(self._refreshCallback)

    def _refreshCallback(self, returned, result):
        """Callback for the refresh."""
        if returned:
            self._setupHelp()
            if result.loggedIn:
                self._buildFlights()

    def _selectionChanged(self, flightList, indexes):
        """Called when the selection is changed."""
        self._saveButton.set_sensitive(len(indexes)==1)
        self._printButton.set_sensitive(len(indexes)==1)
        self._deleteButton.set_sensitive(len(indexes)==1)
        self._updateNextButton()

    def _updatePendingButton(self):
        """Update the senstivity of the Pending button."""
        self._pendingButton.set_sensitive(self._pendingFlightsWindow.hasFlights)

    def _updateNextButton(self):
        """Update the sensitivity of the Next button."""
        sensitive = len(self._flightList.selectedIndexes)==1 and \
            len(self._flights)>0 and \
            not self._pendingFlightsWindowShown
        if sensitive:
            flight = self._getSelectedFlight()
            flightDate = datetime.datetime.strptime(flight.date, "%Y-%m-%d").date()
            tomorrow = datetime.date.today() + datetime.timedelta(days=1)
            print(flightDate, tomorrow)
            sensitive = flightDate <= tomorrow
        self._button.set_sensitive(sensitive)

    def _loadButtonClicked(self, loadButton):
        """Called when the load a flight button is clicked."""
        dialog = self._getLoadDialog()
        dialog.show_all()
        response = dialog.run()
        dialog.hide()

        if response==Gtk.ResponseType.OK:
            fileName = dialog.get_filename()
            print("Loading", fileName)
            bookedFlight = web.BookedFlight()
            try:
                with open(fileName, "rt") as f:
                    bookedFlight.readFromFile(f, self._wizard._loginResult.fleet)
                self.addFlight(bookedFlight)
            except Exception as e:
                print("Failed to load flight:", util.utf2unicode(str(e)))
                dialog = Gtk.MessageDialog(parent = self._wizard.gui.mainWindow,
                                           type = Gtk.MessageType.ERROR,
                                           message_format =
                                           xstr("flightsel_load_failed"))
                dialog.add_button(xstr("button_ok"), Gtk.ResponseType.OK)
                dialog.set_title(WINDOW_TITLE_BASE)
                secondary = xstr("flightsel_load_failed_sec")
                dialog.format_secondary_markup(secondary)
                dialog.run()
                dialog.hide()

    def _forwardClicked(self, button):
        """Called when the forward button was clicked."""
        if self._completed:
            self._wizard.jumpPage(self._nextID, finalize = False)
        else:
            self._flightSelected()

    def _rowActivated(self, flightList, index):
        """Called when a row is activated."""
        if not self._completed:
            self._flightSelected()

    def _flightSelected(self):
        """Called when a flight has been selected."""
        flight = self._getSelectedFlight()
        self._wizard._bookedFlight = flight
        self._wizard.gui.enableFlightInfo(flight.aircraftType)

        self._updateDepartureGate()

    def _getSelectedFlight(self):
        """Get the currently selected flight."""
        indexes = self._flightList.selectedIndexes
        assert(len(indexes)==1)
        return self._flights[indexes[0]]

    def _updateDepartureGate(self):
        """Update the departure gate for the booked flight."""
        flight = self._wizard._bookedFlight
        if self._wizard.gui.config.onlineGateSystem and \
           self._wizard.loggedIn and not self._wizard.entranceExam:
            if flight.departureICAO=="LHBP":
                self._wizard.getFleet(self._fleetRetrieved)
            else:
                self._wizard.updatePlane(self._planeUpdated,
                                         flight.tailNumber,
                                         const.PLANE_AWAY)
        else:
            self._nextID = "connect"
            self._wizard.jumpPage("connect")

    def _fleetRetrieved(self, fleet):
        """Called when the fleet has been retrieved."""
        if fleet is None:
            self._nextID = "connect"
            self._wizard.jumpPage("connect")
        else:
            plane = fleet[self._wizard._bookedFlight.tailNumber]
            if plane is None:
                self._nextID = "connect"
                self._wizard.jumpPage("connect")
            elif plane.gateNumber is not None and \
                 not fleet.isGateConflicting(plane):
                self._wizard._departureGate = plane.gateNumber
                self._nextID = "connect"
                self._wizard.jumpPage("connect")
            else:
                self._nextID = "gatesel"
                self._wizard.jumpPage("gatesel")

    def _planeUpdated(self, success):
        """Callback for the plane updating."""
        self._nextID = "connect"
        self._wizard.jumpPage("connect")

    def _getSaveDialog(self):
        """Get the dialog to load a flight file."""
        if self._saveDialog is not None:
            return self._saveDialog

        gui = self._wizard.gui
        dialog = Gtk.FileChooserDialog(title = WINDOW_TITLE_BASE + " - " +
                                       xstr("flightsel_save_title"),
                                       action = Gtk.FileChooserAction.SAVE,
                                       buttons = (Gtk.STOCK_CANCEL,
                                                  Gtk.ResponseType.CANCEL,
                                                  Gtk.STOCK_OK, Gtk.ResponseType.OK),
                                       parent = gui.mainWindow)
        dialog.set_modal(True)
        dialog.set_do_overwrite_confirmation(True)

        filter = Gtk.FileFilter()
        filter.set_name(xstr("flightsel_filter_flights"))
        filter.add_pattern("*.vaflight")
        dialog.add_filter(filter)

        filter = Gtk.FileFilter()
        filter.set_name(xstr("file_filter_all"))
        filter.add_pattern("*.*")
        dialog.add_filter(filter)

        self._saveDialog = dialog

        return dialog

    def _getLoadDialog(self):
        """Get the dialog to load a flight file."""
        if self._loadDialog is not None:
            return self._loadDialog

        gui = self._wizard.gui
        dialog = Gtk.FileChooserDialog(title = WINDOW_TITLE_BASE + " - " +
                                       xstr("flightsel_load_title"),
                                       action = Gtk.FileChooserAction.OPEN,
                                       buttons = (Gtk.STOCK_CANCEL,
                                                  Gtk.ResponseType.CANCEL,
                                                  Gtk.STOCK_OK, Gtk.ResponseType.OK),
                                       parent = gui.mainWindow)
        dialog.set_modal(True)

        filter = Gtk.FileFilter()
        filter.set_name(xstr("flightsel_filter_flights"))
        filter.add_pattern("*.vaflight")
        dialog.add_filter(filter)

        filter = Gtk.FileFilter()
        filter.set_name(xstr("file_filter_all"))
        filter.add_pattern("*.*")
        dialog.add_filter(filter)

        self._loadDialog = dialog

        return dialog

    def _createListPopupMenu(self):
        """Get the flight list popup menu."""
        menu = Gtk.Menu()

        menuItem = Gtk.MenuItem()
        menuItem.set_label(xstr("flightsel_popup_select"))
        menuItem.set_use_underline(True)
        menuItem.connect("activate", self._popupSelect)
        menuItem.show()

        menu.append(menuItem)

        menuItem = Gtk.MenuItem()
        menuItem.set_label(xstr("flightsel_popup_save"))
        menuItem.set_use_underline(True)
        menuItem.connect("activate", self._popupSave)
        menuItem.show()

        menu.append(menuItem)

        menuItem = Gtk.MenuItem()
        menuItem.set_label(xstr("flightsel_popup_print"))
        menuItem.set_use_underline(True)
        menuItem.connect("activate", self._popupPrint)
        menuItem.show()

        menu.append(menuItem)

        menuItem = Gtk.MenuItem()
        menuItem.set_label(xstr("flightsel_popup_delete"))
        menuItem.set_use_underline(True)
        menuItem.connect("activate", self._popupDelete)
        menuItem.show()

        menu.append(menuItem)

        return menu

    def _popupSelect(self, menuItem):
        """Called when the Select menu item is activated in the popup menu."""
        if not self._completed:
            self._flightSelected()

    def _popupSave(self, menuItem):
        """Called when the Save menu item is activated in the popup menu."""
        if not self._completed:
            self._saveSelected()

    def _popupPrint(self, menuItem):
        """Called when the Print briefing menu item is activated in the popup menu."""
        if not self._completed:
            self._printSelected()

    def _popupDelete(self, menuItem):
        """Called when the Delete menu item is activated in the popup menu."""
        if not self._completed:
            self._deleteSelected()

#-----------------------------------------------------------------------------

class GateSelectionPage(Page):
    """Page to select a free gate at LHBP.
    This page should be displayed only if we have fleet information!."""
    def __init__(self, wizard):
        """Construct the gate selection page."""
        super(GateSelectionPage, self).__init__(wizard, "gatesel",
                                                xstr("gatesel_title"),
                                                xstr("gatesel_help"))

        self._listStore = Gtk.ListStore(str)
        self._gateList = Gtk.TreeView(self._listStore)
        column = Gtk.TreeViewColumn(None, Gtk.CellRendererText(),
                                    text = 0)
        column.set_expand(True)
        self._gateList.append_column(column)
        self._gateList.set_headers_visible(False)
        self._gateList.connect("row-activated", self._rowActivated)

        gateSelection = self._gateList.get_selection()
        gateSelection.connect("changed", self._selectionChanged)

        scrolledWindow = Gtk.ScrolledWindow()
        scrolledWindow.add(self._gateList)
        scrolledWindow.set_size_request(50, -1)
        scrolledWindow.set_policy(Gtk.PolicyType.AUTOMATIC,
                                  Gtk.PolicyType.AUTOMATIC)
        scrolledWindow.set_shadow_type(Gtk.ShadowType.IN)

        alignment = Gtk.Alignment(xalign = 0.5, yalign = 0.0, xscale = 0.0, yscale = 1.0)
        alignment.add(scrolledWindow)

        self.setMainWidget(alignment)

        self.addCancelFlightButton()

        self.addPreviousButton(clicked = self._backClicked)

        self._button = self.addNextButton(sensitive = False,
                                          clicked = self._forwardClicked)

    def activate(self):
        """Fill the gate list."""
        self._listStore.clear()
        self._gateList.set_sensitive(True)
        occupiedGateNumbers = self._wizard._fleet.getOccupiedGateNumbers()
        for gate in lhbpGates.gates:
            if gate.isAvailable(lhbpGates, occupiedGateNumbers):
                self._listStore.append([gate.number])

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
            self._gateSelected()
        else:
            self._wizard.jumpPage("connect")

    def _rowActivated(self, flightList, path, column):
        """Called when a row is activated."""
        if not self._completed:
            self._gateSelected()

    def _gateSelected(self):
        """Called when a gate has been selected."""
        selection = self._gateList.get_selection()
        (listStore, iter) = selection.get_selected()
        (gateNumber,) = listStore.get(iter, 0)

        self._wizard._departureGate = gateNumber

        self._wizard.updatePlane(self._planeUpdated,
                                 self._wizard._bookedFlight.tailNumber,
                                 const.PLANE_HOME, gateNumber)

    def _planeUpdated(self, success):
        """Callback for the plane updating call."""
        if success is None or success:
            self._wizard.jumpPage("connect")
        else:
            dialog = Gtk.MessageDialog(parent = self._wizard.gui.mainWindow,
                                       type = Gtk.MessageType.ERROR,
                                       message_format = xstr("gatesel_conflict"))
            dialog.add_button(xstr("button_ok"), Gtk.ResponseType.OK)
            dialog.set_title(WINDOW_TITLE_BASE)
            dialog.format_secondary_markup(xstr("gatesel_conflict_sec"))
            dialog.run()
            dialog.hide()

            self._wizard.getFleet(self._fleetRetrieved)

    def _fleetRetrieved(self, fleet):
        """Called when the fleet has been retrieved."""
        if fleet is None:
            self._wizard.jumpPage("connect")
        else:
            self.activate()

#-----------------------------------------------------------------------------

class RegisterPage(Page):
    """A page to enter the registration data."""

    # The minimal year of birth
    _minYearOfBirth = 1900

    # The maximal year of birth
    _maxYearOfBirth = datetime.date.today().year

    # The regular expression to check the e-mail address with
    _emailAddressRE = re.compile("[^@]+@[^@]+\.[^@]+")

    def __init__(self, wizard):
        """Construct the registration page."""
        super(RegisterPage, self).__init__(wizard, "register",
                                           xstr("register_title"),
                                           xstr("register_help"))

        alignment = Gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)

        table = Gtk.Table(12, 4)
        table.set_row_spacings(4)
        table.set_col_spacings(24)
        alignment.add(table)
        self.setMainWidget(alignment)

        row = 0

        labelAlignment = Gtk.Alignment(xalign = 1.0, yalign = 0.5,
                                       xscale = 0.0, yscale = 0.0)
        label = Gtk.Label(xstr("register_name1"))
        label.set_use_underline(True)
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, row, row+1)

        self._name1 = Gtk.Entry()
        self._name1.connect("changed", self._updateButtons)
        self._name1.set_tooltip_text(xstr("register_name1_tooltip"))
        self._name1.set_width_chars(15)
        table.attach(self._name1, 1, 2, row, row+1)
        label.set_mnemonic_widget(self._name1)

        labelAlignment = Gtk.Alignment(xalign = 1.0, yalign = 0.5,
                                       xscale = 0.0, yscale = 0.0)
        label = Gtk.Label(xstr("register_name2"))
        label.set_use_underline(True)
        labelAlignment.add(label)
        table.attach(labelAlignment, 2, 3, row, row+1)

        self._name2 = Gtk.Entry()
        self._name2.connect("changed", self._updateButtons)
        self._name2.set_tooltip_text(xstr("register_name2_tooltip"))
        self._name2.set_width_chars(15)
        table.attach(self._name2, 3, 4, row, row+1)
        label.set_mnemonic_widget(self._name2)

        row += 1

        labelAlignment = Gtk.Alignment(xalign = 1.0, yalign = 0.5,
                                       xscale = 0.0, yscale = 0.0)
        label = Gtk.Label(xstr("register_year_of_birth"))
        label.set_use_underline(True)
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, row, row+1)

        alignment = Gtk.Alignment(xalign = 0.0, yalign = 0.0,
                                  xscale = 0.0, yscale = 0.0)

        self._yearOfBirth = Gtk.SpinButton()
        self._yearOfBirth.set_increments(step = 1, page = 10)
        self._yearOfBirth.set_range(min = RegisterPage._minYearOfBirth,
                                    max = RegisterPage._maxYearOfBirth)
        self._yearOfBirth.set_numeric(True)
        self._yearOfBirth.set_tooltip_text(xstr("register_year_of_birth_tooltip"))
        self._yearOfBirth.set_width_chars(5)
        self._yearOfBirth.connect("changed", self._updateButtons)
        self._yearOfBirth.connect("value-changed", self._updateButtons)
        alignment.add(self._yearOfBirth)
        table.attach(alignment, 1, 2, row, row+1)
        label.set_mnemonic_widget(self._yearOfBirth)

        row += 1

        labelAlignment = Gtk.Alignment(xalign = 1.0, yalign = 0.5,
                                       xscale = 0.0, yscale = 0.0)
        label = Gtk.Label(xstr("register_email"))
        label.set_use_underline(True)
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, row, row+1)

        self._emailAddress = Gtk.Entry()
        self._emailAddress.connect("changed", self._updateButtons)
        self._emailAddress.set_tooltip_text(xstr("register_email_tooltip"))
        table.attach(self._emailAddress, 1, 2, row, row+1)
        label.set_mnemonic_widget(self._emailAddress)

        self._emailAddressPublic = Gtk.CheckButton(xstr("register_email_public"))
        self._emailAddressPublic.set_use_underline(True)
        self._emailAddressPublic.set_tooltip_text(xstr("register_email_public_tooltip"))
        table.attach(self._emailAddressPublic, 2, 4, row, row+1)

        row += 1

        labelAlignment = Gtk.Alignment(xalign = 1.0, yalign = 0.5,
                                       xscale = 0.0, yscale = 0.0)
        label = Gtk.Label(xstr("register_vatsim_id"))
        label.set_use_underline(True)
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, row, row+1)

        alignment = Gtk.Alignment(xalign = 0.0, yalign = 0.0,
                                  xscale = 0.0, yscale = 0.0)
        self._vatsimID = IntegerEntry()
        self._vatsimID.connect("changed", self._updateButtons)
        self._vatsimID.set_tooltip_text(xstr("register_vatsim_id_tooltip"))
        self._vatsimID.set_width_chars(7)
        alignment.add(self._vatsimID)
        table.attach(alignment, 1, 2, row, row+1)
        label.set_mnemonic_widget(self._vatsimID)

        labelAlignment = Gtk.Alignment(xalign = 0.0, yalign = 0.5,
                                       xscale = 0.0, yscale = 0.0)
        label = Gtk.Label(xstr("register_ivao_id"))
        label.set_use_underline(True)
        labelAlignment.add(label)
        table.attach(labelAlignment, 2, 3, row, row+1)

        alignment = Gtk.Alignment(xalign = 0.0, yalign = 0.0,
                                  xscale = 0.0, yscale = 0.0)
        self._ivaoID = IntegerEntry()
        self._ivaoID.connect("changed", self._updateButtons)
        self._ivaoID.set_tooltip_text(xstr("register_ivao_id_tooltip"))
        self._ivaoID.set_width_chars(7)
        alignment.add(self._ivaoID)
        table.attach(alignment, 3, 4, row, row+1)
        label.set_mnemonic_widget(self._ivaoID)

        row += 1

        labelAlignment = Gtk.Alignment(xalign = 1.0, yalign = 0.5,
                                       xscale = 0.0, yscale = 0.0)
        label = Gtk.Label(xstr("register_phone_num"))
        label.set_use_underline(True)
        label.set_use_markup(True)
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, row, row+1)

        self._phoneNumber = Gtk.Entry()
        self._phoneNumber.set_tooltip_text(xstr("register_phone_num_tooltip"))
        table.attach(self._phoneNumber, 1, 2, row, row+1)
        label.set_mnemonic_widget(self._phoneNumber)

        row += 1

        labelAlignment = Gtk.Alignment(xalign = 1.0, yalign = 0.5,
                                       xscale = 0.0, yscale = 0.0)
        label = Gtk.Label(xstr("register_nationality"))
        label.set_use_underline(True)
        label.set_use_markup(True)
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, row, row+1)


        self._nationality = Gtk.Entry()
        self._nationality.set_tooltip_text(xstr("register_nationality_tooltip"))
        table.attach(self._nationality, 1, 2, row, row+1)
        label.set_mnemonic_widget(self._nationality)

        placeholder = Gtk.Label()
        placeholder.set_text(xstr("register_password_mismatch"))
        placeholder.set_use_markup(True)
        placeholder.set_child_visible(False)
        placeholder.hide()
        table.attach(placeholder, 2, 4, row, row+1)

        row += 1

        labelAlignment = Gtk.Alignment(xalign = 1.0, yalign = 0.5,
                                       xscale = 0.0, yscale = 0.0)
        label = Gtk.Label(xstr("register_password"))
        label.set_use_underline(True)
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, row, row+1)

        self._password = Gtk.Entry()
        self._password.set_visibility(False)
        self._password.connect("changed", self._updateButtons)
        self._password.set_tooltip_text(xstr("register_password_tooltip"))
        table.attach(self._password, 1, 2, row, row+1)
        label.set_mnemonic_widget(self._password)

        alignment = Gtk.Alignment(xalign = 0.0, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)
        self._passwordStatus = Gtk.Label()
        alignment.add(self._passwordStatus)
        table.attach(alignment, 2, 4, row, row+1)

        row += 1

        labelAlignment = Gtk.Alignment(xalign = 1.0, yalign = 0.5,
                                       xscale = 0.0, yscale = 0.0)
        label = Gtk.Label(xstr("register_password2"))
        label.set_use_underline(True)
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, row, row+1)

        self._password2 = Gtk.Entry()
        self._password2.set_visibility(False)
        self._password2.connect("changed", self._updateButtons)
        self._password2.set_tooltip_text(xstr("register_password2_tooltip"))
        table.attach(self._password2, 1, 2, row, row+1)
        label.set_mnemonic_widget(self._password2)

        alignment = Gtk.Alignment(xalign = 0.0, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)
        self._password2Status = Gtk.Label()
        alignment.add(self._password2Status)
        table.attach(alignment, 2, 4, row, row+1)

        row += 1

        self._rememberButton = Gtk.CheckButton(xstr("remember_password"))
        self._rememberButton.set_use_underline(True)
        self._rememberButton.set_tooltip_text(xstr("login_remember_tooltip"))
        table.attach(self._rememberButton, 1, 3, row, row+1)

        cancelButton = \
          self.addButton(xstr("button_cancel"))
        cancelButton.connect("clicked", self._cancelClicked)

        self._registerButton = \
          self.addButton(xstr("button_register"), default = True,
                              tooltip = xstr("button_register_tooltip"))
        self._registerButton.connect("clicked", self._registerClicked)

        self._updateButtons()

    @property
    def name1(self):
        """Get the first name component entered."""
        return self._name1.get_text()

    @property
    def name2(self):
        """Get the second name component entered."""
        return self._name2.get_text()

    @property
    def yearOfBirth(self):
        """Get the year of birth."""
        yearOfBirthText = self._yearOfBirth.get_text()
        return int(yearOfBirthText) if yearOfBirthText else 0

    @property
    def emailAddress(self):
        """Get the e-mail address."""
        return self._emailAddress.get_text()

    @property
    def emailAddressPublic(self):
        """Get the whether the e-mail address is public."""
        return self._emailAddressPublic.get_active()

    @property
    def vatsimID(self):
        """Get the VATSIM ID."""
        return self._vatsimID.get_int()

    @property
    def ivaoID(self):
        """Get the IVAO ID."""
        return self._ivaoID.get_int()

    @property
    def phoneNumber(self):
        """Get the phone number."""
        return self._phoneNumber.get_text()

    @property
    def nationality(self):
        """Get the nationality."""
        return self._nationality.get_text()

    @property
    def password(self):
        """Get the password."""
        return self._password.get_text()

    @property
    def rememberPassword(self):
        """Get whether the password should be remembered."""
        return self._rememberButton.get_active()

    def activate(self):
        """Setup the route from the booked flight."""
        self._yearOfBirth.set_value(0)
        self._yearOfBirth.set_text("")
        self._updateButtons()

    def _updateButtons(self, widget = None):
        """Update the sensitive state of the buttons"""
        yearOfBirth = self.yearOfBirth

        emailAddress = self.emailAddress
        emailAddressMatch = RegisterPage._emailAddressRE.match(emailAddress)

        vatsimID = self.vatsimID
        ivaoID = self.ivaoID

        password = self.password
        password2 = self._password2.get_text()
        if not password:
            self._passwordStatus.set_text("")
        elif len(password)<5:
            self._passwordStatus.set_text(xstr("register_password_too_short"))
        else:
            self._passwordStatus.set_text(xstr("register_password_ok"))
        self._passwordStatus.set_use_markup(True)

        if len(password)<5 or not password2:
            self._password2Status.set_text("")
        elif password!=password2:
            self._password2Status.set_text(xstr("register_password_mismatch"))
        else:
            self._password2Status.set_text(xstr("register_password_ok"))
        self._password2Status.set_use_markup(True)

        sensitive = \
            len(self.name1)>0 and len(self.name2)>0 and \
            yearOfBirth>=RegisterPage._minYearOfBirth and \
            yearOfBirth<=RegisterPage._maxYearOfBirth and \
            emailAddressMatch is not None and \
            (vatsimID>=800000 or ivaoID>=100000) and \
            len(password)>=5 and password==password2

        self._registerButton.set_sensitive(sensitive)

    def _cancelClicked(self, button):
        """Called when the Cancel button is clicked."""
        self.goBack()

    def _registerClicked(self, button):
        """Called when the Register button is clicked."""
        nameOrder = xstr("register_nameorder")

        if nameOrder=="eastern":
            surName = self.name1
            firstName = self.name2
        else:
            surName = self.name2
            firstName = self.name1

        nationality = self.nationality.lower()

        if getLanguage().lower()=="hu" or nationality.find("hung")!=-1 or \
           nationality.find("magyar")!=-1:
            requestedNameOrder = "eastern"
        else:
            requestedNameOrder = "western"

        registrationData = web.Registration(surName, firstName,
                                            requestedNameOrder,
                                            self.yearOfBirth,
                                            self.emailAddress,
                                            self.emailAddressPublic,
                                            self.vatsimID, self.ivaoID,
                                            self.phoneNumber, self.nationality,
                                            self.password)
        print("Registering with data:")
        print("  name:", self.name1, self.name2, registrationData.firstName, registrationData.surName, requestedNameOrder)
        print("  yearOfBirth:", self.yearOfBirth, registrationData.yearOfBirth)
        print("  emailAddress:", self.emailAddress, registrationData.emailAddress)
        print("  emailAddressPublic:", self.emailAddressPublic, registrationData.emailAddressPublic)
        print("  vatsimID:", self.vatsimID, registrationData.vatsimID)
        print("  ivaoID:", self.ivaoID, registrationData.ivaoID)
        print("  phoneNumber:", self.phoneNumber, registrationData.phoneNumber)
        print("  nationality:", self.nationality, registrationData.nationality)

        gui = self._wizard.gui
        gui.beginBusy(xstr("register_busy"))
        gui.webHandler.register(self._registerResultCallback, registrationData)

    def _registerResultCallback(self, returned, result):
        """Called when the registration result is available."""
        GObject.idle_add(self._handleRegisterResult, returned, result)

    def _handleRegisterResult(self, returned, result):
        """Handle the registration result."""
        gui = self._wizard.gui

        gui.endBusy()

        print("Registration result:")
        print("  returned:", returned)
        if returned:
            print("  registered:", result.registered)
            if result.registered:
                print("  pilotID", result.pilotID)
                print("  loggedIn", result.loggedIn)
            print("  emailAlreadyRegistered:", result.emailAlreadyRegistered)
            print("  invalidData:", result.invalidData)

        registrationOK = returned and result.registered

        message = xstr("register_ok") if registrationOK \
                  else xstr("register_failed")
        secondaryMessage = None
        if registrationOK:
            if result.loggedIn:
                secondaryMessage = xstr("register_info") % (result.pilotID,)
            else:
                secondaryMessage = xstr("register_nologin") % (result.pilotID,)
            messageType = Gtk.MessageType.INFO

            config = gui.config
            config.pilotID = result.pilotID
            config.rememberPassword = self.rememberPassword
            if config.rememberPassword:
                config.password = self.password
            else:
                config.password = ""

            config.save()
        elif returned and result.emailAlreadyRegistered:
            secondaryMessage = xstr("register_email_already")
            messageType = Gtk.MessageType.ERROR
        elif returned and result.invalidData:
            secondaryMessage = xstr("register_invalid_data")
            messageType = Gtk.MessageType.ERROR
        else:
            secondaryMessage = xstr("register_error")
            messageType = Gtk.MessageType.ERROR

        dialog = Gtk.MessageDialog(parent = gui.mainWindow,
                                   type = messageType,
                                   message_format = message)
        dialog.set_title(WINDOW_TITLE_BASE + " - " +
                         xstr("register_result_title"))
        dialog.format_secondary_markup(secondaryMessage)

        dialog.add_button(xstr("button_ok"), 0)

        dialog.run()
        dialog.hide()

        if registrationOK:
            if result.loggedIn:
                self._wizard._loginResult = result
                self._wizard.nextPage()
            else:
                self._wizard.jumpPage("login")

#-----------------------------------------------------------------------------

class StudentPage(Page):
    """A page displayed to students after logging in."""
    _entryExamStatusQueryInterval = 60*1000

    def __init__(self, wizard):
        """Construct the student page."""
        super(StudentPage, self).__init__(wizard, "student",
                                          xstr("student_title"),
                                          xstr("student_help"))


        self._getEntryExamStatusCancelled = False

        alignment = Gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 0.5, yscale = 0.0)

        table = Gtk.Table(6, 4)
        table.set_row_spacings(4)
        table.set_col_spacings(0)
        table.set_homogeneous(False)
        alignment.add(table)
        self.setMainWidget(alignment)

        row = 0

        labelAlignment = Gtk.Alignment(xalign=0.0, yalign = 0.5,
                                       xscale=0.0, yscale = 0.0)
        label = Gtk.Label(xstr("student_entry_exam_status"))
        label.set_alignment(0.0, 0.5)
        labelAlignment.add(label)
        labelAlignment.resize_children()
        table.attach(labelAlignment, 0, 1, row, row + 1,
                     xoptions = Gtk.AttachOptions.FILL)

        alignment = Gtk.Alignment(xalign=0.0, yalign = 0.5,
                                  xscale=1.0, yscale = 0.0)
        self._entryExamStatus = Gtk.Label()
        self._entryExamStatus.set_use_markup(True)
        self._entryExamStatus.set_alignment(0.0, 0.5)
        alignment.add(self._entryExamStatus)
        alignment.resize_children()
        table.attach(alignment, 1, 4, row, row + 1)

        row += 1

        buttonAlignment = Gtk.Alignment(xalign=0.0, xscale=1.0)
        button = self._entryExamButton = Gtk.Button(xstr("student_entry_exam"))
        button.set_use_underline(True)
        button.connect("clicked", self._entryExamClicked)
        button.set_tooltip_text(xstr("student_entry_exam_tooltip"))

        buttonAlignment.add(button)
        table.attach(buttonAlignment, 0, 4, row, row + 1,
                     xoptions = Gtk.AttachOptions.FILL,
                     ypadding = 4)

        row += 3

        labelAlignment = Gtk.Alignment(xalign=0.0, yalign = 0.5,
                                       xscale=0.0, yscale = 0.0)
        label = Gtk.Label(xstr("student_check_flight_status"))
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, row, row + 1,
                     xoptions = Gtk.AttachOptions.FILL)

        alignment = Gtk.Alignment(xalign=0.0, yalign = 0.5,
                                  xscale=1.0, yscale = 0.0)
        self._checkFlightStatus = Gtk.Label()
        self._checkFlightStatus.set_use_markup(True)
        self._checkFlightStatus.set_alignment(0.0, 0.5)
        alignment.add(self._checkFlightStatus)
        table.attach(alignment, 1, 4, row, row + 1)

        row += 1

        alignment = Gtk.Alignment(xalign=0.0, xscale=1.0)

        hbox = Gtk.HBox()
        hbox.set_homogeneous(False)
        hbox.set_spacing(0)

        aircraftTypesModel = Gtk.ListStore(str, int)
        for aircraftType in web.BookedFlight.checkFlightTypes:
            aircraftTypesModel.append([aircraftNames[aircraftType],
                                       aircraftType])

        aircraftTypeAlignment = Gtk.Alignment(xalign = 0.0, xscale = 1.0)

        self._aircraftType = Gtk.ComboBox(model = aircraftTypesModel)
        renderer = Gtk.CellRendererText()
        self._aircraftType.pack_start(renderer, True)
        self._aircraftType.add_attribute(renderer, "text", 0)
        self._aircraftType.set_tooltip_text(xstr("student_check_flight_type_tooltip"))
        self._aircraftType.set_active(0)

        aircraftTypeAlignment.add(self._aircraftType)

        hbox.pack_start(aircraftTypeAlignment, False, False, 0)

        buttonAlignment = Gtk.Alignment(xalign=0.0, xscale=1.0)
        button = self._checkFlightButton = Gtk.Button(xstr("student_check_flight"))
        button.set_use_underline(True)
        button.connect("clicked", self._checkFlightClicked)
        button.set_tooltip_text(xstr("student_check_flight_tooltip"))

        hbox.pack_start(button, True, True, 0)

        alignment.add(hbox)
        table.attach(alignment, 0, 4, row, row + 1,
                     xoptions = Gtk.AttachOptions.FILL)

    @property
    def aircraftType(self):
        """Get the type of the aircraft used to perform the check flight."""
        index = self._aircraftType.get_active()
        return self._aircraftType.get_model()[index][1]

    def activate(self):
        """Activate the student page."""
        print("StudentPage.activate")
        self._getEntryExamStatusCancelled = False

        loginResult = self._wizard.loginResult
        self._entryExamLink = loginResult.entryExamLink

        self._updateEntryExamStatus(loginResult.entryExamPassed)
        self._getEntryExamStatus()

        # FIXME: call with real value
        self._updateCheckFlightStatus(self._wizard.loginResult.checkFlightStatus)

    def finalize(self):
        """Finalize the page."""
        print("StudentPage.finalize")
        self._getEntryExamStatusCancelled = True

    def _entryExamClicked(self, button):
        """Called when the entry exam button is clicked."""
        webbrowser.open(self._entryExamLink)

    def _getEntryExamStatus(self):
        """Initiate the query of the entry exam status after the interval."""
        if not self._getEntryExamStatusCancelled:
            GObject.timeout_add(StudentPage._entryExamStatusQueryInterval,
                                lambda: self._wizard.gui.webHandler. \
                                getEntryExamStatus(self._entryExamStatusCallback))

    def _entryExamStatusCallback(self, returned, result):
        """Called when the entry exam status is available."""
        GObject.idle_add(self._handleEntryExamStatus, returned, result)

    def _handleEntryExamStatus(self, returned, result):
        """Called when the entry exam status is availabe."""
        print("_handleEntryExamStatus", returned, result)
        if returned and not self._getEntryExamStatusCancelled:
            self._entryExamLink = result.entryExamLink
            self._updateEntryExamStatus(result.entryExamPassed)
            if result.madeFO:
                self._madeFO()
            else:
                self._getEntryExamStatus()

    def _updateEntryExamStatus(self, passed):
        """Update the entry exam status display and button."""
        self._entryExamStatus.set_text(xstr("student_entry_exam_passed")
                                       if passed else
                                       xstr("student_entry_exam_not_passed"))
        self._entryExamStatus.set_use_markup(True)
        self._entryExamButton.set_sensitive(not passed)
        self._wizard._loginResult.entryExamPassed = passed

    def _checkFlightClicked(self, button):
        """Called when the check flight button is clicked."""
        aircraftType = self.aircraftType
        self._wizard._bookedFlight = \
            web.BookedFlight.forCheckFlight(aircraftType)
        self._wizard.gui.enableFlightInfo(aircraftType)
        self._wizard.jumpPage("connect")

    def _updateCheckFlightStatus(self, passed):
        """Update the status of the check flight."""
        self._aircraftType.set_sensitive(not passed)
        self._checkFlightStatus.set_text(xstr("student_check_flight_passed")
                                         if passed else
                                         xstr("student_check_flight_not_passed"))
        self._checkFlightStatus.set_use_markup(True)
        self._checkFlightButton.set_sensitive(not passed)

    def _madeFO(self):
        """Handle the event when the pilot has become a first officer."""
        wizard = self._wizard
        loginResult = wizard.loginResult
        loginResult.rank = "FO"

        gui = wizard.gui

        dialog = Gtk.MessageDialog(parent = gui.mainWindow,
                                   type = Gtk.MessageType.INFO,
                                   message_format = xstr("student_fo"))

        dialog.add_button(xstr("button_ok"), Gtk.ResponseType.OK)
        dialog.set_title(WINDOW_TITLE_BASE)
        secondary = xstr("student_fo_secondary")
        dialog.format_secondary_markup(secondary)
        dialog.run()
        dialog.hide()

        gui.reset()

#-----------------------------------------------------------------------------

class ConnectPage(Page):
    """Page which displays the departure airport and gate (if at LHBP)."""
    def __init__(self, wizard):
        """Construct the connect page."""
        help = "Load the aircraft below into the simulator and park it\n" \
               "at the given airport, at the gate below, if present.\n\n" \
               "Then press the Connect button to connect to the simulator."
        completedHelp = "The basic data of your flight can be read below."
        super(ConnectPage, self).__init__(wizard, "connect",
                                          xstr("connect_title"),
                                          xstr("connect_help"),
                                          completedHelp = xstr("connect_chelp"))

        self._selectSimulator = os.name=="nt" or "FORCE_SELECT_SIM" in os.environ

        alignment = Gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)

        table = Gtk.Table(7 if self._selectSimulator else 5, 2)
        table.set_row_spacings(4)
        table.set_col_spacings(16)
        table.set_homogeneous(True)
        alignment.add(table)
        self.setMainWidget(alignment)

        labelAlignment = Gtk.Alignment(xalign=1.0, xscale=0.0)
        label = Gtk.Label(xstr("connect_flightno"))
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, 0, 1)

        labelAlignment = Gtk.Alignment(xalign=0.0, xscale=0.0)
        self._flightNumber = Gtk.Label()
        self._flightNumber.set_width_chars(9)
        self._flightNumber.set_alignment(0.0, 0.5)
        labelAlignment.add(self._flightNumber)
        table.attach(labelAlignment, 1, 2, 0, 1)

        labelAlignment = Gtk.Alignment(xalign=1.0, xscale=0.0)
        label = Gtk.Label(xstr("connect_acft"))
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, 1, 2)

        labelAlignment = Gtk.Alignment(xalign=0.0, xscale=0.0)
        self._aircraft = Gtk.Label()
        self._aircraft.set_width_chars(25)
        self._aircraft.set_alignment(0.0, 0.5)
        labelAlignment.add(self._aircraft)
        table.attach(labelAlignment, 1, 2, 1, 2)

        labelAlignment = Gtk.Alignment(xalign=1.0, xscale=0.0)
        label = Gtk.Label(xstr("connect_tailno"))
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, 2, 3)

        labelAlignment = Gtk.Alignment(xalign=0.0, xscale=0.0)
        self._tailNumber = Gtk.Label()
        self._tailNumber.set_width_chars(10)
        self._tailNumber.set_alignment(0.0, 0.5)
        labelAlignment.add(self._tailNumber)
        table.attach(labelAlignment, 1, 2, 2, 3)

        labelAlignment = Gtk.Alignment(xalign=1.0, xscale=0.0)
        label = Gtk.Label(xstr("connect_airport"))
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, 3, 4)

        labelAlignment = Gtk.Alignment(xalign=0.0, xscale=0.0)
        self._departureICAO = Gtk.Label()
        self._departureICAO.set_width_chars(6)
        self._departureICAO.set_alignment(0.0, 0.5)
        labelAlignment.add(self._departureICAO)
        table.attach(labelAlignment, 1, 2, 3, 4)

        labelAlignment = Gtk.Alignment(xalign=1.0, xscale=0.0)
        label = Gtk.Label(xstr("connect_gate"))
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, 4, 5)

        labelAlignment = Gtk.Alignment(xalign=0.0, xscale=0.0)
        self._departureGate = Gtk.Label()
        self._departureGate.set_width_chars(5)
        self._departureGate.set_alignment(0.0, 0.5)
        labelAlignment.add(self._departureGate)
        table.attach(labelAlignment, 1, 2, 4, 5)

        if self._selectSimulator:
            labelAlignment = Gtk.Alignment(xalign=1.0, xscale=0.0, yalign=0.5)
            label = Gtk.Label(xstr("connect_sim"))
            labelAlignment.add(label)
            table.attach(labelAlignment, 0, 1, 5, 7)

            selectAlignment = Gtk.Alignment(xalign=0.0, xscale=0.0, yalign=0.5)

            selectBox = Gtk.HBox()
            self._selectMSFS = \
                Gtk.RadioButton.new_with_mnemonic_from_widget(None,
                                                              xstr("connect_sim_msfs"))

            selectBox.pack_start(self._selectMSFS, False, False, 0);

            self._selectXPlane = \
                Gtk.RadioButton.new_with_mnemonic_from_widget(self._selectMSFS,
                                                              xstr("connect_sim_xplane"))

            selectBox.pack_start(self._selectXPlane, False, False, 8);

            selectAlignment.add(selectBox)
            table.attach(selectAlignment, 1, 2, 5, 7)


        self.addCancelFlightButton()

        self._previousButton = \
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

        aircraftType = aircraftNames[bookedFlight.aircraftType]
        self._aircraft.set_markup("<b>" + aircraftType + "</b>")

        self._tailNumber.set_markup("<b>" + bookedFlight.tailNumber + "</b>")

        icao = bookedFlight.departureICAO
        self._departureICAO.set_markup("<b>" + icao + "</b>")
        gate = self._wizard._departureGate
        if gate!="-":
            gate = "<b>" + gate + "</b>"
        self._departureGate.set_markup(gate)

        if self._selectSimulator:
            config = self._wizard.gui.config
            self._selectMSFS.set_active(config.defaultMSFS)
            self._selectXPlane.set_active(not config.defaultMSFS)

        self._previousButton.set_sensitive(not self._wizard.entranceExam)

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
        if self._selectSimulator:
            simulatorType = const.SIM_MSFS9 if self._selectMSFS.get_active() \
                                            else const.SIM_XPLANE10
        else:
            simulatorType = const.SIM_MSFS9 if os.name=="nt" \
              else const.SIM_XPLANE10

        config = self._wizard.gui.config
        config.defaultMSFS = simulatorType == const.SIM_MSFS9
        config.save()

        self._wizard._connectSimulator(simulatorType)

    def _forwardClicked(self, button):
        """Called when the Forward button is pressed."""
        self._wizard.nextPage()

#-----------------------------------------------------------------------------

class PayloadPage(Page):
    """Page to allow setting up the payload."""
    def __init__(self, wizard):
        """Construct the page."""
        super(PayloadPage, self).__init__(wizard, "payload",
                                          xstr("payload_title"),
                                          xstr("payload_help") + "\n\n \n \n",
                                          completedHelp = xstr("payload_chelp"))

        alignment = Gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)

        table = Gtk.Table(7, 3)
        table.set_row_spacings(4)
        table.set_col_spacings(16)
        table.set_homogeneous(False)
        alignment.add(table)
        self.setMainWidget(alignment)

        self._crewLabel = label = Gtk.Label(xstr("payload_crew"))
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, 0, 1)

        self._numCockpitCrew = Gtk.Label()

        self._numCabinCrew = IntegerEntry(defaultValue = 0)
        self._numCabinCrew.set_width_chars(6)
        self._numCabinCrew.connect("integer-changed", self._weightChanged)
        self._numCabinCrew.set_tooltip_text(xstr("payload_crew_tooltip"))

        crewBox = Gtk.HBox()
        crewBox.pack_start(self._numCockpitCrew, False, False, 0)
        crewBox.pack_start(Gtk.Label("+"), False, False, 4)
        crewBox.pack_start(self._numCabinCrew, False, False, 0)
        crewBox.set_halign(Gtk.Align.END)

        table.attach(crewBox, 1, 2, 0, 1)
        label.set_mnemonic_widget(self._numCabinCrew)

        label = Gtk.Label(xstr("payload_crew_info"))
        label.set_halign(Gtk.Align.START)
        table.attach(label, 2, 3, 0, 1)

        self._paxLabel = label = Gtk.Label(xstr("payload_pax"))
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, 1, 2)

        self._numPassengers = IntegerEntry(defaultValue = 0)
        self._numPassengers.set_width_chars(6)
        self._numPassengers.connect("integer-changed", self._weightChanged)
        self._numPassengers.set_tooltip_text(xstr("payload_pax_tooltip"))

        self._numChildren = IntegerEntry(defaultValue = 0)
        self._numChildren.set_width_chars(6)
        self._numChildren.connect("integer-changed", self._weightChanged)
        self._numChildren.set_tooltip_text(xstr("payload_pax_children_tooltip"))

        self._numInfants = IntegerEntry(defaultValue = 0)
        self._numInfants.set_width_chars(6)
        self._numInfants.connect("integer-changed", self._weightChanged)
        self._numInfants.set_tooltip_text(xstr("payload_pax_infants_tooltip"))

        paxBox = Gtk.HBox()
        paxBox.pack_start(self._numPassengers, False, False, 0)
        paxBox.pack_start(Gtk.Label("+"), False, False, 4)
        paxBox.pack_start(self._numChildren, False, False, 0)
        paxBox.pack_start(Gtk.Label("+"), False, False, 4)
        paxBox.pack_start(self._numInfants, False, False, 0)

        table.attach(paxBox, 1, 2, 1, 2)
        label.set_mnemonic_widget(self._numPassengers)

        label = Gtk.Label(xstr("payload_pax_info"))
        label.set_halign(Gtk.Align.START)
        table.attach(label, 2, 3, 1, 2)

        label = Gtk.Label(xstr("payload_bag"))
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, 2, 3)

        self._bagWeight = IntegerEntry(defaultValue = 0)
        self._bagWeight.set_width_chars(6)
        self._bagWeight.connect("integer-changed", self._weightChanged)
        self._bagWeight.set_tooltip_text(xstr("payload_bag_tooltip"))
        self._bagWeight.set_hexpand(False)
        self._bagWeight.set_halign(Gtk.Align.END)
        table.attach(self._bagWeight, 1, 2, 2, 3)
        label.set_mnemonic_widget(self._bagWeight)

        label = Gtk.Label("kg")
        label.set_halign(Gtk.Align.START)
        table.attach(label, 2, 3, 2, 3)

        label = Gtk.Label(xstr("payload_cargo"))
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, 3, 4)

        self._cargoWeight = IntegerEntry(defaultValue = 0)
        self._cargoWeight.set_width_chars(6)
        self._cargoWeight.connect("integer-changed", self._weightChanged)
        self._cargoWeight.set_tooltip_text(xstr("payload_cargo_tooltip"))
        self._cargoWeight.set_hexpand(False)
        self._cargoWeight.set_halign(Gtk.Align.END)
        table.attach(self._cargoWeight, 1, 2, 3, 4)
        label.set_mnemonic_widget(self._cargoWeight)

        label = Gtk.Label("kg")
        label.set_halign(Gtk.Align.START)
        table.attach(label, 2, 3, 3, 4)

        label = Gtk.Label(xstr("payload_mail"))
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, 4, 5)

        self._mailWeight = IntegerEntry(defaultValue = 0)
        self._mailWeight.set_width_chars(6)
        self._mailWeight.connect("integer-changed", self._weightChanged)
        self._mailWeight.set_tooltip_text(xstr("payload_mail_tooltip"))
        self._mailWeight.set_hexpand(False)
        self._mailWeight.set_halign(Gtk.Align.END)
        table.attach(self._mailWeight, 1, 2, 4, 5)
        label.set_mnemonic_widget(self._mailWeight)

        label = Gtk.Label("kg")
        label.set_halign(Gtk.Align.START)
        table.attach(label, 2, 3, 4, 5)

        label = Gtk.Label("<b>" + xstr("payload_zfw") + "</b>")
        label.set_alignment(0.0, 0.5)
        label.set_use_markup(True)
        table.attach(label, 0, 1, 5, 6)

        self._calculatedZFW = Gtk.Label()
        self._calculatedZFW.set_width_chars(6)
        self._calculatedZFW.set_alignment(1.0, 0.5)
        table.attach(self._calculatedZFW, 1, 2, 5, 6)

        label = Gtk.Label("kg")
        label.set_halign(Gtk.Align.START)
        table.attach(label, 2, 3, 5, 6)

        self._zfwButton = Gtk.Button(xstr("payload_fszfw"))
        self._zfwButton.set_use_underline(True)
        self._zfwButton.connect("clicked", self._zfwRequested)
        self._zfwButton.set_tooltip_text(xstr("payload_fszfw_tooltip"))
        table.attach(self._zfwButton, 0, 1, 6, 7)

        self._simulatorZFW = Gtk.Label("-")
        self._simulatorZFW.set_width_chars(6)
        self._simulatorZFW.set_alignment(1.0, 0.5)
        table.attach(self._simulatorZFW, 1, 2, 6, 7)
        self._simulatorZFWValue = None

        label = Gtk.Label("kg")
        label.set_halign(Gtk.Align.START)
        table.attach(label, 2, 3, 6, 7)

        self.addCancelFlightButton()
        self._backButton = self.addPreviousButton(clicked = self._backClicked)
        self._button = self.addNextButton(clicked = self._forwardClicked)

    @property
    def numCockpitCrew(self):
        """The number of the cockpit crew members on the flight."""
        return self._wizard._bookedFlight.numCockpitCrew

    @property
    def numCabinCrew(self):
        """The number of the cabin members on the flight."""
        return self._numCabinCrew.get_int()

    @property
    def numPassengers(self):
        """The number of the adult passengers on the flight."""
        return self._numPassengers.get_int()

    @property
    def numChildren(self):
        """The number of the child passengers on the flight."""
        return self._numChildren.get_int()

    @property
    def numInfants(self):
        """The number of the infant passengers on the flight."""
        return self._numInfants.get_int()

    @property
    def bagWeight(self):
        """Get the bag weight entered."""
        return self._bagWeight.get_int()

    @property
    def cargoWeight(self):
        """Get the cargo weight entered."""
        return self._cargoWeight.get_int()

    @property
    def mailWeight(self):
        """Get the bag weight entered."""
        return self._mailWeight.get_int()

    def activate(self):
        """Setup the information."""
        bookedFlight = self._wizard._bookedFlight

        self._numCockpitCrew.set_markup("<b>" +
                                        str(bookedFlight.numCockpitCrew) +
                                        "</b>")
        self._numCabinCrew.set_int(bookedFlight.numCabinCrew)
        self._numCabinCrew.set_sensitive(True)


        self._numPassengers.set_int(bookedFlight.numPassengers)
        self._numPassengers.set_sensitive(True)

        self._numChildren.set_int(bookedFlight.numChildren)
        self._numChildren.set_sensitive(True)

        self._numInfants.set_int(bookedFlight.numInfants)
        self._numInfants.set_sensitive(True)

        self._bagWeight.set_int(bookedFlight.bagWeight)
        self._bagWeight.set_sensitive(True)

        if bookedFlight.flightType==const.FLIGHTTYPE_CHARTER:
            self._cargoWeight.set_int(0)
            self._cargoWeight.set_sensitive(False)
            self._mailWeight.set_int(0)
            self._mailWeight.set_sensitive(False)
        else:
            self._cargoWeight.set_int(bookedFlight.cargoWeight)
            self._cargoWeight.set_sensitive(True)
            self._mailWeight.set_int(bookedFlight.mailWeight)
            self._mailWeight.set_sensitive(True)

        self._simulatorZFW.set_text("-")
        self._simulatorZFWValue = None
        self._zfwButton.set_sensitive(True)
        self._updateCalculatedZFW()

    def finalize(self):
        """Finalize the payload page."""
        self._numCabinCrew.set_sensitive(False)
        self._numPassengers.set_sensitive(False)
        self._numChildren.set_sensitive(False)
        self._numInfants.set_sensitive(False)
        self._bagWeight.set_sensitive(False)
        self._cargoWeight.set_sensitive(False)
        self._mailWeight.set_sensitive(False)
        self._wizard.gui.initializeWeightHelp()

    def calculateZFW(self):
        """Calculate the ZFW value."""
        bookedFlight = self._wizard._bookedFlight

        zfw = bookedFlight.dow
        zfw += (self._numCabinCrew.get_int() - bookedFlight.dowNumCabinCrew) *  \
            const.WEIGHT_CABIN_CREW
        zfw += self._numPassengers.get_int() * \
            (const.WEIGHT_PASSENGER_CHARTER
             if bookedFlight.flightType==const.FLIGHTTYPE_CHARTER
             else const.WEIGHT_PASSENGER)
        zfw += self._numChildren.get_int() * const.WEIGHT_CHILD
        zfw += self._numInfants.get_int() * const.WEIGHT_INFANT
        zfw += self._bagWeight.get_int()
        zfw += self._cargoWeight.get_int()
        zfw += self._mailWeight.get_int()
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

    def _weightChanged(self, entry, weight):
        """Called when one of the weight values or humanm counts has
        changed."""
        bookedFlight = self._wizard._bookedFlight
        numPassengers = \
            self._numPassengers.get_int() + \
            self._numChildren.get_int() + \
            self._numInfants.get_int()
        minCabinCrew = 0 if numPassengers==0 else \
            (bookedFlight.maxPassengers // 50) + 1

        extraHelp = []
        enoughCrew = self._numCabinCrew.get_int() >= minCabinCrew
        if enoughCrew:
            self._crewLabel.set_text(xstr("payload_crew"))
            self.setHelp(xstr("payload_help"))
        else:
            self._crewLabel.set_markup("<b><span foreground=\"red\">" +
                                       xstr("payload_crew") +
                                       "</span></b>")
            extraHelp.append(xstr("payload_help_few_crew") % (minCabinCrew,))
        self._crewLabel.set_use_underline(True)

        tooManyPassengers = numPassengers>bookedFlight.maxPassengers
        if tooManyPassengers:
            self._paxLabel.set_markup("<b><span foreground=\"red\">" +
                                      xstr("payload_pax") +
                                      "</span></b>")
            extraHelp.append(xstr("payload_help_many_pax") % (bookedFlight.maxPassengers,))
        else:
            self._paxLabel.set_text(xstr("payload_pax"))
        self._paxLabel.set_use_underline(True)

        hlp = xstr("payload_help") + "\n\n"
        for eh in extraHelp:
            hlp += "<b><span foreground=\"red\">" + eh + "</span></b>\n"
        hlp += " \n" * (2-len(extraHelp))
        self.setHelp(hlp)

        self._button.set_sensitive(enoughCrew and not tooManyPassengers)


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
        GObject.idle_add(self._processZFW, zfw)

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
        super(TimePage, self).__init__(wizard, "time",
                                       xstr("time_title"),
                                       xstr("time_help"),
                                       completedHelp = xstr("time_chelp"))

        alignment = Gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)

        table = Gtk.Table(3, 2)
        table.set_row_spacings(4)
        table.set_col_spacings(16)
        table.set_homogeneous(False)
        alignment.add(table)
        self.setMainWidget(alignment)

        label = Gtk.Label(xstr("time_departure"))
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, 0, 1)

        self._departure = Gtk.Label()
        self._departure.set_alignment(0.0, 0.5)
        table.attach(self._departure, 1, 2, 0, 1)

        label = Gtk.Label(xstr("time_arrival"))
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, 1, 2)

        self._arrival = Gtk.Label()
        self._arrival.set_alignment(0.0, 0.5)
        table.attach(self._arrival, 1, 2, 1, 2)

        self._timeButton = Gtk.Button(xstr("time_fs"))
        self._timeButton.set_use_underline(True)
        self._timeButton.set_tooltip_text(xstr("time_fs_tooltip"))
        self._timeButton.connect("clicked", self._timeRequested)
        table.attach(self._timeButton, 0, 1, 2, 3)

        self._simulatorTime = Gtk.Label("-")
        self._simulatorTime.set_alignment(0.0, 0.5)
        table.attach(self._simulatorTime, 1, 2, 2, 3)

        self.addCancelFlightButton()

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
        GObject.idle_add(self._processTime, timestamp)

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

            gui.simulator.getFuel(self._handleFuel)
        else:
            self._wizard.nextPage()

    def _handleFuel(self, fuelData):
        """Callback for the fuel query operation."""
        GObject.idle_add(self._processFuel, fuelData)

    def _processFuel(self, fuelData):
        """Process the given fuel data."""
        self._wizard.gui.endBusy()
        self._wizard._fuelData = fuelData
        self._wizard.nextPage()

#-----------------------------------------------------------------------------

class RoutePage(Page):
    """The page containing the route and the flight level."""
    def __init__(self, wizard):
        """Construct the page."""
        super(RoutePage, self).__init__(wizard, "route",
                                        xstr("route_title"),
                                        xstr("route_help"),
                                        completedHelp = xstr("route_chelp"))

        alignment = Gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)

        mainBox = Gtk.VBox()
        alignment.add(mainBox)
        self.setMainWidget(alignment)

        levelBox = Gtk.HBox()

        label = Gtk.Label(xstr("route_level"))
        label.set_use_underline(True)
        levelBox.pack_start(label, True, True, 0)

        self._cruiseLevel = Gtk.SpinButton()
        self._cruiseLevel.set_increments(step = 10, page = 100)
        self._cruiseLevel.set_range(min = 0, max = 500)
        self._cruiseLevel.set_tooltip_text(xstr("route_level_tooltip"))
        self._cruiseLevel.set_numeric(True)
        self._cruiseLevel.connect("changed", self._cruiseLevelChanged)
        self._cruiseLevel.connect("value-changed", self._cruiseLevelChanged)
        label.set_mnemonic_widget(self._cruiseLevel)

        levelBox.pack_start(self._cruiseLevel, False, False, 8)

        alignment = Gtk.Alignment(xalign = 0.0, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)
        alignment.add(levelBox)

        mainBox.pack_start(alignment, False, False, 0)


        routeBox = Gtk.VBox()

        alignment = Gtk.Alignment(xalign = 0.0, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)
        label = Gtk.Label(xstr("route_route"))
        label.set_use_underline(True)
        alignment.add(label)
        routeBox.pack_start(alignment, True, True, 0)

        routeWindow = Gtk.ScrolledWindow()
        routeWindow.set_size_request(400, 80)
        routeWindow.set_shadow_type(Gtk.ShadowType.IN)
        routeWindow.set_policy(Gtk.PolicyType.AUTOMATIC,
                               Gtk.PolicyType.AUTOMATIC)

        self._uppercasingRoute = False

        self._route = Gtk.TextView()
        self._route.set_tooltip_text(xstr("route_route_tooltip"))
        self._route.set_wrap_mode(Gtk.WrapMode.WORD)
        self._route.get_buffer().connect("changed", self._routeChanged)
        self._route.get_buffer().connect_after("insert-text", self._routeInserted)
        routeWindow.add(self._route)

        label.set_mnemonic_widget(self._route)
        routeBox.pack_start(routeWindow, True, True, 0)

        mainBox.pack_start(routeBox, True, True, 8)

        alternateBox = Gtk.HBox()

        label = Gtk.Label(xstr("route_altn"))
        label.set_use_underline(True)
        alternateBox.pack_start(label, True, True, 0)

        self._alternate = Gtk.Entry()
        self._alternate.set_width_chars(6)
        self._alternate.connect("changed", self._alternateChanged)
        self._alternate.set_tooltip_text(xstr("route_altn_tooltip"))
        label.set_mnemonic_widget(self._alternate)

        alternateBox.pack_start(self._alternate, False, False, 8)

        alignment = Gtk.Alignment(xalign = 0.0, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)
        alignment.add(alternateBox)

        mainBox.pack_start(alignment, False, False, 0)

        self.addCancelFlightButton()

        self._backButton = self.addPreviousButton(clicked = self._backClicked)
        self._button = self.addNextButton(clicked = self._forwardClicked)

    @property
    def filedCruiseLevel(self):
        """Get the filed cruise level."""
        return self._cruiseLevel.get_value_as_int()

    @filedCruiseLevel.setter
    def filedCruiseLevel(self, fl):
        """Set the filed cruise level."""
        self._cruiseLevel.set_value(fl)

    @property
    def route(self):
        """Get the route."""
        return self._getRoute()

    @route.setter
    def route(self, r):
        """Set the route."""
        self._route.get_buffer().set_text(r)

    @property
    def alternate(self):
        """Get the ICAO code of the alternate airport."""
        return self._alternate.get_text()

    @alternate.setter
    def alternate(self, a):
        """Set the ICAO code of the alternate airport."""
        self._alternate.set_text(a)

    def activate(self):
        """Setup the route from the booked flight."""
        self._cruiseLevel.set_value(0)
        self._cruiseLevel.set_text("")
        self._route.get_buffer().set_text(self._wizard._bookedFlight.route)
        self._alternate.set_text("")
        self._updateForwardButton()

    def _getRoute(self):
        """Get the text of the route."""
        buffer = self._route.get_buffer()
        return buffer.get_text(buffer.get_start_iter(),
                               buffer.get_end_iter(), True)

    def _updateForwardButton(self):
        """Update the sensitivity of the forward button."""
        flight = self._wizard.gui.flight
        useSimBrief = \
            flight is not None and flight.aircraft.simBriefData is not None and \
            self._wizard.gui.config.useSimBrief and \
            self._wizard.usingSimBrief is not False

        cruiseLevelText = self._cruiseLevel.get_text()
        cruiseLevel = int(cruiseLevelText) if cruiseLevelText else 0

        alternate = self._alternate.get_text()
        if useSimBrief:
            self._button.set_sensitive((len(alternate)==0 or len(alternate)==4
                                        or self._wizard.entranceExam) and
                                       (cruiseLevel==0 or cruiseLevel>=50))
        else:
            cruiseLevelText = self._cruiseLevel.get_text()
            cruiseLevel = int(cruiseLevelText) if cruiseLevelText else 0
            self._button.set_sensitive(cruiseLevel>=50 and self._getRoute()!="" and
                                       (len(alternate)==4 or self._wizard.entranceExam))

    def _cruiseLevelChanged(self, *arg):
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

    def _alternateChanged(self, entry):
        """Called when the alternate airport has changed."""
        entry.set_text(entry.get_text().upper())
        self._updateForwardButton()

    def _backClicked(self, button):
        """Called when the Back button is pressed."""
        self.goBack()

    def _forwardClicked(self, button):
        """Called when the Forward button is clicked."""
        if self._wizard.gui.flight.aircraft.simBriefData is None:
            self._wizard.usingSimBrief = False
        if self._wizard.gui.config.useSimBrief and \
           self._wizard.usingSimBrief is not False:
            self._wizard.jumpPage("simbrief_setup")
        else:
            self._wizard.usingSimBrief = False
            self._wizard.jumpPage("fuel")

#-----------------------------------------------------------------------------

class SimBriefCredentialsDialog(Gtk.Dialog):
    """A dialog window to ask for SimBrief credentials."""
    def __init__(self, gui, userName, password, rememberPassword):
        """Construct the dialog."""
        super(SimBriefCredentialsDialog, self).__init__(WINDOW_TITLE_BASE + " - " +
                                                        xstr("simbrief_credentials_title"),
                                                        gui.mainWindow,
                                                        Gtk.DialogFlags.MODAL)
        self.add_button(xstr("button_cancel"), Gtk.ResponseType.CANCEL)
        self.add_button(xstr("button_ok"), Gtk.ResponseType.OK)

        contentArea = self.get_content_area()

        contentAlignment = Gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                         xscale = 0.0, yscale = 0.0)
        contentAlignment.set_padding(padding_top = 4, padding_bottom = 16,
                                     padding_left = 8, padding_right = 8)

        contentArea.pack_start(contentAlignment, False, False, 0)

        contentVBox = Gtk.VBox()
        contentAlignment.add(contentVBox)

        label = Gtk.Label(xstr("simbrief_login_failed"))
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

        label = Gtk.Label(xstr("simbrief_username"))
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, 0, 1)

        self._userName = Gtk.Entry()
        self._userName.set_width_chars(16)
        #self._userName.connect("changed",
        #                       lambda button: self._updateForwardButton())
        self._userName.set_tooltip_text(xstr("simbrief_username_tooltip"))
        self._userName.set_text(userName)
        table.attach(self._userName, 1, 2, 0, 1)
        label.set_mnemonic_widget(self._userName)

        label = Gtk.Label(xstr("simbrief_password"))
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, 1, 2)

        self._password = Gtk.Entry()
        self._password.set_visibility(False)
        #self._password.connect("changed",
        #                       lambda button: self._updateForwardButton())
        self._password.set_tooltip_text(xstr("simbrief_password_tooltip"))
        self._password.set_text(password)
        table.attach(self._password, 1, 2, 1, 2)
        label.set_mnemonic_widget(self._password)

        self._rememberButton = Gtk.CheckButton(xstr("simbrief_remember_password"))
        self._rememberButton.set_use_underline(True)
        self._rememberButton.set_tooltip_text(xstr("simbrief_remember_tooltip"))
        self._rememberButton.set_active(rememberPassword)
        table.attach(self._rememberButton, 1, 2, 2, 3, ypadding = 8)

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
        return self._rememberButton.get_active()

    def run(self):
        """Run the dialog."""
        self.show_all()

        response = super(SimBriefCredentialsDialog, self).run()

        self.hide()

        return response

#-----------------------------------------------------------------------------

class SimBriefSetupPage(Page):
    """Page for setting up some parameters for SimBrief."""
    monthNum2Name = [
        "JAN",
        "FEB",
        "MAR",
        "APR",
        "MAY",
        "JUN",
        "JUL",
        "AUG",
        "SEP",
        "OCT",
        "NOV",
        "DEC"
        ]

    progress2Message = {
        cef.SIMBRIEF_PROGRESS_SEARCHING_BROWSER: "simbrief_progress_searching_browser",
        cef.SIMBRIEF_PROGRESS_LOADING_FORM: "simbrief_progress_loading_form",
        cef.SIMBRIEF_PROGRESS_FILLING_FORM: "simbrief_progress_filling_form",
        cef.SIMBRIEF_PROGRESS_WAITING_LOGIN: "simbrief_progress_waiting_login",
        cef.SIMBRIEF_PROGRESS_LOGGING_IN: "simbrief_progress_logging_in",
        cef.SIMBRIEF_PROGRESS_WAITING_RESULT: "simbrief_progress_waiting_result",
        cef.SIMBRIEF_PROGRESS_RETRIEVING_BRIEFING: "simbrief_progress_retrieving_briefing"
        }

    result2Message = {
        cef.SIMBRIEF_RESULT_ERROR_OTHER: "simbrief_result_error_other",
        cef.SIMBRIEF_RESULT_ERROR_NO_FORM: "simbrief_result_error_no_form",
        cef.SIMBRIEF_RESULT_ERROR_NO_POPUP: "simbrief_result_error_no_popup",
        cef.SIMBRIEF_RESULT_ERROR_LOGIN_FAILED: "simbrief_result_error_login_failed"
        }

    _resultQueryInterval = 2000

    _waitTimeout = 2 * 60.0

    @staticmethod
    def getHTMLFilePath():
        """Get the path of the HTML file to contain the generated flight
        plan."""
        if os.name=="nt":
            return os.path.join(tempfile.gettempdir(),
                                "mlx_simbrief" +
                                (".secondary" if secondaryInstallation else "") +
                                ".html")
        else:
            import pwd
            return os.path.join(tempfile.gettempdir(),
                                "mlx_simbrief." + pwd.getpwuid(os.getuid())[0] + "" +
                                (".secondary" if secondaryInstallation else "") +
                                ".html")

    def __init__(self, wizard):
        """Construct the setup page."""

        super(SimBriefSetupPage, self).__init__(wizard, "simbrief_setup",
                                                xstr("simbrief_setup_title"),
                                                xstr("simbrief_setup_help"),
                                                xstr("simbrief_setup_chelp"))

        alignment = Gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)

        table = Gtk.Table(7, 3)
        table.set_row_spacings(4)
        table.set_col_spacings(16)
        table.set_homogeneous(False)
        alignment.add(table)
        self.setMainWidget(alignment)


        row = 0

        frame = Gtk.Frame.new()
        self._useInternalBrowser = Gtk.CheckButton(xstr("simbrief_uib"))
        frame.set_label_widget(self._useInternalBrowser)
        frame.set_label_align(0.025, 0.5)

        self._useInternalBrowser.set_use_underline(True)
        self._useInternalBrowser.connect("toggled",
                                         self._useInternalBrowserToggled)
        self._useInternalBrowser.set_tooltip_text(xstr("simbrief_uib_tooltip"))

        uibTable = Gtk.Table(2, 3)
        uibTable.set_row_spacings(4)
        uibTable.set_col_spacings(16)
        uibTable.set_homogeneous(False)

        uibRow = 0

        label = Gtk.Label(xstr("simbrief_username"))
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        uibTable.attach(label, 0, 1, uibRow, uibRow+1)

        self._userName = Gtk.Entry()
        self._userName.set_width_chars(16)
        self._userName.connect("changed",
                               lambda button: self._updateForwardButton())
        self._userName.set_tooltip_text(xstr("simbrief_username_tooltip"))
        uibTable.attach(self._userName, 1, 2, uibRow, uibRow+1)
        label.set_mnemonic_widget(self._userName)
        uibRow += 1

        label = Gtk.Label(xstr("simbrief_password"))
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        uibTable.attach(label, 0, 1, uibRow, uibRow+1)

        self._password = Gtk.Entry()
        self._password.set_visibility(False)
        self._password.connect("changed",
                               lambda button: self._updateForwardButton())
        self._password.set_tooltip_text(xstr("simbrief_password_tooltip"))
        uibTable.attach(self._password, 1, 2, uibRow, uibRow+1)
        label.set_mnemonic_widget(self._password)

        self._rememberButton = Gtk.CheckButton(xstr("simbrief_remember_password"))
        self._rememberButton.set_use_underline(True)
        self._rememberButton.set_tooltip_text(xstr("simbrief_remember_tooltip"))
        uibTable.attach(self._rememberButton, 2, 3, uibRow, uibRow+1, ypadding = 8)
        uibRow += 1

        uibTable.set_margin_top(6)
        uibTable.set_margin_bottom(6)
        uibTable.set_margin_left(4)
        uibTable.set_margin_right(4)

        frame.add(uibTable)
        frame.set_margin_bottom(10)

        table.attach(frame, 0, 3, row, row+1)
        row += 1

        label = Gtk.Label(xstr("simbrief_extra_fuel"))
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, row, row+1)

        self._extraFuel = IntegerEntry(defaultValue = 0)
        self._extraFuel.set_width_chars(6)
        self._extraFuel.set_tooltip_text(xstr("simbrief_extra_fuel_tooltip"))
        table.attach(self._extraFuel, 1, 2, row, row+1)
        label.set_mnemonic_widget(self._extraFuel)

        label = Gtk.Label("kg")
        label.set_alignment(0.0, 0.5)
        table.attach(label, 2, 3, row, row+1)
        row += 1

        label = Gtk.Label(xstr("simbrief_takeoff_runway"))
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, row, row+1)

        self._takeoffRunway = Gtk.Entry()
        self._takeoffRunway.set_width_chars(10)
        self._takeoffRunway.set_tooltip_text(xstr("simbrief_takeoff_runway_tooltip"))
        self._takeoffRunway.connect("changed", self._upperChanged)
        table.attach(self._takeoffRunway, 1, 2, row, row+1)
        label.set_mnemonic_widget(self._takeoffRunway)
        row += 1

        label = Gtk.Label(xstr("simbrief_landing_runway"))
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, row, row+1)

        self._landingRunway = Gtk.Entry()
        self._landingRunway.set_width_chars(10)
        self._landingRunway.set_tooltip_text(xstr("simbrief_landing_runway_tooltip"))
        self._landingRunway.connect("changed", self._upperChanged)
        table.attach(self._landingRunway, 1, 2, row, row+1)
        label.set_mnemonic_widget(self._landingRunway)
        row += 1

        label = Gtk.Label(xstr("simbrief_climb_profile"))
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, row, row+1)

        self._climbProfile = Gtk.ComboBox()
        renderer = Gtk.CellRendererText()
        self._climbProfile.pack_start(renderer, True)
        self._climbProfile.add_attribute(renderer, "text", 0)
        self._climbProfile.set_tooltip_text(xstr("simbrief_climb_profile_tooltip"))
        table.attach(self._climbProfile, 1, 2, row, row+1)
        label.set_mnemonic_widget(self._climbProfile)
        row += 1

        label = Gtk.Label(xstr("simbrief_cruise_profile"))
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, row, row+1)

        self._cruiseProfile = Gtk.ComboBox()
        renderer = Gtk.CellRendererText()
        self._cruiseProfile.pack_start(renderer, True)
        self._cruiseProfile.add_attribute(renderer, "text", 0)
        self._cruiseProfile.set_tooltip_text(xstr("simbrief_cruise_profile_tooltip"))
        self._cruiseProfile.connect("changed", self._cruiseProfileChanged)
        table.attach(self._cruiseProfile, 1, 2, row, row+1)
        label.set_mnemonic_widget(self._cruiseProfile)

        self._cruiseParameter = Gtk.Entry()
        self._cruiseParameter.set_width_chars(5)
        self._cruiseParameter.set_tooltip_text(xstr("simbrief_cruise_parameter_tooltip"))
        self._cruiseParameter.set_sensitive(False)
        self._cruiseParameter.connect("changed", self._cruiseParameterChanged)
        table.attach(self._cruiseParameter, 2, 3, row, row+1)

        row += 1

        label = Gtk.Label(xstr("simbrief_descent_profile"))
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, row, row+1)

        self._descentProfile = Gtk.ComboBox()
        renderer = Gtk.CellRendererText()
        self._descentProfile.pack_start(renderer, True)
        self._descentProfile.add_attribute(renderer, "text", 0)
        self._descentProfile.set_tooltip_text(xstr("simbrief_descent_profile_tooltip"))
        table.attach(self._descentProfile, 1, 2, row, row+1)
        label.set_mnemonic_widget(self._descentProfile)

        self.addCancelFlightButton()

        self._backButton = self.addPreviousButton(clicked = self._backClicked)
        self._button = self.addNextButton(clicked = self._forwardClicked)

        self._resultTimestamp = None

    def activate(self):
        """Activate the SimBrief setup page"""
        config = self._wizard.gui.config

        self._useInternalBrowser.set_active(config.useInternalBrowserForSimBrief)
        self._useInternalBrowser.set_sensitive(True)

        self._userName.set_text(config.simBriefUserName)
        self._userName.set_sensitive(config.useInternalBrowserForSimBrief)

        self._password.set_text(config.simBriefPassword)
        self._password.set_sensitive(config.useInternalBrowserForSimBrief)

        self._rememberButton.set_active(config.rememberSimBriefPassword)
        self._rememberButton.set_sensitive(config.useInternalBrowserForSimBrief)

        self._extraFuel.set_int(0)
        self._extraFuel.set_sensitive(True)

        self._takeoffRunway.set_text("")
        self._takeoffRunway.set_sensitive(True)

        self._landingRunway.set_text("")
        self._landingRunway.set_sensitive(True)

        simBriefData = self._wizard.gui.flight.aircraft.simBriefData
        for (control, profiles) in [(self._climbProfile,
                                     simBriefData.climbProfiles),
                                    (self._cruiseProfile,
                                     simBriefData.cruiseProfiles),
                                    (self._descentProfile,
                                     simBriefData.descentProfiles)]:
            model = Gtk.ListStore(str)
            for profile in profiles:
                model.append([profile])
            control.set_model(model)
            control.set_sensitive(True)

        self._climbProfile.set_active(0)
        self._cruiseProfile.set_active(0)
        self._descentProfile.set_active(0)
        self._cruiseParameter.set_text("")

        self._resultTimestamp = None
        self._waitEnd = None

        self._updateForwardButton()

    def _updateForwardButton(self):
        """Update the sensitivity of the forward button."""
        self._button.set_sensitive(True)

        sensitive = not self._useInternalBrowser.get_active() or \
           (len(self._userName.get_text())>0 and
            len(self._password.get_text())>0)
        if sensitive:
            simBriefData = self._wizard.gui.flight.aircraft.simBriefData
            cruiseProfileIndex = self._cruiseProfile.get_active()
            sensitive = \
                cruiseProfileIndex not in simBriefData.cruiseParameters or \
                not simBriefData.cruiseParameters[cruiseProfileIndex][0] or \
                len(self._cruiseParameter.get_text())>0

        self._button.set_sensitive(sensitive)

    def _backClicked(self, button):
        """Called when the Back button is pressed."""
        self.goBack()

    def _forwardClicked(self, button):
        if self._completed:
            self._wizard.nextPage()
        else:
            config = self._wizard.gui.config

            config.simBriefUserName = self._userName.get_text()

            rememberPassword = self._rememberButton.get_active()
            config.simBriefPassword = \
              self._password.get_text() if rememberPassword else ""
            config.rememberSimBriefPassword = rememberPassword

            config.useInternalBrowserForSimBrief = \
                self._useInternalBrowser.get_active()

            config.save()

            self._wizard.gui.simulator.requestTime(self._handleTime)

    def _useInternalBrowserToggled(self, checkButton):
        """Called when the check button indicating if the internal browser
        should be used is toggled."""
        useInternalBrowserForSimBrief = self._useInternalBrowser.get_active()
        self._userName.set_sensitive(useInternalBrowserForSimBrief)
        self._password.set_sensitive(useInternalBrowserForSimBrief)
        self._rememberButton.set_sensitive(useInternalBrowserForSimBrief)
        self._updateForwardButton()

    def _handleTime(self, simulatorNow):
        """Handle the result of a time retrieval."""
        GObject.idle_add(self._processTime, simulatorNow)

    def _processTime(self, simulatorNow):
        """Process the given time."""
        plan = self._getPlan(simulatorNow)
        print("plan:", plan)

        takeoffRunway = self._takeoffRunway.get_text()
        if takeoffRunway:
            self._wizard.takeoffRunway = takeoffRunway

        landingRunway = self._landingRunway.get_text()
        if landingRunway:
            self._wizard.landingRunway = landingRunway

        self._useInternalBrowser.set_sensitive(False)
        self._userName.set_sensitive(False)
        self._password.set_sensitive(False)
        self._rememberButton.set_sensitive(False)
        self._extraFuel.set_sensitive(False)
        self._takeoffRunway.set_sensitive(False)
        self._landingRunway.set_sensitive(False)

        self._climbProfile.set_sensitive(False)
        self._cruiseProfile.set_sensitive(False)
        self._cruiseParameter.set_sensitive(False)
        self._descentProfile.set_sensitive(False)

        self._wizard.gui.beginBusy(xstr("simbrief_calling"))

        url = cef.SimBriefHandler.getFormURL(plan)
        print("url:", url)

        config = self._wizard.gui.config
        if config.useInternalBrowserForSimBrief:
            self._waitEnd = 0
            cef.callSimBrief(plan,
                             self._getCredentials,
                             self._simBriefProgress,
                             SimBriefSetupPage.getHTMLFilePath())
        else:
            webbrowser.open(url = url, new = 1)
            self._waitEnd = time.time() + SimBriefSetupPage._waitTimeout
            GObject.timeout_add(SimBriefSetupPage._resultQueryInterval,
                                lambda: self._wizard.gui.webHandler. \
                                getSimBriefResult(self._resultCallback,
                                                  self._resultTimestamp))


        startSound(const.SOUND_NOTAM)

    def _getCredentials(self, count):
        """Get the credentials.

        If count is 0, the user name and password entered into the setup page
        are returned. Otherwise a dialog box is displayed informing the user of
        invalid credentials and requesting another set of them."""
        print("_getCredentials", count)
        if count==0:
            return (self._userName.get_text(), self._password.get_text())
        else:
            gui = self._wizard.gui
            config = gui.config

            dialog = SimBriefCredentialsDialog(gui,
                                               config.simBriefUserName,
                                               config.simBriefPassword,
                                               config.rememberSimBriefPassword)
            response = dialog.run()

            if response==Gtk.ResponseType.OK:
                userName = dialog.userName
                self._userName.set_text(userName)
                password = dialog.password
                self._password.set_text(password)
                rememberPassword = dialog.rememberPassword

                config.simBriefUserName = userName

                config.simBriefPassword = \
                    password if rememberPassword else ""
                config.rememberSimBriefPassword = rememberPassword

                config.save()

                return (userName, password)
            else:
                return (None, None)

    def _simBriefProgress(self, progress, result, flightInfo):
        """The real SimBrief progress handler."""
        print("_simBriefProgress", progress, result, flightInfo)
        if result==cef.SIMBRIEF_RESULT_NONE:
            message = SimBriefSetupPage.progress2Message.get(progress,
                                                             "simbrief_progress_unknown")
            self._wizard.gui.updateBusyState(xstr(message))
        else:
            if result==cef.SIMBRIEF_RESULT_OK:
                self._waitEnd = 0
                self._wizard.gui.webHandler. \
                    getSimBriefResult(self._resultCallback,
                                      self._resultTimestamp)
            else:
                self._wizard.gui.endBusy()

                message = SimBriefSetupPage.result2Message.get(result,
                                                               "simbrief_result_unknown")
                dialog = Gtk.MessageDialog(parent = self._wizard.gui.mainWindow,
                                           type = Gtk.MessageType.ERROR,
                                           message_format =
                                           xstr(message) + "\n"+
                                           xstr("simbrief_cancelled"))

                dialog.add_button(xstr("button_ok"), Gtk.ResponseType.OK)
                dialog.set_title(WINDOW_TITLE_BASE)
                secondary = xstr("flightsel_save_failed_sec")
                dialog.format_secondary_markup(secondary)
                dialog.run()
                dialog.hide()

                self._wizard.usingSimBrief = False
                self._wizard.jumpPage("fuel", fromPageShift = 1)

    def _getPlan(self, simulatorNow):
        """Get the flight plan data for SimBrief."""
        print("timestamp:", simulatorNow)

        self._resultTimestamp = now = int(time.time())

        plan = {
            "airline": "MAH",
            "selcal": "XXXX",
            "fuelfactor": "P000",
            "contpct": "0.05",
            "resvrule": "45",
            "taxiout": "10",
            "taxiin": "10",
            "civalue": "AUTO",
            "lang": "hun" if getLanguage().lower()=="hu" else "eng",
            "sessionID": self._wizard._loginResult.sessionID,
            "timestamp": now
            }

        wizard = self._wizard
        gui = wizard.gui

        loginResult = wizard.loginResult
        plan["cpt"] = loginResult.pilotName
        plan["pid"] = loginResult.pilotID

        bookedFlight = wizard.bookedFlight
        plan["fltnum"] = wizard.bookedFlight.callsign[2:]
        plan["type"] = const.icaoCodes[bookedFlight.aircraftType]
        plan["orig"] = bookedFlight.departureICAO
        plan["dest"] = bookedFlight.arrivalICAO
        plan["reg"] = bookedFlight.tailNumber
        plan["pax"] = str(bookedFlight.numPassengers)

        departureTime = bookedFlight.departureTime
        print("departureTime", departureTime)

        tm = time.gmtime(simulatorNow)
        diffMinutes = (departureTime.hour - tm.tm_hour)*60 + \
            departureTime.minute - tm.tm_min
        while diffMinutes<0:
            diffMinutes += 24*60

        realDepartureTime = datetime.datetime.utcnow()
        realDepartureTime += datetime.timedelta(minutes = diffMinutes)

        plan["date"] = "%02d%s%02d" % (realDepartureTime.day,
                                       SimBriefSetupPage.monthNum2Name[realDepartureTime.month-1],
                                       realDepartureTime.year%100)
        plan["deph"] = str(realDepartureTime.hour)
        plan["depm"] = str(realDepartureTime.minute)

        arrivalTime = bookedFlight.arrivalTime
        blockMinutes = (arrivalTime.hour - departureTime.hour)*60 + \
            arrivalTime.minute - departureTime.minute
        while blockMinutes<0:
            blockMinutes += 24*60
        plan["steh"] = str(blockMinutes//60)
        plan["stem"] = str(blockMinutes%60)

        plan["manualzfw"] = str(wizard.zfw / 1000.0)
        plan["cargo"] = str((wizard.bagWeight + wizard.cargoWeight + wizard.mailWeight)/1000.0)

        route = wizard.route
        if route:
            plan["route"] = route

        filedCruiseAltitude = wizard.filedCruiseAltitude
        if filedCruiseAltitude>0:
            plan["fl"] = filedCruiseAltitude

        alternate = wizard.alternate
        if alternate:
            plan["altn"] = wizard.alternate

        plan["addedfuel"] = str(self._extraFuel.get_int() / 1000.0)
        plan["origrwy"] = self._takeoffRunway.get_text()
        plan["destrwy"] = self._landingRunway.get_text()

        for (key, control) in [("climb", self._climbProfile),
                               ("cruise", self._cruiseProfile),
                               ("descent", self._descentProfile)]:
            model = control.get_model()
            active = control.get_active_iter()
            value = model.get_value(active, 0)
            plan[key] = value

        cruiseParameters = self._wizard.gui.flight.aircraft.simBriefData.cruiseParameters
        cruiseProfileIndex = self._cruiseProfile.get_active()
        if cruiseProfileIndex in cruiseParameters:
            value = self._cruiseParameter.get_text()
            if value:
                plan[cruiseParameters[cruiseProfileIndex][1]] = value

        return plan

    def _resultCallback(self, returned, result):
        """Callback for the SimBrief result query."""
        GObject.idle_add(self._handleResult, returned, result)

    def _handleResult(self, returned, result):
        """Handle an RPC query result."""
        print("_handleResult", returned, result)
        if result.result and result.result.get("result"):
            link = result.result.get("result")
            if link=="<failed>":
                self._wizard.gui.endBusy()

                self._finishWithError()
            else:
                link ="https://www.simbrief.com/ofp/flightplans/xml/" + link + ".xml"

                thread = threading.Thread(target = self._getResults, args = (link,))
                thread.daemon = True
                thread.start()

        elif time.time() >= self._waitEnd:
            self._wizard.gui.endBusy()

            self._finishWithError()
        else:
            GObject.timeout_add(SimBriefSetupPage._resultQueryInterval,
                                lambda: self._wizard.gui.webHandler. \
                                getSimBriefResult(self._resultCallback,
                                                  self._resultTimestamp))

    def _upperChanged(self, entry, arg = None):
        """Called when the value of some entry widget has changed and the value
        should be converted to uppercase."""
        entry.set_text(entry.get_text().upper())

    def _cruiseProfileChanged(self, comboBox):
        """Called when the cruise profile has changed.

        It updates the sensitivity of the cruise parameter entry field"""
        simBriefData = self._wizard.gui.flight.aircraft.simBriefData

        activeIndex = self._cruiseProfile.get_active()
        self._cruiseParameter.set_sensitive(activeIndex in
                                            simBriefData.cruiseParameters)

        self._updateForwardButton()

    def _cruiseParameterChanged(self, entry):
        """Called when the cruise parameter has changed.

        The sensitivty of the Forward button will be updated"""
        self._updateForwardButton()

    def _getResults(self, link):
        """Get the result from the given link."""
        ## Holds analysis data to be used
        flightInfo = {}
        try:
            availableInfo = {}

            # Obtaining the xml
            response = urllib.request.urlopen(link,
                                              cafile = certifi.where())
            content = etree.iterparse(response)

            for (action, element) in content:
                # Processing tags that occur multiple times
                if element.tag == "weather":
                    weatherElementList = list(element)
                    for weatherElement in weatherElementList:
                        flightInfo[weatherElement.tag] = weatherElement.text
                elif element.tag in ["files", "prefile"]:
                    availableInfo[element.tag] = element
                elif element.tag == "general":
                    generalElementList = list(element)
                    for generalElement in generalElementList:
                        if generalElement.tag in ["initial_altitude",
                                                  "route_ifps",
                                                  "costindex"]:
                            flightInfo[generalElement.tag] = generalElement.text
                elif element.tag == "origin":
                    originElementList = list(element)
                    for originElement in originElementList:
                        if originElement.tag == "plan_rwy":
                            flightInfo["dep_rwy"] = originElement.text
                elif element.tag == "destination":
                    destinationElementList = list(element)
                    for destinationElement in destinationElementList:
                        if destinationElement.tag == "plan_rwy":
                            flightInfo["arr_rwy"] = destinationElement.text
                elif element.tag == "alternate":
                    alternateElementList = list(element)
                    for alternateElement in alternateElementList:
                        if alternateElement.tag == "icao_code":
                            flightInfo["altn_icao"] = alternateElement.text
                elif element.tag == "fuel":
                    fuelElementList = list(element)
                    for fuelElement in fuelElementList:
                        if fuelElement.tag == "extra":
                            flightInfo["fuel_extra"] = fuelElement.text
                else:
                    availableInfo[element.tag] = element.text

            # Processing plan_html
            ## Obtaining chart links
            imageLinks = []
            for imageLinkElement in lxml.html.find_class(availableInfo["plan_html"],
                                                         "ofpmaplink"):
                for imageLink in imageLinkElement.iterlinks():
                    if imageLink[1] == 'src':
                        imageLinks.append(imageLink[2])
            flightInfo["image_links"] = imageLinks
            print((sorted(availableInfo.keys())))
            htmlFilePath = SimBriefSetupPage.getHTMLFilePath()
            with open(htmlFilePath, 'w') as f:
                f.write("<html>")
                f.write("<body>")
                f.write("<h3 style=\"text-align: center;\">%s</h3></br>" % (xstr("simbrief_result_briefing"),))
                f.write("<div style=\"height: 300px; width: fit-content; overflow: auto; margin: 0 auto;\">")
                f.write(availableInfo["plan_html"])
                f.write("</div>\n")

                f.write("<h2/>");
                f.write("<h3 style=\"text-align: center;\">%s</h3></br>" % (xstr("simbrief_result_downloads"),))
                f.write("<div style=\"height: 300px; width: fit-content; overflow: auto; margin: 0 auto\">")
                f.write("<table style=\"border: 1px solid; border-collapse: collapse;\">")

                directory = ""
                for fileData in availableInfo["files"]:
                    if fileData.tag=="directory":
                        directory = fileData.text

                for fileData in availableInfo["files"]:
                    if fileData.tag in ["pdf", "file"]:
                        name = fileData.find("name").text
                        link = fileData.find("link").text

                        f.write("<tr>")
                        f.write("<td style=\"border: 1px solid; padding-left: 10px; padding-right: 10px; padding-top: 5px; padding-bottom: 5px;\">")
                        f.write(name)
                        f.write("</td>")
                        f.write("<td style=\"border: 1px solid; padding-left: 10px; padding-right: 10px; padding-top: 5px; padding-bottom: 5px;\">")
                        url = directory + link
                        target = " target=\"_blank\"" if fileData.tag=="pdf" else ""
                        f.write("<a href=\"%s\"%s>%s</a>" % (url, target, name))
                        f.write("</td>")
                        f.write("</tr>")

                f.write("</table>")
                f.write("</div>\n")

                f.write("<h2/>")
                f.write("<h3 style=\"text-align: center;\">%s</h3></br>" % (xstr("simbrief_result_prefile"),))
                f.write("<div style=\"height: 400px; width: fit-content; margin: 0 auto\">")
                f.write("<table style=\"border: 1px solid; border-collapse: collapse;\">")
                for prefileData in availableInfo["prefile"]:
                    name = prefileData.find("name").text
                    link = prefileData.find("link").text
                    f.write("<tr>")
                    f.write("<td style=\"border: 1px solid; padding-left: 10px; padding-right: 10px; padding-top: 5px; padding-bottom: 5px;\">")
                    f.write("<a href=\"%s\" target=\"_blank\">%s</a>" % (link, name))
                    f.write("</td>");
                    f.write("</tr>")

                f.write("</table>")
                f.write("</div>\n")

                f.write("</body>")
                f.write("</html>")

        except Exception as e:
            print("_getResults", e)

        GObject.idle_add(self._resultsAvailable, flightInfo)

    def _resultsAvailable(self, flightInfo):
        """Called from the result retrieval thread when the result is
        available."""
        print("_resultsAvailable")
        self._wizard.gui.endBusy()

        if flightInfo:
            self._wizard.departureMETARChanged(flightInfo["orig_metar"],
                                               self)
            self._wizard.arrivalMETARChanged(flightInfo["dest_metar"], self,
                                             fromDownload = True)

            cruiseLevel = int(flightInfo["initial_altitude"])/100
            self._wizard.filedCruiseLevel = cruiseLevel

            (route, sid, star) = self._getRouteData(flightInfo)
            self._wizard.route = route
            self._wizard.departureSID = sid
            self._wizard.arrivalSTAR = star

            self._wizard.alternate = flightInfo["altn_icao"]

            takeoffRunway = flightInfo["dep_rwy"]
            self._wizard.takeoffRunway = takeoffRunway
            self._takeoffRunway.set_text(takeoffRunway)

            landingRunway = flightInfo["arr_rwy"]
            self._wizard.landingRunway = landingRunway
            self._landingRunway.set_text(landingRunway)

            if "costindex" in flightInfo:
                self._setCostIndex(flightInfo["costindex"])

            if "fuel_extra" in flightInfo:
                self._extraFuel.set_text(flightInfo["fuel_extra"])

            self._wizard.nextPage()
        else:
            self._finishWithError()

    def _finishWithError(self):
        """Display an error dialog, and when it is accepted, cancel
        SimBrief briefing and jump to the fuel page."""
        dialog = Gtk.MessageDialog(parent = self._wizard.gui.mainWindow,
                                   type = Gtk.MessageType.ERROR,
                                   message_format =
                                   xstr("simbrief_result_error_other") + "\n"+
                                   xstr("simbrief_cancelled"))

        dialog.add_button(xstr("button_ok"), Gtk.ResponseType.OK)
        dialog.set_title(WINDOW_TITLE_BASE)
        secondary = xstr("flightsel_save_failed_sec")
        dialog.format_secondary_markup(secondary)
        dialog.run()
        dialog.hide()

        self._wizard.usingSimBrief = False
        self._wizard.jumpPage("fuel", fromPageShift = 1)

    def _getRouteData(self, flightInfo):
        """Analyze the route information provided by SimBrief.

        Returns a tuple of
        - the route
        - the SID (may be None)
        - the STAR (may be None)"""
        route = flightInfo["route_ifps"]
        print("route:", route)
        words = re.split("\\s+", route)

        sid = None
        star = None

        if len(words)>1:
            if words[0]=="DCT":
                words = words[1:]
            elif len(words[0])>=7 and len(words[1])==5:
                if words[0][:5]==words[1]:
                    sid = words[0]
                    words = words[1:]

            if words[-1]=="DCT":
                words = words[:-1]
            elif len(words[-1])>=7 and len(words[-2])==5:
                if words[-1][:5]==words[-2]:
                    star = words[-1]
                    words = words[:-1]

        if sid is not None and sid[5].isdigit():
            sid = sid[:5] + " " + sid[5:]
        if star is not None and star[5].isdigit():
            star = star[:5] + " " + star[5:]

        return (" ".join(words), sid, star)

    def _setCostIndex(self, costIndex):
        """Set the cost index, if the selected cruise profile is a CI."""
        cruiseParameters = self._wizard.gui.flight.aircraft.simBriefData.cruiseParameters
        cruiseProfileIndex = self._cruiseProfile.get_active()
        if cruiseProfileIndex in cruiseParameters:
            if cruiseParameters[cruiseProfileIndex][1]=="civalue":
                self._cruiseParameter.set_text(str(costIndex))

#-----------------------------------------------------------------------------

class SimBriefingPage(Page):
    """Page to display the SimBrief HTML briefing."""
    class BrowserLifeSpanHandler(object):
        """The life-span handler of a browser."""
        def __init__(self, simBriefingPage):
            """Construct the life-span handler for the given page."""
            self._simBriefingPage = simBriefingPage

        def OnBeforeClose(self, browser):
            """Called before closing the browser."""
            if browser is self._simBriefingPage._browser:
                self._simBriefingPage._invalidateBrowser()

        def OnBeforeDownload(self, browser, downloadItem, suggestedName, callback):
            callback.Continue(suggestedName, True)
            return True

    def __init__(self, wizard):
        """Construct the setup page."""

        super(SimBriefingPage, self).__init__(wizard, "simbrief_result",
                                              xstr("simbrief_result_title"), "")

        self._container = cef.getContainer()
        self._container.set_size_request(650, -1)

        self.setMainWidget(self._container)

        self._browser = None

        self.addCancelFlightButton()

        self.addPreviousButton(clicked = self._backClicked)

        self._button = self.addNextButton(clicked = self._forwardClicked)
        self._button.set_label(xstr("briefing_button"))
        self._button.set_has_tooltip(False)
        self._button.set_use_stock(False)

    def prepareShow(self):
        """Prepare the page for showing (again)."""
        if self._browser is None:
            self._startBrowser()
        else:
            self._browser.Reload()

    def prepareHide(self):
        """Prepare the page for hiding."""
        if os.name!="nt":
            self._browser.CloseBrowser(False)

    def grabDefault(self):
        """If the page has a default button, make it the default one."""
        super(SimBriefingPage, self).grabDefault()

        if self._browser is None:
            self._startBrowser()

    def _backClicked(self, button):
        """Called when the Back button has been pressed."""
        self.goBack()

    def _forwardClicked(self, button):
        """Called when the Forward button has been pressed."""
        if not self._completed:
            self._button.set_label(xstr("button_next"))
            self._button.set_tooltip_text(xstr("button_next_tooltip"))
            self._wizard.usingSimBrief = True
            self.complete()

        self._wizard.nextPage()

    def _startBrowser(self):
        """Start the browser.

        If a container is needed, create one."""
        if self._container is None:
            self._container = cef.getContainer()
            self.setMainWidget(self._container)
        else:
            self._container.show()

        url = "file://" + SimBriefSetupPage.getHTMLFilePath()
        self._browser = cef.startInContainer(self._container, url)

        lifeSpanHandler = SimBriefingPage.BrowserLifeSpanHandler(self)
        self._browser.SetClientHandler(lifeSpanHandler)

    def _invalidateBrowser(self):
        """Invalidate the browser (and associated stuff)."""
        self._container.hide()
        self._browser = None

    def finalizeCEF(self):
        """Close the CEF browser."""
        if self._browser is not None:
            self._container.hide()
            self._browser.CloseBrowser(True)
            self._browser = None

#-----------------------------------------------------------------------------

class FuelTank(Gtk.VBox):
    """Widget for the fuel tank."""
    def __init__(self, fuelTank, name, capacity, currentWeight):
        """Construct the widget for the tank with the given name."""
        super(FuelTank, self).__init__()

        self._enabled = True
        self.fuelTank = fuelTank
        self.capacity = capacity
        self.currentWeight = currentWeight
        self.expectedWeight = currentWeight

        self._label = label = Gtk.Label("<b>" + name + "</b>")
        label.set_use_markup(True)
        label.set_use_underline(True)
        label.set_justify(Gtk.Justification.CENTER)
        label.set_alignment(0.5, 1.0)

        self._tankFigure = Gtk.EventBox()
        self._tankFigure.set_size_request(38, 200)
        self._tankFigure.set_visible_window(False)
        self._tankFigure.set_tooltip_markup(xstr("fuel_tank_tooltip"))

        self._tankFigure.connect("draw", self._drawTankFigure)
        self._tankFigure.connect("button_press_event", self._buttonPressed)
        self._tankFigure.connect("motion_notify_event", self._motionNotify)

        self._tankFigure.add_events(Gdk.EventMask.SCROLL_MASK)
        self._tankFigure.connect("scroll-event", self._scrolled)

        alignment = Gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 0.0, yscale = 1.0)
        alignment.add(self._tankFigure)

        self.pack_start(alignment, True, True, 4)

        self._expectedButton = Gtk.SpinButton()
        self._expectedButton.set_numeric(True)
        self._expectedButton.set_range(0, self.capacity)
        self._expectedButton.set_increments(10, 100)
        self._expectedButton.set_value(currentWeight)
        self._expectedButton.set_alignment(1.0)
        self._expectedButton.set_width_chars(5)
        self._expectedButton.connect("value-changed", self._expectedChanged)

        label.set_mnemonic_widget(self._expectedButton)

    @property
    def label(self):
        """Get the label with the caption."""
        return self._label

    @property
    def expectedButton(self):
        """Get the button containing the expected value."""
        return self._expectedButton

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

        context = eventOrContext
        (xOffset, yOffset) = (0, 0)

        width = tankFigure.get_allocated_width()
        height = tankFigure.get_allocated_height()

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
        if self._enabled and event.state==Gdk.ModifierType.BUTTON1_MASK:
            self._setExpectedFromY(event.y)

    def _scrolled(self, tankFigure, event):
        """Called when a scroll event is received."""
        if self._enabled:
            increment = 1 if event.state==Gdk.ModifierType.CONTROL_MASK \
                        else 100 if event.state==Gdk.ModifierType.SHIFT_MASK \
                        else 10 if event.state==0 else 0
            if increment!=0:
                if event.direction==Gdk.ScrollDirection.DOWN:
                    increment *= -1
                self._expectedButton.spin(Gtk.SpinType.USER_DEFINED, increment)

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
        super(FuelPage, self).__init__(wizard, "fuel",
                                       xstr("fuel_title"),
                                       xstr("fuel_help_pre") +
                                       xstr("fuel_help_post"),
                                       completedHelp = xstr("fuel_chelp"))

        self._fuelTanks = []
        self._fuelTable = None
        self._fuelAlignment = Gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                            xscale = 0.0, yscale = 1.0)
        self.setMainWidget(self._fuelAlignment)

        tankData = [(tank, 2500, 3900) for tank in acft.mostFuelTanks]
        self._setupTanks(tankData)

        self.addCancelFlightButton()

        self._backButton = self.addPreviousButton(clicked = self._backClicked)
        self._button = self.addNextButton(clicked = self._forwardClicked)

        self._pumpIndex = 0

    def activate(self):
        """Activate the page."""
        self._setupTanks(self._wizard._fuelData)

        aircraft = self._wizard.gui.flight.aircraft
        minLandingFuel = aircraft.minLandingFuel
        recommendedLandingFuel = aircraft.recommendedLandingFuel

        middleHelp = "" if minLandingFuel is None else \
            (xstr("fuel_help_min") % (minLandingFuel,)) \
            if recommendedLandingFuel is None else \
            (xstr("fuel_help_min_rec") % (minLandingFuel,
                                          recommendedLandingFuel))
        self.setHelp(xstr("fuel_help_pre") + middleHelp + xstr("fuel_help_post"))

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
        elif self._wizard.usingSimBrief:
            self._wizard.jumpPage("takeoff")
        else:
            self._wizard.jumpPage("briefing1")

    def _setupTanks(self, tankData):
        """Setup the tanks for the given data."""
        numTanks = len(tankData)
        if self._fuelTable is not None:
            self._fuelAlignment.remove(self._fuelTable)

        self._fuelTanks = []
        self._fuelTable = Gtk.Grid()
        self._fuelTable.set_column_homogeneous(True)
        self._fuelTable.set_row_spacing(4)
        self._fuelTable.set_column_spacing(16 if numTanks<5 else 0)
        index = 0
        for (tank, current, capacity) in tankData:
            fuelTank = FuelTank(tank,
                                xstr("fuel_tank_" +
                                     const.fuelTank2string(tank)),
                                capacity, current)
            self._fuelTanks.append(fuelTank)

            alignment = Gtk.Alignment(xalign = 0.5, yalign = 1.0,
                                      xscale = 1.0, yscale = 0.0)
            alignment.add(fuelTank.label)
            self._fuelTable.attach(alignment,
                                   index*(1 if numTanks<5 else 2), 0,
                                   1 if numTanks<5 else 3, 1)

            alignment = Gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                      xscale = 0.0, yscale = 1.0)
            alignment.add(fuelTank)
            self._fuelTable.attach(alignment,
                                   index*(1 if numTanks<5 else 2) +
                                   (0 if numTanks<5 else 1), 1, 1, 1)


            alignment = Gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                      xscale = 1.0, yscale = 0.0)
            alignment.add(fuelTank.expectedButton)

            self._fuelTable.attach(alignment,
                                   index* (1 if numTanks<5 else 2),
                                   2 if (index%2)==0 or numTanks<5 else 3,
                                   1 if numTanks<5 else 3, 1)

            index += 1

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
            if self._wizard.usingSimBrief:
                self._wizard.gui.startMonitoring()
                self._wizard.jumpPage("takeoff")
            else:
                bookedFlight = self._wizard._bookedFlight
                self._wizard.gui.beginBusy(xstr("route_down_notams"))
                self._wizard.gui.webHandler.getNOTAMs(self._notamsCallback,
                                                      bookedFlight.departureICAO,
                                                      bookedFlight.arrivalICAO)
                startSound(const.SOUND_NOTAM)
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
            GObject.timeout_add(50, self._pump)

    def _notamsCallback(self, returned, result):
        """Callback for the NOTAMs."""
        GObject.idle_add(self._handleNOTAMs, returned, result)

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
        GObject.idle_add(self._handleMETARs, returned, result)

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

        number = 1 if departure else 2

        title = xstr("briefing_title") % (number,
                                          xstr("briefing_departure")
                                          if departure
                                          else xstr("briefing_arrival"))
        super(BriefingPage, self).__init__(wizard,
                                           "briefing%d" % (number,),
                                           title, xstr("briefing_help"),
                                           completedHelp = xstr("briefing_chelp"))

        alignment = Gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 1.0, yscale = 1.0)

        mainBox = Gtk.VBox()
        alignment.add(mainBox)
        self.setMainWidget(alignment)

        self._notamsFrame = Gtk.Frame()
        self._notamsFrame.set_label(xstr("briefing_notams_init"))
        scrolledWindow = Gtk.ScrolledWindow()
        scrolledWindow.set_size_request(-1, 128)
        # FIXME: these constants should be in common
        scrolledWindow.set_policy(Gtk.PolicyType.AUTOMATIC,
                                  Gtk.PolicyType.AUTOMATIC)
        self._notams = Gtk.TextView()
        self._notams.set_editable(False)
        self._notams.set_accepts_tab(False)
        self._notams.set_wrap_mode(Gtk.WrapMode.WORD)
        scrolledWindow.add(self._notams)
        alignment = Gtk.Alignment(xalign = 0.0, yalign = 0.0,
                                  xscale = 1.0, yscale = 1.0)
        alignment.set_padding(padding_top = 4, padding_bottom = 0,
                              padding_left = 0, padding_right = 0)
        alignment.add(scrolledWindow)
        self._notamsFrame.add(alignment)
        mainBox.pack_start(self._notamsFrame, True, True, 4)

        self._metarFrame = Gtk.Frame()
        self._metarFrame.set_label(xstr("briefing_metar_init"))
        scrolledWindow = Gtk.ScrolledWindow()
        scrolledWindow.set_size_request(-1, 32)
        scrolledWindow.set_policy(Gtk.PolicyType.AUTOMATIC,
                                  Gtk.PolicyType.AUTOMATIC)

        self._updatingMETAR = False

        self._metar = Gtk.TextView()
        self._metar.set_accepts_tab(False)
        self._metar.set_wrap_mode(Gtk.WrapMode.WORD)
        self._metar.get_buffer().connect("changed", self._metarChanged)
        self._metar.get_buffer().connect_after("insert-text", self._metarInserted)
        scrolledWindow.add(self._metar)
        alignment = Gtk.Alignment(xalign = 0.0, yalign = 0.0,
                                  xscale = 1.0, yscale = 1.0)
        alignment.set_padding(padding_top = 4, padding_bottom = 0,
                              padding_left = 0, padding_right = 0)
        alignment.add(scrolledWindow)
        self._metarFrame.add(alignment)
        mainBox.pack_start(self._metarFrame, True, True, 4)
        self.metarEdited = False

        self.addCancelFlightButton()

        self.addPreviousButton(clicked = self._backClicked)
        self._button = self.addNextButton(clicked = self._forwardClicked)

    @property
    def metar(self):
        """Get the METAR on the page."""
        buffer = self._metar.get_buffer()
        return buffer.get_text(buffer.get_start_iter(),
                               buffer.get_end_iter(), True)

    def setMETAR(self, metar):
        """Set the METAR."""
        self._metar.get_buffer().set_text(metar)
        self.metarEdited = False

    def changeMETAR(self, metar, fromEditing = True):
        """Change the METAR as a result of an edit on one of the other
        pages."""
        self._updatingMETAR = True
        self._metar.get_buffer().set_text(metar)
        self._updatingMETAR = False

        self._updateButton()
        self.metarEdited = fromEditing

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
                s += str(notam)
                s += "-------------------- * --------------------\n"
            buffer.set_text(s)

        self._metarFrame.set_label(xstr("briefing_metar_template") % (icao,))
        buffer = self._metar.get_buffer()
        self._updatingMETAR = True
        if metar is None:
            buffer.set_text("")
            self.setHelp(xstr("briefing_help_nometar"))
        else:
            buffer.set_text(metar)
        self._updatingMETAR = False
        self._updateButton()

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
        print("BriefingPage.metarChanged", self._updatingMETAR)
        if not self._updatingMETAR:
            self.metarEdited = True
            self._updateButton()
            metar = buffer.get_text(buffer.get_start_iter(),
                                buffer.get_end_iter(), True)
            self._wizard.metarChanged(metar, self)

    def _metarInserted(self, textBuffer, iter, text, length):
        """Called when new characters are inserted into the METAR.

        It uppercases all characters."""
        print("BriefingPage.metarInserted", self._updatingMETAR)
        if not self._updatingMETAR:
            self._updatingMETAR = True

            iter1 = iter.copy()
            iter1.backward_chars(length)
            textBuffer.delete(iter, iter1)

            textBuffer.insert(iter, text.upper())

            self._updatingMETAR = False

    def _updateButton(self):
        """Update the sensitivity of the Next button based on the contents of
        the METAR field."""
        buffer = self._metar.get_buffer()
        self._button.set_sensitive(buffer.get_text(buffer.get_start_iter(),
                                                   buffer.get_end_iter(),
                                                   True)!="")


#-----------------------------------------------------------------------------

class TakeoffPage(Page):
    """Page for entering the takeoff data."""
    def __init__(self, wizard):
        """Construct the takeoff page."""
        super(TakeoffPage, self).__init__(wizard, "takeoff",
                                          xstr("takeoff_title"),
                                          xstr("takeoff_help"),
                                          completedHelp = xstr("takeoff_chelp"))

        self._forwardAllowed = False

        alignment = Gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)

        table = Gtk.Table(9, 24)
        table.set_row_spacings(4)
        table.set_col_spacings(16)
        table.set_homogeneous(False)
        alignment.add(table)
        self.setMainWidget(alignment)

        row = 0

        label = Gtk.Label(xstr("takeoff_metar"))
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, row, row+1)

        self._metar = Gtk.Entry()
        self._metar.set_width_chars(40)
        self._metar.set_tooltip_text(xstr("takeoff_metar_tooltip"))
        self._metar.connect("changed", self._metarChanged)
        self._metar.get_buffer().connect_after("inserted-text", self._metarInserted)
        table.attach(self._metar, 1, 24, row, row+1)
        label.set_mnemonic_widget(self._metar)

        self._updatingMETAR = False

        row += 1

        label = Gtk.Label(xstr("takeoff_runway"))
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, row, row+1)

        self._runway = Gtk.Entry()
        self._runway.set_width_chars(10)
        self._runway.set_tooltip_text(xstr("takeoff_runway_tooltip"))
        self._runway.connect("changed", self._upperChanged)
        table.attach(self._runway, 1, 3, row, row+1)
        label.set_mnemonic_widget(self._runway)

        row += 1

        label = Gtk.Label(xstr("takeoff_sid"))
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, row, row+1)

        self._sid = Gtk.ComboBox.new_with_model_and_entry(comboModel)

        self._sid.set_entry_text_column(0)
        self._sid.get_child().set_width_chars(10)
        self._sid.set_tooltip_text(xstr("takeoff_sid_tooltip"))
        self._sid.connect("changed", self._upperChangedComboBox)
        table.attach(self._sid, 1, 3, row, row+1)
        label.set_mnemonic_widget(self._sid)

        row += 1

        label = Gtk.Label(xstr("takeoff_v1"))
        label.set_use_markup(True)
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, row, row+1)

        self._v1 = IntegerEntry()
        self._v1.set_width_chars(4)
        self._v1.set_tooltip_markup(xstr("takeoff_v1_tooltip_knots"))
        self._v1.connect("integer-changed", self._valueChanged)
        table.attach(self._v1, 2, 3, row, row+1)
        label.set_mnemonic_widget(self._v1)

        self._v1Unit = Gtk.Label(xstr("label_knots"))
        self._v1Unit.set_alignment(0.0, 0.5)
        table.attach(self._v1Unit, 3, 4, row, row+1)

        row += 1

        label = Gtk.Label(xstr("takeoff_vr"))
        label.set_use_markup(True)
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, row, row+1)

        self._vr = IntegerEntry()
        self._vr.set_width_chars(4)
        self._vr.set_tooltip_markup(xstr("takeoff_vr_tooltip_knots"))
        self._vr.connect("integer-changed", self._valueChanged)
        table.attach(self._vr, 2, 3, row, row+1)
        label.set_mnemonic_widget(self._vr)

        self._vrUnit = Gtk.Label(xstr("label_knots"))
        self._vrUnit.set_alignment(0.0, 0.5)
        table.attach(self._vrUnit, 3, 4, row, row+1)

        row += 1

        label = Gtk.Label(xstr("takeoff_v2"))
        label.set_use_markup(True)
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, row, row+1)

        self._v2 = IntegerEntry()
        self._v2.set_width_chars(4)
        self._v2.set_tooltip_markup(xstr("takeoff_v2_tooltip_knots"))
        self._v2.connect("integer-changed", self._valueChanged)
        table.attach(self._v2, 2, 3, row, row+1)
        label.set_mnemonic_widget(self._v2)

        self._v2Unit = Gtk.Label(xstr("label_knots"))
        self._v2Unit.set_alignment(0.0, 0.5)
        table.attach(self._v2Unit, 3, 4, row, row+1)

        row += 1

        self._derateType = acft.DERATE_NONE

        self._derateLabel = Gtk.Label()
        self._derateLabel.set_use_underline(True)
        self._derateLabel.set_markup(xstr("takeoff_derate_tupolev"))
        self._derateLabel.set_alignment(0.0, 0.5)
        table.attach(self._derateLabel, 0, 1, row, row+1)

        self._derate = Gtk.Alignment()
        table.attach(self._derate, 2, 4, row, row+1)
        self._derateWidget = None
        self._derateEntry = None
        self._derateUnit = None
        self._derateButtons = None

        row += 1

        self._antiIceOn = Gtk.CheckButton(xstr("takeoff_antiice"))
        self._antiIceOn.set_use_underline(True)
        self._antiIceOn.set_tooltip_text(xstr("takeoff_antiice_tooltip"))
        table.attach(self._antiIceOn, 2, 4, row, row+1)

        row += 1

        self._rto = Gtk.CheckButton(xstr("takeoff_rto"))
        self._rto.set_use_underline(True)
        self._rto.set_tooltip_text(xstr("takeoff_rto_tooltip"))
        self._rto.connect("toggled", self._rtoToggled)
        table.attach(self._rto, 2, 4, row, row+1, ypadding = 8)

        self.addCancelFlightButton()

        self.addPreviousButton(clicked = self._backClicked)

        self._button = self.addNextButton(clicked = self._forwardClicked)

        self._active = False

    @property
    def runway(self):
        """Get the runway."""
        return self._runway.get_text()

    @property
    def sid(self):
        """Get the SID."""
        text = self._sid.get_child().get_text()
        return text if self._sid.get_active()!=0 and text and text!="N/A" \
               else None

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

    @property
    def derate(self):
        """Get the derate value, if any."""
        if self._derateWidget is None:
            return None
        if self._derateType==acft.DERATE_BOEING:
            derate = self._derateEntry.get_text()
            return derate if derate else None
        elif self._derateType==acft.DERATE_EPR:
            derate = self._derateWidget.get_text()
            return derate if derate else None
        elif self._derateType==acft.DERATE_TUPOLEV:
            return acft.DERATE_TUPOLEV_NOMINAL \
                   if self._derateButtons[0].get_active() \
                   else acft.DERATE_TUPOLEV_TAKEOFF
        elif self._derateType==acft.DERATE_B462:
            return self._derateWidget.get_active()
        else:
            return None

    @property
    def antiIceOn(self):
        """Get whether the anti-ice system has been turned on."""
        return self._antiIceOn.get_active()

    @antiIceOn.setter
    def antiIceOn(self, value):
        """Set the anti-ice indicator."""
        self._antiIceOn.set_active(value)

    @property
    def rtoIndicated(self):
        """Get whether the pilot has indicated if there was an RTO."""
        return self._rto.get_active()

    def activate(self):
        """Activate the page."""
        print("TakeoffPage.activate")

        self._updatingMETAR = True
        self._metar.get_buffer().set_text(self._wizard.departureMETAR, -1)
        self._updatingMETAR = False

        if self._wizard.takeoffRunway is None:
            self._runway.set_text("")
        else:
            self._runway.set_text(self._wizard.takeoffRunway)
        self._runway.set_sensitive(True)
        if self._wizard.departureSID is None:
            self._sid.set_active(0)
        else:
            self._sid.get_child().set_text(self._wizard.departureSID)
        self._sid.set_sensitive(True)
        self._v1.set_int(None)
        self._v1.set_sensitive(True)
        self._vr.set_int(None)
        self._vr.set_sensitive(True)
        self._v2.set_int(None)
        self._v2.set_sensitive(True)

        i18nSpeedUnit = self._wizard.gui.flight.getI18NSpeedUnit()
        speedUnit = xstr("label" + i18nSpeedUnit)
        self._v1Unit.set_text(speedUnit)
        self._vrUnit.set_text(speedUnit)
        self._v2Unit.set_text(speedUnit)

        self._v1.set_tooltip_markup(xstr("takeoff_v1_tooltip" + i18nSpeedUnit))
        self._vr.set_tooltip_markup(xstr("takeoff_vr_tooltip" + i18nSpeedUnit))
        self._v2.set_tooltip_markup(xstr("takeoff_v2_tooltip" + i18nSpeedUnit))

        self._derateType = self._wizard.gui.flight.aircraft.derateType

        self._setupDerateWidget()

        self._rto.set_active(False)
        self._rto.set_sensitive(False)

        self._button.set_sensitive(False)
        self._forwardAllowed = False

        self._active = True

    def allowForward(self):
        """Allow going to the next page."""
        print("TakeoffPage.allowForward")
        self._forwardAllowed = True
        self._updateForwardButton()

    def reset(self):
        """Reset the page if the wizard is reset."""
        print("TakeoffPage.reset")

        super(TakeoffPage, self).reset()
        self._v1.reset()
        self._vr.reset()
        self._v2.reset()
        self._hasDerate = False
        self._antiIceOn.set_active(False)
        self._active = False

    def setRTOEnabled(self, enabled):
        """Set the RTO checkbox enabled or disabled."""
        if not enabled:
            self._rto.set_active(False)
        self._rto.set_sensitive(enabled)

    def changeMETAR(self, metar, fromEditing = True):
        """Change the METAR as a result of an edit on one of the other
        pages."""
        if self._active:
            print("TakeoffPage.changeMETAR")
            self._updatingMETAR = True
            self._metar.get_buffer().set_text(metar, -1)
            self._updatingMETAR = False

            self._updateForwardButton()

    def _updateForwardButton(self):
        """Update the sensitivity of the forward button based on some conditions."""
        sensitive = self._forwardAllowed and \
                    self._metar.get_text()!="" and \
                    self._runway.get_text()!="" and \
                    self.sid is not None and \
                    self.v1 is not None and \
                    self.vr is not None and \
                    self.v2 is not None and \
                    self.v1 <= self.vr and \
                    self.vr <= self.v2 and \
                    (self._derateType==acft.DERATE_NONE or
                     self.derate is not None)

        print("TakeoffPage._updateForwardButton: forwardAllowed:", self._forwardAllowed, ", sensitive:", sensitive)
        if self._forwardAllowed:
            print("  METAR: ", self._metar.get_text())
            print("  runway: ", self._runway.get_text())
            print("  SID:", self.sid)
            print("  V1:", self.v1)
            print("  VR:", self.vr)
            print("  V2:", self.v2)
            print("  derateType:", self._derateType)
            print("  derate:", self.derate)

        self._button.set_sensitive(sensitive)

    def _valueChanged(self, widget, arg = None):
        """Called when the value of some widget has changed."""
        print("TakeoffPage._valueChanged")

        self._updateForwardButton()

    def _upperChanged(self, entry, arg = None):
        """Called when the value of some entry widget has changed and the value
        should be converted to uppercase."""
        print("TakeoffPage._upperChanged")
        entry.set_text(entry.get_text().upper())
        self._valueChanged(entry, arg)

    def _upperChangedComboBox(self, comboBox):
        """Called for combo box widgets that must be converted to uppercase."""
        entry = comboBox.get_child()
        if comboBox.get_active()==-1:
            entry.set_text(entry.get_text().upper())
        self._valueChanged(entry)

    def _derateChanged(self, entry):
        """Called when the value of the derate is changed."""
        print("TakeoffPage._derateChanged")
        self._updateForwardButton()

    def _rtoToggled(self, button):
        """Called when the RTO check button is toggled."""
        self._wizard.rtoToggled(button.get_active())

    def _backClicked(self, button):
        """Called when the Back button is pressed."""
        self.goBack()

    def _forwardClicked(self, button):
        """Called when the forward button is clicked."""
        aircraft = self._wizard.gui.flight.aircraft
        aircraft.updateV1R2()
        if self.derate is not None:
            aircraft.updateDerate()
        aircraft.updateTakeoffAntiIce()
        self._wizard.nextPage()

    def _setupDerateWidget(self):
        """Setup the derate widget."""
        if self._derateWidget is not None:
            self._derate.remove(self._derateWidget)

        if self._derateType==acft.DERATE_BOEING:
            self._derateLabel.set_text(xstr("takeoff_derate_boeing"))
            self._derateLabel.set_use_underline(True)
            self._derateLabel.set_sensitive(True)

            self._derateEntry = Gtk.Entry()
            self._derateEntry.set_width_chars(7)
            self._derateEntry.set_tooltip_text(xstr("takeoff_derate_boeing_tooltip"))
            self._derateEntry.set_alignment(1.0)
            self._derateEntry.connect("changed", self._derateChanged)
            self._derateLabel.set_mnemonic_widget(self._derateEntry)

            self._derateUnit = Gtk.Label("%")
            self._derateUnit.set_alignment(0.0, 0.5)

            self._derateWidget = Gtk.Table(3, 1)
            self._derateWidget.set_row_spacings(4)
            self._derateWidget.set_col_spacings(16)
            self._derateWidget.set_homogeneous(False)

            self._derateWidget.attach(self._derateEntry, 0, 2, 0, 1)
            self._derateWidget.attach(self._derateUnit, 2, 3, 0, 1)

            self._derate.add(self._derateWidget)
        elif self._derateType==acft.DERATE_EPR:
            self._derateLabel.set_text("_EPR:")
            self._derateLabel.set_use_underline(True)
            self._derateLabel.set_sensitive(True)

            self._derateWidget = Gtk.Entry()
            self._derateWidget.set_width_chars(7)
            self._derateWidget.set_tooltip_text(xstr("takeoff_derate_epr_tooltip"))
            self._derateWidget.set_alignment(1.0)
            self._derateWidget.connect("changed", self._derateChanged)
            self._derateLabel.set_mnemonic_widget(self._derateWidget)

            self._derate.add(self._derateWidget)
        elif self._derateType==acft.DERATE_TUPOLEV:
            self._derateLabel.set_text(xstr("takeoff_derate_tupolev"))
            self._derateLabel.set_use_underline(True)
            self._derateLabel.set_sensitive(True)

            nominal = Gtk.RadioButton.\
                new_with_label_from_widget(None,
                                           xstr("takeoff_derate_tupolev_nominal"))
            nominal.set_use_underline(True)
            nominal.set_tooltip_text(xstr("takeoff_derate_tupolev_nominal_tooltip"))
            nominal.connect("toggled", self._derateChanged)

            takeoff = Gtk.RadioButton.\
                new_with_label_from_widget(nominal,
                                           xstr("takeoff_derate_tupolev_takeoff"))

            takeoff.set_use_underline(True)
            takeoff.set_tooltip_text(xstr("takeoff_derate_tupolev_takeoff_tooltip"))
            takeoff.connect("toggled", self._derateChanged)

            self._derateButtons = [nominal, takeoff]

            self._derateWidget = Gtk.HBox()
            self._derateWidget.pack_start(nominal, False, False, 4)
            self._derateWidget.pack_start(takeoff, False, False, 4)

            self._derate.add(self._derateWidget)
        elif self._derateType==acft.DERATE_B462:
            self._derateLabel.set_text("")

            self._derateWidget = Gtk.CheckButton(xstr("takeoff_derate_b462"))
            self._derateWidget.set_tooltip_text(xstr("takeoff_derate_b462_tooltip"))
            self._derateWidget.set_use_underline(True)
            self._derate.add(self._derateWidget)
        else:
            self._derateWidget = None
            self._derateLabel.set_text("")
            self._derateLabel.set_sensitive(False)

    def _metarChanged(self, entry):
        """Called when the METAR has changed."""
        print("TakeoffPage.metarChanged", self._updatingMETAR)
        if not self._updatingMETAR:
            self._updateForwardButton()
            self._wizard.metarChanged(entry.get_text(), self)

    def _metarInserted(self, buffer, position, text, length):
        """Called when new characters are inserted into the METAR.

        It uppercases all characters."""
        print("TakeoffPage.metarInserted", self._updatingMETAR)
        if not self._updatingMETAR:
            self._updatingMETAR = True

            buffer.delete_text(position, length)
            buffer.insert_text(position, text.upper(), length)

            self._updatingMETAR = False

#-----------------------------------------------------------------------------

class CruisePage(Page):
    """The page containing the flight level that might change during flight."""
    def __init__(self, wizard):
        """Construct the page."""
        super(CruisePage, self).__init__(wizard, "cruise",
                                         xstr("cruise_title"),
                                         xstr("cruise_help"))

        self._loggable = False
        self._loggedCruiseLevel = 240
        self._activated = False

        alignment = Gtk.Alignment(xalign = 0.5, yalign = 0.0,
                                  xscale = 0.0, yscale = 1.0)

        mainBox = Gtk.VBox()
        alignment.add(mainBox)
        self.setMainWidget(alignment)

        alignment = Gtk.Alignment(xalign = 0.0, yalign = 0.0,
                                  xscale = 0.0, yscale = 0.0)
        mainBox.pack_start(alignment, False, False, 16)

        levelBox = Gtk.HBox()

        label = Gtk.Label(xstr("route_level"))
        label.set_use_underline(True)
        levelBox.pack_start(label, True, True, 0)

        self._cruiseLevel = Gtk.SpinButton()
        self._cruiseLevel.set_increments(step = 10, page = 100)
        self._cruiseLevel.set_range(min = 50, max = 500)
        self._cruiseLevel.set_tooltip_text(xstr("cruise_route_level_tooltip"))
        self._cruiseLevel.set_numeric(True)
        self._cruiseLevel.connect("value-changed", self._cruiseLevelChanged)
        label.set_mnemonic_widget(self._cruiseLevel)

        levelBox.pack_start(self._cruiseLevel, False, False, 8)

        self._updateButton = Gtk.Button(xstr("cruise_route_level_update"));
        self._updateButton.set_use_underline(True)
        self._updateButton.set_tooltip_text(xstr("cruise_route_level_update_tooltip"))
        self._updateButton.connect("clicked", self._updateButtonClicked)

        levelBox.pack_start(self._updateButton, False, False, 16)

        mainBox.pack_start(levelBox, False, False, 0)

        alignment = Gtk.Alignment(xalign = 0.0, yalign = 0.0,
                                  xscale = 0.0, yscale = 1.0)
        mainBox.pack_start(alignment, True, True, 0)

        self.addCancelFlightButton()

        self._backButton = self.addPreviousButton(clicked = self._backClicked)
        self._button = self.addNextButton(clicked = self._forwardClicked)

    @property
    def activated(self):
        """Determine if the page is already activated or not."""
        return self._activated

    @property
    def cruiseLevel(self):
        """Get the cruise level."""
        return self._loggedCruiseLevel

    @property
    def loggableCruiseLevel(self):
        """Get the cruise level which should be logged."""
        return self._cruiseLevel.get_value_as_int()

    def setLoggable(self, loggable):
        """Set whether the cruise altitude can be logged."""
        self._loggable = loggable
        self._updateButtons()

    def activate(self):
        """Setup the route from the booked flight."""
        self._loggedCruiseLevel = self._wizard.filedCruiseLevel
        self._cruiseLevel.set_value(self._loggedCruiseLevel)
        self._activated = True

    def reset(self):
        """Reset the page."""
        self._loggable = False
        self._activated = False
        super(CruisePage, self).reset()

    def _updateButtons(self):
        """Update the sensitivity of the buttons."""
        self._updateButton.set_sensitive(self._loggable and
                                         self.loggableCruiseLevel!=
                                         self._loggedCruiseLevel)

    def _cruiseLevelChanged(self, spinButton):
        """Called when the cruise level has changed."""
        self._updateButtons()

    def _updateButtonClicked(self, button):
        """Called when the update button is clicked."""
        if self._wizard.cruiseLevelChanged():
            self._loggedCruiseLevel = self.loggableCruiseLevel
            self._updateButtons()

    def _backClicked(self, button):
        """Called when the Back button is pressed."""
        self.goBack()

    def _forwardClicked(self, button):
        """Called when the Forward button is clicked."""
        self._wizard.nextPage()

#-----------------------------------------------------------------------------

class LandingPage(Page):
    """Page for entering landing data."""
    def __init__(self, wizard):
        """Construct the landing page."""
        super(LandingPage, self).__init__(wizard, "landing",
                                          xstr("landing_title"),
                                          xstr("landing_help"),
                                          completedHelp = xstr("landing_chelp"))

        self._flightEnded = False

        alignment = Gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)

        table = Gtk.Table(7, 24)
        table.set_row_spacings(4)
        table.set_col_spacings(16)
        table.set_homogeneous(False)
        alignment.add(table)
        self.setMainWidget(alignment)

        row = 0

        label = Gtk.Label(xstr("landing_metar"))
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 1, 2, row, row+1)

        self._metar = Gtk.Entry()
        self._metar.set_width_chars(40)
        self._metar.set_tooltip_text(xstr("landing_metar_tooltip"))
        self._metar.connect("changed", self._metarChanged)
        self._metar.get_buffer().connect_after("inserted-text", self._metarInserted)
        table.attach(self._metar, 2, 24, row, row+1)
        label.set_mnemonic_widget(self._metar)

        self._updatingMETAR = False

        row += 1

        label = Gtk.Label(xstr("landing_star"))
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 1, 2, row, row + 1)

        self._star = Gtk.ComboBox.new_with_model_and_entry(comboModel)

        self._star.set_entry_text_column(0)
        self._star.get_child().set_width_chars(10)
        self._star.set_tooltip_text(xstr("landing_star_tooltip"))
        self._star.connect("changed", self._upperChangedComboBox)
        self._star.set_sensitive(False)
        table.attach(self._star, 2, 4, row, row + 1)
        label.set_mnemonic_widget(self._star)

        row += 1

        label = Gtk.Label(xstr("landing_transition"))
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 1, 2, row, row + 1)

        self._transition = Gtk.ComboBox.new_with_model_and_entry(comboModel)

        self._transition.set_entry_text_column(0)
        self._transition.get_child().set_width_chars(10)
        self._transition.set_tooltip_text(xstr("landing_transition_tooltip"))
        self._transition.connect("changed", self._upperChangedComboBox)
        self._transition.set_sensitive(False)
        table.attach(self._transition, 2, 4, row, row + 1)
        label.set_mnemonic_widget(self._transition)

        row += 1

        label = Gtk.Label(xstr("landing_runway"))
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 1, 2, row, row + 1)

        self._runway = Gtk.Entry()
        self._runway.set_width_chars(10)
        self._runway.set_tooltip_text(xstr("landing_runway_tooltip"))
        self._runway.connect("changed", self._upperChanged)
        table.attach(self._runway, 2, 4, row, row + 1)
        label.set_mnemonic_widget(self._runway)

        row += 1

        label = Gtk.Label(xstr("landing_approach"))
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 1, 2, row, row + 1)

        self._approachType = Gtk.Entry()
        self._approachType.set_width_chars(10)
        self._approachType.set_tooltip_text(xstr("landing_approach_tooltip"))
        self._approachType.connect("changed", self._upperChanged)
        table.attach(self._approachType, 2, 4, row, row + 1)
        label.set_mnemonic_widget(self._approachType)

        row += 1

        label = Gtk.Label(xstr("landing_vref"))
        label.set_use_markup(True)
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 1, 2, row, row + 1)

        self._vref = IntegerEntry()
        self._vref.set_width_chars(5)
        self._vref.set_tooltip_markup(xstr("landing_vref_tooltip_knots"))
        self._vref.connect("integer-changed", self._vrefChanged)
        table.attach(self._vref, 3, 4, row, row + 1)
        label.set_mnemonic_widget(self._vref)

        self._vrefUnit = Gtk.Label(xstr("label_knots"))
        table.attach(self._vrefUnit, 4, 5, row, row + 1)

        row += 1

        self._antiIceOn = Gtk.CheckButton(xstr("landing_antiice"))
        self._antiIceOn.set_use_underline(True)
        self._antiIceOn.set_tooltip_text(xstr("landing_antiice_tooltip"))
        table.attach(self._antiIceOn, 3, 5, row, row + 1)

        self.addCancelFlightButton()

        self.addPreviousButton(clicked = self._backClicked)

        self._button = self.addNextButton(clicked = self._forwardClicked)

        self._active = False

    @property
    def star(self):
        """Get the STAR or None if none entered."""
        text = self._star.get_child().get_text()
        return text if self._star.get_active()!=0 and text and text!="N/A" \
               else None

    @property
    def transition(self):
        """Get the transition or None if none entered."""
        text = self._transition.get_child().get_text()
        return text if self._transition.get_active()!=0 and text and text!="N/A" \
               else None

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

    @property
    def antiIceOn(self):
        """Get whether the anti-ice system has been turned on."""
        return self._antiIceOn.get_active()

    @antiIceOn.setter
    def antiIceOn(self, value):
        """Set the anti-ice indicator."""
        self._antiIceOn.set_active(value)

    def reset(self):
        """Reset the page if the wizard is reset."""
        super(LandingPage, self).reset()
        self._vref.reset()
        self._antiIceOn.set_active(False)
        self._flightEnded = False
        self._active = False

    def activate(self):
        """Called when the page is activated."""
        self._updatingMETAR = True
        self._metar.get_buffer().set_text(self._wizard.arrivalMETAR, -1)
        self._updatingMETAR = False

        if self._wizard.arrivalSTAR is None:
            self._star.set_active(0)
        else:
            self._star.get_child().set_text(self._wizard.arrivalSTAR)
        self._star.set_sensitive(True)

        self._transition.set_active(0)
        self._transition.set_sensitive(True)

        if self._wizard.landingRunway is None:
            self._runway.set_text("")
        else:
            self._runway.set_text(self._wizard.landingRunway)
        self._runway.set_sensitive(True)

        self._approachType.set_text("")
        self._approachType.set_sensitive(True)

        self._vref.set_int(None)
        self._vref.set_sensitive(True)

        i18nSpeedUnit = self._wizard.gui.flight.getI18NSpeedUnit()
        speedUnit = xstr("label" + i18nSpeedUnit)
        self._vrefUnit.set_text(speedUnit)

        self._vref.set_tooltip_markup(xstr("landing_vref_tooltip" +
                                           i18nSpeedUnit))

        self._updateForwardButton()

        self._active = True

    def flightEnded(self):
        """Called when the flight has ended."""
        super(LandingPage, self).flightEnded()
        self._flightEnded = True
        self._updateForwardButton()

    def changeMETAR(self, metar, fromEditing = True):
        """Change the METAR as a result of an edit on one of the other
        pages."""
        if self._active:
            print("LandingPage.changeMETAR")
            self._updatingMETAR = True
            self._metar.get_buffer().set_text(metar, -1)
            self._updatingMETAR = False

            self._updateForwardButton()

    def _updateForwardButton(self):
        """Update the sensitivity of the forward button."""
        sensitive = self._flightEnded and \
                    self._metar.get_text()!="" and \
                    (self.star is not None or
                     self.transition is not None) and \
                    self._runway.get_text()!="" and \
                    self._approachType.get_text()!="" and \
                    self.vref is not None
        self._button.set_sensitive(sensitive)

    def _upperChanged(self, entry):
        """Called for entry widgets that must be converted to uppercase."""
        entry.set_text(entry.get_text().upper())
        self._updateForwardButton()

    def _upperChangedComboBox(self, comboBox):
        """Called for combo box widgets that must be converted to uppercase."""
        if comboBox.get_active()==-1:
            entry = comboBox.get_child()
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
        wizard = self._wizard

        aircraft = wizard.gui.flight.aircraft
        aircraft.updateVRef()
        aircraft.updateLandingAntiIce()
        if wizard.gui.config.onlineGateSystem and \
           wizard.loggedIn and not self._completed and \
           wizard.bookedFlight.arrivalICAO=="LHBP" and \
           not wizard.entranceExam:
            wizard.getFleet(callback = self._fleetRetrieved, force = True)
        elif wizard.entranceExam:
            self._handleEntranceExamDone()
        else:
            wizard.nextPage()

    def _fleetRetrieved(self, fleet):
        """Callback for the fleet retrieval."""
        self._wizard.nextPage()

    def _metarChanged(self, entry):
        """Called when the METAR has changed."""
        print("LandingPage.metarChanged", self._updatingMETAR)
        if not self._updatingMETAR:
            self._updateForwardButton()
            self._wizard.metarChanged(entry.get_text(), self)

    def _metarInserted(self, buffer, position, text, length):
        """Called when new characters are inserted into the METAR.

        It uppercases all characters."""
        print("LandingPage.metarInserted", self._updatingMETAR)
        if not self._updatingMETAR:
            self._updatingMETAR = True

            buffer.delete_text(position, length)
            buffer.insert_text(position, text.upper(), length)

            self._updatingMETAR = False

    def _handleEntranceExamDone(self):
        """Handle the end of the entrance exam.

        If the there was a NO-GO fault, notify the user that exam is a failure
        and take them back to the student page. Otherwise congratulate, update
        the database to reflect that the exam has been taken and go back to the
        student page."""
        self._wizard.jumpPage("chkfinish")

#-----------------------------------------------------------------------------

class PIREPSaveHelper(object):
    """A helper to use for saving PIREPs."""
    def __init__(self, wizard):
        """Construct the helper."""
        super(PIREPSaveHelper, self).__init__()

        self._wizard = wizard

        self._lastSavePath = None
        self._savePIREPDialog = None

    def addButton(self, page):
        """Add a button to save the PIREP to the given page."""
        return page.addButton(xstr("finish_save"), sensitive = False,
                              clicked = self._saveClicked,
                              tooltip = xstr("finish_save_tooltip"),
                              clickedArg = page)

    def autoSavePIREP(self, page):
        """Perform the automatic saving of the PIREP."""
        self._lastSavePath = os.path.join(self._wizard.gui.config.pirepDirectory,
                                          self._getDefaultPIREPName())
        self._lastSavePath = self._lastSavePath
        self._savePIREP(page, automatic = True)

    def _getDefaultPIREPName(self):
        """Get the default name of the PIREP."""
        gui = self._wizard.gui

        bookedFlight = gui.bookedFlight
        tm = time.gmtime()

        pilotID = self._wizard.pilotID
        if pilotID: pilotID += " "
        return "%s%s %02d%02d %s-%s.pirep" % \
               (pilotID, str(bookedFlight.departureTime.date()),
                tm.tm_hour, tm.tm_min,
                bookedFlight.departureICAO, bookedFlight.arrivalICAO)

    def _saveClicked(self, button, page):
        """Called when the Save PIREP button is clicked."""
        gui = self._wizard.gui

        fileName = self._getDefaultPIREPName()

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

        if result==Gtk.ResponseType.OK:
            self._lastSavePath = dialog.get_filename()
            self._savePIREP(page)

    def _savePIREP(self, page, automatic = False):
        """Perform the saving of the PIREP."""

        gui = self._wizard.gui

        if automatic:
            gui.beginBusy(xstr("finish_autosave_busy"))

        pirep = PIREP(gui.flight)
        error = pirep.save(self._lastSavePath)

        if automatic:
            gui.endBusy()

        if error:
            type = Gtk.MessageType.ERROR
            message = xstr("finish_save_failed")
            secondary = xstr("finish_save_failed_sec") % (error,)
        else:
            type = Gtk.MessageType.INFO
            message = xstr("finish_save_done")
            if automatic:
                secondary = xstr("finish_save_done_sec") % (self._lastSavePath,)
            else:
                secondary = None
            page.setPIREPSaved()

        dialog = Gtk.MessageDialog(parent = gui.mainWindow,
                                   type = type, message_format = message)
        dialog.add_button(xstr("button_ok"), Gtk.ResponseType.OK)
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
            dialog = Gtk.FileChooserDialog(title = WINDOW_TITLE_BASE + " - " +
                                           xstr("finish_save_title"),
                                           action = Gtk.FileChooserAction.SAVE,
                                           buttons = (Gtk.STOCK_CANCEL,
                                                      Gtk.ResponseType.CANCEL,
                                                      Gtk.STOCK_OK, Gtk.ResponseType.OK),
                                           parent = gui.mainWindow)
            dialog.set_modal(True)
            dialog.set_do_overwrite_confirmation(True)

            filter = Gtk.FileFilter()
            filter.set_name(xstr("file_filter_pireps"))
            filter.add_pattern("*.pirep")
            dialog.add_filter(filter)

            filter = Gtk.FileFilter()
            filter.set_name(xstr("file_filter_all"))
            filter.add_pattern("*.*")
            dialog.add_filter(filter)

            self._savePIREPDialog = dialog

        return self._savePIREPDialog

#-----------------------------------------------------------------------------

class FinishPage(Page):
    """Flight finish page."""
    def __init__(self, wizard, saveHelper):
        """Construct the finish page."""
        help = xstr("finish_help") + xstr("finish_help_goodtime")
        super(FinishPage, self).__init__(wizard, "finish",
                                         xstr("finish_title"), help)

        alignment = Gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)

        table = Gtk.Table(10, 2)
        table.set_row_spacings(4)
        table.set_col_spacings(16)
        table.set_homogeneous(False)
        alignment.add(table)
        self.setMainWidget(alignment)

        row = 0

        labelAlignment = Gtk.Alignment(xalign=1.0, xscale=0.0)
        label = Gtk.Label(xstr("finish_rating"))
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, row, row+1)

        labelAlignment = Gtk.Alignment(xalign=0.0, xscale=0.0)
        self._flightRating = Gtk.Label()
        self._flightRating.set_width_chars(8)
        self._flightRating.set_alignment(0.0, 0.5)
        self._flightRating.set_use_markup(True)
        labelAlignment.add(self._flightRating)
        table.attach(labelAlignment, 1, 2, row, row+1)

        row += 1

        labelAlignment = Gtk.Alignment(xalign=1.0, xscale=0.0)
        label = Gtk.Label(xstr("finish_dep_time"))
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, row, row+1)

        labelAlignment = Gtk.Alignment(xalign=0.0, xscale=0.0)
        self._depTime = Gtk.Label()
        self._depTime.set_width_chars(13)
        self._depTime.set_alignment(0.0, 0.5)
        self._depTime.set_use_markup(True)
        self._depTime.set_tooltip_markup(xstr("finish_dep_time_tooltip"))
        labelAlignment.add(self._depTime)
        table.attach(labelAlignment, 1, 2, row, row+1)

        row += 1

        labelAlignment = Gtk.Alignment(xalign=1.0, xscale=0.0)
        label = Gtk.Label(xstr("finish_flight_time"))
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, row, row+1)

        labelAlignment = Gtk.Alignment(xalign=0.0, xscale=0.0)
        self._flightTime = Gtk.Label()
        self._flightTime.set_width_chars(10)
        self._flightTime.set_alignment(0.0, 0.5)
        self._flightTime.set_use_markup(True)
        labelAlignment.add(self._flightTime)
        table.attach(labelAlignment, 1, 2, row, row+1)

        row += 1

        labelAlignment = Gtk.Alignment(xalign=1.0, xscale=0.0)
        label = Gtk.Label(xstr("finish_block_time"))
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, row, row+1)

        labelAlignment = Gtk.Alignment(xalign=0.0, xscale=0.0)
        self._blockTime = Gtk.Label()
        self._blockTime.set_width_chars(10)
        self._blockTime.set_alignment(0.0, 0.5)
        self._blockTime.set_use_markup(True)
        labelAlignment.add(self._blockTime)
        table.attach(labelAlignment, 1, 2, row, row+1)

        row += 1

        labelAlignment = Gtk.Alignment(xalign=1.0, xscale=0.0)
        label = Gtk.Label(xstr("finish_arr_time"))
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, row, row+1)

        labelAlignment = Gtk.Alignment(xalign=0.0, xscale=0.0)
        self._arrTime = Gtk.Label()
        self._arrTime.set_width_chars(13)
        self._arrTime.set_alignment(0.0, 0.5)
        self._arrTime.set_use_markup(True)
        self._arrTime.set_tooltip_markup(xstr("finish_arr_time_tooltip"))
        labelAlignment.add(self._arrTime)
        table.attach(labelAlignment, 1, 2, row, row+1)

        row += 1

        labelAlignment = Gtk.Alignment(xalign=1.0, xscale=0.0)
        label = Gtk.Label(xstr("finish_distance"))
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, row, row+1)

        labelAlignment = Gtk.Alignment(xalign=0.0, xscale=0.0)
        self._distanceFlown = Gtk.Label()
        self._distanceFlown.set_width_chars(10)
        self._distanceFlown.set_alignment(0.0, 0.5)
        self._distanceFlown.set_use_markup(True)
        labelAlignment.add(self._distanceFlown)
        table.attach(labelAlignment, 1, 2, row, row+1)

        row += 1

        labelAlignment = Gtk.Alignment(xalign=1.0, xscale=0.0)
        label = Gtk.Label(xstr("finish_fuel"))
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, row, row+1)

        labelAlignment = Gtk.Alignment(xalign=0.0, xscale=0.0)
        self._fuelUsed = Gtk.Label()
        self._fuelUsed.set_width_chars(10)
        self._fuelUsed.set_alignment(0.0, 0.5)
        self._fuelUsed.set_use_markup(True)
        labelAlignment.add(self._fuelUsed)
        table.attach(labelAlignment, 1, 2, row, row+1)

        row += 1

        labelAlignment = Gtk.Alignment(xalign = 1.0, xscale = 0.0,
                                       yalign = 0.5, yscale = 0.0)
        label = Gtk.Label(xstr("finish_type"))
        label.set_use_underline(True)
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, row, row+1)

        self._onlineFlight = Gtk.CheckButton(xstr("finish_online"))
        self._onlineFlight.set_use_underline(True)
        self._onlineFlight.set_tooltip_text(xstr("finish_online_tooltip"))
        onlineFlightAlignment = Gtk.Alignment(xalign=0.0, xscale=0.0)
        onlineFlightAlignment.add(self._onlineFlight)
        table.attach(onlineFlightAlignment, 1, 2, row, row + 1)

        row += 1

        labelAlignment = Gtk.Alignment(xalign = 1.0, xscale = 0.0,
                                       yalign = 0.5, yscale = 0.0)
        self._gateLabel = Gtk.Label(xstr("finish_gate"))
        self._gateLabel.set_use_underline(True)
        labelAlignment.add(self._gateLabel)
        table.attach(labelAlignment, 0, 1, row, row+1)

        self._gatesModel = Gtk.ListStore(str)

        self._gate = Gtk.ComboBox(model = self._gatesModel)
        renderer = Gtk.CellRendererText()
        self._gate.pack_start(renderer, True)
        self._gate.add_attribute(renderer, "text", 0)
        self._gate.set_tooltip_text(xstr("finish_gate_tooltip"))
        self._gate.connect("changed", self._gateChanged)
        gateAlignment = Gtk.Alignment(xalign=0.0, xscale=1.0)
        gateAlignment.add(self._gate)
        table.attach(gateAlignment, 1, 2, row, row+1)
        self._gateLabel.set_mnemonic_widget(self._gate)

        self.addButton(xstr("finish_newFlight"),
                       sensitive = True,
                       clicked = self._newFlightClicked,
                       tooltip = xstr("finish_newFlight_tooltip"),
                       padding = 16)

        self.addPreviousButton(clicked = self._backClicked)

        self._saveHelper = saveHelper
        self._saveButton = saveHelper.addButton(self)

        self._tooBigTimeDifference = False
        self._deferredAutoSave = False
        self._pirepSaved = False
        self._pirepSent = False

        self._sendButton = self.addButton(xstr("sendPIREP"), default = True,
                                          sensitive = False,
                                          clicked = self._sendClicked,
                                          tooltip = xstr("sendPIREP_tooltip"))

        # self._formatTime(datetime.datetime(1970, 1, 1, 0, 10), 10*60.0)
        # self._formatTime(datetime.datetime(1970, 1, 1, 0, 10), 20*60.0)
        # self._formatTime(datetime.datetime(1970, 1, 1, 0, 10), 0*60.0)
        # self._formatTime(datetime.datetime(1970, 1, 1, 0, 10), (23*60.0+50)*60.0)
        # self._formatTime(datetime.datetime(1970, 1, 1, 1, 0), (1*60.0+5)*60.0)
        # self._formatTime(datetime.datetime(1970, 1, 1, 1, 0), (0*60.0+50)*60.0)
        # self._formatTime(datetime.datetime(1970, 1, 1, 23, 55), (0*60.0+5)*60.0)
        # self._formatTime(datetime.datetime(1970, 1, 1, 23, 55), (23*60.0+45)*60.0)

    @property
    def online(self):
        """Get whether the flight was an online flight or not."""
        return self._onlineFlight.get_active()

    def activate(self):
        """Activate the page."""
        self._deferredAutoSave = False
        self._pirepSaved = False
        self._pirepSent = False

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

        self._onlineFlight.set_active(self._wizard.loggedIn)

        self._gatesModel.clear()
        if self._wizard.gui.config.onlineGateSystem and \
           self._wizard.loggedIn and \
           self._wizard.bookedFlight.arrivalICAO=="LHBP" and \
           not self._wizard.entranceExam:
            occupiedGateNumbers = self._wizard._fleet.getOccupiedGateNumbers()
            for gate in lhbpGates.gates:
                if gate.isAvailable(lhbpGates, occupiedGateNumbers):
                    self._gatesModel.append([gate.number])
            self._gateLabel.set_sensitive(True)
            self._gate.set_sensitive(True)
            self._gate.set_active(-1)
        else:
            self._gateLabel.set_sensitive(False)
            self._gate.set_sensitive(False)

        self._updateTimes()

    def updateButtons(self):
        """Update the sensitivity state of the buttons."""
        gui = self._wizard.gui
        faultsExplained = gui.faultsFullyExplained
        timesCorrect = not self._tooBigTimeDifference or \
                       gui.hasComments or gui.hasDelayCode
        sensitive = gui.flight is not None and \
                    gui.flight.stage==const.STAGE_END and \
                    (self._gatesModel.get_iter_first() is None or
                     self._gate.get_active()>=0) and \
                     faultsExplained and timesCorrect

        self._updateHelp(faultsExplained, timesCorrect)

        wasSensitive = self._saveButton.get_sensitive()

        if gui.config.pirepAutoSave and sensitive and not wasSensitive:
            if gui.isWizardActive():
                self._saveHelper.autoSavePIREP(self)
            else:
                self._deferredAutoSave = True

        if not sensitive:
            self._deferredAutoSave = False

        self._saveButton.set_sensitive(sensitive)
        self._sendButton.set_sensitive(sensitive and
                                       self._wizard.bookedFlight.id is not None)

    def grabDefault(self):
        """If the page has a default button, make it the default one."""
        super(FinishPage, self).grabDefault()
        if self._deferredAutoSave:
            self._saveHelper.autoSavePIREP(self)
            self._deferredAutoSave = False

    def setPIREPSaved(self):
        """Mark the PIREP as saved."""
        self._pirepSaved = True

    def _backClicked(self, button):
        """Called when the Back button is pressed."""
        self.goBack()

    def _gateChanged(self, comboBox):
        """Called when the arrival gate has changed."""
        self.updateButtons()

    def _newFlightClicked(self, button):
        """Called when the new flight button is clicked."""
        gui = self._wizard.gui
        if not self._pirepSent and not self._pirepSaved:
            dialog = Gtk.MessageDialog(parent = gui.mainWindow,
                                       type = Gtk.MessageType.QUESTION,
                                       message_format = xstr("finish_newFlight_question"))

            dialog.add_button(xstr("button_no"), Gtk.ResponseType.NO)
            dialog.add_button(xstr("button_yes"), Gtk.ResponseType.YES)

            dialog.set_title(WINDOW_TITLE_BASE)
            result = dialog.run()
            dialog.hide()
            if result!=Gtk.ResponseType.YES:
                return

        gui.reset()

    def _sendClicked(self, button):
        """Called when the Send button is clicked."""
        pirep = PIREP(self._wizard.gui.flight)
        self._wizard.gui.sendPIREP(pirep,
                                   callback = self._handlePIREPSent)

    def _handlePIREPSent(self, returned, result):
        """Callback for the PIREP sending result."""
        self._pirepSent = returned and result.success
        if self._wizard.gui.config.onlineGateSystem and \
           self._wizard.loggedIn and not self._wizard.entranceExam and \
           returned and result.success:
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

    def _formatTime(self, scheduledTime, realTimestamp, warningError):
        """Format the departure or arrival time based on the given data as a
        markup for a label."""
        (warning, error) = warningError
        realTime = time.gmtime(realTimestamp)

        if warning:
            colour = "red" if error else "orange"
            markupBegin = '<span foreground="%s">' % (colour,)
            markupEnd = '</span>'
        else:
            markupBegin = markupEnd = ""

        markup = "<b>%s%02d:%02d [%02d:%02d]%s</b>" % \
                 (markupBegin,
                  realTime.tm_hour, realTime.tm_min,
                  scheduledTime.hour, scheduledTime.minute,
                  markupEnd)

        return markup

    def _updateTimes(self):
        """Format the flight times and the help text according to the flight
        type.

        The buttons are also updated.
        """
        flight = self._wizard.gui._flight
        bookedFlight = flight.bookedFlight

        (departureWarning, departureError) = flight.blockTimeStartWrong
        (arrivalWarning, arrivalError) = flight.blockTimeEndWrong

        if bookedFlight.flightType==const.FLIGHTTYPE_VIP:
            departureError = arrivalError = False

        self._tooBigTimeDifference = departureError and arrivalError

        self._depTime.set_markup(self._formatTime(bookedFlight.departureTime,
                                                  flight.blockTimeStart,
                                                  (departureWarning,
                                                   departureError)))

        self._arrTime.set_markup(self._formatTime(bookedFlight.arrivalTime,
                                                  flight.blockTimeEnd,
                                                  (arrivalWarning,
                                                   arrivalError)))

        self.updateButtons()

    def _updateHelp(self, faultsExplained, timesCorrect):
        """Update the help text according to the actual situation."""
        if not faultsExplained:
            self.setHelp(xstr("finish_help") + xstr("finish_help_faults"))
        elif not timesCorrect:
            self.setHelp(xstr("finish_help") + xstr("finish_help_wrongtime"))
        else:
            self.setHelp(xstr("finish_help") + xstr("finish_help_goodtime"))


#-----------------------------------------------------------------------------

class CheckFlightFinishPage(Page):
    """Finish page for a check flight."""
    def __init__(self, wizard, saveHelper):
        """Construct the check flight finish page."""
        super(CheckFlightFinishPage, self).__init__(wizard,
                                                    "chkfinish",
                                                    xstr("chkfinish_title"),
                                                    "")

        alignment = Gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 1.0, yscale = 1.0)
        self._label = Gtk.Label()
        alignment.add(self._label)

        self.setMainWidget(alignment)

        self._saveHelper = saveHelper
        self._saveButton = saveHelper.addButton(self)

        self._button = self.addNextButton(sensitive = False,
                                          clicked =  self._forwardClicked)

    def activate(self):
        """Activate the page."""
        wizard = self._wizard
        loginResult = wizard.loginResult
        gui = wizard.gui
        rating = gui.flight.logger.getRating()

        if rating>=0:
            loginResult.checkFlightStatus = True

        firstOfficer = \
          loginResult.entryExamPassed and loginResult.checkFlightStatus

        if firstOfficer:
            loginResult.rank = "FO"

        if rating<0:
            mainMessage = xstr("chkfinish_failed")
        else:
            mainMessage = xstr("chkfinish_passed_begin")
            if firstOfficer:
                mainMessage += xstr("chkfinish_passed_fo")
            mainMessage += xstr("chkfinish_passed_end")

        if firstOfficer:
            nextMessage = xstr("chkfinish_next")
        else:
            nextMessage = xstr("chkfinish_next_student_begin")
            if not loginResult.entryExamPassed and \
               not loginResult.checkFlightStatus:
                nextMessage += xstr("chkfinish_next_student_nothing")
            elif loginResult.entryExamPassed and \
                 not loginResult.checkFlightStatus:
                nextMessage += xstr("chkfinish_next_student_no_flight")
            elif not loginResult.entryExamPassed and \
                 loginResult.checkFlightStatus:
                nextMessage += xstr("chkfinish_next_student_no_exam")

        self._label.set_text(mainMessage +
                             xstr("chkfinish_savepirep") +
                             nextMessage)
        self._label.set_use_markup(True)
        self._label.set_alignment(0.5, 0.0)

        self._saveButton.set_sensitive(True)
        self._button.set_sensitive(True)

    def _forwardClicked(self, button):
        """Jump to the student page if there are some tasks to do,
        or to the flight selection page, if the pilot is allowed to perform
        MAVA flights."""
        wizard = self._wizard
        gui = wizard.gui

        loginResult = wizard.loginResult
        if loginResult.checkFlightStatus:
            gui.beginBusy(xstr("chkfinish_updateweb_busy"))
            gui.webHandler.setCheckFlightPassed(self._checkFlightPassedSetCallback,
                                                wizard.checkFlightAircraftType)
        else:
            self._resetGUI()

    def _checkFlightPassedSetCallback(self, returned, result):
        """Called when the check flight status has been set."""
        GObject.idle_add(self._checkFlightPassedSet, returned, result)

    def _checkFlightPassedSet(self, returned, result):
        """Handle the result of an attempt to set the check flight status."""
        gui = self._wizard.gui

        gui.endBusy()

        if returned:
            self._resetGUI()
        else:
            dialog = Gtk.MessageDialog(parent = gui.mainWindow,
                                       type = Gtk.MessageType.ERROR,
                                       message_format =
                                       xstr("chkfinish_passedset_failed"))
            dialog.set_title(WINDOW_TITLE_BASE + " - " +
                             xstr("chkfinish_passedset_failed_title"))
            dialog.format_secondary_markup(xstr("chkfinish_passedset_failed_secondary"))

            dialog.add_button(xstr("button_ok"), 0)

            dialog.run()
            dialog.hide()

    def _resetGUI(self):
        """Reset the GUI."""
        gui = self._wizard.gui
        gui.reset()

#-----------------------------------------------------------------------------

class Wizard(Gtk.VBox):
    """The flight wizard."""
    def __init__(self, gui):
        """Construct the wizard."""
        super(Wizard, self).__init__()

        self.gui = gui

        self._pages = []
        self._currentPage = None

        self._loginPage = LoginPage(self)
        self._pages.append(self._loginPage)
        self._flightSelectionPage = FlightSelectionPage(self)
        self._pages.append(self._flightSelectionPage)
        self._pages.append(GateSelectionPage(self))
        self._pages.append(RegisterPage(self))
        self._studentPage = StudentPage(self)
        self._pages.append(self._studentPage)
        self._pages.append(ConnectPage(self))
        self._payloadPage = PayloadPage(self)
        self._pages.append(self._payloadPage)
        self._payloadIndex = len(self._pages)
        self._pages.append(TimePage(self))
        self._routePage = RoutePage(self)
        self._pages.append(self._routePage)
        self._simBriefSetupPage = SimBriefSetupPage(self)
        self._pages.append(self._simBriefSetupPage)
        self._simBriefingPage = SimBriefingPage(self)
        self._pages.append(self._simBriefingPage)
        self._pages.append(FuelPage(self))
        self._departureBriefingPage = BriefingPage(self, True)
        self._pages.append(self._departureBriefingPage)
        self._arrivalBriefingPage = BriefingPage(self, False)
        self._pages.append(self._arrivalBriefingPage)
        self._arrivalBriefingIndex = len(self._pages)
        self._takeoffPage = TakeoffPage(self)
        self._pages.append(self._takeoffPage)
        self._cruisePage = CruisePage(self)
        self._pages.append(self._cruisePage)
        self._landingPage = LandingPage(self)
        self._pages.append(self._landingPage)

        pirepSaveHelper = PIREPSaveHelper(self)

        self._finishPage = FinishPage(self, pirepSaveHelper)
        self._pages.append(self._finishPage)
        self._pages.append(CheckFlightFinishPage(self, pirepSaveHelper))

        self._requestedWidth = None
        self._requestedHeight = None

        self.connect("size-allocate", self._sizeAllocate)

        for page in self._pages:
            page.show_all()
            page.setStyle()

        self._initialize()
        self._allocateSize()

    def _sizeAllocate(self, widget, allocation):
        if self._requestedWidth is not None and \
           self._requestedHeight is not None:
           return

        (maxWidth, maxHeight) = self._allocateSize()

        self._requestedWidth = maxWidth
        self._requestedHeight = maxHeight

    def _allocateSize(self):
        """Perform the real size allocation."""

        if self._currentPage is not None:
            self.remove(self._pages[self._currentPage])

        maxWidth = 0
        maxHeight = 0
        for page in self._pages:
            self.add(page)
            self.show_all()
            pageSizeRequest = page.size_request()
            width = pageSizeRequest.width
            height = pageSizeRequest.height
            maxWidth = max(maxWidth, width)
            maxHeight = max(maxHeight, height)
            self.remove(page)

        if self._currentPage is not None:
            self.add(self._pages[self._currentPage])

        self.set_size_request(maxWidth, maxHeight)

        return (maxWidth, maxHeight)

    @property
    def pilotID(self):
        """Get the pilot ID, if given."""
        return self._loginPage.pilotID

    @property
    def entranceExam(self):
        """Get whether an entrance exam is about to be taken."""
        return self._loginResult is not None and self._loginResult.rank=="STU"

    @property
    def loggedIn(self):
        """Indicate if there was a successful login."""
        return self._loginResult is not None

    @property
    def loginResult(self):
        """Get the login result."""
        return self._loginResult

    @property
    def checkFlightAircraftType(self):
        """Get the type of the aircraft used to perform the check flight."""
        return self._studentPage.aircraftType

    def setCurrentPage(self, index, finalize = False, fromPageShift = None):
        """Set the current page to the one with the given index.

        @param fromPageShift if given, the relative index of one of the
        previous pages that should be used as the from-page of the next
        page. E.g. if fromPageShift is 1, the previous page will be the
        from-page."""
        assert index < len(self._pages)

        fromPage = self._currentPage
        if fromPage is not None:
            page = self._pages[fromPage]
            if finalize and not page._completed:
                page.complete()
            page.prepareHide()
            self.remove(page)
            if fromPageShift is not None:
                fromPage -= fromPageShift

        self._currentPage = index
        page = self._pages[index]
        self.add(page)
        if page._fromPage is None:
            page._fromPage = fromPage
            page.initialize()
        page.prepareShow()
        self.show_all()
        if fromPage is not None:
            self.grabDefault()

    @property
    def bookedFlight(self):
        """Get the booked flight selected."""
        return self._bookedFlight

    @property
    def numCockpitCrew(self):
        """Get the number of cockpit crew members."""
        return self._payloadPage.numCockpitCrew

    @property
    def numCabinCrew(self):
        """Get the number of cabin crew members."""
        return self._payloadPage.numCabinCrew

    @property
    def numPassengers(self):
        """Get the number of passengers."""
        return self._payloadPage.numPassengers

    @property
    def numChildren(self):
        """Get the number of child passengers."""
        return self._payloadPage.numChildren

    @property
    def numInfants(self):
        """Get the number of infant passengers."""
        return self._payloadPage.numInfants

    @property
    def bagWeight(self):
        """Get the baggage weight."""
        return self._payloadPage.bagWeight

    @property
    def cargoWeight(self):
        """Get the cargo weight."""
        return self._payloadPage.cargoWeight

    @property
    def mailWeight(self):
        """Get the mail weight."""
        return self._payloadPage.mailWeight

    @property
    def zfw(self):
        """Get the calculated ZFW value."""
        return 0 if self._bookedFlight is None \
               else self._payloadPage.calculateZFW()

    @property
    def filedCruiseLevel(self):
        """Get the filed cruise level."""
        return self._routePage.filedCruiseLevel

    @filedCruiseLevel.setter
    def filedCruiseLevel(self, fl):
        """Set the filed cruise level."""
        self._routePage.filedCruiseLevel = fl

    @property
    def filedCruiseAltitude(self):
        """Get the filed cruise altitude."""
        return self._routePage.filedCruiseLevel * 100

    @property
    def cruiseAltitude(self):
        """Get the cruise altitude."""
        level = self._cruisePage.cruiseLevel if self._cruisePage.activated \
                else self._routePage.filedCruiseLevel
        return level * 100

    @property
    def loggableCruiseAltitude(self):
        """Get the cruise altitude that can be logged."""
        if self._cruisePage.activated:
            return self._cruisePage.loggableCruiseLevel * 100
        else:
            return 0

    @property
    def route(self):
        """Get the route."""
        return self._routePage.route

    @route.setter
    def route(self, r):
        """Set the route."""
        self._routePage.route = r

    @property
    def alternate(self):
        """Get the ICAO code of the alternate airport."""
        return self._routePage.alternate

    @alternate.setter
    def alternate(self, a):
        """Set the ICAO code of the alternate airport."""
        self._routePage.alternate = a

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

    @sid.setter
    def sid(self, s):
        """Set the SID."""
        self._takeoffPage.sid = s

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
    def derate(self):
        """Get the derate value."""
        return self._takeoffPage.derate

    @property
    def takeoffAntiIceOn(self):
        """Get whether the anti-ice system was on during take-off."""
        return self._takeoffPage.antiIceOn

    @takeoffAntiIceOn.setter
    def takeoffAntiIceOn(self, value):
        """Set anti-ice on indicator."""
        self._takeoffPage.antiIceOn = value

    @property
    def rtoIndicated(self):
        """Get whether the pilot has indicated that an RTO has occured."""
        return self._takeoffPage.rtoIndicated

    @property
    def arrivalRunway(self):
        """Get the arrival runway."""
        return self._landingPage.runway

    @property
    def star(self):
        """Get the STAR."""
        return self._landingPage.star

    @star.setter
    def star(self, s):
        """Set the STAR."""
        self._landingPage.star = s

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
    def landingAntiIceOn(self):
        """Get whether the anti-ice system was on during landing."""
        return self._landingPage.antiIceOn

    @landingAntiIceOn.setter
    def landingAntiIceOn(self, value):
        """Set anti-ice on indicator."""
        self._landingPage.antiIceOn = value

    @property
    def flightType(self):
        """Get the flight type."""
        return self._finishPage.flightType

    @property
    def online(self):
        """Get whether the flight was online or not."""
        return self._finishPage.online

    @property
    def usingSimBrief(self):
        """Indicate if we are using a SimBrief briefing or not."""
        return self._usingSimBrief

    @usingSimBrief.setter
    def usingSimBrief(self, x):
        """Set whether we are using a SimBrief briefing or not."""
        self._usingSimBrief = x

    def nextPage(self, finalize = True):
        """Go to the next page."""
        nextPageID = self._pages[self._currentPage].nextPageID
        self.jumpPage(1 if nextPageID is None else nextPageID, finalize)

    def jumpPage(self, countOrID, finalize = True, fromPageShift = None):
        """Go to the page which is 'count' pages after the current one."""
        if isinstance(countOrID, str):
            targetIndex = self._getIndexOf(countOrID)
        else:
            targetIndex = self._currentPage + countOrID
        self.setCurrentPage(targetIndex,
                            finalize = finalize, fromPageShift = fromPageShift)

    def grabDefault(self):
        """Make the default button of the current page the default."""
        self._pages[self._currentPage].grabDefault()

    def connected(self, fsType, descriptor):
        """Called when the connection could be made to the simulator."""
        self.nextPage()

    def reset(self, loginResult):
        """Resets the wizard to go back to the login page."""
        self._initialize(keepLoginResult = loginResult is None,
                         loginResult = loginResult)

    def setStage(self, stage):
        """Set the flight stage to the given one."""
        if stage!=const.STAGE_END:
            self._cruisePage.setLoggable(Flight.canLogCruiseAltitude(stage))

        if stage==const.STAGE_TAKEOFF:
            self._takeoffPage.allowForward()
        elif stage==const.STAGE_LANDING:
            if not self._arrivalBriefingPage.metarEdited:
                print("Downloading arrival METAR again")
                self.gui.webHandler.getMETARs(self._arrivalMETARCallback,
                                              [self._bookedFlight.arrivalICAO])

        elif stage==const.STAGE_END:
            for page in self._pages:
                page.flightEnded()

    def _initialize(self, keepLoginResult = False, loginResult = None):
        """Initialize the wizard."""
        if not keepLoginResult:
            self._loginResult = loginResult

        self._loginCallback = None

        self._fleet = None
        self._fleetCallback = None

        self._bookedFlight = None
        self._departureGate = "-"
        self._fuelData = None
        self._departureNOTAMs = None
        self._departureMETAR = None
        self._arrivalNOTAMs = None
        self._arrivalMETAR = None
        self._usingSimBrief = None
        self.takeoffRunway = None
        self.departureSID = None
        self.landingRunway = None
        self.arrivalSTAR = None

        firstPage = 0 if self._loginResult is None else 1
        for page in self._pages[firstPage:]:
            page.reset()

        self.setCurrentPage(firstPage)
        #self.setCurrentPage(10)

    @property
    def isDepartureGateTaxiThrough(self):
        """Determine if the departure gate is a taxi-through one."""
        if self._departureGate=="-":
            return True
        else:
            gate = lhbpGates.find(self._departureGate)
            return False if gate is None else gate.taxiThrough

    def login(self, callback, pilotID, password):
        """Called when the login button was clicked."""
        self._loginCallback = callback
        if pilotID is None:
            loginResult = self._loginResult
            assert loginResult is not None and loginResult.loggedIn
            pilotID = loginResult.pilotID
            password = loginResult.password
            busyMessage = xstr("reload_busy")
        else:
            self._loginResult = None
            busyMessage = xstr("login_busy")

        self.gui.beginBusy(busyMessage)

        self.gui.webHandler.login(self._loginResultCallback,
                                  pilotID, password)

    def reloadFlights(self, callback):
        """Reload the flights from the MAVA server."""
        self.login(callback, None, None)

    def addFlight(self, bookedFlight):
        """Add the given booked flight to the flight selection page."""
        self._flightSelectionPage.addFlight(bookedFlight)

    def reflyFlight(self, bookedFlight):
        """Add the given booked flight to the flight selection page."""
        self._removePendingFlight(bookedFlight)
        self._flightSelectionPage._reflyFlight(bookedFlight)

    def deleteFlight(self, bookedFlight):
        """Remove the given flight from the pending flight list."""
        self._removePendingFlight(bookedFlight)
        self._flightSelectionPage._updatePending()

    def cancelFlight(self, reloadCallback):
        """Cancel the flight.

        If it is an entry exam flight, we go back to the student page.
        Otherwise we reload the flights."""
        if self.entranceExam:
            self.reset(None)
            self.jumpPage("student")
        else:
            self.reloadFlights(reloadCallback)

    def cruiseLevelChanged(self):
        """Called when the cruise level is changed."""
        return self.gui.cruiseLevelChanged()

    def metarChanged(self, metar, originator):
        """Called when a METER is changed on on of the pages.

        originator is the page that originated the changed. It will be used to
        determine which METAR (departure or arrival) has changed."""
        metar = metar.upper()
        if originator in [self._departureBriefingPage, self._takeoffPage]:
            self.departureMETARChanged(metar, originator)
        else:
            self.arrivalMETARChanged(metar, originator)

    def departureMETARChanged(self, metar, originator):
        """Called when the departure METAR has been edited on one of the
        pages.

        originator is the page that originated the change. It will not be
        called to set the METAR, while others will be."""
        for page in [self._departureBriefingPage, self._takeoffPage]:
            if page is not originator:
                page.changeMETAR(metar)

    def arrivalMETARChanged(self, metar, originator, fromDownload = False):
        """Called when the arrival METAR has been edited on one of the
        pages.

        originator is the page that originated the change. It will not be
        called to set the METAR, while others will be."""
        for page in [self._arrivalBriefingPage, self._landingPage]:
            if page is not originator:
                page.changeMETAR(metar, fromEditing = not fromDownload)

    def _removePendingFlight(self, flight):
        """Remove the given pending flight from the login result."""
        for flights in [self._loginResult.reportedFlights,
                        self._loginResult.rejectedFlights]:
            for f in flights:
                if f.id==flight.id:
                    flights.remove(f)
                    return

    def _loginResultCallback(self, returned, result):
        """The login result callback, called in the web handler's thread."""
        GObject.idle_add(self._handleLoginResult, returned, result)

    def _handleLoginResult(self, returned, result):
        """Handle the login result."""
        self.gui.endBusy()
        isReload = self._loginResult is not None
        if returned:
            if result.loggedIn:
                self._loginResult = result
                self.gui.loginSuccessful()
            else:
                if isReload:
                    message = xstr("reload_failed")
                else:
                    message = xstr("login_entranceExam_invalid"
                                   if self.entranceExam else
                                   xstr("login_invalid"))
                dialog = Gtk.MessageDialog(parent = self.gui.mainWindow,
                                           type = Gtk.MessageType.ERROR,
                                           message_format = message)
                dialog.add_button(xstr("button_ok"), Gtk.ResponseType.OK)
                dialog.set_title(WINDOW_TITLE_BASE)
                if isReload:
                    secondary = xstr("reload_failed_sec")
                else:
                    secondary = xstr("login_entranceExam_invalid_sec"
                                     if self.entranceExam else
                                     xstr("login_invalid_sec"))
                dialog.format_secondary_markup(secondary)
                dialog.run()
                dialog.hide()
        else:
            message = xstr("reload_failconn") if isReload \
                      else xstr("login_failconn")
            dialog = Gtk.MessageDialog(parent = self.gui.mainWindow,
                                       type = Gtk.MessageType.ERROR,
                                       message_format = message)
            dialog.add_button(xstr("button_ok"), Gtk.ResponseType.OK)
            dialog.set_title(WINDOW_TITLE_BASE)
            secondary = xstr("reload_failconn_sec") if isReload \
                        else xstr("login_failconn_sec")
            dialog.format_secondary_markup(secondary)

            dialog.run()
            dialog.hide()

        callback = self._loginCallback
        self._loginCallback = None
        callback(returned, result)

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

    def updateRTO(self):
        """Update the RTO state.

        The RTO checkbox will be enabled if the flight has an RTO state and the
        comments field contains some text."""
        flight = self.gui.flight
        rtoEnabled = flight is not None and flight.hasRTO and \
                     self.gui.hasComments
        self._takeoffPage.setRTOEnabled(rtoEnabled)

    def commentsChanged(self):
        """Called when the comments have changed."""
        self.updateRTO()
        self._finishPage.updateButtons()

    def delayCodesChanged(self):
        """Called when the delay codes have changed."""
        self._finishPage.updateButtons()

    def faultExplanationsChanged(self):
        """Called when the faults and their explanations have changed."""
        self._finishPage.updateButtons()

    def rtoToggled(self, indicated):
        """Called when the RTO indication has changed."""
        self.gui.rtoToggled(indicated)

    def finalizeCEF(self):
        """Called when any CEF browsers should be finalized."""
        self._simBriefingPage.finalizeCEF()

    def _connectSimulator(self, simulatorType):
        """Connect to the simulator."""
        self.gui.connectSimulator(self._bookedFlight, simulatorType)

    def _arrivalMETARCallback(self, returned, result):
        """Called when the METAR of the arrival airport is retrieved."""
        GObject.idle_add(self._handleArrivalMETAR, returned, result)

    def _handleArrivalMETAR(self, returned, result):
        """Called when the METAR of the arrival airport is retrieved."""
        icao = self._bookedFlight.arrivalICAO
        if returned and icao in result.metars:
            metar = result.metars[icao]
            if metar!="":
                self._arrivalBriefingPage.setMETAR(metar)

    def _getIndexOf(self, pageID):
        """Get the index for the given page ID.

        It is an assertion failure if the ID is not found."""
        for index in range(0, len(self._pages)):
            page = self._pages[index]
            if page.id==pageID:
                return index
        assert False

#-----------------------------------------------------------------------------
