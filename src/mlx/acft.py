
import const
import checks
import fs
import util

import sys
import time
import traceback

from collections import deque

#---------------------------------------------------------------------------------------

## @package mlx.acft
#
# The simulator-independent aircraft classes.
#
# This module contains the aircraft classes that contain some general data
# about each aircraft type in the MAVA Fleet. The base class, \ref Aircraft
# also implements some parts of the logging and traces some data. The classes
# are also responsible for creating the \ref mlx.checks "checkers". Most of
# them are created by the \ref Aircraft class' constructor, but there can be
# type-specific differences. For example the lights are different for different
# types, so there is a \ref Aircraft._appendLightsLoggers "function" which can
# be reimplemented in child classes, if needed. This class maintains also the
# \ref SmoothedValue "smoothed values" of the IAS and the VS and set these
# values in the \ref mlx.fs.AircraftState "aircraft state" when it is received
# from the simulator.

#---------------------------------------------------------------------------------------

class SmoothedValue(object):
    """A smoothed value."""
    def __init__(self):
        """Construct the value."""
        self._deque = deque()
        self._sum = 0

    def add(self, length, value):
        """Add the given value and smooth with the given length."""
        dequeLength = len(self._deque)
        while dequeLength>=length:
            self._sum -= self._deque.popleft()
            dequeLength -= 1

        self._sum += value
        self._deque.append(value)

    def get(self):
        """Get the average."""
        return self._sum / len(self._deque)
        
#---------------------------------------------------------------------------------------

