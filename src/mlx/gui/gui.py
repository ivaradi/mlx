# The main file for the GUI

from statusicon import StatusIcon
from statusbar import Statusbar
from update import Updater
from mlx.gui.common import *
from mlx.gui.flight import Wizard

import mlx.const as const
import mlx.fs as fs
import mlx.flight as flight
import mlx.logger as logger
import mlx.acft as acft
import mlx.web as web

import time
import threading
import sys

acftTypes = [ ("Boeing 737-600", const.AIRCRAFT_B736),
              ("Boeing 737-700", const.AIRCRAFT_B737),
              ("Boeing 737-800", const.AIRCRAFT_B738),
              ("Bombardier Dash 8-Q400", const.AIRCRAFT_DH8D),
              ("Boeing 737-300", const.AIRCRAFT_B733),
              ("Boeing 737-400", const.AIRCRAFT_B734),
              ("Boeing 737-500", const.AIRCRAFT_B735),
              ("Boeing 767-200", const.AIRCRAFT_B762),
              ("Boeing 767-300", const.AIRCRAFT_B763),
              ("Bombardier CRJ200", const.AIRCRAFT_CRJ2),
              ("Fokker 70", const.AIRCRAFT_F70),
              ("Lisunov Li-2", const.AIRCRAFT_DC3),
              ("Tupolev Tu-134", const.AIRCRAFT_T134),
              ("Tupolev Tu-154", const.AIRCRAFT_T154),
              ("Yakovlev Yak-40", const.AIRCRAFT_YK40) ]

