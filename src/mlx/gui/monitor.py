
from mlx.gui.common import *

import mlx.const as const
import mlx.util as util

import time

#------------------------------------------------------------------------------

## @package mlx.gui.monitor
#
# The monitoring window
#
# The \ref MonitorWindow class is a window containing the data received from
# the simulator by the logger.

#------------------------------------------------------------------------------

class MonitorWindow(gtk.Window):
    """The window for the data monitor."""
    def __init__(self, gui, iconDirectory):
        """Construct the monitor window."""
        super(MonitorWindow, self).__init__()

        self._gui = gui

        self.set_resizable(False)
        self.set_title(WINDOW_TITLE_BASE + " - Data Monitor")
        self.set_icon_from_file(os.path.join(iconDirectory, "logo.ico"))
        self.connect("delete-event",
                     lambda a, b: self._gui.hideMonitorWindow())

        alignment = gtk.Alignment(xscale = 1.0, yscale = 1.0)

        alignment.set_padding(padding_top = 4, padding_bottom = 10,
                              padding_left = 16, padding_right = 16)

        table = gtk.Table(rows = 9, columns = 14)
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
        table.attach(self._onTheGround, 10, 11, 0, 1)

        self._antiIceOn = gtk.Label("ANTI-ICE")
        table.attach(self._antiIceOn, 11, 12, 0, 1)

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

        (label, self._vs) = self._createLabeledEntry("VS:", 13)
        table.attach(label, 10, 11, 1, 2)
        table.attach(self._vs, 11, 12, 1, 2)

        (label, self._ias) = self._createLabeledEntry("IAS:", 11)
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
        table.attach(self._antiCollisionLightsOn, 1, 2, 5, 6)

        self._strobeLightsOn = gtk.Label("STROBE")
        table.attach(self._strobeLightsOn, 2, 3, 5, 6)

        self._landingLightsOn = gtk.Label("LANDING")
        table.attach(self._landingLightsOn, 3, 4, 5, 6)

        self._pitotHeatOn = gtk.Label("PITOT HEAT")
        table.attach(self._pitotHeatOn, 4, 5, 5, 6)

        self._parking = gtk.Label("PARKING")
        table.attach(self._parking, 5, 6, 5, 6)

        self._gearControlDown = gtk.Label("GEAR LEVER DOWN")
        table.attach(self._gearControlDown, 6, 8, 5, 6)

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

        (label, self._position) = self._createLabeledEntry("Position:", 25)
        table.attach(label, 6, 7, 6, 7)
        table.attach(self._position, 7, 10, 6, 7)

        (label, self._elevatorTrim) = self._createLabeledEntry("Trim:", 5)
        table.attach(label, 10, 11, 6, 7)
        table.attach(self._elevatorTrim, 11, 12, 6, 7)

        self._apMaster = gtk.Label("AP MASTER")
        table.attach(self._apMaster, 0, 1, 7, 8)

        self._apHeadingHold = gtk.Label("AP HDG HOLD")
        table.attach(self._apHeadingHold, 1, 2, 7, 8)

        (label, self._apHeading) = self._createLabeledEntry("AP HDG:", 5)
        table.attach(label, 2, 3, 7, 8)
        table.attach(self._apHeading, 3, 4, 7, 8)

        self._xpdrC = gtk.Label("XPDR C")
        table.attach(self._xpdrC, 4, 5, 7, 8)

        self._apAltitudeHold = gtk.Label("AP ALT HOLD")
        table.attach(self._apAltitudeHold, 5, 6, 7, 8)

        (label, self._apAltitude) = self._createLabeledEntry("AP ALT:", 10)
        table.attach(label, 6, 7, 7, 8)
        table.attach(self._apAltitude, 7, 8, 7, 8)

        (label, self._adf1) = self._createLabeledEntry("ADF1:", 5)
        table.attach(label, 8, 9, 7, 8)
        table.attach(self._adf1, 9, 10, 7, 8)

        (label, self._adf2) = self._createLabeledEntry("ADF2:", 5)
        table.attach(label, 10, 11, 7, 8)
        table.attach(self._adf2, 11, 12, 7, 8)

        (label, self._qnh) = self._createLabeledEntry("QNH:", 7)
        table.attach(label, 0, 1, 8, 9)
        table.attach(self._qnh, 1, 2, 8, 9)

        (label, self._cog) = self._createLabeledEntry("CoG:", 7)
        table.attach(label, 2, 3, 8, 9)
        table.attach(self._cog, 3, 4, 8, 9)

        (label, self._ils) = self._createLabeledEntry("ILS:", 7)
        table.attach(label, 4, 5, 8, 9)
        table.attach(self._ils, 5, 6, 8, 9)

        (label, self._crs1) = self._createLabeledEntry("CRS1:", 7)
        table.attach(label, 6, 7, 8, 9)
        table.attach(self._crs1, 7, 8, 8, 9)

        (label, self._crs2) = self._createLabeledEntry("CRS2:", 7)
        table.attach(label, 8, 9, 8, 9)
        table.attach(self._crs2, 9, 10, 8, 9)

        (label, self._crsi) = self._createLabeledEntry("CRSI:", 7)
        table.attach(label, 10, 11, 8, 9)
        table.attach(self._crsi, 11, 12, 8, 9)

        alignment.add(table)

        self.add(alignment)

        self._previousState = None

        self.setData()

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

    def setData(self, aircraftState = None):
        """Set the data.

        If aircraftState is None, everything will be set to its default."""
        if aircraftState is None:
            self._timestamp.set_text("--:--:--")
            self._paused.set_sensitive(False)
            self._trickMode.set_sensitive(False)
            self._overspeed.set_sensitive(False)
            self._stalled.set_sensitive(False)
            self._onTheGround.set_sensitive(False)
            self._antiIceOn.set_sensitive(False)
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
            self._landingLightsOn.set_text("LANDING")
            self._landingLightsOn.set_sensitive(False)
            self._pitotHeatOn.set_sensitive(False)
            self._parking.set_sensitive(False)
            self._gearControlDown.set_sensitive(False)
            self._gearsDown.set_sensitive(False)
            self._spoilersArmed.set_sensitive(False)
            self._spoilersExtension.set_text("-")
            self._windSpeed.set_text("-")
            self._windDirection.set_text("-")
            self._position.set_text("-")
            self._elevatorTrim.set_text("-")
            self._apMaster.set_sensitive(False)
            self._apHeadingHold.set_sensitive(False)
            self._apHeading.set_text("-")
            self._xpdrC.set_sensitive(False)
            self._apAltitudeHold.set_sensitive(False)
            self._apAltitude.set_text("-")
            self._adf1.set_text("-")
            self._adf2.set_text("-")
            self._qnh.set_text("-")
            self._cog.set_text("-")
            self._ils.set_text("-")
            self._crs1.set_text("-")
            self._crs2.set_text("-")
            self._crsi.set_text("-")
        else:
            self._timestamp.set_text(time.strftime("%H:%M:%S",
                                                   time.gmtime(aircraftState.timestamp)))
            self._paused.set_sensitive(aircraftState.paused)
            self._trickMode.set_sensitive(aircraftState.trickMode)
            self._overspeed.set_sensitive(aircraftState.overspeed)
            self._stalled.set_sensitive(aircraftState.stalled)
            self._onTheGround.set_sensitive(aircraftState.onTheGround)
            self._antiIceOn.set_sensitive(aircraftState.antiIceOn is True)
            self._zfw.set_text("%.0f" % (aircraftState.zfw,))
            self._grossWeight.set_text("%.0f" % (aircraftState.grossWeight,))
            self._heading.set_text("%03.0f" % (aircraftState.heading,))
            self._pitch.set_text("%.0f" % (aircraftState.pitch,))
            self._bank.set_text("%.0f" % (aircraftState.bank,))
            self._vs.set_text("%.0f (%.0f)" % (aircraftState.vs,
                                               aircraftState.smoothedVS))
            self._ias.set_text("%.0f (%.0f)" % (aircraftState.ias,
                                                aircraftState.smoothedIAS))
            self._mach.set_text("%.2f" % (aircraftState.mach,))
            self._groundSpeed.set_text("%.0f" % (aircraftState.groundSpeed,))
            self._radioAltitude.set_text("%.0f" % (aircraftState.radioAltitude,))
            self._altitude.set_text("%.0f" % (aircraftState.altitude,))
            self._gLoad.set_text("%.2f" % (aircraftState.gLoad,))
            self._flapsSet.set_text("%.0f" % (aircraftState.flapsSet,))
            self._flaps.set_text("%.0f" % (aircraftState.flaps,))
            self._altimeter.set_text("%.0f" % (aircraftState.altimeter,))
            self._squawk.set_text(aircraftState.squawk)
            self._nav1.set_text("-" if aircraftState.nav1 is None else aircraftState.nav1)
            self._nav2.set_text("-" if aircraftState.nav2 is None else aircraftState.nav2)
            self._qnh.set_text("%.0f" % (aircraftState.qnh,))

            fuelStr = ""
            for (_tank, fuel) in aircraftState.fuel:
                if fuelStr: fuelStr += ", "
                fuelStr += "%.0f" % (fuel,)
            self._fuel.set_text(fuelStr)

            if aircraftState.n1 is not None:
                n1Str = ""
                for n1 in aircraftState.n1:
                    if n1Str: n1Str += ", "
                    n1Str += "%.0f" % (n1,)
            elif aircraftState.rpm is not None:
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

            self._navLightsOn.set_sensitive(aircraftState.navLightsOn is True)
            self._antiCollisionLightsOn.set_sensitive(aircraftState.antiCollisionLightsOn is True)
            self._strobeLightsOn.set_sensitive(aircraftState.strobeLightsOn is True)

            if self._previousState is None or \
               ((self._previousState.landingLightsOn is None)!=
                (aircraftState.landingLightsOn is None)):
                if aircraftState.landingLightsOn is None:
                    self._landingLightsOn.set_markup('<span strikethrough="true">LANDING</span>')
                else:
                    self._landingLightsOn.set_text("LANDING")
            self._landingLightsOn.set_sensitive(aircraftState.landingLightsOn is True)

            self._pitotHeatOn.set_sensitive(aircraftState.pitotHeatOn is True)
            self._parking.set_sensitive(aircraftState.parking)
            self._gearControlDown.set_sensitive(aircraftState.gearControlDown)
            self._gearsDown.set_sensitive(aircraftState.gearsDown)
            self._spoilersArmed.set_sensitive(aircraftState.spoilersArmed is True)
            self._spoilersExtension.set_text("%.0f" % (aircraftState.spoilersExtension,))
            self._windSpeed.set_text("%.0f" % (aircraftState.windSpeed,))
            self._windDirection.set_text("%03.0f" % (aircraftState.windDirection,))
            self._position.set_text(util.getCoordinateString((aircraftState.latitude,
                                                              aircraftState.longitude)))
            self._elevatorTrim.set_text("%.2f" % (aircraftState.elevatorTrim,))
            self._apMaster.set_sensitive(aircraftState.apMaster is True)
            self._apHeadingHold.set_sensitive(aircraftState.apHeadingHold is True)
            self._apHeading.set_text("-" if aircraftState.apHeading is None
                                     else "%03.0f" % (aircraftState.apHeading,))
            self._xpdrC.set_sensitive(aircraftState.xpdrC is True)
            self._apAltitudeHold.set_sensitive(aircraftState.apAltitudeHold is True)
            self._apAltitude.set_text("-" if aircraftState.apAltitude is None
                                      else "%5.0f" % (aircraftState.apAltitude,))

            self._adf1.set_text("-" if aircraftState.adf1 is None else aircraftState.adf1)
            self._adf2.set_text("-" if aircraftState.adf2 is None else aircraftState.adf2)
            self._cog.set_text("%.2f%%" % (aircraftState.cog*100.0,))

            self._ils.set_text("-" if aircraftState.ils is None else aircraftState.ils)

            self._crs1.set_text("-" if aircraftState.nav1_obs is None else str(aircraftState.nav1_obs))
            self._crs2.set_text("-" if aircraftState.nav2_obs is None else str(aircraftState.nav2_obs))
            self._crsi.set_text("-" if aircraftState.ils_obs is None else str(aircraftState.ils_obs))

#------------------------------------------------------------------------------