class Aircraft(object):
    """Base class for aircraft."""
    @staticmethod
    def create(flight):
        """Create an aircraft instance for the type in the given flight."""
        return _classes[flight.aircraftType](flight)

    def __init__(self, flight):
        """Construct the aircraft for the given type."""
        self._flight = flight
        self._aircraftState = None
       
        self._maxVS = -10000.0
        self._minVS = 10000.0

        self._v1r2LineIndex = None
        self._vrefLineIndex = None

        self.humanWeight = 82.0

        self._checkers = []

        config = flight.config
        # Loggers

        self._checkers.append(checks.StageChecker())
        self._checkers.append(checks.TakeOffLogger())

        self._checkers.append(checks.AltimeterLogger())
        
        self._checkers.append(checks.NAV1Logger())
        self._checkers.append(checks.NAV2Logger())
        self._checkers.append(checks.ADF1Logger())
        self._checkers.append(checks.ADF2Logger())
        self._checkers.append(checks.SquawkLogger())

        self._appendLightsLoggers()

        self._checkers.append(checks.FlapsLogger())

        self._checkers.append(checks.GearsLogger())
        self._checkers.append(checks.CruiseSpeedLogger())
        self._checkers.append(checks.SpoilerLogger())

        if config.isMessageTypeFS(const.MESSAGETYPE_VISIBILITY):
            self._checkers.append(checks.VisibilityChecker())

        # FIXME: we should have a central data model object, and not collect
        # the data from the GUI. However, some pieces of data (e.g. V-speeds,
        # etc. that is entered into the GUI) *should* be a part of the GUI and
        # queried from it, so the model should have a reference to the GUI as
        # well and access such data via the GUI!
        if config.onlineACARS and flight.loggedIn and not flight.entranceExam:
            self._checkers.append(checks.ACARSSender(flight._gui))

        # Fault checkers

        self._appendLightsCheckers()

        self._checkers.append(checks.BankChecker())

        self._checkers.append(checks.FlapsRetractChecker())
        self._checkers.append(checks.FlapsSpeedLimitChecker())

        self._checkers.append(checks.GearsDownChecker())
        self._checkers.append(checks.GearSpeedLimitChecker())

        self._checkers.append(checks.GLoadChecker())

        self._checkers.append(checks.MLWChecker())
        self._checkers.append(checks.MTOWChecker())
        self._checkers.append(checks.MZFWChecker())
        self._checkers.append(checks.PayloadChecker())

        self._checkers.append(checks.SpeedChecker())
        self._checkers.append(checks.VSChecker())

        timeout = 5.0 + config.realIASSmoothingLength - 1
        self._checkers.append(checks.OverspeedChecker(timeout = timeout))
                              
        self._checkers.append(checks.StallChecker())

        self._checkers.append(checks.PitotChecker())
        
        self._checkers.append(checks.ReverserChecker())

        if flight.aircraftType is not None and config.enableApproachCallouts:
            approachCallouts = flight.config.getApproachCallouts(flight.aircraftType)
            if approachCallouts:
                self._checkers.append(checks.ApproachCalloutsPlayer(approachCallouts))

        self._smoothedIAS = SmoothedValue()
        self._smoothedVS = SmoothedValue()

    @property
    def type(self):
        """Get the type of the aircraft."""
        return self._flight.aircraftType

    @property
    def flight(self):
        """Get the flight the aircraft belongs to."""
        return self._flight

    @property
    def logger(self):
        """Get the logger to use for the aircraft."""
        return self._flight.logger

    @property
    def state(self):
        """Get the current aircraft state."""
        return self._aircraftState

    @property
    def speedInKnots(self):
        """Indicate if the speed is in knots.

        This default implementation returns True."""
        return True

    @property
    def timestamp(self):
        """Get the timestamp of the current state."""
        return None if self._aircraftState is None \
               else self._aircraftState.timestamp
        
    def getFlapsSpeedLimit(self, flaps):
        """Get the speed limit for the given flaps setting."""
        return self.flapSpeedLimits[flaps] if flaps in self.flapSpeedLimits \
               else None

    def modelChanged(self, timestamp, aircraftName, modelName):
        """Called when the simulator's aircraft changes."""
        self._flight.logger.message(timestamp,
                                    "Aircraft: name='%s', model='%s'" % \
                                    (aircraftName, modelName))

    def handleState(self, aircraftState):
        """Called when the state of the aircraft changes.

        This is the function that the simulator calls directly with the new
        state."""
        try:
            config = self._flight.config

            self._smoothedIAS.add(config.realIASSmoothingLength, aircraftState.ias)
            aircraftState.smoothedIAS = self._smoothedIAS.get()

            self._smoothedVS.add(config.realVSSmoothingLength, aircraftState.vs)
            aircraftState.smoothedVS = self._smoothedVS.get()

            for checker in self._checkers:
                try:
                    checker.check(self._flight, self, self._flight.logger,
                                  self._aircraftState, aircraftState)
                except:
                    print >> sys.stderr, "Checker", checker, "failed"
                    traceback.print_exc()

            self._flight.handleState(self._aircraftState, aircraftState)

            self._maxVS = max(self._maxVS, aircraftState.vs)
            self._minVS = min(self._minVS, aircraftState.vs)
        except:
            print >> sys.stderr, "Failed to handle the state"
            traceback.print_exc()
        finally:
            self._aircraftState = aircraftState
    
    def setStage(self, aircraftState, newStage):
        """Set the given stage as the new one and do whatever should be
        done."""
        if self._flight.setStage(aircraftState.timestamp, newStage):
            if newStage==const.STAGE_PUSHANDTAXI:
                self.logger.message(aircraftState.timestamp, "Block time start")
                self._flight.logFuel(aircraftState)
                self.logger.message(aircraftState.timestamp, 
                                    "ZFW: %.2f kg" % (aircraftState.zfw))
                flight = self._flight
                if flight.v1 is None or flight.vr is None or flight.v2 is None:
                    fs.sendMessage(const.MESSAGETYPE_HELP,
                                   "Don't forget to set the takeoff V-speeds!",
                                   5)
            elif newStage==const.STAGE_TAKEOFF:
                self.logger.message(aircraftState.timestamp,
                                    "Flight time start")
                self.logger.message(aircraftState.timestamp, 
                                    "Takeoff weight: %.0f kg, MTOW: %.0f kg" % \
                                    (aircraftState.grossWeight, self.mtow))
                self.logger.message(aircraftState.timestamp,
                                    "Wind %03.0f degrees at %.0f knots" % \
                                    (aircraftState.windDirection, 
                                     aircraftState.windSpeed))
                self._logV1R2()
            elif newStage==const.STAGE_TAXIAFTERLAND:
                flight = self._flight
                bookedFlight = flight.bookedFlight
                config = flight.config
                if config.onlineGateSystem and \
                   flight.loggedIn and \
                   not flight.entranceExam and \
                   bookedFlight.arrivalICAO=="LHBP" and \
                   config.isMessageTypeFS(const.MESSAGETYPE_GATE_SYSTEM):
                    self._flight.getFleet(callback = self._fleetRetrieved,
                                          force = True)
                self.logger.message(aircraftState.timestamp, "Flight time end")
                self._flight.logFuel(aircraftState)
                self.logger.message(aircraftState.timestamp,
                                    "Landing weight: %.0f kg, MLW: %.0f" % \
                                    (aircraftState.grossWeight, self.mlw))
                self.logger.message(aircraftState.timestamp,
                                    "Vertical speed range: %.0f..%.0f feet/min" % \
                                    (self._minVS, self._maxVS))
            elif newStage==const.STAGE_PARKING:
                self.logger.message(aircraftState.timestamp, "Block time end")
            elif newStage==const.STAGE_END:
                flightLength = self._flight.flightTimeEnd - self._flight.flightTimeStart
                self.logger.message(aircraftState.timestamp,
                                    "Flight time: " +
                                    util.getTimeIntervalString(flightLength))
                self.logger.message(aircraftState.timestamp,
                                    "Flown distance: %.2f NM" % \
                                    (self._flight.flownDistance,))                
                blockLength = self._flight.blockTimeEnd - self._flight.blockTimeStart
                self.logger.message(aircraftState.timestamp,
                                    "Block time: " +
                                    util.getTimeIntervalString(blockLength))

    def prepareFlare(self):
        """Called when it is detected that we will soon flare.

        On the first call, it should start monitoring some parameters more
        closely to determine flare time."""
        self.flight.simulator.startFlare()

    def flareStarted(self, windSpeed, windDirection, visibility, 
                     flareStart, flareStartFS):
        """Called when the flare has started."""
        self.logger.message(self._aircraftState.timestamp, "The flare has begun")
        self.logger.message(self._aircraftState.timestamp,
                            "Wind %03.0f degrees at %.0f knots" % \
                            (windDirection, windSpeed))
        self.logger.message(self._aircraftState.timestamp,
                            "Visibility: %.0f metres" % (visibility,))
        self.logger.message(self._aircraftState.timestamp,
                            "Altimeter setting: %.0f hPa" % \
                            (self._aircraftState.altimeter,))
        self._logVRef()
        self.flight.flareStarted(flareStart, flareStartFS)
        fs.sendMessage(const.MESSAGETYPE_INFORMATION, "Flare-time", 3)
         
    def flareFinished(self, flareEnd, flareEndFS, tdRate, tdRateCalculatedByFS,
                      ias, pitch, bank, heading):
        """Called when the flare has finished."""
        (flareTimeFromFS, flareTime) = self.flight.flareFinished(flareEnd,
                                                                 flareEndFS,
                                                                 tdRate)
        self.logger.message(self._aircraftState.timestamp,
                            "Flaretime: %.3f (from %s)" % \
                            (flareTime, 
                             "the simulator" if flareTimeFromFS else "real time",))
        self.logger.message(self._aircraftState.timestamp,
                            "Touchdown rate: %.0f feet/min" % (tdRate,))
        self.logger.message(self._aircraftState.timestamp,
                            "Touchdown rate was calculated by the %s" % \
                            ("simulator" if tdRateCalculatedByFS else "logger",))
        flight = self._flight
        self.logger.message(self._aircraftState.timestamp,
                            "Touchdown speed: %.0f %s" % \
                            (flight.speedFromKnots(ias),
                             flight.getEnglishSpeedUnit()))
        self.logger.message(self._aircraftState.timestamp,
                            "Touchdown pitch: %.1f degrees" % (pitch,))
        self.logger.message(self._aircraftState.timestamp,
                            "Touchdown bank: %.1f degrees" % (bank,))
        self.logger.message(self._aircraftState.timestamp,
                            "Touchdown heading: %03.0f degrees" % (heading,))
        self.logger.message(self._aircraftState.timestamp, 
                           "Centre of gravity:  %.1f%%" % \
                            (self._aircraftState.cog*100.0,))

    def cancelFlare(self):
        """Cancel flare, if it has started."""
        self.flight.simulator.cancelFlare()

    def checkFlightEnd(self, aircraftState):
        """Check if the end of the flight has arrived.

        This default implementation checks the N1 values, but for
        piston-powered aircraft you need to check the RPMs."""
        for n1 in aircraftState.n1:
            if n1>=0.5: return False
        return True

    def updateV1R2(self):
        """Update the V1, Vr and V2 values from the flight, if the these values
        have already been logged."""
        if self._v1r2LineIndex is not None:
            self._logV1R2()

    def _appendLightsLoggers(self):
        """Append the loggers needed for the lights.

        This default implementation adds the loggers for the anti-collision
        lights, the landing lights, the strobe lights and the NAV lights."""
        self._checkers.append(checks.AnticollisionLightsLogger())
        self._checkers.append(checks.LandingLightsLogger())
        self._checkers.append(checks.StrobeLightsLogger())
        self._checkers.append(checks.NavLightsLogger())

    def _appendLightsCheckers(self):
        """Append the checkers needed for the lights.

        This default implementation adds the checkers for the anti-collision
        lights, the landing lights, the strobe lights and the NAV lights."""
        self._checkers.append(checks.AntiCollisionLightsChecker())
        self._checkers.append(checks.LandingLightsChecker())
        self._checkers.append(checks.NavLightsChecker())
        self._checkers.append(checks.StrobeLightsChecker())

    def _speedToLog(self, speed):
        """Convert the given speed (being either None or expressed in the
        flight's speed unit into a string."""
        if speed is None:
            return "-"
        else:
            return str(speed) + " " + self._flight.getEnglishSpeedUnit()

    def _logV1R2(self):
        """Log the V1, Vr and V2 value either newly, or by updating the
        corresponding line."""
        message = "Speeds calculated by the pilot: V1: %s, VR: %s, V2: %s" % \
                  (self._speedToLog(self._flight.v1),
                   self._speedToLog(self._flight.vr),
                   self._speedToLog(self._flight.v2))

        if self._v1r2LineIndex is None:
            self._v1r2LineIndex = \
                self.logger.message(self._aircraftState.timestamp, message)
        else:
            self.logger.updateLine(self._v1r2LineIndex, message)

    def updateVRef(self):
        """Update the Vref value from the flight, if the Vref value has already
        been logged."""
        if self._vrefLineIndex is not None:
            self._logVRef()

    def _logVRef(self):
        """Log the Vref value either newly, or by updating the corresponding
        line."""
        message = "VRef speed calculated by the pilot: %s" % \
                  (self._speedToLog(self._flight.vref),)
        if self._vrefLineIndex is None:
            self._vrefLineIndex = \
                self.logger.message(self._aircraftState.timestamp, message)
        else:
            self.logger.updateLine(self._vrefLineIndex, message)

    def _fleetRetrieved(self, fleet):
        """Callback for the fleet retrieval result."""
        if fleet is not None:
            gateList = ""
            occupiedGateNumbers = fleet.getOccupiedGateNumbers()
            for gateNumber in const.lhbpGateNumbers:
                if gateNumber not in occupiedGateNumbers:
                    if gateList: gateList += ", "
                    gateList += gateNumber
            fs.sendMessage(const.MESSAGETYPE_GATE_SYSTEM,
                           "Free gates: " + gateList, 20)
        

