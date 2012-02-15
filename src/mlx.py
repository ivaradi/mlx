# The main program

import const
import fs
import flight
import logger
import acft
import sys

import os
import math
import time

if os.name=="nt" or "FORCE_PYGTK" in os.environ:
    print "Using PyGTK"
    pygobject = False
    import pygtk
    import gtk
    import gobject
else:
    print "Using PyGObject"
    pygobject = True
    from gi.repository import Gtk as gtk
    from gi.repository import GObject as gobject

import cairo

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
    def __init__(self):
        """Construct the GUI."""
        self._connecting = False
        self._connected = False
        self._logger = logger.Logger(output = self)
        self._flight = None
        self._simulator = None

    def build(self):
        """Build the GUI."""
        win = gtk.Window()
        win.set_title("MAVA Logger X " + const.VERSION)
        win.connect("delete-event", gtk.main_quit)

        mainVBox = gtk.VBox()
        win.add(mainVBox)

        setupFrame = self._buildSetupFrame()
        setupFrame.set_border_width(8)
        mainVBox.pack_start(setupFrame, False, False, 0)

        dataFrame = self._buildDataFrame()
        dataFrame.set_border_width(8)
        mainVBox.pack_start(dataFrame, False, False, 0)

        logFrame = self._buildLogFrame()
        logFrame.set_border_width(8)
        mainVBox.pack_start(logFrame, True, True, 0)

        win.show_all()        

    def run(self):
        """Run the GUI."""
        gtk.main()
        if self._flight is not None:
            simulator = self._flight.simulator
            simulator.stopMonitoring()
            simulator.disconnect()            

    def connected(self, fsType, descriptor):
        """Called when we have connected to the simulator."""
        self._connected = True
        self._updateConnState()
        self._logger.untimedMessage("Connected to the simulator %s" % (descriptor,))
        
    def disconnected(self):
        """Called when we have disconnected from the simulator."""
        self._connected = False
        self._updateConnState()
        self._logger.untimedMessage("Disconnected from the simulator")

    def write(self, msg):
        """Write the given message to the log."""
        gobject.idle_add(self._writeLog, msg)
        
    def check(self, flight, aircraft, logger, oldState, state):
        """Update the data."""
        gobject.idle_add(self._setData, state)

    def _drawConnState(self, connStateArea, eventOrContext):
        """Draw the connection state."""
        context = eventOrContext if pygobject else connStateArea.window.cairo_create()

        if self._connecting:
            if self._connected:
                context.set_source_rgb(0.0, 1.0, 0.0)
            else:
                context.set_source_rgb(1.0, 0.0, 0.0)
        else:
            context.set_source_rgb(0.75, 0.75, 0.75)

        width = connStateArea.get_allocated_width() if pygobject \
                else connStateArea.allocation.width
        height = connStateArea.get_allocated_height() if pygobject \
                 else connStateArea.allocation.height
        context.arc(width/2, height/2, 8, 0, 2*math.pi)

        context.fill()

    def _updateConnState(self):
        """Initiate the updating of the connection state icon."""
        self._connStateArea.queue_draw()

    def _connectToggled(self, button):
        """Callback for the connection button."""
        if self._connectButton.get_active():
            self._logger.reset()
            self._flight = flight.Flight(self._logger)

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
            self._connecting = False
            self._simulator.stopMonitoring()
            self._simulator.disconnect()
            self._flight = None

        self._updateConnState()

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

        self._connectButton = gtk.ToggleButton(label = "Connect")
        self._connectButton.set_tooltip_text("Push to connect to Flight Simulator and start a new flight.\n"
                                             "Push again to disconnect from FS.")
        
        self._connectButton.connect("toggled", self._connectToggled)

        setupBox.pack_start(self._connectButton, False, False, 0)

        setupBox.pack_start(gtk.VSeparator(), False, False, 8)    

        self._connStateArea = gtk.DrawingArea()
        self._connStateArea.set_size_request(16, 16)
        self._connStateArea.set_tooltip_markup('The state of the connection.\n'
                                               '<span foreground="grey">Grey</span> means idle.\n'
                                               '<span foreground="red">Red</span> means trying to connect.\n'
                                               '<span foreground="green">Green</span> means connected.')

        if pygobject:
            self._connStateArea.connect("draw", self._drawConnState)
        else:
            self._connStateArea.connect("expose_event", self._drawConnState)

        alignment = gtk.Alignment(xalign = 0.5, yalign = 0.5)
        alignment.add(self._connStateArea)

        setupBox.pack_start(alignment, False, False, 8)

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

        (label, self._fuel) = self._createLabeledEntry("Fuel:", 20, xalign = 0.0)
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

def main():
    """The main operation of the program."""
    gobject.threads_init()
    gui = GUI()
    gui.build()
    gui.run()
              
if __name__ == "__main__":
    main()


