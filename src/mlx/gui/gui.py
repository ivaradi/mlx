# The main file for the GUI

from statusicon import StatusIcon
from statusbar import Statusbar
from info import FlightInfo
from update import Updater
from mlx.gui.common import *
from mlx.gui.flight import Wizard
from mlx.gui.monitor import MonitorWindow
from mlx.gui.weighthelp import WeightHelp

import mlx.const as const
import mlx.fs as fs
import mlx.flight as flight
import mlx.logger as logger
import mlx.acft as acft
import mlx.web as web
from  mlx.i18n import xstr

import time
import threading
import sys

#------------------------------------------------------------------------------

class GUI(fs.ConnectionListener):
    """The main GUI class."""
    @staticmethod
    def _formatFlightLogLine(timeStr, line):
        """Format the given line for flight logging."""
        if timeStr is not None:
            line = timeStr + ": " + line
        return line + "\n"
        
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
        self._monitoring = False

        self._stdioLock = threading.Lock()
        self._stdioText = ""

        self.webHandler = web.Handler()
        self.webHandler.start()

        self.toRestart = False

    def build(self, iconDirectory):
        """Build the GUI."""
        
        window = gtk.Window()
        window.set_title(WINDOW_TITLE_BASE)
        window.set_icon_from_file(os.path.join(iconDirectory, "logo.ico"))
        window.connect("delete-event",
                       lambda a, b: self.hideMainWindow())
        window.connect("window-state-event", self._handleMainWindowState)
        accelGroup = gtk.AccelGroup()
        window.add_accel_group(accelGroup)

        mainVBox = gtk.VBox()
        window.add(mainVBox)

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
        label = gtk.Label(xstr("tab_log"))
        label.set_use_underline(True)
        label.set_tooltip_text(xstr("tab_log_tooltip"))
        self._notebook.append_page(logWidget, label)

        (self._debugLogWidget, self._debugLogView) = self._buildLogWidget()
        self._debugLogWidget.show_all()

        mainVBox.pack_start(gtk.HSeparator(), False, False, 0)

        self._statusbar = Statusbar()
        mainVBox.pack_start(self._statusbar, False, False, 0)

        self._notebook.connect("switch-page", self._notebookPageSwitch)

        self._monitorWindow = MonitorWindow(self, iconDirectory)
        self._monitorWindow.add_accel_group(accelGroup)
        self._monitorWindowX = None
        self._monitorWindowY = None
        self._selfToggling = False

        window.show_all()
        self._wizard.grabDefault()
        self._weightHelp.reset()
        self._weightHelp.disable()

        self._mainWindow = window

        self._statusIcon = StatusIcon(iconDirectory, self)

        self._busyCursor = gdk.Cursor(gdk.CursorType.WATCH if pygobject
                                      else gdk.WATCH)

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
    def bookedFlight(self):
        """Get the booked flight selected, if any."""
        return self._wizard.bookedFlight

    @property
    def cargoWeight(self):
        """Get the cargo weight."""
        return self._wizard.cargoWeight

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
    def flightDefects(self):
        """Get the flight defects."""
        return self._flightInfo.flightDefects

    @property
    def delayCodes(self):
        """Get the delay codes."""
        return self._flightInfo.delayCodes

    def run(self):
        """Run the GUI."""
        if self.config.autoUpdate:
            self._updater = Updater(self,
                                    self._programDirectory,
                                    self.config.updateURL,
                                    self._mainWindow)
            self._updater.start()

        gtk.main()

        self._disconnect()

    def connected(self, fsType, descriptor):
        """Called when we have connected to the simulator."""
        self._connected = True
        self._logger.untimedMessage("Connected to the simulator %s" % (descriptor,))
        gobject.idle_add(self._handleConnected, fsType, descriptor)

    def _handleConnected(self, fsType, descriptor):
        """Called when the connection to the simulator has succeeded."""
        self._statusbar.updateConnection(self._connecting, self._connected)
        self.endBusy()
        if not self._reconnecting:
            self._wizard.connected(fsType, descriptor)
        self._reconnecting = False

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

    def enableFlightInfo(self):
        """Enable the flight info tab."""
        self._flightInfo.enable()

    def reset(self):
        """Reset the GUI."""
        self._disconnect()

        self._flightInfo.reset()
        self._flightInfo.disable()
        self.resetFlightStatus()

        self._weightHelp.reset()
        self._weightHelp.disable()
        self._wizard.reset()
        self._notebook.set_current_page(0)

        self._logView.get_buffer().set_text("")

    def _disconnect(self):
        """Disconnect from the simulator if connected."""
        self.stopMonitoring()

        if self._connected:
            self._flight.simulator.disconnect()
            self._connected = False

        self._connecting = False
        self._reconnecting = False
        self._statusbar.updateConnection(False, False)
            
    def addFlightLogLine(self, timeStr, line):
        """Write the given message line to the log."""
        gobject.idle_add(self._writeLog,
                         GUI._formatFlightLogLine(timeStr, line),
                         self._logView)

    def updateFlightLogLine(self, index, timeStr, line):
        """Update the line with the given index."""
        gobject.idle_add(self._updateFlightLogLine, index,
                         GUI._formatFlightLogLine(timeStr, line))

    def _updateFlightLogLine(self, index, line):
        """Replace the contents of the given line in the log."""
        buffer = self._logView.get_buffer()
        startIter = buffer.get_iter_at_line(index)
        endIter = buffer.get_iter_at_line(index + 1)
        buffer.delete(startIter, endIter)
        buffer.insert(startIter, line)
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
            self._disconnect()

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
        if (event.changed_mask&iconified)!=0 and (event.new_window_state&iconified)!=0:
            self.hideMainWindow(savePosition = False)

    def hideMainWindow(self, savePosition = True):
        """Hide the main window and save its position."""
        if savePosition:
            (self._mainWindowX, self._mainWindowY) = \
                 self._mainWindow.get_window().get_root_origin()
        else:
            self._mainWindowX = self._mainWindowY = None
        self._mainWindow.hide()
        self._statusIcon.mainWindowHidden()
        return True

    def showMainWindow(self):
        """Show the main window at its former position."""
        if self._mainWindowX is not None and self._mainWindowY is not None:
            self._mainWindow.move(self._mainWindowX, self._mainWindowY)

        self._mainWindow.show()
        self._mainWindow.deiconify()
            
        self._statusIcon.mainWindowShown()

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
            
        for line in lines:
            #print >> sys.__stdout__, line
            self._writeLog(line + "\n", self._debugLogView)

        if text:
            #print >> sys.__stdout__, text,
            self._writeLog(text, self._debugLogView)

    def connectSimulator(self, aircraftType):
        """Connect to the simulator for the first time."""
        self._logger.reset()

        self._flight = flight.Flight(self._logger, self)
        self._flight.aircraftType = aircraftType
        self._flight.aircraft = acft.Aircraft.create(self._flight)
        self._flight.aircraft._checkers.append(self)
        
        if self._simulator is None:
            self._simulator = fs.createSimulator(const.SIM_MSFS9, self)

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

    def _buildMenuBar(self, accelGroup):
        """Build the main menu bar."""
        menuBar = gtk.MenuBar()
        
        fileMenuItem = gtk.MenuItem(xstr("menu_file"))
        fileMenu = gtk.Menu()
        fileMenuItem.set_submenu(fileMenu)
        menuBar.append(fileMenuItem)

        quitMenuItem = gtk.ImageMenuItem(gtk.STOCK_QUIT)
        quitMenuItem.set_use_stock(True)
        quitMenuItem.set_label(xstr("menu_file_quit"))
        quitMenuItem.add_accelerator("activate", accelGroup,
                                     ord(xstr("menu_file_quit_key")),
                                     CONTROL_MASK, ACCEL_VISIBLE)
        quitMenuItem.connect("activate", self._quit)
        fileMenu.append(quitMenuItem)


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
        logScroller.add(logView)

        logBox = gtk.VBox()
        logBox.pack_start(logScroller, True, True, 0)
        logBox.set_size_request(-1, 200)

        alignment.add(logBox)

        return (alignment, logView)

    def _writeLog(self, msg, logView):
        """Write the given message to the log."""
        buffer = logView.get_buffer()
        buffer.insert(buffer.get_end_iter(), msg)
        logView.scroll_mark_onscreen(buffer.get_insert())

    def _quit(self, what = None, force = False):
        """Quit from the application."""
        if force:
            result=RESPONSETYPE_YES
        else:
            dialog = gtk.MessageDialog(parent = self._mainWindow,
                                       type = MESSAGETYPE_QUESTION,
                                       buttons = BUTTONSTYPE_YES_NO,
                                       message_format = xstr("quit_question"))

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