#---------------------------------------------------------------------------------------

class Boeing737(Aircraft):
    """Base class for the various aircraft in the Boeing 737 family.

    The aircraft type-specific values in the aircraft state have the following
    structure:
    - fuel: left, centre, right
    - n1: left, right
    - reverser: left, right"""    
    def __init__(self, flight):
        super(Boeing737, self).__init__(flight)
        self._checkers.append(checks.ThrustChecker())

        self.gearSpeedLimit = 270
        self.flapSpeedLimits = { 1 : 260,
                                 2 : 260,
                                 5 : 250,
                                 10 : 210,
                                 15 : 200,
                                 25 : 190,
                                 30 : 175,
                                 40 : 162 }

#---------------------------------------------------------------------------------------

class B736(Boeing737):
    """Boeing 737-600 aircraft."""
    def __init__(self, flight):
        super(B736, self).__init__(flight)
        self.dow = 38307
        self.mtow = 58328
        self.mlw = 54657
        self.mzfw = 51482

#---------------------------------------------------------------------------------------

class B737(Boeing737):
    """Boeing 737-700 aircraft."""
    def __init__(self, flight):
        super(B737, self).__init__(flight)
        self.dow = 39250
        self.mtow = 61410
        self.mlw = 58059
        self.mzfw = 54657