class GUI(fs.ConnectionListener):
    """The main GUI class."""
    def __init__(self, programDirectory, config):
        """Construct the GUI."""
        gobject.threads_init()

        self._programDirectory = programDirectory
        self.config = config
        self._connecting = False
        self._connected = False
        self._logger = logger.Logger(output = self)
        self._flight = None
        self._simulator = None

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


        dataVBox = gtk.VBox()
        label = gtk.Label("_Data")
        label.set_use_underline(True)
        label.set_tooltip_text("FSUIPC data access")

        if "USE_SCROLLEDDATA" in os.environ:
            dataScrolledWindow = gtk.ScrolledWindow()
            dataScrolledWindow.add_with_viewport(dataVBox)
            notebook.append_page(dataScrolledWindow, label)
        else:
            notebook.append_page(dataVBox, label)

        setupFrame = self._buildSetupFrame()
        setupFrame.set_border_width(8)
        dataVBox.pack_start(setupFrame, False, False, 0)

        dataFrame = self._buildDataFrame()
        dataFrame.set_border_width(8)
        dataVBox.pack_start(dataFrame, False, False, 0)

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

        window.show_all()
        self._wizard.grabDefault()

        self._mainWindow = window

        self._statusIcon = StatusIcon(iconDirectory, self)

        self._busyCursor = gdk.Cursor(gdk.CursorType.WATCH if pygobject
                                      else gdk.WATCH)

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
            simulator.stopMonitoring()
            simulator.disconnect()            

    def connected(self, fsType, descriptor):
        """Called when we have connected to the simulator."""
        self._connected = True
        self._logger.untimedMessage("Connected to the simulator %s" % (descriptor,))
        gobject.idle_add(self._statusbar.updateConnection,
                         self._connecting, self._connected)
        
    def disconnected(self):
        """Called when we have disconnected from the simulator."""
        self._connected = False
        self._logger.untimedMessage("Disconnected from the simulator")
        gobject.idle_add(self._statusbar.updateConnection,
                         self._connecting, self._connected)

    def write(self, msg):
        """Write the given message to the log."""
        gobject.idle_add(self._writeLog, msg)
        
    def check(self, flight, aircraft, logger, oldState, state):
        """Update the data."""
        gobject.idle_add(self._setData, state)

    def resetFlightStatus(self):
        """Reset the status of the flight."""
        self._statusbar.resetFlightStatus()
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
        print dir(self._mainWindow)
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
            
    def _connectToggled(self, button):
        """Callback for the connection button."""
        if self._connectButton.get_active():
            self._logger.reset()
            self._flight = flight.Flight(self._logger, self)

            acftListModel = self._acftList.get_model()
            self._flight.aircraftType = \
                acftListModel[self._acftList.get_active()][1]
            self._flight.aircraft = acft.Aircraft.create(self._flight)
            self._flight.aircraft._checkers.append(self)

            self._flight.cruiseAltitude = self._flSpinButton.get_value_as_int() * 100

            self._flight.zfw = self._zfwSpinButton.get_value_as_int()

            if self._simulator is None:
                self._simulator = fs.createSimulator(const.SIM_MSFS9, self)

            self._flight.simulator = self._simulator

            self._connecting = True
            self._simulator.connect(self._flight.aircraft)
            self._simulator.startMonitoring()
        else:
            self.resetFlightStatus()
            self._connecting = False
            self._simulator.stopMonitoring()
            self._simulator.disconnect()
            self._flight = None

        self._statusbar.updateConnection(self._connecting, self._connected)

    def _buildSetupFrame(self):
        """Build the setup frame."""
        setupFrame = gtk.Frame(label = "Setup")

        frameAlignment = gtk.Alignment(xalign = 0.5)

        frameAlignment.set_padding(padding_top = 4, padding_bottom = 10,
                                   padding_left = 16, padding_right = 16)

        setupFrame.add(frameAlignment)

        setupBox = gtk.HBox()
        frameAlignment.add(setupBox)

        # self._fs9Button = gtk.RadioButton(label = "FS9")
        # self._fs9Button.set_tooltip_text("Use MS Flight Simulator 2004")
        # setupBox.pack_start(self._fs9Button, False, False, 0)

        # self._fsxButton = gtk.RadioButton(group = self._fs9Button, label = "FSX")
        # self._fsxButton.set_tooltip_text("Use MS Flight Simulator X")
        # setupBox.pack_start(self._fsxButton, False, False, 0)

        # setupBox.pack_start(gtk.VSeparator(), False, False, 8)

        alignment = gtk.Alignment(yalign = 0.5)
        alignment.set_padding(padding_top = 0, padding_bottom = 0,
                              padding_left = 0, padding_right = 16)
        alignment.add(gtk.Label("Aicraft:"))
        setupBox.pack_start(alignment, False, False, 0)

        acftListModel = gtk.ListStore(str, int)
        for (name, type) in acftTypes:
            acftListModel.append([name, type])

        self._acftList = gtk.ComboBox(model = acftListModel)    
        renderer_text = gtk.CellRendererText()
        self._acftList.pack_start(renderer_text, True)
        self._acftList.add_attribute(renderer_text, "text", 0)
        self._acftList.set_active(0)
        self._acftList.set_tooltip_text("Select the type of the aircraft used for the flight.")

        setupBox.pack_start(self._acftList, True, True, 0)

        setupBox.pack_start(gtk.VSeparator(), False, False, 8)

        alignment = gtk.Alignment(yalign = 0.5)
        alignment.set_padding(padding_top = 0, padding_bottom = 0,
                              padding_left = 0, padding_right = 16)
        alignment.add(gtk.Label("Cruise FL:"))
        setupBox.pack_start(alignment, False, False, 0)

        self._flSpinButton = gtk.SpinButton()
        self._flSpinButton.set_increments(step = 10, page = 100)
        self._flSpinButton.set_range(min = 0, max = 500)
        self._flSpinButton.set_value(240)
        self._flSpinButton.set_tooltip_text("The cruise flight level.")
        self._flSpinButton.set_numeric(True)

        setupBox.pack_start(self._flSpinButton, False, False, 0)

        setupBox.pack_start(gtk.VSeparator(), False, False, 8)

        alignment = gtk.Alignment(yalign = 0.5)
        alignment.set_padding(padding_top = 0, padding_bottom = 0,
                              padding_left = 0, padding_right = 16)
        alignment.add(gtk.Label("ZFW:"))
        setupBox.pack_start(alignment, False, False, 0)

        self._zfwSpinButton = gtk.SpinButton()
        self._zfwSpinButton.set_increments(step = 100, page = 1000)
        self._zfwSpinButton.set_range(min = 0, max = 500000)
        self._zfwSpinButton.set_value(50000)
        self._zfwSpinButton.set_tooltip_text("The Zero Fuel Weight for the flight in kgs")
        self._zfwSpinButton.set_numeric(True)

        setupBox.pack_start(self._zfwSpinButton, False, False, 0)

        setupBox.pack_start(gtk.VSeparator(), False, False, 8)    

        self._connectButton = gtk.ToggleButton(label = "_Connect",
                                               use_underline = True)
        self._connectButton.set_tooltip_text("Push to connect to Flight Simulator and start a new flight.\n"
                                             "Push again to disconnect from FS.")
        self._connectButton.set_can_default(True)
        
        self._connectButton.connect("toggled", self._connectToggled)

        setupBox.pack_start(self._connectButton, False, False, 0)

        setupBox.pack_start(gtk.VSeparator(), False, False, 8)    

        self._quitButton = gtk.Button(label = "_Quit", use_underline = True)
        self._quitButton.set_tooltip_text("Quit the program.")
        
        self._quitButton.connect("clicked", self._quit)

        setupBox.pack_start(self._quitButton, False, False, 0)

        return setupFrame

    def _createLabeledEntry(self, label, width = 8, xalign = 1.0):
        """Create a labeled entry.

        Return a tuple consisting of:
        - the box
        - the entry."""
        
        alignment = gtk.Alignment(xalign = 1.0, yalign = 0.5, xscale = 1.0)
        alignment.set_padding(padding_top = 0, padding_bottom = 0,
                              padding_left = 0, padding_right = 16)
        alignment.add(gtk.Label(label))

        entry = gtk.Entry()
        entry.set_editable(False)
        entry.set_width_chars(width)
        entry.set_max_length(width)
        entry.set_alignment(xalign)

        return (alignment, entry)

    def _buildDataFrame(self):
        """Build the frame for the data."""
        dataFrame = gtk.Frame(label = "Data")

        frameAlignment = gtk.Alignment(xscale = 1.0, yscale = 1.0)

        frameAlignment.set_padding(padding_top = 4, padding_bottom = 10,
                                   padding_left = 16, padding_right = 16)

        table = gtk.Table(rows = 7, columns = 12)
        table.set_homogeneous(False)
        table.set_row_spacings(4)
        table.set_col_spacings(8)

        (label, self._timestamp) = self._createLabeledEntry("Time:")
        table.attach(label, 0, 1, 0, 1)
        table.attach(self._timestamp, 1, 2, 0, 1)

        self._paused = gtk.Label("PAUSED")
        table.attach(self._paused, 2, 4, 0, 1)
        
        self._trickMode = gtk.Label("TRICKMODE")
        table.attach(self._trickMode, 4, 6, 0, 1, xoptions = 0)
        
        self._overspeed = gtk.Label("OVERSPEED")
        table.attach(self._overspeed, 6, 8, 0, 1)
        
        self._stalled = gtk.Label("STALLED")
        table.attach(self._stalled, 8, 10, 0, 1)
        
        self._onTheGround = gtk.Label("ONTHEGROUND")
        table.attach(self._onTheGround, 10, 12, 0, 1)
        
        (label, self._zfw) = self._createLabeledEntry("ZFW:", 6)
        table.attach(label, 0, 1, 1, 2)
        table.attach(self._zfw, 1, 2, 1, 2)

        (label, self._grossWeight) = self._createLabeledEntry("Weight:", 6)
        table.attach(label, 2, 3, 1, 2)
        table.attach(self._grossWeight, 3, 4, 1, 2)

        (label, self._heading) = self._createLabeledEntry("Heading:", 3)
        table.attach(label, 4, 5, 1, 2)
        table.attach(self._heading, 5, 6, 1, 2)

        (label, self._pitch) = self._createLabeledEntry("Pitch:", 3)
        table.attach(label, 6, 7, 1, 2)
        table.attach(self._pitch, 7, 8, 1, 2)

        (label, self._bank) = self._createLabeledEntry("Bank:", 3)
        table.attach(label, 8, 9, 1, 2)
        table.attach(self._bank, 9, 10, 1, 2)

        (label, self._vs) = self._createLabeledEntry("VS:", 5)
        table.attach(label, 10, 11, 1, 2)
        table.attach(self._vs, 11, 12, 1, 2)

        (label, self._ias) = self._createLabeledEntry("IAS:", 4)
        table.attach(label, 0, 1, 2, 3)
        table.attach(self._ias, 1, 2, 2, 3)

        (label, self._mach) = self._createLabeledEntry("Mach:", 4)
        table.attach(label, 2, 3, 2, 3)
        table.attach(self._mach, 3, 4, 2, 3)

        (label, self._groundSpeed) = self._createLabeledEntry("GS:", 4)
        table.attach(label, 4, 5, 2, 3)
        table.attach(self._groundSpeed, 5, 6, 2, 3)

        (label, self._radioAltitude) = self._createLabeledEntry("Radio alt.:", 6)
        table.attach(label, 6, 7, 2, 3)
        table.attach(self._radioAltitude, 7, 8, 2, 3)

        (label, self._altitude) = self._createLabeledEntry("Altitude:", 6)
        table.attach(label, 8, 9, 2, 3)
        table.attach(self._altitude, 9, 10, 2, 3)

        (label, self._gLoad) = self._createLabeledEntry("G-Load:", 4)
        table.attach(label, 10, 11, 2, 3)
        table.attach(self._gLoad, 11, 12, 2, 3)

        (label, self._flapsSet) = self._createLabeledEntry("Flaps set:", 2)
        table.attach(label, 0, 1, 3, 4)
        table.attach(self._flapsSet, 1, 2, 3, 4)

        (label, self._flaps) = self._createLabeledEntry("Flaps:", 2)
        table.attach(label, 2, 3, 3, 4)
        table.attach(self._flaps, 3, 4, 3, 4)

        (label, self._altimeter) = self._createLabeledEntry("Altimeter:", 4)
        table.attach(label, 4, 5, 3, 4)
        table.attach(self._altimeter, 5, 6, 3, 4)

        (label, self._squawk) = self._createLabeledEntry("Squawk:", 4)
        table.attach(label, 6, 7, 3, 4)
        table.attach(self._squawk, 7, 8, 3, 4)

        (label, self._nav1) = self._createLabeledEntry("NAV1:", 5)
        table.attach(label, 8, 9, 3, 4)
        table.attach(self._nav1, 9, 10, 3, 4)

        (label, self._nav2) = self._createLabeledEntry("NAV2:", 5)
        table.attach(label, 10, 11, 3, 4)
        table.attach(self._nav2, 11, 12, 3, 4)

        (label, self._fuel) = self._createLabeledEntry("Fuel:", 40, xalign = 0.0)
        table.attach(label, 0, 1, 4, 5)
        table.attach(self._fuel, 1, 4, 4, 5)

        (label, self._n1) = self._createLabeledEntry("N1/RPM:", 20, xalign = 0.0)
        table.attach(label, 4, 5, 4, 5)
        table.attach(self._n1, 5, 8, 4, 5)

        (label, self._reverser) = self._createLabeledEntry("Reverser:", 20, xalign = 0.0)
        table.attach(label, 8, 9, 4, 5)
        table.attach(self._reverser, 9, 12, 4, 5)

        self._navLightsOn = gtk.Label("NAV")
        table.attach(self._navLightsOn, 0, 1, 5, 6)

        self._antiCollisionLightsOn = gtk.Label("ANTICOLLISION")
        table.attach(self._antiCollisionLightsOn, 1, 3, 5, 6)

        self._strobeLightsOn = gtk.Label("STROBE")
        table.attach(self._strobeLightsOn, 3, 4, 5, 6)

        self._landingLightsOn = gtk.Label("LANDING")
        table.attach(self._landingLightsOn, 4, 5, 5, 6)

        self._pitotHeatOn = gtk.Label("PITOT HEAT")
        table.attach(self._pitotHeatOn, 5, 7, 5, 6)

        self._parking = gtk.Label("PARKING")
        table.attach(self._parking, 7, 8, 5, 6)

        self._gearsDown = gtk.Label("GEARS DOWN")
        table.attach(self._gearsDown, 8, 10, 5, 6)

        self._spoilersArmed = gtk.Label("SPOILERS ARMED")
        table.attach(self._spoilersArmed, 10, 12, 5, 6)

        (label, self._spoilersExtension) = self._createLabeledEntry("Spoilers:", 3)
        table.attach(label, 0, 1, 6, 7)
        table.attach(self._spoilersExtension, 1, 2, 6, 7)

        (label, self._windSpeed) = self._createLabeledEntry("Wind speed:", 3)
        table.attach(label, 2, 3, 6, 7)
        table.attach(self._windSpeed, 3, 4, 6, 7)

        (label, self._windDirection) = self._createLabeledEntry("Wind from:", 3)
        table.attach(label, 4, 5, 6, 7)
        table.attach(self._windDirection, 5, 6, 6, 7)

        frameAlignment.add(table)

        dataFrame.add(frameAlignment)

        self._setData()

        return dataFrame        

    def _setData(self, aircraftState = None):
        """Set the data.

        If aircraftState is None, everything will be set to its default."""
        if aircraftState is None:
            self._timestamp.set_text("--:--:--")
            self._paused.set_sensitive(False)
            self._trickMode.set_sensitive(False)
            self._overspeed.set_sensitive(False)
            self._stalled.set_sensitive(False)
            self._onTheGround.set_sensitive(False)
            self._zfw.set_text("-")
            self._grossWeight.set_text("-")
            self._heading.set_text("-")
            self._pitch.set_text("-")
            self._bank.set_text("-")
            self._vs.set_text("-")
            self._ias.set_text("-")
            self._mach.set_text("-")
            self._groundSpeed.set_text("-")
            self._radioAltitude.set_text("-")
            self._altitude.set_text("-")
            self._gLoad.set_text("-")
            self._flapsSet.set_text("-")
            self._flaps.set_text("-")
            self._altimeter.set_text("-")
            self._squawk.set_text("-")
            self._nav1.set_text("-")
            self._nav2.set_text("-")
            self._fuel.set_text("-")
            self._n1.set_text("-")
            self._reverser.set_text("-")
            self._navLightsOn.set_sensitive(False)
            self._antiCollisionLightsOn.set_sensitive(False)
            self._strobeLightsOn.set_sensitive(False)
            self._landingLightsOn.set_sensitive(False)
            self._pitotHeatOn.set_sensitive(False)
            self._parking.set_sensitive(False)
            self._gearsDown.set_sensitive(False)
            self._spoilersArmed.set_sensitive(False)
            self._spoilersExtension.set_text("-")
            self._windSpeed.set_text("-")
            self._windDirection.set_text("-")
        else:
            self._timestamp.set_text(time.strftime("%H:%M:%S",
                                                   time.gmtime(aircraftState.timestamp)))
            self._paused.set_sensitive(aircraftState.paused)
            self._trickMode.set_sensitive(aircraftState.trickMode)
            self._overspeed.set_sensitive(aircraftState.overspeed)
            self._stalled.set_sensitive(aircraftState.stalled)
            self._onTheGround.set_sensitive(aircraftState.onTheGround)
            self._zfw.set_text("%.0f" % (aircraftState.zfw,))
            self._grossWeight.set_text("%.0f" % (aircraftState.grossWeight,))
            self._heading.set_text("%03.0f" % (aircraftState.heading,))
            self._pitch.set_text("%.0f" % (aircraftState.pitch,))
            self._bank.set_text("%.0f" % (aircraftState.bank,))
            self._vs.set_text("%.0f" % (aircraftState.vs,))
            self._ias.set_text("%.0f" % (aircraftState.ias,))
            self._mach.set_text("%.2f" % (aircraftState.mach,))
            self._groundSpeed.set_text("%.0f" % (aircraftState.groundSpeed,))
            self._radioAltitude.set_text("%.0f" % (aircraftState.radioAltitude,))
            self._altitude.set_text("%.0f" % (aircraftState.altitude,))
            self._gLoad.set_text("%.2f" % (aircraftState.gLoad,))
            self._flapsSet.set_text("%.0f" % (aircraftState.flapsSet,))
            self._flaps.set_text("%.0f" % (aircraftState.flaps,))
            self._altimeter.set_text("%.0f" % (aircraftState.altimeter,))
            self._squawk.set_text(aircraftState.squawk)
            self._nav1.set_text(aircraftState.nav1)
            self._nav2.set_text(aircraftState.nav2)

            fuelStr = ""
            for fuel in aircraftState.fuel:
                if fuelStr: fuelStr += ", "
                fuelStr += "%.0f" % (fuel,)                
            self._fuel.set_text(fuelStr)

            if hasattr(aircraftState, "n1"):
                n1Str = ""
                for n1 in aircraftState.n1:
                    if n1Str: n1Str += ", "
                    n1Str += "%.0f" % (n1,)
            elif hasattr(aircraftState, "rpm"):
                n1Str = ""
                for rpm in aircraftState.rpm:
                    if n1Str: n1Str += ", "
                    n1Str += "%.0f" % (rpm,)
            else:
                n1Str = "-"
            self._n1.set_text(n1Str)

            reverserStr = ""
            for reverser in aircraftState.reverser:
                if reverserStr: reverserStr += ", "
                reverserStr += "ON" if reverser else "OFF"
            self._reverser.set_text(reverserStr)

            self._navLightsOn.set_sensitive(aircraftState.navLightsOn)
            self._antiCollisionLightsOn.set_sensitive(aircraftState.antiCollisionLightsOn)
            self._strobeLightsOn.set_sensitive(aircraftState.strobeLightsOn)
            self._landingLightsOn.set_sensitive(aircraftState.landingLightsOn)
            self._pitotHeatOn.set_sensitive(aircraftState.pitotHeatOn)
            self._parking.set_sensitive(aircraftState.parking)
            self._gearsDown.set_sensitive(aircraftState.gearsDown)
            self._spoilersArmed.set_sensitive(aircraftState.spoilersArmed)
            self._spoilersExtension.set_text("%.0f" % (aircraftState.spoilersExtension,))
            self._windSpeed.set_text("%.0f" % (aircraftState.windSpeed,))
            self._windDirection.set_text("%03.0f" % (aircraftState.windDirection,))

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
        self._statusIcon.destroy()
        return gtk.main_quit()

    def _notebookPageSwitch(self, notebook, page, page_num):
        """Called when the current page of the notebook has changed."""
        if page_num==0:
            gobject.idle_add(self._wizard.grabDefault)
        elif page_num==1:
            gobject.idle_add(self._connectButton.grab_default)
        else:
            self._mainWindow.set_default(None)

