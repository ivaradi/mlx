# The main file for the GUI

from statusicon import StatusIcon
from statusbar import Statusbar
from update import Updater
from mlx.gui.common import *
from mlx.gui.flight import Wizard
from mlx.gui.monitor import MonitorWindow

import mlx.const as const
import mlx.fs as fs
import mlx.flight as flight
import mlx.logger as logger
import mlx.acft as acft
import mlx.web as web

import time
import threading
import sys

#------------------------------------------------------------------------------

class GUI(fs.ConnectionListener):
    """The main GUI class."""
    def __init__(self, programDirectory, config):
        """Construct the GUI."""
        gobject.threads_init()

        self._programDirectory = programDirectory
        self.config = config
        self._connecting = False
        self._reconnecting = False
        self._connected = False
        self._logger = logger.Logger(output = self)
        self._flight = None
        self._simulator = None
        self._monitoring = False

        self._stdioLock = threading.Lock()
        self._stdioText = ""
        self._stdioAfterNewLine = True

        self.webHandler = web.Handler()
        self.webHandler.start()

        self.toRestart = False

    def build(self, iconDirectory):
        """Build the GUI."""
        
        window = gtk.Window()
        window.set_title("MAVA Logger X " + const.VERSION)
        window.set_icon_from_file(os.path.join(iconDirectory, "logo.ico"))
        window.connect("delete-event",
                       lambda a, b: self.hideMainWindow())
        window.connect("window-state-event", self._handleMainWindowState)

        mainVBox = gtk.VBox()
        window.add(mainVBox)

        notebook = gtk.Notebook()
        mainVBox.add(notebook)

        self._wizard = Wizard(self)
        label = gtk.Label("_Flight")
        label.set_use_underline(True)
        label.set_tooltip_text("Flight wizard")
        notebook.append_page(self._wizard, label)

        logVBox = gtk.VBox()
        label = gtk.Label("_Log")
        label.set_use_underline(True)
        label.set_tooltip_text("Flight log")
        notebook.append_page(logVBox, label)
        
        logFrame = self._buildLogFrame()
        logFrame.set_border_width(8)
        logVBox.pack_start(logFrame, True, True, 0)

        mainVBox.pack_start(gtk.HSeparator(), False, False, 0)

        self._statusbar = Statusbar()
        mainVBox.pack_start(self._statusbar, False, False, 0)

        notebook.connect("switch-page", self._notebookPageSwitch)

        self._monitorWindow = MonitorWindow(self, iconDirectory)
        self._monitorWindowX = None
        self._monitorWindowY = None

        window.show_all()
        self._wizard.grabDefault()

        self._mainWindow = window

        self._statusIcon = StatusIcon(iconDirectory, self)

        self._busyCursor = gdk.Cursor(gdk.CursorType.WATCH if pygobject
                                      else gdk.WATCH)

    @property
    def simulator(self):
        """Get the simulator used by us."""
        return self._simulator
        
    @property
    def flight(self):
        """Get the flight being performed."""
        return self._flight
        
    def run(self):
        """Run the GUI."""
        if self.config.autoUpdate:
            self._updater = Updater(self,
                                    self._programDirectory,
                                    self.config.updateURL,
                                    self._mainWindow)
            self._updater.start()

        gtk.main()

        if self._flight is not None:
            simulator = self._flight.simulator
            if self._monitoring:
                simulator.stopMonitoring()
                self._monitoring = False
            simulator.disconnect()                        

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

        dialog = gtk.MessageDialog(type = MESSAGETYPE_ERROR,
                                   message_format =
                                   "Cannot connect to the simulator.",
                                   parent = self._mainWindow)
        dialog.format_secondary_markup("Rectify the situation, and press <b>Try again</b> "
                                       "to try the connection again, " 
                                       "or <b>Cancel</b> to cancel the flight.")
        
        dialog.add_button("_Cancel", 0)
        dialog.add_button("_Try again", 1)
        dialog.set_default_response(1)
        
        result = dialog.run()
        dialog.hide()
        if result == 1:
            self.beginBusy("Connecting to the simulator.")
            self._simulator.reconnect()
        else:
            self._connecting = False
            self._reconnecting = False
            self._statusbar.updateConnection(self._connecting, self._connected)
            self._wizard.connectionFailed()
        
    def disconnected(self):
        """Called when we have disconnected from the simulator."""
        self._connected = False
        self._logger.untimedMessage("Disconnected from the simulator")

        gobject.idle_add(self._disconnected)

    def _disconnected(self):
        """Called when we have disconnected from the simulator unexpectedly."""        
        self._statusbar.updateConnection(self._connecting, self._connected)

        dialog = gtk.MessageDialog(type = MESSAGETYPE_ERROR,
                                   message_format =
                                   "The connection to the simulator failed unexpectedly.",
                                   parent = self._mainWindow)
        dialog.format_secondary_markup("If the simulator has crashed, restart it "
                                       "and restore your flight as much as possible "
                                       "to the state it was in before the crash.\n"
                                       "Then press <b>Reconnect</b> to reconnect.\n\n"
                                       "If you want to cancel the flight, press <b>Cancel</b>.")

        dialog.add_button("_Cancel", 0)
        dialog.add_button("_Reconnect", 1)
        dialog.set_default_response(1)

        result = dialog.run()
        dialog.hide()
        if result == 1:
            self.beginBusy("Connecting to the simulator.")
            self._reconnecting = True
            self._simulator.reconnect()
        else:
            self._connecting = False
            self._reconnecting = False
            self._statusbar.updateConnection(self._connecting, self._connected)
            self._wizard.disconnected()

    def write(self, msg):
        """Write the given message to the log."""
        gobject.idle_add(self._writeLog, msg)
        
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
        return True

    def showMonitorWindow(self):
        """Show the monitor window."""
        if self._monitorWindowX is not None and self._monitorWindowY is not None:
            self._monitorWindow.move(self._monitorWindowX, self._monitorWindowY)
        self._monitorWindow.show_all()
        self._statusIcon.monitorWindowShown()

    def restart(self):
        """Quit and restart the application."""
        self.toRestart = True
        self._quit()

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
        self._mainWindow.get_window().set_cursor(self._busyCursor)
        self._statusbar.updateBusyState(message)

    def endBusy(self):
        """End a period of background processing."""
        self._mainWindow.get_window().set_cursor(None)
        self._statusbar.updateBusyState(None)

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
            if self._stdioAfterNewLine:
                line = "[STDIO] " + line
            self._writeLog(line + "\n")
            self._stdioAfterNewLine = True

        if text:
            if self._stdioAfterNewLine:
                text = "[STDIO] " + text
            self._writeLog(text)
            self._stdioAfterNewLine = False

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

        self.beginBusy("Connecting to the simulator...")
        self._statusbar.updateConnection(self._connecting, self._connected)

        self._connecting = True
        self._simulator.connect(self._flight.aircraft)        

    def startMonitoring(self):
        """Start monitoring."""
        self._simulator.startMonitoring()
        self._monitoring = True

    def stopMonitoring(self):
        """Stop monitoring."""
        self._simulator.stoptMonitoring()
        self._monitoring = False

    def _buildLogFrame(self):
        """Build the frame for the log."""
        logFrame = gtk.Frame(label = "Log")

        frameAlignment = gtk.Alignment(xscale = 1.0, yscale = 1.0)

        frameAlignment.set_padding(padding_top = 4, padding_bottom = 10,
                                   padding_left = 16, padding_right = 16)

        logFrame.add(frameAlignment)

        logScroller = gtk.ScrolledWindow()
        self._logView = gtk.TextView()
        self._logView.set_editable(False)
        logScroller.add(self._logView)

        logBox = gtk.VBox()
        logBox.pack_start(logScroller, True, True, 0)
        logBox.set_size_request(-1, 200)

        frameAlignment.add(logBox)

        return logFrame

    def _writeLog(self, msg):
        """Write the given message to the log."""
        buffer = self._logView.get_buffer()
        buffer.insert(buffer.get_end_iter(), msg)
        self._logView.scroll_mark_onscreen(buffer.get_insert())

    def _quit(self, what = None):
        """Quit from the application."""
        dialog = gtk.MessageDialog(type = MESSAGETYPE_QUESTION,
                                   buttons = BUTTONSTYPE_YES_NO,
                                   message_format =
                                   "Are you sure to quit the logger?")
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