#---------------------------------------------------------------------------------------

class B738(Boeing737):
    """Boeing 737-800 aircraft."""
    def __init__(self, flight):
        super(B738, self).__init__(flight)
        self.dow = 42690
        self.mtow = 71709
        self.mlw = 65317
        self.mzfw = 61688

#---------------------------------------------------------------------------------------

class B738Charter(B738):
    """Boeing 737-800 aircraft used for charters."""
    def __init__(self, flight):
        super(B738Charter, self).__init__(flight)
        self.mtow = 77791

#---------------------------------------------------------------------------------------

class B733(Boeing737):
    """Boeing 737-300 aircraft."""
    def __init__(self, flight):
        super(B733, self).__init__(flight)
        self.dow = 32700
        self.mtow = 62820
        self.mlw = 51700
        self.mzfw = 48410

#---------------------------------------------------------------------------------------

class B734(Boeing737):
    """Boeing 737-400 aircraft."""
    def __init__(self, flight):
        super(B734, self).__init__(flight)
        self.dow = 33200
        self.mtow = 68050
        self.mlw = 56200
        self.mzfw = 53100

#---------------------------------------------------------------------------------------

class B735(Boeing737):
    """Boeing 737-500 aircraft."""
    def __init__(self, flight):
        super(B735, self).__init__(flight)
        self.dow = 31300
        self.mtow = 60550
        self.mlw = 50000
        self.mzfw = 46700