class TrackerStatusIcon(gtk.StatusIcon):
	def __init__(self):
		gtk.StatusIcon.__init__(self)
		menu = '''
			<ui>
			 <menubar name="Menubar">
			  <menu action="Menu">
			   <menuitem action="Search"/>
			   <menuitem action="Preferences"/>
			   <separator/>
			   <menuitem action="About"/>
			  </menu>
			 </menubar>
			</ui>
		'''
		actions = [
			('Menu',  None, 'Menu'),
			('Search', None, '_Search...', None, 'Search files with MetaTracker', self.on_activate),
			('Preferences', gtk.STOCK_PREFERENCES, '_Preferences...', None, 'Change MetaTracker preferences', self.on_preferences),
			('About', gtk.STOCK_ABOUT, '_About...', None, 'About MetaTracker', self.on_about)]
		ag = gtk.ActionGroup('Actions')
		ag.add_actions(actions)
		self.manager = gtk.UIManager()
		self.manager.insert_action_group(ag, 0)
		self.manager.add_ui_from_string(menu)
		self.menu = self.manager.get_widget('/Menubar/Menu/About').props.parent
		search = self.manager.get_widget('/Menubar/Menu/Search')
		search.get_children()[0].set_markup('<b>_Search...</b>')
		search.get_children()[0].set_use_underline(True)
		search.get_children()[0].set_use_markup(True)
		#search.get_children()[1].set_from_stock(gtk.STOCK_FIND, gtk.ICON_SIZE_MENU)
		self.set_from_stock(gtk.STOCK_FIND)
		self.set_tooltip('Tracker Desktop Search')
		self.set_visible(True)
		self.connect('activate', self.on_activate)
		self.connect('popup-menu', self.on_popup_menu)

	def on_activate(self, data):
		os.spawnlpe(os.P_NOWAIT, 'tracker-search-tool', os.environ)

	def on_popup_menu(self, status, button, time):
		self.menu.popup(None, None, None, button, time)

	def on_preferences(self, data):
		print 'preferences'

	def on_about(self, data):
		dialog = gtk.AboutDialog()
		dialog.set_name('Tracker')
		dialog.set_version('0.5.0')
		dialog.set_comments('A desktop indexing and search tool')
		dialog.set_website('www.freedesktop.org/Tracker')
		dialog.run()
		dialog.destroy()
