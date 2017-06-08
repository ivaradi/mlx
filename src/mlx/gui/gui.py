# -*- coding: utf-8 -*-

from statusicon import StatusIcon
from statusbar import Statusbar
from info import FlightInfo
from update import Updater
from mlx.gui.common import *
from mlx.gui.flight import Wizard
from mlx.gui.monitor import MonitorWindow
from mlx.gui.weighthelp import WeightHelp
from mlx.gui.gates import FleetGateStatus
from mlx.gui.prefs import Preferences
from mlx.gui.checklist import ChecklistEditor
from mlx.gui.callouts import ApproachCalloutsEditor
from mlx.gui.flightlist import AcceptedFlightsWindow
from mlx.gui.pirep import PIREPViewer, PIREPEditor
from mlx.gui.bugreport import BugReportDialog
from mlx.gui.acars import ACARS
from mlx.gui.timetable import TimetableWindow
import cef

import mlx.const as const
import mlx.fs as fs
import mlx.flight as flight
import mlx.logger as logger
import mlx.acft as acft
import mlx.web as web
import mlx.singleton as singleton
import mlx.airports as airports
from  mlx.i18n import xstr, getLanguage
from mlx.pirep import PIREP

import time
import threading
import sys
import datetime
import webbrowser

#------------------------------------------------------------------------------

## @package mlx.gui.gui
#
# The main GUI class.
#
# The \ref GUI class is the main class of the GUI. It is a connection listener,
# and aggregates all the windows, the menu, etc. It maintains the connection to
# the simulator as well as the flight object.

#------------------------------------------------------------------------------