#---------------------------------------------------------------------------------------

class DH8D(Aircraft):
    """Bombardier Dash-8 Q400 aircraft.

    The aircraft type-specific values in the aircraft state have the following
    structure:
    - fuel: left, right
    - n1: left, right
    - reverser: left, right."""

    def __init__(self, flight):
        super(DH8D, self).__init__(flight)
        self.dow = 17185
        self.mtow = 29257
        self.mlw = 28009
        self.mzfw = 25855
        self.gearSpeedLimit = 215
        self.flapSpeedLimits = { 5 : 200,
                                 10 : 181,
                                 15 : 172,
                                 35 : 158 }

#---------------------------------------------------------------------------------------

class Boeing767(Aircraft):
    """Base class for the various aircraft in the Boeing 767 family.

    The aircraft type-specific values in the aircraft state have the following
    structure:
    - fuel: left, centre, right
    - n1: left, right
    - reverser: left, right"""

    def __init__(self, flight):
        super(Boeing767, self).__init__(flight)
        self._checkers.append(checks.ThrustChecker())
        self.gearSpeedLimit = 270
        self.flapSpeedLimits = { 1 : 255,
                                 5 : 235,
                                 10 : 215,
                                 20 : 215,
                                 25 : 185,
                                 30 : 175 }

#---------------------------------------------------------------------------------------

class B762(Boeing767):
    """Boeing 767-200 aircraft."""
    def __init__(self, flight):
        super(B762, self).__init__(flight)
        self.dow = 84507
        self.mtow = 175540
        self.mlw = 126098
        self.mzfw = 114758

#---------------------------------------------------------------------------------------

class B763(Boeing767):
    """Boeing 767-300 aircraft."""
    def __init__(self, flight):
        super(B763, self).__init__(cflight)
        self.dow = 91311
        self.mtow = 181436
        self.mlw = 137892
        self.mzfw = 130635

#---------------------------------------------------------------------------------------

class CRJ2(Aircraft):
    """Bombardier CRJ-200 aircraft.

    The aircraft type-specific values in the aircraft state have the following
    structure:
    - fuel: left, centre, right
    - n1: left, right
    - reverser: left, right."""
    def __init__(self, flight):
        super(CRJ2, self).__init__(flight)
        self._checkers.append(checks.ThrustChecker())
        self.dow = 14549
        self.mtow = 22995
        self.mlw = 21319
        self.mzfw = 19958
        self.gearSpeedLimit = 240
        self.flapSpeedLimits = { 8 : 260,
                                 20 : 220,
                                 30 : 190,
                                 45 : 175 }

#---------------------------------------------------------------------------------------

class F70(Aircraft):
    """Fokker 70 aircraft.

    The aircraft type-specific values in the aircraft state have the following
    structure:
    - fuel: left, centre, right
    - n1: left, right
    - reverser: left, right."""
    def __init__(self, flight):
        super(F70, self).__init__(flight)
        self._checkers.append(checks.ThrustChecker())
        self.dow = 24283
        self.mtow = 38100 # FIXME: differentiate by registration number,
                          # MTOW of HA-LMF: 41955
        self.mlw = 36740
        self.mzfw = 32655
        self.gearSpeedLimit = 200
        self.flapSpeedLimits = { 8 : 250,
                                 15 : 220,
                                 25 : 220,
                                 42 : 180 }

#---------------------------------------------------------------------------------------

class DC3(Aircraft):
    """Lisunov Li-2 (DC-3) aircraft.

    The aircraft type-specific values in the aircraft state have the following
    structure:
    - fuel: left aux, left, right, right aux
    - rpm: left, right
    - reverser: left, right."""
    def __init__(self, flight):
        super(DC3, self).__init__(flight)
        self.dow = 8627
        self.mtow = 11884
        self.mlw = 11793
        self.mzfw = 11780
        self.gearSpeedLimit = 148
        self.flapSpeedLimits = { 15 : 135,
                                 30 : 99,
                                 45 : 97 }

    def _checkFlightEnd(self, aircraftState):
        """Check if the end of the flight has arrived.

        This implementation checks the RPM values to be 0."""
        for rpm in aircraftState.rpm:
            if rpm>0: return False
        return True

#---------------------------------------------------------------------------------------

class T134(Aircraft):
    """Tupolev Tu-134 aircraft.

    The aircraft type-specific values in the aircraft state have the following
    structure:
    - fuel: left tip, left aux, centre, right aux, right tip, external 1,
    external 2
    - n1: left, right
    - reverser: left, right."""
    def __init__(self, flight):
        super(T134, self).__init__(flight)
        self._checkers.append(checks.ThrustChecker())
        self.dow = 29500
        self.mtow = 49000
        self.mlw = 43000
        self.mzfw = 38500
        self.gearSpeedLimit = 216
        self.flapSpeedLimits = { 10 : 450,
                                 20 : 400,
                                 30 : 300 }

    @property
    def speedInKnots(self):
        """Indicate if the speed is in knots."""
        return False
    
    def _appendLightsLoggers(self):
        """Append the loggers needed for the lights."""
        self._checkers.append(checks.AnticollisionLightsLogger())
        self._checkers.append(checks.LandingLightsLogger())
        self._checkers.append(checks.NavLightsLogger())

    def _appendLightsCheckers(self):
        """Append the checkers needed for the lights."""
        self._checkers.append(checks.TupolevAntiCollisionLightsChecker())
        self._checkers.append(checks.LandingLightsChecker())
        self._checkers.append(checks.NavLightsChecker())

#---------------------------------------------------------------------------------------

class T154(Aircraft):
    """Tupolev Tu-154 aircraft.

    The aircraft type-specific values in the aircraft state have the following
    structure:
    - fuel: left aux, left, centre, centre 2, right, right aux
    - n1: left, centre, right
    - reverser: left, right"""
    def __init__(self, flight):
        super(T154, self).__init__(flight)
        self.dow = 53259
        self.mtow = 98000
        self.mlw = 78000
        self.mzfw = 72000
        self.gearSpeedLimit = 216
        self.flapSpeedLimits = { 15 : 227,
                                 28 : 194,
                                 45 : 162 }

    @property
    def speedInKnots(self):
        """Indicate if the speed is in knots."""
        return False
    
    def _appendLightsLoggers(self):
        """Append the loggers needed for the lights."""
        self._checkers.append(checks.AnticollisionLightsLogger())
        self._checkers.append(checks.LandingLightsLogger())
        self._checkers.append(checks.NavLightsLogger())

    def _appendLightsCheckers(self):
        """Append the checkers needed for the lights."""
        self._checkers.append(checks.AntiCollisionLightsChecker())
        self._checkers.append(checks.LandingLightsChecker())
        self._checkers.append(checks.NavLightsChecker())