class GUI(fs.ConnectionListener):
    """The main GUI class."""
    _authors = [ (u"Váradi", u"István", "prog_test"),
                 (u"Galyassy", u"Tamás", "negotiation"),
                 (u"Kurják", u"Ákos", "test"),
                 (u"Nagy", u"Dániel", "test"),
                 (u"Radó", u"Iván", "test"),
                 (u"Petrovszki", u"Gábor", "test"),
                 (u"Serfőző", u"Tamás", "test"),
                 (u"Szebenyi", u"Bálint", "test"),
                 (u"Zsebényi-Loksa", u"Gergely", "test") ]

    def __init__(self, programDirectory, config):
        """Construct the GUI."""
        gobject.threads_init()

        self._programDirectory = programDirectory
        self.config = config
        self._connecting = False
        self._reconnecting = False
        self._connected = False
        self._logger = logger.Logger(self)
        self._flight = None
        self._simulator = None
        self._fsType = None
        self._monitoring = False

        self._fleet = None

        self._fleetCallback = None

        self._updatePlaneCallback = None
        self._updatePlaneTailNumber = None
        self._updatePlaneStatus = None
        self._updatePlaneGateNumber = None

        self._stdioLock = threading.Lock()
        self._stdioText = ""
        self._stdioStartingLine = True

        self._sendPIREPCallback = None
        self._sendBugReportCallback = None

        self._credentialsCondition = threading.Condition()
        self._credentialsAvailable = False
        self._credentialsUserName = None
        self._credentialsPassword = None

        self.webHandler = web.Handler(config, self._getCredentialsCallback)
        self.webHandler.start()

        self.toRestart = False

    def build(self, iconDirectory):
        """Build the GUI."""

        self._mainWindow = window = gtk.Window()
        window.set_title(WINDOW_TITLE_BASE)
        window.set_icon_from_file(os.path.join(iconDirectory, "logo.ico"))
        window.set_resizable(False)
        window.connect("delete-event", self.deleteMainWindow)
        window.connect("window-state-event", self._handleMainWindowState)
        if os.name=="nt":
            window.connect("leave-notify-event", self._handleLeaveNotify)
        accelGroup = gtk.AccelGroup()
        window.add_accel_group(accelGroup)
        window.realize()

        mainVBox = gtk.VBox()
        window.add(mainVBox)

        self._preferences = Preferences(self)
        self._timetableWindow = TimetableWindow(self)
        self._timetableWindow.connect("delete-event", self._hideTimetableWindow)
        self._flightsWindow = AcceptedFlightsWindow(self)
        self._flightsWindow.connect("delete-event", self._hideFlightsWindow)
        self._checklistEditor = ChecklistEditor(self)
        self._approachCalloutsEditor = ApproachCalloutsEditor(self)
        self._bugReportDialog = BugReportDialog(self)

        menuBar = self._buildMenuBar(accelGroup)
        mainVBox.pack_start(menuBar, False, False, 0)

        self._notebook = gtk.Notebook()
        mainVBox.pack_start(self._notebook, True, True, 4)

        self._wizard = Wizard(self)
        label = gtk.Label(xstr("tab_flight"))
        label.set_use_underline(True)
        label.set_tooltip_text(xstr("tab_flight_tooltip"))
        self._notebook.append_page(self._wizard, label)

        self._flightInfo = FlightInfo(self)
        label = gtk.Label(xstr("tab_flight_info"))
        label.set_use_underline(True)
        label.set_tooltip_text(xstr("tab_flight_info_tooltip"))
        self._notebook.append_page(self._flightInfo, label)
        self._flightInfo.disable()

        self._weightHelp = WeightHelp(self)
        label = gtk.Label(xstr("tab_weight_help"))
        label.set_use_underline(True)
        label.set_tooltip_text(xstr("tab_weight_help_tooltip"))
        self._notebook.append_page(self._weightHelp, label)

        (logWidget, self._logView)  = self._buildLogWidget()
        addFaultTag(self._logView.get_buffer())
        label = gtk.Label(xstr("tab_log"))
        label.set_use_underline(True)
        label.set_tooltip_text(xstr("tab_log_tooltip"))
        self._notebook.append_page(logWidget, label)

        self._fleetGateStatus = FleetGateStatus(self)
        label = gtk.Label(xstr("tab_gates"))
        label.set_use_underline(True)
        label.set_tooltip_text(xstr("tab_gates_tooltip"))
        self._notebook.append_page(self._fleetGateStatus, label)

        self._acars = ACARS(self)
        label = gtk.Label("ACARS")
        label.set_use_underline(True)
        self._notebook.append_page(self._acars, label)

        (self._debugLogWidget, self._debugLogView) = self._buildLogWidget()
        self._debugLogWidget.show_all()

        mainVBox.pack_start(gtk.HSeparator(), False, False, 0)

        self._statusbar = Statusbar(iconDirectory)
        mainVBox.pack_start(self._statusbar, False, False, 0)

        self._notebook.connect("switch-page", self._notebookPageSwitch)

        self._monitorWindow = MonitorWindow(self, iconDirectory)
        self._monitorWindow.add_accel_group(accelGroup)
        self._monitorWindowX = None
        self._monitorWindowY = None
        self._selfToggling = False

        self._pirepViewer = PIREPViewer(self)
        self._messagedPIREPViewer = PIREPViewer(self, showMessages = True)

        self._pirepEditor = PIREPEditor(self)

        window.show_all()
        if os.name=="nt":
            window.get_window().focus()

        self._wizard.grabDefault()
        self._weightHelp.reset()
        self._weightHelp.disable()

        self._statusIcon = StatusIcon(iconDirectory, self)

        self._busyCursor = gdk.Cursor(gdk.CursorType.WATCH if pygobject
                                      else gdk.WATCH)

        self._loadPIREPDialog = None
        self._lastLoadedPIREP = None

        self._hotkeySetID = None
        self._pilotHotkeyIndex = None
        self._checklistHotkeyIndex = None

        self._aboutDialog = None

    @property
    def mainWindow(self):
        """Get the main window of the GUI."""
        return self._mainWindow

    @property
    def logger(self):
        """Get the logger used by us."""
        return self._logger

    @property
    def simulator(self):
        """Get the simulator used by us."""
        return self._simulator

    @property
    def flight(self):
        """Get the flight being performed."""
        return self._flight

    @property
    def fsType(self):
        """Get the flight simulator type."""
        return self._fsType

    @property
    def entranceExam(self):
        """Get whether an entrance exam is about to be taken."""
        return self._wizard.entranceExam

    @property
    def loggedIn(self):
        """Indicate if the user has logged in properly."""
        return self._wizard.loggedIn

    @property
    def loginResult(self):
        """Get the result of the login."""
        return self._wizard.loginResult

    @property
    def bookedFlight(self):
        """Get the booked flight selected, if any."""
        return self._wizard.bookedFlight

    @property
    def numCrew(self):
        """Get the number of crew members."""
        return self._wizard.numCrew

    @property
    def numPassengers(self):
        """Get the number of passengers."""
        return self._wizard.numPassengers

    @property
    def bagWeight(self):
        """Get the bag weight."""
        return self._wizard.bagWeight

    @property
    def cargoWeight(self):
        """Get the cargo weight."""
        return self._wizard.cargoWeight

    @property
    def mailWeight(self):
        """Get the mail weight."""
        return self._wizard.mailWeight

    @property
    def zfw(self):
        """Get Zero-Fuel Weight calculated for the current flight."""
        return self._wizard.zfw

    @property
    def filedCruiseAltitude(self):
        """Get cruise altitude filed for the current flight."""
        return self._wizard.filedCruiseAltitude

    @property
    def cruiseAltitude(self):
        """Get cruise altitude set for the current flight."""
        return self._wizard.cruiseAltitude

    @property
    def loggableCruiseAltitude(self):
        """Get the cruise altitude that can be logged."""
        return self._wizard.loggableCruiseAltitude

    @property
    def route(self):
        """Get the flight route."""
        return self._wizard.route

    @property
    def departureMETAR(self):
        """Get the METAR of the deprature airport."""
        return self._wizard.departureMETAR

    @property
    def arrivalMETAR(self):
        """Get the METAR of the deprature airport."""
        return self._wizard.arrivalMETAR

    @property
    def departureRunway(self):
        """Get the name of the departure runway."""
        return self._wizard.departureRunway

    @property
    def sid(self):
        """Get the SID."""
        return self._wizard.sid

    @property
    def v1(self):
        """Get the V1 speed calculated for the flight."""
        return self._wizard.v1

    @property
    def vr(self):
        """Get the Vr speed calculated for the flight."""
        return self._wizard.vr

    @property
    def v2(self):
        """Get the V2 speed calculated for the flight."""
        return self._wizard.v2

    @property
    def derate(self):
        """Get the derate value calculated for the flight."""
        return self._wizard.derate

    @property
    def takeoffAntiIceOn(self):
        """Get whether the anti-ice system was on during take-off."""
        return self._wizard.takeoffAntiIceOn

    @takeoffAntiIceOn.setter
    def takeoffAntiIceOn(self, value):
        """Set the anti-ice on indicator."""
        gobject.idle_add(self._setTakeoffAntiIceOn, value)

    @property
    def rtoIndicated(self):
        """Get whether the pilot has indicated than an RTO has occured."""
        return self._wizard.rtoIndicated

    @property
    def arrivalRunway(self):
        """Get the arrival runway."""
        return self._wizard.arrivalRunway

    @property
    def star(self):
        """Get the STAR."""
        return self._wizard.star

    @property
    def transition(self):
        """Get the transition."""
        return self._wizard.transition

    @property
    def approachType(self):
        """Get the approach type."""
        return self._wizard.approachType

    @property
    def vref(self):
        """Get the Vref speed calculated for the flight."""
        return self._wizard.vref

    @property
    def landingAntiIceOn(self):
        """Get whether the anti-ice system was on during landing."""
        return self._wizard.landingAntiIceOn

    @landingAntiIceOn.setter
    def landingAntiIceOn(self, value):
        """Set the anti-ice on indicator."""
        gobject.idle_add(self._setLandingAntiIceOn, value)

    @property
    def flightType(self):
        """Get the flight type."""
        return self._wizard.flightType

    @property
    def online(self):
        """Get whether the flight was online or not."""
        return self._wizard.online

    @property
    def comments(self):
        """Get the comments."""
        return self._flightInfo.comments

    @property
    def hasComments(self):
        """Indicate whether there is a comment."""
        return self._flightInfo.hasComments

    @property
    def flightDefects(self):
        """Get the flight defects."""
        return self._flightInfo.faultsAndExplanations

    @property
    def delayCodes(self):
        """Get the delay codes."""
        return self._flightInfo.delayCodes

    @property
    def hasDelayCode(self):
        """Determine if there is at least one delay code selected."""
        return self._flightInfo.hasDelayCode

    @property
    def faultsFullyExplained(self):
        """Determine if all the faults have been fully explained by the
        user."""
        return self._flightInfo.faultsFullyExplained

    if pygobject:
        @property
        def backgroundColour(self):
            """Get the background colour of the main window."""
            return self._mainWindow.get_style_context().\
              get_background_color(gtk.StateFlags.NORMAL)

    def run(self):
        """Run the GUI."""
        if self.config.autoUpdate:
            self._updater = Updater(self,
                                    self._programDirectory,
                                    self.config.updateURL,
                                    self._mainWindow)
            self._updater.start()
        else:
            self.updateDone()

        cef.initialize(self._cefInitialized)

        singleton.raiseCallback = self.raiseCallback
        gtk.main()
        singleton.raiseCallback = None

        cef.finalize()

        self._disconnect()

    def updateDone(self):
        """Called when the update is done (and there is no need to restart)."""
        gobject.idle_add(self._updateDone)

    def connected(self, fsType, descriptor):
        """Called when we have connected to the simulator."""
        self._connected = True
        self._logger.untimedMessage("MLX %s connected to the simulator %s" % \
                                    (const.VERSION, descriptor))
        fs.sendMessage(const.MESSAGETYPE_INFORMATION,
                       "Welcome to MAVA Logger X " + const.VERSION)
        gobject.idle_add(self._handleConnected, fsType, descriptor)

    def _handleConnected(self, fsType, descriptor):
        """Called when the connection to the simulator has succeeded."""
        self._statusbar.updateConnection(self._connecting, self._connected)
        self.endBusy()
        if not self._reconnecting:
            self._wizard.connected(fsType, descriptor)
        self._reconnecting = False
        self._fsType = fsType
        self._listenHotkeys()

    def connectionFailed(self):
        """Called when the connection failed."""
        self._logger.untimedMessage("Connection to the simulator failed")
        gobject.idle_add(self._connectionFailed)

    def _connectionFailed(self):
        """Called when the connection failed."""
        self.endBusy()
        self._statusbar.updateConnection(self._connecting, self._connected)

        dialog = gtk.MessageDialog(parent = self._mainWindow,
                                   type = MESSAGETYPE_ERROR,
                                   message_format = xstr("conn_failed"))

        dialog.set_title(WINDOW_TITLE_BASE)
        dialog.format_secondary_markup(xstr("conn_failed_sec"))

        dialog.add_button(xstr("button_cancel"), 0)
        dialog.add_button(xstr("button_tryagain"), 1)
        dialog.set_default_response(1)

        result = dialog.run()
        dialog.hide()
        if result == 1:
            self.beginBusy(xstr("connect_busy"))
            self._simulator.reconnect()
        else:
            self.reset()

    def disconnected(self):
        """Called when we have disconnected from the simulator."""
        self._connected = False
        self._logger.untimedMessage("Disconnected from the simulator")
        if self._flight is not None:
            self._flight.disconnected()

        gobject.idle_add(self._disconnected)

    def _disconnected(self):
        """Called when we have disconnected from the simulator unexpectedly."""
        self._statusbar.updateConnection(self._connecting, self._connected)

        dialog = gtk.MessageDialog(type = MESSAGETYPE_ERROR,
                                   message_format = xstr("conn_broken"),
                                   parent = self._mainWindow)
        dialog.set_title(WINDOW_TITLE_BASE)
        dialog.format_secondary_markup(xstr("conn_broken_sec"))

        dialog.add_button(xstr("button_cancel"), 0)
        dialog.add_button(xstr("button_reconnect"), 1)
        dialog.set_default_response(1)

        result = dialog.run()
        dialog.hide()
        if result == 1:
            self.beginBusy(xstr("connect_busy"))
            self._reconnecting = True
            self._simulator.reconnect()
        else:
            self.reset()

    def enableFlightInfo(self, aircraftType):
        """Enable the flight info tab."""
        self._flightInfo.enable(aircraftType)

    def cancelFlight(self):
        """Cancel the current file, if the user confirms it."""
        dialog = gtk.MessageDialog(parent = self._mainWindow,
                                   type = MESSAGETYPE_QUESTION,
                                   message_format = xstr("cancelFlight_question"))

        dialog.add_button(xstr("button_no"), RESPONSETYPE_NO)
        dialog.add_button(xstr("button_yes"), RESPONSETYPE_YES)

        dialog.set_title(WINDOW_TITLE_BASE)
        result = dialog.run()
        dialog.hide()

        if result==RESPONSETYPE_YES:
            self.reset()

    def reset(self):
        """Reset the GUI."""
        self._disconnect()

        self._simulator = None

        self._flightInfo.reset()
        self._flightInfo.disable()
        self.resetFlightStatus()

        self._weightHelp.reset()
        self._weightHelp.disable()
        self._notebook.set_current_page(0)

        self._logView.get_buffer().set_text("")

        if self.loggedIn:
            self._wizard.cancelFlight(self._handleReloadResult)
        else:
            self._wizard.reset(None)

    def _handleReloadResult(self, returned, result):
        """Handle the result of the reloading of the flights."""
        self._wizard.reset(result if returned and result.loggedIn else None)

    def _disconnect(self, closingMessage = None, duration = 3):
        """Disconnect from the simulator if connected."""
        self.stopMonitoring()
        self._clearHotkeys()

        if self._connected:
            if closingMessage is None:
                self._flight.simulator.disconnect()
            else:
                fs.sendMessage(const.MESSAGETYPE_ENVIRONMENT,
                               closingMessage, duration,
                               disconnect = True)
            self._connected = False

        self._connecting = False
        self._reconnecting = False
        self._statusbar.updateConnection(False, False)
        self._weightHelp.disable()

        return True

    def insertFlightLogLine(self, index, timestampString, text, isFault):
        """Insert the flight log line with the given data."""
        gobject.idle_add(self._insertFlightLogLine, index,
                         formatFlightLogLine(timestampString, text),
                         isFault)

    def _insertFlightLogLine(self, index, line, isFault):
        """Perform the real insertion.

        To be called from the event loop."""
        buffer = self._logView.get_buffer()
        lineIter = buffer.get_iter_at_line(index)
        insertTextBuffer(buffer, lineIter, line, isFault = isFault)
        self._logView.scroll_mark_onscreen(buffer.get_insert())

    def removeFlightLogLine(self, index):
        """Remove the flight log line with the given index."""
        gobject.idle_add(self._removeFlightLogLine, index)

    def addFault(self, id, timestampString, text):
        """Add a fault to the list of faults."""
        faultText = formatFlightLogLine(timestampString, text).strip()
        gobject.idle_add(self._flightInfo.addFault, id, faultText)

    def updateFault(self, id, timestampString, text):
        """Update a fault in the list of faults."""
        faultText = formatFlightLogLine(timestampString, text).strip()
        gobject.idle_add(self._flightInfo.updateFault, id, faultText)

    def clearFault(self, id):
        """Clear a fault in the list of faults."""
        gobject.idle_add(self._flightInfo.clearFault, id)

    def _removeFlightLogLine(self, index):
        """Perform the real removal."""
        buffer = self._logView.get_buffer()
        startIter = buffer.get_iter_at_line(index)
        endIter = buffer.get_iter_at_line(index+1)
        buffer.delete(startIter, endIter)
        self._logView.scroll_mark_onscreen(buffer.get_insert())

    def check(self, flight, aircraft, logger, oldState, state):
        """Update the data."""
        gobject.idle_add(self._monitorWindow.setData, state)
        gobject.idle_add(self._statusbar.updateTime, state.timestamp)

    def resetFlightStatus(self):
        """Reset the status of the flight."""
        self._statusbar.resetFlightStatus()
        self._statusbar.updateTime()
        self._statusIcon.resetFlightStatus()

    def setStage(self, stage):
        """Set the stage of the flight."""
        gobject.idle_add(self._setStage, stage)

    def _setStage(self, stage):
        """Set the stage of the flight."""
        self._statusbar.setStage(stage)
        self._statusIcon.setStage(stage)
        self._wizard.setStage(stage)
        if stage==const.STAGE_END:
            welcomeMessage = \
                airports.getWelcomeMessage(self.bookedFlight.arrivalICAO)
            self._disconnect(closingMessage =
                             "Flight plan closed. " + welcomeMessage,
                             duration = 5)

    def setRating(self, rating):
        """Set the rating of the flight."""
        gobject.idle_add(self._setRating, rating)

    def _setRating(self, rating):
        """Set the rating of the flight."""
        self._statusbar.setRating(rating)
        self._statusIcon.setRating(rating)

    def setNoGo(self, reason):
        """Set the rating of the flight to No-Go with the given reason."""
        gobject.idle_add(self._setNoGo, reason)

    def _setNoGo(self, reason):
        """Set the rating of the flight."""
        self._statusbar.setNoGo(reason)
        self._statusIcon.setNoGo(reason)

    def _handleMainWindowState(self, window, event):
        """Hande a change in the state of the window"""
        iconified = gdk.WindowState.ICONIFIED if pygobject \
                    else gdk.WINDOW_STATE_ICONIFIED

        if (event.changed_mask&WINDOW_STATE_WITHDRAWN)!=0:
            if (event.new_window_state&WINDOW_STATE_WITHDRAWN)!=0:
                self._statusIcon.mainWindowHidden()
            else:
                self._statusIcon.mainWindowShown()

        if self.config.hideMinimizedWindow and not pygobject and \
           (event.changed_mask&WINDOW_STATE_ICONIFIED)!=0 and \
           (event.new_window_state&WINDOW_STATE_ICONIFIED)!=0:
            self.hideMainWindow(savePosition = False)
        elif (event.changed_mask&WINDOW_STATE_ICONIFIED)!=0 and \
             (event.new_window_state&WINDOW_STATE_ICONIFIED)==0:
            self._mainWindow.present()

    def _handleLeaveNotify(self, widget, event):
        """Handle the leave-notify event.

        Here we reset the focus to the main window as CEF might have acquired
        it earlier."""
        self._mainWindow.get_window().focus()

    def raiseCallback(self):
        """Callback for the singleton handling code."""
        gobject.idle_add(self.raiseMainWindow)

    def raiseMainWindow(self):
        """Show the main window if invisible, and raise it."""
        if not self._mainWindow.get_visible():
            self.showMainWindow()
        self._mainWindow.present()

    def deleteMainWindow(self, window, event):
        """Handle the delete event for the main window."""
        if self.config.quitOnClose:
            self._quit()
        else:
            self.hideMainWindow()
        return True

    def hideMainWindow(self, savePosition = True):
        """Hide the main window and save its position."""
        if savePosition:
            (self._mainWindowX, self._mainWindowY) = \
                 self._mainWindow.get_window().get_root_origin()
        else:
            self._mainWindowX = self._mainWindowY = None
        self._mainWindow.hide()
        return True

    def showMainWindow(self):
        """Show the main window at its former position."""
        if self._mainWindowX is not None and self._mainWindowY is not None:
            self._mainWindow.move(self._mainWindowX, self._mainWindowY)

        if pygobject:
            self._mainWindow.show()
        else:
            self._mainWindow.present()
        self._mainWindow.deiconify()

    def toggleMainWindow(self):
        """Toggle the main window."""
        if self._mainWindow.get_visible():
            self.hideMainWindow()
        else:
            self.showMainWindow()

    def hideMonitorWindow(self, savePosition = True):
        """Hide the monitor window."""
        if savePosition:
            (self._monitorWindowX, self._monitorWindowY) = \
                 self._monitorWindow.get_window().get_root_origin()
        else:
            self._monitorWindowX = self._monitorWindowY = None
        self._monitorWindow.hide()
        self._statusIcon.monitorWindowHidden()
        if self._showMonitorMenuItem.get_active():
            self._selfToggling = True
            self._showMonitorMenuItem.set_active(False)
        return True

    def showMonitorWindow(self):
        """Show the monitor window."""
        if self._monitorWindowX is not None and self._monitorWindowY is not None:
            self._monitorWindow.move(self._monitorWindowX, self._monitorWindowY)
        self._monitorWindow.show_all()
        self._statusIcon.monitorWindowShown()
        if not self._showMonitorMenuItem.get_active():
            self._selfToggling = True
            self._showMonitorMenuItem.set_active(True)

    def _toggleMonitorWindow(self, menuItem):
        if self._selfToggling:
            self._selfToggling = False
        elif self._monitorWindow.get_visible():
            self.hideMonitorWindow()
        else:
            self.showMonitorWindow()

    def restart(self):
        """Quit and restart the application."""
        self.toRestart = True
        self._quit(force = True)

    def flushStdIO(self):
        """Flush any text to the standard error that could not be logged."""
        if self._stdioText:
            sys.__stderr__.write(self._stdioText)

    def writeStdIO(self, text):
        """Write the given text into standard I/O log."""
        with self._stdioLock:
            self._stdioText += text

        gobject.idle_add(self._writeStdIO)

    def beginBusy(self, message):
        """Begin a period of background processing."""
        self._wizard.set_sensitive(False)
        self._weightHelp.set_sensitive(False)
        self._mainWindow.get_window().set_cursor(self._busyCursor)
        self._statusbar.updateBusyState(message)

    def updateBusyState(self, message):
        """Update the busy state."""
        self._statusbar.updateBusyState(message)

    def endBusy(self):
        """End a period of background processing."""
        self._mainWindow.get_window().set_cursor(None)
        self._weightHelp.set_sensitive(True)
        self._wizard.set_sensitive(True)
        self._statusbar.updateBusyState(None)

    def initializeWeightHelp(self):
        """Initialize the weight help tab."""
        self._weightHelp.reset()
        self._weightHelp.enable()

    def getFleetAsync(self, callback = None, force = None):
        """Get the fleet asynchronously."""
        gobject.idle_add(self.getFleet, callback, force)

    def getFleet(self, callback = None, force = False):
        """Get the fleet.

        If force is False, and we already have a fleet retrieved,
        that one will be used."""
        if self._fleet is None or force:
            self._fleetCallback = callback
            self.beginBusy(xstr("fleet_busy"))
            self.webHandler.getFleet(self._fleetResultCallback)
        else:
            callback(self._fleet)

    def commentsChanged(self):
        """Indicate that the comments have changed."""
        self._wizard.commentsChanged()

    def delayCodesChanged(self):
        """Called when the delay codes have changed."""
        self._wizard.delayCodesChanged()

    def faultExplanationsChanged(self):
        """Called when the status of the explanations of the faults have
        changed."""
        self._wizard.faultExplanationsChanged()

    def updateRTO(self, inLoop = False):
        """Indicate that the RTO state should be updated."""
        if inLoop:
            self._wizard.updateRTO()
        else:
            gobject.idle_add(self.updateRTO, True)

    def rtoToggled(self, indicated):
        """Called when the user has toggled the RTO checkbox."""
        self._flight.rtoToggled(indicated)

    def _fleetResultCallback(self, returned, result):
        """Called when the fleet has been queried."""
        gobject.idle_add(self._handleFleetResult, returned, result)

    def _handleFleetResult(self, returned, result):
        """Handle the fleet result."""
        self.endBusy()
        if returned:
            self._fleet = result.fleet
        else:
            self._fleet = None

            dialog = gtk.MessageDialog(parent = self.mainWindow,
                                       type = MESSAGETYPE_ERROR,
                                       message_format = xstr("fleet_failed"))
            dialog.add_button(xstr("button_ok"), RESPONSETYPE_OK)
            dialog.set_title(WINDOW_TITLE_BASE)
            dialog.run()
            dialog.hide()

        callback = self._fleetCallback
        self._fleetCallback = None
        if  callback is not None:
            callback(self._fleet)
        self._fleetGateStatus.handleFleet(self._fleet)

    def updatePlane(self, tailNumber, status,
                    gateNumber = None, callback = None):
        """Update the status of the given plane."""
        self.beginBusy(xstr("fleet_update_busy"))

        self._updatePlaneCallback = callback

        self._updatePlaneTailNumber = tailNumber
        self._updatePlaneStatus = status
        self._updatePlaneGateNumber = gateNumber

        self.webHandler.updatePlane(self._updatePlaneResultCallback,
                                    tailNumber, status, gateNumber)

    def _updatePlaneResultCallback(self, returned, result):
        """Called when the status of a plane has been updated."""
        gobject.idle_add(self._handleUpdatePlaneResult, returned, result)

    def _handleUpdatePlaneResult(self, returned, result):
        """Handle the plane update result."""
        self.endBusy()
        if returned:
            success = result.success
            if success:
                if self._fleet is not None:
                    self._fleet.updatePlane(self._updatePlaneTailNumber,
                                            self._updatePlaneStatus,
                                            self._updatePlaneGateNumber)
                    self._fleetGateStatus.handleFleet(self._fleet)
        else:
            dialog = gtk.MessageDialog(parent = self.mainWindow,
                                       type = MESSAGETYPE_ERROR,
                                       message_format = xstr("fleet_update_failed"))
            dialog.add_button(xstr("button_ok"), RESPONSETYPE_ACCEPT)
            dialog.set_title(WINDOW_TITLE_BASE)
            dialog.run()
            dialog.hide()

            success = None

        callback = self._updatePlaneCallback
        self._updatePlaneCallback = None
        if callback is not None:
            callback(success)

    def _writeStdIO(self):
        """Perform the real writing."""
        with self._stdioLock:
            text = self._stdioText
            self._stdioText = ""
        if not text: return

        lines = text.splitlines()
        if text[-1]=="\n":
            text = ""
        else:
            text = lines[-1]
            lines = lines[:-1]

        now = datetime.datetime.now()
        timeStr = "%02d:%02d:%02d: " % (now.hour, now.minute, now.second)

        for line in lines:
            #print >> sys.__stdout__, line
            if self._stdioStartingLine:
                self._writeLog(timeStr, self._debugLogView)
            self._writeLog(line + "\n", self._debugLogView)
            self._stdioStartingLine = True

        if text:
            #print >> sys.__stdout__, text,
            if self._stdioStartingLine:
                self._writeLog(timeStr, self._debugLogView)
            self._writeLog(text, self._debugLogView)
            self._stdioStartingLine = False

    def connectSimulator(self, bookedFlight, simulatorType):
        """Connect to the simulator for the first time."""
        self._logger.reset()

        self._flight = flight.Flight(self._logger, self)
        self._flight.flareTimeFromFS = self.config.flareTimeFromFS
        self._flight.aircraftType = bookedFlight.aircraftType
        self._flight.aircraft = acft.Aircraft.create(self._flight, bookedFlight)
        self._flight.aircraft._checkers.append(self)

        if self._simulator is None:
            self._simulator = fs.createSimulator(simulatorType, self)
            fs.setupMessageSending(self.config, self._simulator)
            self._setupTimeSync()

        self._flight.simulator = self._simulator

        self.beginBusy(xstr("connect_busy"))
        self._statusbar.updateConnection(self._connecting, self._connected)

        self._connecting = True
        self._simulator.connect(self._flight.aircraft)

    def startMonitoring(self):
        """Start monitoring."""
        if not self._monitoring:
            self.simulator.startMonitoring()
            self._monitoring = True

    def stopMonitoring(self):
        """Stop monitoring."""
        if self._monitoring:
            self.simulator.stopMonitoring()
            self._monitoring = False

    def cruiseLevelChanged(self):
        """Called when the cruise level is changed in the flight wizard."""
        if self._flight is not None:
            return self._flight.cruiseLevelChanged()
        else:
            return False

    def _buildMenuBar(self, accelGroup):
        """Build the main menu bar."""
        menuBar = gtk.MenuBar()

        fileMenuItem = gtk.MenuItem(xstr("menu_file"))
        fileMenu = gtk.Menu()
        fileMenuItem.set_submenu(fileMenu)
        menuBar.append(fileMenuItem)

        loadPIREPMenuItem = gtk.ImageMenuItem(gtk.STOCK_OPEN)
        loadPIREPMenuItem.set_use_stock(True)
        loadPIREPMenuItem.set_label(xstr("menu_file_loadPIREP"))
        loadPIREPMenuItem.add_accelerator("activate", accelGroup,
                                          ord(xstr("menu_file_loadPIREP_key")),
                                          CONTROL_MASK, ACCEL_VISIBLE)
        loadPIREPMenuItem.connect("activate", self._loadPIREP)
        fileMenu.append(loadPIREPMenuItem)

        fileMenu.append(gtk.SeparatorMenuItem())

        quitMenuItem = gtk.ImageMenuItem(gtk.STOCK_QUIT)
        quitMenuItem.set_use_stock(True)
        quitMenuItem.set_label(xstr("menu_file_quit"))
        quitMenuItem.add_accelerator("activate", accelGroup,
                                     ord(xstr("menu_file_quit_key")),
                                     CONTROL_MASK, ACCEL_VISIBLE)
        quitMenuItem.connect("activate", self._quit)
        fileMenu.append(quitMenuItem)

        toolsMenuItem = gtk.MenuItem(xstr("menu_tools"))
        toolsMenu = gtk.Menu()
        toolsMenuItem.set_submenu(toolsMenu)
        menuBar.append(toolsMenuItem)

        self._timetableMenuItem = timetableMenuItem = \
          gtk.ImageMenuItem(gtk.STOCK_INDENT)
        timetableMenuItem.set_use_stock(True)
        timetableMenuItem.set_label(xstr("menu_tools_timetable"))
        timetableMenuItem.add_accelerator("activate", accelGroup,
                                          ord(xstr("menu_tools_timetable_key")),
                                          CONTROL_MASK, ACCEL_VISIBLE)
        timetableMenuItem.connect("activate", self.showTimetable)
        self._timetableMenuItem.set_sensitive(False)
        toolsMenu.append(timetableMenuItem)

        self._flightsMenuItem = flightsMenuItem = \
          gtk.ImageMenuItem(gtk.STOCK_SPELL_CHECK)
        flightsMenuItem.set_use_stock(True)
        flightsMenuItem.set_label(xstr("menu_tools_flights"))
        flightsMenuItem.add_accelerator("activate", accelGroup,
                                        ord(xstr("menu_tools_flights_key")),
                                        CONTROL_MASK, ACCEL_VISIBLE)
        flightsMenuItem.connect("activate", self.showFlights)
        self._flightsMenuItem.set_sensitive(False)
        toolsMenu.append(flightsMenuItem)

        checklistMenuItem = gtk.ImageMenuItem(gtk.STOCK_APPLY)
        checklistMenuItem.set_use_stock(True)
        checklistMenuItem.set_label(xstr("menu_tools_chklst"))
        checklistMenuItem.add_accelerator("activate", accelGroup,
                                          ord(xstr("menu_tools_chklst_key")),
                                          CONTROL_MASK, ACCEL_VISIBLE)
        checklistMenuItem.connect("activate", self._editChecklist)
        toolsMenu.append(checklistMenuItem)

        approachCalloutsMenuItem = gtk.ImageMenuItem(gtk.STOCK_EDIT)
        approachCalloutsMenuItem.set_use_stock(True)
        approachCalloutsMenuItem.set_label(xstr("menu_tools_callouts"))
        approachCalloutsMenuItem.add_accelerator("activate", accelGroup,
                                                 ord(xstr("menu_tools_callouts_key")),
                                                 CONTROL_MASK, ACCEL_VISIBLE)
        approachCalloutsMenuItem.connect("activate", self._editApproachCallouts)
        toolsMenu.append(approachCalloutsMenuItem)

        prefsMenuItem = gtk.ImageMenuItem(gtk.STOCK_PREFERENCES)
        prefsMenuItem.set_use_stock(True)
        prefsMenuItem.set_label(xstr("menu_tools_prefs"))
        prefsMenuItem.add_accelerator("activate", accelGroup,
                                      ord(xstr("menu_tools_prefs_key")),
                                      CONTROL_MASK, ACCEL_VISIBLE)
        prefsMenuItem.connect("activate", self._editPreferences)
        toolsMenu.append(prefsMenuItem)

        toolsMenu.append(gtk.SeparatorMenuItem())

        bugReportMenuItem = gtk.ImageMenuItem(gtk.STOCK_PASTE)
        bugReportMenuItem.set_use_stock(True)
        bugReportMenuItem.set_label(xstr("menu_tools_bugreport"))
        bugReportMenuItem.add_accelerator("activate", accelGroup,
                                          ord(xstr("menu_tools_bugreport_key")),
                                          CONTROL_MASK, ACCEL_VISIBLE)
        bugReportMenuItem.connect("activate", self._reportBug)
        toolsMenu.append(bugReportMenuItem)

        viewMenuItem = gtk.MenuItem(xstr("menu_view"))
        viewMenu = gtk.Menu()
        viewMenuItem.set_submenu(viewMenu)
        menuBar.append(viewMenuItem)

        self._showMonitorMenuItem = gtk.CheckMenuItem()
        self._showMonitorMenuItem.set_label(xstr("menu_view_monitor"))
        self._showMonitorMenuItem.set_use_underline(True)
        self._showMonitorMenuItem.set_active(False)
        self._showMonitorMenuItem.add_accelerator("activate", accelGroup,
                                                  ord(xstr("menu_view_monitor_key")),
                                                  CONTROL_MASK, ACCEL_VISIBLE)
        self._showMonitorMenuItem.connect("toggled", self._toggleMonitorWindow)
        viewMenu.append(self._showMonitorMenuItem)

        showDebugMenuItem = gtk.CheckMenuItem()
        showDebugMenuItem.set_label(xstr("menu_view_debug"))
        showDebugMenuItem.set_use_underline(True)
        showDebugMenuItem.set_active(False)
        showDebugMenuItem.add_accelerator("activate", accelGroup,
                                          ord(xstr("menu_view_debug_key")),
                                          CONTROL_MASK, ACCEL_VISIBLE)
        showDebugMenuItem.connect("toggled", self._toggleDebugLog)
        viewMenu.append(showDebugMenuItem)

        helpMenuItem = gtk.MenuItem(xstr("menu_help"))
        helpMenu = gtk.Menu()
        helpMenuItem.set_submenu(helpMenu)
        menuBar.append(helpMenuItem)

        manualMenuItem = gtk.ImageMenuItem(gtk.STOCK_HELP)
        manualMenuItem.set_use_stock(True)
        manualMenuItem.set_label(xstr("menu_help_manual"))
        manualMenuItem.add_accelerator("activate", accelGroup,
                                       ord(xstr("menu_help_manual_key")),
                                       CONTROL_MASK, ACCEL_VISIBLE)
        manualMenuItem.connect("activate", self._showManual)
        helpMenu.append(manualMenuItem)

        helpMenu.append(gtk.SeparatorMenuItem())

        aboutMenuItem = gtk.ImageMenuItem(gtk.STOCK_ABOUT)
        aboutMenuItem.set_use_stock(True)
        aboutMenuItem.set_label(xstr("menu_help_about"))
        aboutMenuItem.add_accelerator("activate", accelGroup,
                                      ord(xstr("menu_help_about_key")),
                                      CONTROL_MASK, ACCEL_VISIBLE)
        aboutMenuItem.connect("activate", self._showAbout)
        helpMenu.append(aboutMenuItem)

        return menuBar

    def _toggleDebugLog(self, menuItem):
        """Toggle the debug log."""
        if menuItem.get_active():
            label = gtk.Label(xstr("tab_debug_log"))
            label.set_use_underline(True)
            label.set_tooltip_text(xstr("tab_debug_log_tooltip"))
            self._debugLogPage = self._notebook.append_page(self._debugLogWidget, label)
            self._notebook.set_current_page(self._debugLogPage)
        else:
            self._notebook.remove_page(self._debugLogPage)

    def _buildLogWidget(self):
        """Build the widget for the log."""
        alignment = gtk.Alignment(xscale = 1.0, yscale = 1.0)

        alignment.set_padding(padding_top = 8, padding_bottom = 8,
                              padding_left = 16, padding_right = 16)

        logScroller = gtk.ScrolledWindow()
        # FIXME: these should be constants in common
        logScroller.set_policy(gtk.PolicyType.AUTOMATIC if pygobject
                               else gtk.POLICY_AUTOMATIC,
                               gtk.PolicyType.AUTOMATIC if pygobject
                               else gtk.POLICY_AUTOMATIC)
        logScroller.set_shadow_type(gtk.ShadowType.IN if pygobject
                                    else gtk.SHADOW_IN)
        logView = gtk.TextView()
        logView.set_editable(False)
        logView.set_cursor_visible(False)
        logScroller.add(logView)

        logBox = gtk.VBox()
        logBox.pack_start(logScroller, True, True, 0)
        logBox.set_size_request(-1, 200)

        alignment.add(logBox)

        return (alignment, logView)

    def _writeLog(self, msg, logView, isFault = False):
        """Write the given message to the log."""
        buffer = logView.get_buffer()
        appendTextBuffer(buffer, msg, isFault = isFault)
        logView.scroll_mark_onscreen(buffer.get_insert())

    def _quit(self, what = None, force = False):
        """Quit from the application."""
        if force:
            result=RESPONSETYPE_YES
        else:
            dialog = gtk.MessageDialog(parent = self._mainWindow,
                                       type = MESSAGETYPE_QUESTION,
                                       message_format = xstr("quit_question"))

            dialog.add_button(xstr("button_no"), RESPONSETYPE_NO)
            dialog.add_button(xstr("button_yes"), RESPONSETYPE_YES)

            dialog.set_title(WINDOW_TITLE_BASE)
            result = dialog.run()
            dialog.hide()

        if result==RESPONSETYPE_YES:
            self._statusIcon.destroy()
            return gtk.main_quit()

    def _notebookPageSwitch(self, notebook, page, page_num):
        """Called when the current page of the notebook has changed."""
        if page_num==0:
            gobject.idle_add(self._wizard.grabDefault)
        else:
            self._mainWindow.set_default(None)

    def loginSuccessful(self):
        """Called when the login is successful."""
        self._flightsMenuItem.set_sensitive(True)
        self._timetableMenuItem.set_sensitive(True)

    def isWizardActive(self):
        """Determine if the flight wizard is active."""
        return self._notebook.get_current_page()==0

    def showTimetable(self, menuItem):
        """Callback for showing the timetable."""
        if self._timetableWindow.hasFlightPairs:
            self._timetableWindow.show_all()
        else:
            date = datetime.date.today()
            self._timetableWindow.setTypes(self.loginResult.types)
            self._timetableWindow.setDate(date)
            self.updateTimeTable(date)
            self.beginBusy(xstr("timetable_query_busy"))

    def updateTimeTable(self, date):
        """Update the time table for the given date."""
        self.beginBusy(xstr("timetable_query_busy"))
        self._timetableWindow.set_sensitive(False)
        window = self._timetableWindow.get_window()
        if window is not None:
            window.set_cursor(self._busyCursor)
        self.webHandler.getTimetable(self._timetableCallback, date,
                                     self.loginResult.types)

    def _timetableCallback(self, returned, result):
        """Called when the timetable has been received."""
        gobject.idle_add(self._handleTimetable, returned, result)

    def _handleTimetable(self, returned, result):
        """Handle the result of the query for the timetable."""
        self.endBusy()
        window = self._timetableWindow.get_window()
        if window is not None:
            window.set_cursor(None)
        self._timetableWindow.set_sensitive(True)
        if returned:
            self._timetableWindow.setFlightPairs(result.flightPairs)
            self._timetableWindow.show_all()
        else:
            dialog = gtk.MessageDialog(parent = self.mainWindow,
                                       type = MESSAGETYPE_ERROR,
                                       message_format = xstr("timetable_failed"))
            dialog.add_button(xstr("button_ok"), RESPONSETYPE_OK)
            dialog.set_title(WINDOW_TITLE_BASE)
            dialog.run()
            dialog.hide()
            self._timetableWindow.clear()

    def showFlights(self, menuItem):
        """Callback for showing the flight list."""
        if self._flightsWindow.hasFlights:
            self._flightsWindow.show_all()
        else:
            self.beginBusy(xstr("acceptedflt_query_busy"))
            self.webHandler.getAcceptedFlights(self._acceptedFlightsCallback)

    def _acceptedFlightsCallback(self, returned, result):
        """Called when the accepted flights have been received."""
        gobject.idle_add(self._handleAcceptedFlights, returned, result)

    def _handleAcceptedFlights(self, returned, result):
        """Handle the result of the query for accepted flights."""
        self.endBusy()
        if returned:
            self._flightsWindow.clear()
            for flight in result.flights:
                self._flightsWindow.addFlight(flight)
            self._flightsWindow.show_all()
        else:
            dialog = gtk.MessageDialog(parent = self.mainWindow,
                                       type = MESSAGETYPE_ERROR,
                                       message_format = xstr("acceptedflt_failed"))
            dialog.add_button(xstr("button_ok"), RESPONSETYPE_OK)
            dialog.set_title(WINDOW_TITLE_BASE)
            dialog.run()
            dialog.hide()

    def _hideTimetableWindow(self, window, event):
        """Hide the window of the timetable."""
        self._timetableWindow.hide()
        return True

    def _hideFlightsWindow(self, window, event):
        """Hide the window of the accepted flights."""
        self._flightsWindow.hide()
        return True

    def _editChecklist(self, menuItem):
        """Callback for editing the checklists."""
        self._checklistEditor.run()

    def _editApproachCallouts(self, menuItem):
        """Callback for editing the approach callouts."""
        self._approachCalloutsEditor.run()

    def _editPreferences(self, menuItem):
        """Callback for editing the preferences."""
        self._clearHotkeys()
        self._preferences.run(self.config)
        self._setupTimeSync()
        self._listenHotkeys()

    def _reportBug(self, menuItem):
        """Callback for reporting a bug."""
        self._bugReportDialog.run()

    def _setupTimeSync(self):
        """Enable or disable the simulator time synchronization based on the
        configuration."""
        simulator = self._simulator
        if simulator is not None:
            if self.config.syncFSTime:
                simulator.enableTimeSync()
            else:
                simulator.disableTimeSync()

    def viewPIREP(self, pirep):
        """Display the PIREP viewer window with the given PIREP."""
        self._pirepViewer.setPIREP(pirep)
        self._pirepViewer.show_all()
        self._pirepViewer.run()
        self._pirepViewer.hide()

    def viewMessagedPIREP(self, pirep):
        """Display the PIREP viewer window with the given PIREP containing
        messages as well."""
        self._messagedPIREPViewer.setPIREP(pirep)
        self._messagedPIREPViewer.show_all()
        self._messagedPIREPViewer.run()
        self._messagedPIREPViewer.hide()

    def editPIREP(self, pirep):
        """Display the PIREP editor window and allow editing the PIREP."""
        self._pirepEditor.setPIREP(pirep)
        self._pirepEditor.show_all()
        if self._pirepEditor.run()==RESPONSETYPE_OK:
            self.beginBusy(xstr("pirepEdit_save_busy"))
            self.webHandler.sendPIREP(self._pirepUpdatedCallback, pirep,
                                      update = True)
        else:
            self._pirepEditor.hide()

    def _pirepUpdatedCallback(self, returned, result):
        """Callback for the PIREP updating result."""
        gobject.idle_add(self._handlePIREPUpdated, returned, result)

    def _handlePIREPUpdated(self, returned, result):
        """Callback for the PIREP updating result."""
        self.endBusy()
        secondaryMarkup = None
        type = MESSAGETYPE_ERROR
        if returned:
            if result.success:
                type = None
            elif result.alreadyFlown:
                messageFormat = xstr("sendPIREP_already")
                secondaryMarkup = xstr("sendPIREP_already_sec")
            elif result.notAvailable:
                messageFormat = xstr("sendPIREP_notavail")
            else:
                messageFormat = xstr("sendPIREP_unknown")
                secondaryMarkup = xstr("sendPIREP_unknown_sec")
        else:
            print "PIREP sending failed", result
            messageFormat = xstr("sendPIREP_failed")
            secondaryMarkup = xstr("sendPIREP_failed_sec")

        if type is not None:
            dialog = gtk.MessageDialog(parent = self._wizard.gui.mainWindow,
                                       type = type, message_format = messageFormat)
            dialog.add_button(xstr("button_ok"), RESPONSETYPE_OK)
            dialog.set_title(WINDOW_TITLE_BASE)
            if secondaryMarkup is not None:
                dialog.format_secondary_markup(secondaryMarkup)

            dialog.run()
            dialog.hide()

        self._pirepEditor.hide()

    def _loadPIREP(self, menuItem):
        """Load a PIREP for sending."""
        dialog = self._getLoadPirepDialog()

        if self._lastLoadedPIREP:
            dialog.set_current_folder(os.path.dirname(self._lastLoadedPIREP))
        else:
            pirepDirectory = self.config.pirepDirectory
            if pirepDirectory is not None:
                dialog.set_current_folder(pirepDirectory)

        result = dialog.run()
        dialog.hide()

        if result==RESPONSETYPE_OK:
            self._lastLoadedPIREP = text2unicode(dialog.get_filename())

            pirep = PIREP.load(self._lastLoadedPIREP)
            if pirep is None:
                dialog = gtk.MessageDialog(parent = self._mainWindow,
                                           type = MESSAGETYPE_ERROR,
                                           message_format = xstr("loadPIREP_failed"))
                dialog.add_button(xstr("button_ok"), RESPONSETYPE_OK)
                dialog.set_title(WINDOW_TITLE_BASE)
                dialog.format_secondary_markup(xstr("loadPIREP_failed_sec"))
                dialog.run()
                dialog.hide()
            else:
                dialog = self._getSendLoadedDialog(pirep)
                dialog.show_all()
                while True:
                    result = dialog.run()

                    if result==RESPONSETYPE_OK:
                        self.sendPIREP(pirep)
                    elif result==1:
                        self.viewPIREP(pirep)
                    else:
                        break

                dialog.hide()

    def _getLoadPirepDialog(self):
        """Get the PIREP loading file chooser dialog.

        If it is not created yet, it will be created."""
        if self._loadPIREPDialog is None:
            dialog = gtk.FileChooserDialog(title = WINDOW_TITLE_BASE + " - " +
                                           xstr("loadPIREP_browser_title"),
                                           action = FILE_CHOOSER_ACTION_OPEN,
                                           buttons = (gtk.STOCK_CANCEL,
                                                      RESPONSETYPE_CANCEL,
                                                      gtk.STOCK_OK, RESPONSETYPE_OK),
                                           parent = self._mainWindow)
            dialog.set_modal(True)


            filter = gtk.FileFilter()
            filter.set_name(xstr("file_filter_pireps"))
            filter.add_pattern("*.pirep")
            dialog.add_filter(filter)

            filter = gtk.FileFilter()
            filter.set_name(xstr("file_filter_all"))
            filter.add_pattern("*.*")
            dialog.add_filter(filter)

            self._loadPIREPDialog = dialog

        return self._loadPIREPDialog

    def _getSendLoadedDialog(self, pirep):
        """Get a dialog displaying the main information of the flight from the
        PIREP and providing Cancel and Send buttons."""
        dialog = gtk.Dialog(title = WINDOW_TITLE_BASE + " - " +
                            xstr("loadPIREP_send_title"),
                            parent = self._mainWindow,
                            flags = DIALOG_MODAL)

        contentArea = dialog.get_content_area()

        label = gtk.Label(xstr("loadPIREP_send_help"))
        alignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)
        alignment.set_padding(padding_top = 16, padding_bottom = 0,
                              padding_left = 48, padding_right = 48)
        alignment.add(label)
        contentArea.pack_start(alignment, False, False, 8)

        table = gtk.Table(5, 2)
        tableAlignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                       xscale = 0.0, yscale = 0.0)
        tableAlignment.set_padding(padding_top = 0, padding_bottom = 32,
                                   padding_left = 48, padding_right = 48)
        table.set_row_spacings(4)
        table.set_col_spacings(16)
        tableAlignment.add(table)
        contentArea.pack_start(tableAlignment, True, True, 8)

        bookedFlight = pirep.bookedFlight

        label = gtk.Label("<b>" + xstr("loadPIREP_send_flightno") + "</b>")
        label.set_use_markup(True)
        labelAlignment = gtk.Alignment(xalign = 1.0, yalign = 0.5,
                                       xscale = 0.0, yscale = 0.0)
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, 0, 1)

        label = gtk.Label(bookedFlight.callsign)
        labelAlignment = gtk.Alignment(xalign = 0.0, yalign = 0.5,
                                       xscale = 0.0, yscale = 0.0)
        labelAlignment.add(label)
        table.attach(labelAlignment, 1, 2, 0, 1)

        label = gtk.Label("<b>" + xstr("loadPIREP_send_date") + "</b>")
        label.set_use_markup(True)
        labelAlignment = gtk.Alignment(xalign = 1.0, yalign = 0.5,
                                       xscale = 0.0, yscale = 0.0)
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, 1, 2)

        label = gtk.Label(str(bookedFlight.departureTime.date()))
        labelAlignment = gtk.Alignment(xalign = 0.0, yalign = 0.5,
                                       xscale = 0.0, yscale = 0.0)
        labelAlignment.add(label)
        table.attach(labelAlignment, 1, 2, 1, 2)

        label = gtk.Label("<b>" + xstr("loadPIREP_send_from") + "</b>")
        label.set_use_markup(True)
        labelAlignment = gtk.Alignment(xalign = 1.0, yalign = 0.5,
                                       xscale = 0.0, yscale = 0.0)
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, 2, 3)

        label = gtk.Label(bookedFlight.departureICAO)
        labelAlignment = gtk.Alignment(xalign = 0.0, yalign = 0.5,
                                       xscale = 0.0, yscale = 0.0)
        labelAlignment.add(label)
        table.attach(labelAlignment, 1, 2, 2, 3)

        label = gtk.Label("<b>" + xstr("loadPIREP_send_to") + "</b>")
        label.set_use_markup(True)
        labelAlignment = gtk.Alignment(xalign = 1.0, yalign = 0.5,
                                       xscale = 0.0, yscale = 0.0)
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, 3, 4)

        label = gtk.Label(bookedFlight.arrivalICAO)
        labelAlignment = gtk.Alignment(xalign = 0.0, yalign = 0.5,
                                       xscale = 0.0, yscale = 0.0)
        labelAlignment.add(label)
        table.attach(labelAlignment, 1, 2, 3, 4)

        label = gtk.Label("<b>" + xstr("loadPIREP_send_rating") + "</b>")
        label.set_use_markup(True)
        labelAlignment = gtk.Alignment(xalign = 1.0, yalign = 0.5,
                                       xscale = 0.0, yscale = 0.0)
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, 4, 5)

        rating = pirep.rating
        label = gtk.Label()
        if rating<0:
            label.set_markup('<b><span foreground="red">NO GO</span></b>')
        else:
            label.set_text("%.1f %%" % (rating,))

        labelAlignment = gtk.Alignment(xalign = 0.0, yalign = 0.5,
                                       xscale = 0.0, yscale = 0.0)
        labelAlignment.add(label)
        table.attach(labelAlignment, 1, 2, 4, 5)

        dialog.add_button(xstr("button_cancel"), RESPONSETYPE_REJECT)
        dialog.add_button(xstr("viewPIREP"), 1)
        dialog.add_button(xstr("sendPIREP"), RESPONSETYPE_OK)

        return dialog

    def sendPIREP(self, pirep, callback = None):
        """Send the given PIREP."""
        self.beginBusy(xstr("sendPIREP_busy"))
        self._sendPIREPCallback = callback
        self.webHandler.sendPIREP(self._pirepSentCallback, pirep)

    def _pirepSentCallback(self, returned, result):
        """Callback for the PIREP sending result."""
        gobject.idle_add(self._handlePIREPSent, returned, result)

    def _handlePIREPSent(self, returned, result):
        """Callback for the PIREP sending result."""
        self.endBusy()
        secondaryMarkup = None
        type = MESSAGETYPE_ERROR
        if returned:
            if result.success:
                type = MESSAGETYPE_INFO
                messageFormat = xstr("sendPIREP_success")
                secondaryMarkup = xstr("sendPIREP_success_sec")
            elif result.alreadyFlown:
                messageFormat = xstr("sendPIREP_already")
                secondaryMarkup = xstr("sendPIREP_already_sec")
            elif result.notAvailable:
                messageFormat = xstr("sendPIREP_notavail")
            else:
                messageFormat = xstr("sendPIREP_unknown")
                secondaryMarkup = xstr("sendPIREP_unknown_sec")
        else:
            print "PIREP sending failed", result
            messageFormat = xstr("sendPIREP_failed")
            secondaryMarkup = xstr("sendPIREP_failed_sec")

        dialog = gtk.MessageDialog(parent = self._wizard.gui.mainWindow,
                                   type = type, message_format = messageFormat)
        dialog.add_button(xstr("button_ok"), RESPONSETYPE_OK)
        dialog.set_title(WINDOW_TITLE_BASE)
        if secondaryMarkup is not None:
            dialog.format_secondary_markup(secondaryMarkup)

        dialog.run()
        dialog.hide()

        callback = self._sendPIREPCallback
        self._sendPIREPCallback = None
        if callback is not None:
            callback(returned, result)

    def sendBugReport(self, summary, description, email, callback = None):
        """Send the bug report with the given data."""
        description += "\n\n" + ("=" * 40)
        description += "\n\nThe contents of the log:\n\n"

        for (timestampString, text) in self._logger.lines:
            description += unicode(formatFlightLogLine(timestampString, text))

        description += "\n\n" + ("=" * 40)
        description += "\n\nThe contents of the debug log:\n\n"

        buffer = self._debugLogView.get_buffer()
        description += buffer.get_text(buffer.get_start_iter(),
                                       buffer.get_end_iter(), True)

        self.beginBusy(xstr("sendBugReport_busy"))
        self._sendBugReportCallback = callback
        self.webHandler.sendBugReport(self._bugReportSentCallback,
                                      summary, description, email)

    def _cefInitialized(self):
        """Called when CEF has been initialized."""
        self._acars.start()
        cef.initializeSimBrief()

    def _bugReportSentCallback(self, returned, result):
        """Callback function for the bug report sending result."""
        gobject.idle_add(self._handleBugReportSent, returned, result)

    def _handleBugReportSent(self, returned, result):
        """Callback for the bug report sending result."""
        self.endBusy()
        secondaryMarkup = None
        type = MESSAGETYPE_ERROR
        if returned:
            if result.success:
                type = MESSAGETYPE_INFO
                messageFormat = xstr("sendBugReport_success") % (result.ticketID,)
                secondaryMarkup = xstr("sendBugReport_success_sec")
            else:
                messageFormat = xstr("sendBugReport_error")
                secondaryMarkup = xstr("sendBugReport_siteerror_sec")
        else:
            messageFormat = xstr("sendBugReport_error")
            secondaryMarkup = xstr("sendBugReport_error_sec")

        dialog = gtk.MessageDialog(parent = self._wizard.gui._bugReportDialog,
                                   type = type, message_format = messageFormat)
        dialog.add_button(xstr("button_ok"), RESPONSETYPE_OK)
        dialog.set_title(WINDOW_TITLE_BASE)
        if secondaryMarkup is not None:
            dialog.format_secondary_markup(secondaryMarkup)

        dialog.run()
        dialog.hide()

        callback = self._sendBugReportCallback
        self._sendBugReportCallback = None
        if callback is not None:
            callback(returned, result)

    def _listenHotkeys(self):
        """Setup the hotkeys based on the configuration."""
        if self._hotkeySetID is None and self._simulator is not None:
            self._pilotHotkeyIndex = None
            self._checklistHotkeyIndex = None

            hotkeys = []

            config = self.config
            if config.enableSounds and config.pilotControlsSounds:
                self._pilotHotkeyIndex = len(hotkeys)
                hotkeys.append(config.pilotHotkey)

            if config.enableChecklists:
                self._checklistHotkeyIndex = len(hotkeys)
                hotkeys.append(config.checklistHotkey)

            if hotkeys:
                self._hotkeySetID = \
                    self._simulator.listenHotkeys(hotkeys, self._handleHotkeys)

    def _clearHotkeys(self):
        """Clear the hotkeys."""
        if self._hotkeySetID is not None:
            self._hotkeySetID=None
            self._simulator.clearHotkeys()

    def _handleHotkeys(self, id, hotkeys):
        """Handle the hotkeys."""
        if id==self._hotkeySetID:
            for index in hotkeys:
                if index==self._pilotHotkeyIndex:
                    print "gui.GUI._handleHotkeys: pilot hotkey pressed"
                    self._flight.pilotHotkeyPressed()
                elif index==self._checklistHotkeyIndex:
                    print "gui.GUI._handleHotkeys: checklist hotkey pressed"
                    self._flight.checklistHotkeyPressed()
                else:
                    print "gui.GUI._handleHotkeys: unhandled hotkey index:", index

    def _showManual(self, menuitem):
        """Show the user's manual."""
        webbrowser.open(url ="file://" +
                        os.path.join(self._programDirectory, "doc", "manual",
                                     getLanguage(), "index.html"),
                        new = 1)

    def _showAbout(self, menuitem):
        """Show the about dialog."""
        dialog = self._getAboutDialog()
        dialog.show_all()
        dialog.run()
        dialog.hide()

    def _getAboutDialog(self):
        """Get the about dialog.

        If it does not exist yet, it will be created."""
        if self._aboutDialog is None:
            dialog = gtk.AboutDialog()
            dialog.set_transient_for(self._mainWindow)
            dialog.set_modal(True)

            logoPath = os.path.join(self._programDirectory, "logo.png")
            logo = pixbuf_new_from_file(logoPath)
            dialog.set_logo(logo)

            dialog.set_program_name(PROGRAM_NAME)
            dialog.set_version(const.VERSION)
            dialog.set_copyright("(c) 2012 by István Váradi")
            dialog.set_website("http://mlx.varadiistvan.hu")
            dialog.set_website_label(xstr("about_website"))

            isHungarian = getLanguage()=="hu"
            authors = []
            for (familyName, firstName, role) in GUI._authors:
                author = "%s %s" % \
                         (familyName if isHungarian else firstName,
                          firstName if isHungarian else familyName)
                role = xstr("about_role_" + role)
                authors.append(author + " (" + role + ")")
            dialog.set_authors(authors)

            dialog.set_license(xstr("about_license"))

            if not pygobject:
                gtk.about_dialog_set_url_hook(self._showAboutURL, None)

            self._aboutDialog = dialog

        return self._aboutDialog

    def _showAboutURL(self, dialog, link, user_data):
        """Show the about URL."""
        webbrowser.open(url = link, new = 1)

    def _setTakeoffAntiIceOn(self, value):
        """Set the anti-ice on indicator."""
        self._wizard.takeoffAntiIceOn = value

    def _setLandingAntiIceOn(self, value):
        """Set the anti-ice on indicator."""
        self._wizard.landingAntiIceOn = value

    def _getCredentialsCallback(self):
        """Called when the web handler asks for the credentials."""
        # FIXME: this is almost the same as
        # SimBriefSetupPage._getCredentialsCallback
        with self._credentialsCondition:
            self._credentialsAvailable = False

            gobject.idle_add(self._getCredentials)

            while not self._credentialsAvailable:
                self._credentialsCondition.wait()

            return (self._credentialsUserName, self._credentialsPassword)

    def _getCredentials(self):
        """Get the credentials."""
        # FIXME: this is almost the same as
        # SimBriefSetupPage._getCredentials
        with self._credentialsCondition:
            config = self.config

            dialog = CredentialsDialog(self, config.pilotID, config.password,
                                       xstr("login_title"),
                                       xstr("button_cancel"),
                                       xstr("button_ok"),
                                       xstr("label_pilotID"),
                                       xstr("login_pilotID_tooltip"),
                                       xstr("label_password"),
                                       xstr("login_password_tooltip"),
                                       xstr("login_info"),
                                       config.rememberPassword,
                                       xstr("remember_password"),
                                       xstr("login_remember_tooltip"))
            response = dialog.run()

            if response==RESPONSETYPE_OK:
                self._credentialsUserName = dialog.userName
                self._credentialsPassword = dialog.password
                rememberPassword = dialog.rememberPassword

                config.pilotID = self._credentialsUserName

                config.password = \
                  self._credentialsPassword if rememberPassword else ""
                config.rememberPassword = rememberPassword

                config.save()
            else:
                self._credentialsUserName = None
                self._credentialsPassword = None

            self._credentialsAvailable = True
            self._credentialsCondition.notify()

    def _updateDone(self):
        """Called when the update is done.

        It checks if we already know the PID, and if not, asks the user whether
        to register."""
        if not self.config.pilotID and not self.config.password:
            dialog = gtk.MessageDialog(parent = self._mainWindow,
                                       type = MESSAGETYPE_QUESTION,
                                       message_format = xstr("register_ask"))

            dialog.set_title(WINDOW_TITLE_BASE)
            dialog.format_secondary_markup(xstr("register_ask_sec"))

            dialog.add_button(xstr("button_cancel"), 0)
            dialog.add_button(xstr("button_register"), 1)
            dialog.set_default_response(1)

            result = dialog.run()
            dialog.hide()
            if result == 1:
                self._wizard.jumpPage("register")