#---------------------------------------------------------------------------------------


class YK40(Aircraft):
    """Yakovlev Yak-40 aircraft.

    The aircraft type-specific values in the aircraft state have the following
    structure:
    - fuel: left, right
    - n1: left, right
    - reverser: left, right"""
    def __init__(self, flight):
        super(YK40, self).__init__(flight)
        self._checkers.append(checks.ThrustChecker())
        self.dow = 9400
        self.mtow = 17200
        self.mlw = 16800
        self.mzfw = 12100
        self.gearSpeedLimit = 165
        self.flapSpeedLimits = { 20 : 165,
                                 35 : 135 }

    @property
    def speedInKnots(self):
        """Indicate if the speed is in knots."""
        return False
    
    def _appendLightsLoggers(self):
        """Append the loggers needed for the lights."""
        self._checkers.append(checks.AnticollisionLightsLogger())
        self._checkers.append(checks.LandingLightsLogger())
        self._checkers.append(checks.NavLightsLogger())

    def _appendLightsCheckers(self):
        """Append the checkers needed for the lights."""
        self._checkers.append(checks.AntiCollisionLightsChecker())
        self._checkers.append(checks.LandingLightsChecker())
        self._checkers.append(checks.NavLightsChecker())

#---------------------------------------------------------------------------------------

mostFuelTanks = [const.FUELTANK_LEFT_TIP, const.FUELTANK_EXTERNAL1,
                 const.FUELTANK_LEFT_AUX,
                 const.FUELTANK_CENTRE,
                 const.FUELTANK_RIGHT_AUX,
                 const.FUELTANK_EXTERNAL2, const.FUELTANK_RIGHT_TIP]

#---------------------------------------------------------------------------------------

_classes = { const.AIRCRAFT_B736  : B736,
             const.AIRCRAFT_B737  : B737,
             const.AIRCRAFT_B738  : B738,
             const.AIRCRAFT_B738C : B738Charter,
             const.AIRCRAFT_B733  : B733,
             const.AIRCRAFT_B734  : B734,
             const.AIRCRAFT_B735  : B735,
             const.AIRCRAFT_DH8D  : DH8D,
             const.AIRCRAFT_B762  : B762,
             const.AIRCRAFT_B763  : B763,
             const.AIRCRAFT_CRJ2  : CRJ2,
             const.AIRCRAFT_F70   : F70,
             const.AIRCRAFT_DC3   : DC3,
             const.AIRCRAFT_T134  : T134,
             const.AIRCRAFT_T154  : T154,
             const.AIRCRAFT_YK40  : YK40 }

#---------------------------------------------------------------------------------------

if __name__ == "__main__":
    value = SmoothedValue()

    print "Adding 1, 12.0"
    value.add(1, 12.0)
    print value.get()

    print "Adding 1, 15.0"
    value.add(1, 15.0)
    print value.get()

    print "Adding 2, 18.0"
    value.add(2, 18.0)
    print value.get()

    print "Adding 2, 20.0"
    value.add(2, 20.0)
    print value.get()

    print "Adding 5, 22.0"
    value.add(5, 22.0)
    print value.get()

    print "Adding 5, 25.0"
    value.add(5, 25.0)
    print value.get()

    print "Adding 5, 29.0"
    value.add(5, 29.0)
    print value.get()

    print "Adding 5, 21.0"
    value.add(5, 21.0)
    print value.get()

    print "Adding 5, 26.0"
    value.add(5, 26.0)
    print value.get()

    print "Adding 2, 30.0"
    value.add(2, 30.0)
    print value.get()

    print "Adding 2, 55.0"
    value.add(2, 55.0)
    print value.get()

#---------------------------------------------------------------------------------------
