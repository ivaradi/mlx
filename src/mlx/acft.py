
from . import const
from . import gates
from . import checks
from . import fs
from .i18n import xstr
from . import util

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

# Derate type: no derate possible
DERATE_NONE = 0

# Derate type: Boeing, i.e. a percentage value.
# For logging, the percentage value is expected as a string (i.e. whatever the
# pilot enters into the text field).
DERATE_BOEING = 1

# Derate type: EPR, i.e. an EPR value.
# For logging, the EPR value is expected as a string (i.e. whatever the pilot
# enters into the text field).
DERATE_EPR = 2

# Derate type: Tupolev, i.e. nominal or takeoff
# For logging, one of the DERATE_TUPOLEV_xxx values are expected.
DERATE_TUPOLEV = 3

# Tupolev derate value: nominal
DERATE_TUPOLEV_NOMINAL = 1

# Tupolev derate value: takeoff
DERATE_TUPOLEV_TAKEOFF = 2

# Derate type: BAe-146, i.e. enabled or not
# For logging, a boolean is expected.
DERATE_B462 = 4

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

class SimBriefData(object):
    """Data to be used when creating SimBrief briefings."""
    def __init__(self, climbProfiles, cruiseProfiles, descentProfiles,
                 cruiseParameters = {}):
        """Construct the SimBrief data with the given profiles.

        cruiseParameters is a dictionary keyed by the cruise profile index. It
        contains a tuple of:
        - a boolean indicating if the parameter is mandatory,
        - the name of the parameter for the SimBrief API
        """
        self.climbProfiles = climbProfiles
        self.cruiseProfiles = cruiseProfiles
        self.descentProfiles = descentProfiles
        self.cruiseParameters = cruiseParameters

#---------------------------------------------------------------------------------------

class Aircraft(object):
    """Base class for aircraft."""
    @staticmethod
    def create(flight, bookedFlight):
        """Create an aircraft instance for the type in the given flight."""
        acft = _classes[flight.aircraftType](flight)
        acft.setBookedFlight(bookedFlight)
        return acft

    def __init__(self, flight, minLandingFuel = None,
                 recommendedLandingFuel = None):
        """Construct the aircraft for the given type."""
        self._flight = flight
        self._minLandingFuel = minLandingFuel
        self._recommendedLandingFuel = recommendedLandingFuel

        self._name = None
        self._modelName = None

        self._aircraftState = None

        self._maxVS = -10000.0
        self._minVS = 10000.0

        self._v1r2LineIndex = None
        self._derateLineID = None
        self._takeoffAntiIceLineID = None
        self._vrefLineIndex = None
        self._landingAntiIceLineID = None

        self.humanWeight = 82.0

        self.initialClimbSpeedAltitude = 1500
        self.reverseMinSpeed = 50

        self.hasStrobeLight = True

        self.maxTakeOffPitch = 15.0
        self.maxTouchDownPitch = 15.0
        self.brakeCoolTime = 10.0

        self.simBriefData = None

        self._checkers = []

        config = flight.config
        # Loggers

        self._checkers.append(checks.StageChecker())
        self._checkers.append(checks.TakeOffLogger())

        self._checkers.append(checks.AltimeterLogger())

        self._ilsLogger = checks.ILSLogger()
        self._checkers.append(self._ilsLogger)
        self._nav1Logger = checks.NAV1Logger()
        self._checkers.append(self._nav1Logger)
        self._nav2Logger = checks.NAV2Logger()
        self._checkers.append(self._nav2Logger)

        self._adf1Logger = checks.ADF1Logger()
        self._checkers.append(self._adf1Logger)
        self._adf2Logger = checks.ADF2Logger()
        self._checkers.append(self._adf2Logger)

        self._checkers.append(checks.SquawkLogger())

        self._appendLightsLoggers()

        self._checkers.append(checks.FlapsLogger())

        self._checkers.append(checks.GearsLogger())
        self._checkers.append(checks.InitialClimbSpeedLogger())
        self._checkers.append(checks.CruiseSpeedLogger())
        self._checkers.append(checks.SpoilerLogger())
        self._checkers.append(checks.APLogger())

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

        self._checkers.append(checks.TransponderChecker())

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

        timeout = 30.0 + config.realIASSmoothingLength - 1
        self._checkers.append(checks.OverspeedChecker(faultTimeout = timeout))

        self._checkers.append(checks.StallChecker())

        self._checkers.append(checks.PitotChecker())

        self._checkers.append(checks.ReverserLogger())
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
    def minLandingFuel(self):
        """Get the minimum acceptable amount of the landing fuel."""
        return self._minLandingFuel

    @property
    def recommendedLandingFuel(self):
        """Get the recommended amount of the landing fuel."""
        return self._recommendedLandingFuel

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
    def aglInFeet(self):
        """Indicate if AGL altitudes are to be logged in feet.

        This default implementation returns True."""
        return True

    @property
    def timestamp(self):
        """Get the timestamp of the current state."""
        return None if self._aircraftState is None \
               else self._aircraftState.timestamp

    @property
    def derateType(self):
        """Get the derate type for this aircraft.

        This default implementation returns DERATE_NONE."""
        return DERATE_NONE

    @property
    def machSpeedAbove(self):
        """Get the altitude above which the cruise speed should be reported
        in Machs."""
        return 24500

    def setBookedFlight(self, bookedFlight):
        """Update the aircraft based on the booked flight data (e.g. tail number).

        This default implementation does nothing."""

    def getDerateLine(self, value):
        """Get the log line for the given derate value.

        It uses the the derate type and produces the standard message for
        each. This children need not override it, although they can."""
        dt = self.derateType

        if dt==DERATE_BOEING:
            return "Derate calculated by the pilot: %s %%" % \
              ("-" if value is None else value,)
        elif dt==DERATE_EPR:
            return "EPR calculated by the pilot: %s" % \
              ("-" if value is None else value,)
        elif dt==DERATE_TUPOLEV:
            return "Thrust setting calculated by the pilot: %s" % \
              ("-" if value is None else
               "nominal" if value==DERATE_TUPOLEV_NOMINAL else "takeoff",)
        elif dt==DERATE_B462:
            return "Derate setting: %s" % \
              ("-" if value is None else "enabled" if value else "disabled",)
        elif dt!=DERATE_NONE:
            print("mlx.acft.getDerateLine: invalid derate type: " + dt)

        return None

    def getFlapsSpeedLimit(self, flaps):
        """Get the speed limit for the given flaps setting."""
        return self.flapSpeedLimits[flaps] if flaps in self.flapSpeedLimits \
               else None

    def modelChanged(self, timestamp, aircraftName, modelName):
        """Called when the simulator's aircraft changes."""
        self._name = aircraftName
        self._modelName = modelName
        if self._flight.stage is not None:
            self._logNameAndModel(timestamp)

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
                    print("Checker", checker, "failed", file=sys.stderr)
                    traceback.print_exc()

            self._flight.handleState(self._aircraftState, aircraftState)

            self._maxVS = max(self._maxVS, aircraftState.vs)
            self._minVS = min(self._minVS, aircraftState.vs)
        except:
            print("Failed to handle the state", file=sys.stderr)
            traceback.print_exc()
        finally:
            self._aircraftState = aircraftState

    def setStage(self, aircraftState, newStage):
        """Set the given stage as the new one and do whatever should be
        done."""
        if newStage==const.STAGE_BOARDING:
            self._logNameAndModel(aircraftState.timestamp)

        oldStage = self._flight.stage

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
                if oldStage == const.STAGE_RTO and self._flight.hasRTO:
                    rtoState = self._flight.rtoState
                    if (aircraftState.timestamp - rtoState.timestamp) < \
                       (self.brakeCoolTime * 60.0):
                        self.logger.fault("brakeCoolTime",
                                          aircraftState.timestamp,
                                          "Did not cool the brakes for at least %.f minutes after the RTO" % (self.brakeCoolTime,),
                                          15.0)
                self.logger.message(aircraftState.timestamp,
                                    "Flight time start")
                self.logger.message(aircraftState.timestamp,
                                    "Takeoff weight: %.0f kg, MTOW: %.0f kg" % \
                                    (aircraftState.grossWeight, self.mtow))
                self._logQNH(aircraftState)
                self.logger.message(aircraftState.timestamp,
                                    "Wind %03.0f/%.0f" % \
                                    (aircraftState.windDirection,
                                     aircraftState.windSpeed))
                self._logRadios(aircraftState)
                self._logV1R2(aircraftState)
                self._logDerate(aircraftState)
                self._logTakeoffAntiIce(aircraftState)
            elif newStage==const.STAGE_DESCENT or newStage==const.STAGE_LANDING:
                self._logRadios(aircraftState)
                if newStage==const.STAGE_LANDING:
                    self._logQNH(aircraftState)
            elif newStage==const.STAGE_GOAROUND:
                from .logger import Logger
                self._flight.handleFault("goaround",
                                         aircraftState.timestamp,
                                         "Go-around detected, please, explain!",
                                         Logger.NO_SCORE)
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
                if self._minLandingFuel is not None and \
                   aircraftState.totalFuel<self._minLandingFuel:
                    self._flight.handleFault(self.__class__,
                                             aircraftState.timestamp,
                                             "The amount of the landing fuel is less than the minimum for this type: %ukgs (possible NO GO!)" %
                                             (self._minLandingFuel,), 0)
                self.logger.message(aircraftState.timestamp,
                                    "Landing weight: %.0f kg, MLW: %.0f" % \
                                    (aircraftState.grossWeight, self.mlw))
                self.logger.message(aircraftState.timestamp,
                                    "Vertical speed range: %.0f..%.0f feet/min" % \
                                    (self._minVS, self._maxVS))
            # elif newStage==const.STAGE_PARKING:
            #     self.logger.message(aircraftState.timestamp, "Block time end")
            elif newStage==const.STAGE_END:
                flightLength = self._flight.flightTimeEnd - self._flight.flightTimeStart
                self.logger.message(aircraftState.timestamp, "Block time end")
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
                            "Wind %03.0f/%.0f" % \
                            (windDirection, windSpeed))
        self.logger.message(self._aircraftState.timestamp,
                            "Visibility: %.0f metres" % (visibility,))
        self._logQNH(self._aircraftState)
        self._logVRef()
        self._logLandingAntiIce(self._aircraftState)
        self.flight.flareStarted(flareStart, flareStartFS)
        fs.sendMessage(const.MESSAGETYPE_INFORMATION, "Flare-time", 3)

    def flareFinished(self, flareEnd, flareEndFS, tdRate, tdRateCalculatedByFS,
                      ias, pitch, bank, heading, gLoad):
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
        self.logger.message(self._aircraftState.timestamp,
                            "Touchdown G-load: %.2f" % (gLoad,))
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
                           "CG: %.1f%%" % \
                            (self._aircraftState.cog*100.0,))

        if abs(pitch)>self.maxTouchDownPitch:
            self._flight.handleNoGo("TDPitch", self._aircraftState.timestamp,
                                    "Touchdown pitch higher than aircraft maximum (%.2f)" % \
                                    (self.maxTouchDownPitch,),
                                    "TD TAILSTRIKE NO GO")

    def cancelFlare(self):
        """Cancel flare, if it has started."""
        self.flight.simulator.cancelFlare()

    def checkFlightEnd(self, aircraftState):
        """Check if the end of the flight has arrived.

        This default implementation checks the N1 values, but for
        piston-powered aircraft you need to check the RPMs."""
        if aircraftState.n1 is not None:
            for n1 in aircraftState.n1:
                if n1 is not None and n1>=0.5: return False
        return True

    def updateV1R2(self):
        """Update the V1, Vr and V2 values from the flight, if the these values
        have already been logged."""
        if self._v1r2LineIndex is not None:
            self._logV1R2()

    def updateDerate(self):
        """Update the derate value from the flight, if the these values
        have already been logged."""
        if self._derateLineID is not None:
            self._logDerate()

    def updateTakeoffAntiIce(self):
        """Update the take-off anti-ice setting."""
        if self._takeoffAntiIceLineID is not None:
            self._logTakeoffAntiIce()

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

    def _logV1R2(self, state = None):
        """Log the V1, Vr and V2 value either newly, or by updating the
        corresponding line."""
        message = "Calc. TO speeds: V1: %s, VR: %s, V2: %s" % \
                  (self._speedToLog(self._flight.v1),
                   self._speedToLog(self._flight.vr),
                   self._speedToLog(self._flight.v2))

        if self._v1r2LineIndex is None:
            if state is None:
                state = self._aircraftState
            self._v1r2LineIndex = \
                self.logger.message(state.timestamp, message)
        else:
            self.logger.updateLine(self._v1r2LineIndex, message)

    def _logDerate(self, state = None):
        """Log the derate values either newly or by updating the corresponding
        line."""
        dt = self.derateType
        if dt==DERATE_NONE:
            return

        message = self.getDerateLine(self._flight.derate)
        if message is not None:
            if self._derateLineID is None:
                if state is None:
                    state = self._aircraftState
                self._derateLineID = \
                  self.logger.message(state.timestamp, message)
            else:
                self.logger.updateLine(self._derateLineID, message)

    def _logTakeoffAntiIce(self, state = None):
        """Log the take-off anti-ice setting either newly or by updating the
        corresponding line."""
        antiIceOn = self._flight.takeoffAntiIceOn
        if state is not None:
            antiIceOn = antiIceOn or state.antiIceOn is True
            self._flight.takeoffAntiIceOn = antiIceOn

        message = "Anti-ice was turned %s" % \
                  ("ON" if antiIceOn else "OFF")

        if self._takeoffAntiIceLineID is None:
            if state is None:
                state = self._aircraftState
            self._takeoffAntiIceLineID = \
                self.logger.message(state.timestamp, message)
        else:
            self.logger.updateLine(self._takeoffAntiIceLineID, message)

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

    def updateLandingAntiIce(self):
        """Update the landing anti-ice setting."""
        if self._landingAntiIceLineID is not None:
            self._logLandingAntiIce()

    def _logLandingAntiIce(self, state = None):
        """Log the landing anti-ice setting either newly or by updating the
        corresponding line."""
        antiIceOn = self._flight.landingAntiIceOn
        if state is not None:
            antiIceOn = antiIceOn or state.antiIceOn is True
            self._flight.landingAntiIceOn = antiIceOn

        message = "Anti-ice was turned %s" % \
                  ("ON" if antiIceOn else "OFF")

        if self._landingAntiIceLineID is None:
            if state is None:
                state = self._aircraftState
            self._landingAntiIceLineID = \
                self.logger.message(state.timestamp, message)
        else:
            self.logger.updateLine(self._landingAntiIceLineID, message)

    def _fleetRetrieved(self, fleet):
        """Callback for the fleet retrieval result."""
        if fleet is not None:
            gateList = ""
            for gate in fleet.iterAvailableLHBPGates(self.flight.bookedFlight.tailNumber):
                if gateList: gateList += ", "
                gateList += gate.number
            fs.sendMessage(const.MESSAGETYPE_GATE_SYSTEM,
                           "Free gates: " + gateList, 20)


    def _logRadios(self, aircraftState):
        """Log the radios from the given aircraft state."""
        flight = self._flight
        logger = flight.logger

        self._ilsLogger.forceLog(flight, logger, aircraftState)
        self._nav1Logger.forceLog(flight, logger, aircraftState)
        self._nav2Logger.forceLog(flight, logger, aircraftState)
        self._adf1Logger.forceLog(flight, logger, aircraftState)
        self._adf2Logger.forceLog(flight, logger, aircraftState)

    def _logQNH(self, aircraftState):
        """Log the current QNH along with the altimeter setting."""
        self.logger.message(aircraftState.timestamp,
                            "QNH: %.2f hPa, altimeter: %.2f hPa" % \
                            (aircraftState.qnh, aircraftState.altimeter))

    def _logNameAndModel(self, timestamp):
        """Log the aircraft's name and model with taking the timestamp from the
        given state."""
        self._flight.logger.message(timestamp,
                                    "Aircraft: name='%s', model='%s'" % \
                                    (self._name, self._modelName))

#---------------------------------------------------------------------------------------

class Boeing737(Aircraft):
    """Base class for the various aircraft in the Boeing 737 family.

    The aircraft type-specific values in the aircraft state have the following
    structure:
    - fuel: left, centre, right
    - n1: left, right
    - reverser: left, right"""
    def __init__(self, flight, minLandingFuel = 2500,
                 recommendedLandingFuel = 3500):
        super(Boeing737, self).__init__(flight,
                                        minLandingFuel = minLandingFuel,
                                        recommendedLandingFuel =
                                        recommendedLandingFuel)

        self.gearSpeedLimit = 270
        self.flapSpeedLimits = { 1 : 260,
                                 2 : 260,
                                 5 : 250,
                                 10 : 210,
                                 15 : 200,
                                 25 : 190,
                                 30 : 175,
                                 40 : 162 }

    @property
    def derateType(self):
        """Get the derate type for this type."""
        return DERATE_BOEING

#---------------------------------------------------------------------------------------

class B736(Boeing737):
    """Boeing 737-600 aircraft."""
    dow = 38307

    def __init__(self, flight):
        super(B736, self).__init__(flight)
        self.mtow = 58328
        self.mlw = 54657
        self.mzfw = 51482
        self.maxTakeOffPitch = 16.2
        self.maxTouchDownPitch = 14.7
        self.simBriefData = SimBriefData(["250/280/78"],
                                         ["CI", "M75", "M78", "M79", "M80", "LRC"],
                                         ["78/280/250"],
                                         cruiseParameters = {0: (False, "civalue")})

#---------------------------------------------------------------------------------------

class B737(Boeing737):
    """Boeing 737-700 aircraft."""
    dow = 39250

    def __init__(self, flight):
        super(B737, self).__init__(flight)
        self.mtow = 61410
        self.mlw = 58059
        self.mzfw = 54657
        self.maxTakeOffPitch = 14.7
        self.maxTouchDownPitch = 13.2
        self.simBriefData = SimBriefData(["250/280/78"],
                                         ["CI", "M75", "M78", "M79", "M80", "LRC"],
                                         ["78/280/250", "78/250/250"],
                                         cruiseParameters = {0: (False, "civalue")})

#---------------------------------------------------------------------------------------

class B738(Boeing737):
    """Boeing 737-800 aircraft."""
    dow = 42690

    def __init__(self, flight):
        super(B738, self).__init__(flight)
        self.mtow = 71791
        self.mlw = 65317
        self.mzfw = 61688
        self.maxTakeOffPitch = 11
        self.maxTouchDownPitch = 9.5
        self.simBriefData = SimBriefData(["250/280/78"],
                                         ["CI", "M76", "M78", "M79", "M80", "LRC"],
                                         ["78/280/250", "78/250/250"],
                                         cruiseParameters = {0: (False, "civalue")})

#---------------------------------------------------------------------------------------

class B738Charter(B738):
    """Boeing 737-800 aircraft used for charters."""
    def __init__(self, flight):
        super(B738Charter, self).__init__(flight)
        self.mtow = 77791
        self.simBriefData = SimBriefData(["AUTO"],
                                         ["280/M74"],
                                         ["AUTO"])

#---------------------------------------------------------------------------------------

class Boeing737CL(Boeing737):
    """Base class for the various aircraft in the Boeing 737 Classic family."""
    def __init__(self, flight):
        super(Boeing737CL, self).__init__(flight, minLandingFuel = 3500,
                                          recommendedLandingFuel = None)

#---------------------------------------------------------------------------------------

class B732(Boeing737CL):
    """Boeing 737-200 aircraft."""
    dow = 27646

    def __init__(self, flight):
        super(B732, self).__init__(flight)
        self.mtow = 52390
        self.mlw = 46720
        self.mzfw = 43091
        self.maxTakeOffPitch = 15.5
        self.maxTouchDownPitch = 15.5
        self.simBriefData = SimBriefData(["250/280/70"],
                                         ["LRC", "M72", "M73", "M74"],
                                         ["74/320/250"])

#---------------------------------------------------------------------------------------

class B733(Boeing737CL):
    """Boeing 737-300 aircraft."""
    dow = 32900

    def __init__(self, flight):
        super(B733, self).__init__(flight)
        self.mtow = 56472
        self.mlw = 51710
        self.mzfw = 47625
        self.maxTakeOffPitch = 13.4
        self.maxTouchDownPitch = 12.0
        self.simBriefData = SimBriefData(["250/280/74"],
                                         ["CI", "M74", "M76", "M78", "LRC"],
                                         ["74/280/250"],
                                         cruiseParameters = {0: (False, "civalue")})

#---------------------------------------------------------------------------------------

class B734(Boeing737CL):
    """Boeing 737-400 aircraft."""
    def __init__(self, flight):
        super(B734, self).__init__(flight)
        self.dow = 35100
        self.mtow = 62822
        self.mlw = 54885
        self.mzfw = 51256
        self.maxTakeOffPitch = 11.4
        self.maxTouchDownPitch = 10
        self.simBriefData = SimBriefData(["250/280/74"],
                                         ["CI", "M74", "M76", "M78", "LRC"],
                                         ["74/280/250"],
                                         cruiseParameters = {0: (False, "civalue")})

#---------------------------------------------------------------------------------------

class B735(Boeing737CL):
    """Boeing 737-500 aircraft."""
    dow = 31900

    def __init__(self, flight):
        super(B735, self).__init__(flight)
        self.mtow = 62823
        self.mlw = 49895
        self.mzfw = 46720
        self.maxTakeOffPitch = 14.7
        self.maxTouchDownPitch = 13.2
        self.simBriefData = SimBriefData(["250/280/74"],
                                         ["CI", "M74", "M76", "M78", "LRC"],
                                         ["74/280/250"],
                                         cruiseParameters = {0: (False, "civalue")})

#---------------------------------------------------------------------------------------

class DH8D(Aircraft):
    """Bombardier Dash-8 Q400 aircraft.

    The aircraft type-specific values in the aircraft state have the following
    structure:
    - fuel: left, right
    - n1: left, right
    - reverser: left, right."""
    dow = 18508

    def __init__(self, flight):
        super(DH8D, self).__init__(flight, minLandingFuel = 2000)
        self.mtow = 29574
        self.mlw = 28123
        self.mzfw = 26308
        self.gearSpeedLimit = 215
        self.flapSpeedLimits = { 5 : 200,
                                 10 : 181,
                                 15 : 172,
                                 35 : 158 }
        self.maxTakeOffPitch = 8.0
        self.maxTouchDownPitch = 7.0
        self.simBriefData = SimBriefData(["I-900", "II-900", "III-900",
                                          "I-850", "II-850", "III-850"],
                                         ["MCR", "ISC", "LRC", "HSC"],
                                         ["I-850", "II-850", "III-850"])

#---------------------------------------------------------------------------------------

class Boeing767(Aircraft):
    """Base class for the various aircraft in the Boeing 767 family.

    The aircraft type-specific values in the aircraft state have the following
    structure:
    - fuel: left, centre, right
    - n1: left, right
    - reverser: left, right"""

    def __init__(self, flight, minLandingFuel = 7000):
        super(Boeing767, self).__init__(flight, minLandingFuel = minLandingFuel)
        self.gearSpeedLimit = 270
        self.flapSpeedLimits = { 1 : 255,
                                 5 : 235,
                                 10 : 215,
                                 20 : 215,
                                 25 : 185,
                                 30 : 175 }

    @property
    def derateType(self):
        """Get the derate type for this type."""
        return DERATE_BOEING

#---------------------------------------------------------------------------------------

class B762(Boeing767):
    """Boeing 767-200 aircraft."""
    dow = 84507

    def __init__(self, flight):
        super(B762, self).__init__(flight)
        self.mtow = 159210
        self.mlw = 126098
        self.mzfw = 114758
        self.maxTakeOffPitch = 13.1
        self.maxTouchDownPitch = 11.6
        self.simBriefData = SimBriefData(["250/290/78"],
                                         ["CI", "M76", "M78", "M80", "M82",
                                          "M84", "M85", "LRC"],
                                         ["78/290/250"],
                                         cruiseParameters = {0: (False, "civalue")})

#---------------------------------------------------------------------------------------

class B763(Boeing767):
    """Boeing 767-300 aircraft."""
    dow = 91311

    def __init__(self, flight):
        super(B763, self).__init__(flight)
        self.mtow = 181436
        self.mlw = 137892
        self.mzfw = 114758
        self.maxTakeOffPitch = 9.6
        self.maxTouchDownPitch = 8.1
        self.simBriefData = SimBriefData(["250/290/78"],
                                         ["CI", "M76", "M78", "M80", "M82", "M84", "LRC"],
                                         ["78/290/250"],
                                         cruiseParameters = {0: (False, "civalue")})

    def setBookedFlight(self, bookedFlight):
        """Update the aircraft based on the booked flight data (e.g. tail number)."""
        if bookedFlight.tailNumber=="HA-LHD":
            self.mtow = 159210
            self.mlw = 126098

#---------------------------------------------------------------------------------------

class CRJ2(Aircraft):
    """Bombardier CRJ-200 aircraft.

    The aircraft type-specific values in the aircraft state have the following
    structure:
    - fuel: left, centre, right
    - n1: left, right
    - reverser: left, right."""
    dow = 14549

    def __init__(self, flight):
        super(CRJ2, self).__init__(flight, minLandingFuel = 1000)
        self.mtow = 22995
        self.mlw = 21319
        self.mzfw = 19958
        self.gearSpeedLimit = 240
        self.flapSpeedLimits = { 8 : 260,
                                 20 : 220,
                                 30 : 190,
                                 45 : 175 }
        self.maxTakeOffPitch = 18.0
        self.maxTouchDownPitch = 18.0
        self.simBriefData = SimBriefData(["250/70", "290/74"],
                                         ["CI", "LRC", "M70", "M72", "M74", "M77", "M80"],
                                         ["74/290/250", "77/320/250"],
                                         cruiseParameters = {0: (False, "civalue")})

#---------------------------------------------------------------------------------------

class F70(Aircraft):
    """Fokker 70 aircraft.

    The aircraft type-specific values in the aircraft state have the following
    structure:
    - fuel: left, centre, right
    - n1: left, right
    - reverser: left, right."""
    dow = 24283

    def __init__(self, flight):
        super(F70, self).__init__(flight, minLandingFuel = 1900)
        self.mtow = 38100 # FIXME: differentiate by registration number,
                          # MTOW of HA-LMF: 41955
        self.mlw = 36740
        self.mzfw = 32655
        self.gearSpeedLimit = 200
        self.flapSpeedLimits = { 8 : 250,
                                 15 : 220,
                                 25 : 220,
                                 42 : 180 }
        self.reverseMinSpeed = 50
        self.maxTakeOffPitch = 16.0
        self.maxTouchDownPitch = 16.0
        self.simBriefData = SimBriefData(["250/280/70"],
                                         ["M70", "LRC"],
                                         ["70/280/250"])

    @property
    def derateType(self):
        """Get the derate type for this type."""
        return DERATE_EPR

#---------------------------------------------------------------------------------------

class DC3(Aircraft):
    """Lisunov Li-2 (DC-3) aircraft.

    The aircraft type-specific values in the aircraft state have the following
    structure:
    - fuel: left aux, left, right, right aux
    - rpm: left, right
    - reverser: left, right."""
    dow = 8627

    def __init__(self, flight):
        super(DC3, self).__init__(flight)
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
    dow = 29500

    def __init__(self, flight):
        super(T134, self).__init__(flight, minLandingFuel = 3000)
        self.mtow = 49000
        self.mlw = 43000
        self.mzfw = 38500
        self.gearSpeedLimit = 216
        self.flapSpeedLimits = { 10 : 450,
                                 20 : 400,
                                 30 : 300 }
        self.reverseMinSpeed = 50

        self.hasStrobeLight = False

        self.maxTakeOffPitch = 16.0
        self.maxTouchDownPitch = 16.0

    @property
    def derateType(self):
        """Get the derate type for this type."""
        return DERATE_TUPOLEV

    @property
    def speedInKnots(self):
        """Indicate if the speed is in knots."""
        return False

    @property
    def aglInFeet(self):
        """Indicate if AGL altituedes are in feet."""
        return False

    def _appendLightsLoggers(self):
        """Append the loggers needed for the lights."""
        self._checkers.append(checks.AnticollisionLightsLogger())
        self._checkers.append(checks.LandingLightsLogger())
        self._checkers.append(checks.NavLightsLogger())

    def _appendLightsCheckers(self):
        """Append the checkers needed for the lights."""
        self._checkers.append(checks.TupolevAntiCollisionLightsChecker())
        self._checkers.append(checks.TupolevLandingLightsChecker())
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
    dow = 53259

    def __init__(self, flight):
        super(T154, self).__init__(flight, minLandingFuel = 5000)
        self.mtow = 98000
        self.mlw = 78000
        self.mzfw = 72000
        self.gearSpeedLimit = 216
        self.flapSpeedLimits = { 15 : 227,
                                 28 : 194,
                                 45 : 162 }
        self.reverseMinSpeed = 50

        self.hasStrobeLight = False

        self.maxTakeOffPitch = 16.0
        self.maxTouchDownPitch = 16.0
        self.simBriefData = SimBriefData(["AUTO"],
                                         ["AUTO"],
                                         ["AUTO"])

    @property
    def speedInKnots(self):
        """Indicate if the speed is in knots."""
        return False

    @property
    def aglInFeet(self):
        """Indicate if AGL altituedes are in feet."""
        return False

    @property
    def derateType(self):
        """Get the derate type for this type."""
        return DERATE_TUPOLEV

    @property
    def machSpeedAbove(self):
        """Get the altitude above which the cruise speed should be reported
        in Machs."""
        return 32000

    def setBookedFlight(self, bookedFlight):
        """Update the aircraft based on the booked flight data (e.g. tail number)."""
        if bookedFlight.tailNumber in ["HA-LCM", "HA-LCN", "HA-LCO", "HA-LCP",
                                       "HA-LCR", "HA-LCU", "HA-LCV"]:
            self.mtow = 100000
            self.mlw = 80000
        elif bookedFlight.tailNumber=="HA-LCX":
            self.mtow = 100000
            self.mlw = 80000
            self.mzfw = 74000

            self.flapSpeedLimits = { 15 : 227,
                                     28 : 194,
                                     36 : 178,
                                     45 : 162 }

    def _appendLightsLoggers(self):
        """Append the loggers needed for the lights."""
        self._checkers.append(checks.AnticollisionLightsLogger())
        self._checkers.append(checks.LandingLightsLogger())
        self._checkers.append(checks.NavLightsLogger())

    def _appendLightsCheckers(self):
        """Append the checkers needed for the lights."""
        self._checkers.append(checks.AntiCollisionLightsChecker())
        self._checkers.append(checks.TupolevLandingLightsChecker())
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
    dow = 9400

    def __init__(self, flight):
        super(YK40, self).__init__(flight)
        self.mtow = 17200
        self.mlw = 16800
        self.mzfw = 12100
        self.gearSpeedLimit = 165
        self.flapSpeedLimits = { 20 : 165,
                                 35 : 135 }

        self.hasStrobeLight = False

    @property
    def speedInKnots(self):
        """Indicate if the speed is in knots."""
        return False

    @property
    def aglInFeet(self):
        """Indicate if AGL altituedes are in feet."""
        return False

    @property
    def derateType(self):
        """Get the derate type for this type."""
        return DERATE_TUPOLEV

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

class B462(Aircraft):
    """British Aerospace BAe-146 aircraft.

    The aircraft type-specific values in the aircraft state have the following
    structure:
    - fuel: left, centre, right
    - n1: left outer, left inner, right inner, right outer
    - reverser: empty (the plane has no reversers)"""
    dow = 25706

    def __init__(self, flight):
        super(B462, self).__init__(flight)
        self.mtow = 43998
        self.mlw = 38599
        self.mzfw = 33792
        self.gearSpeedLimit = 210
        self.flapSpeedLimits = { 18 : 217,
                                 24 : 180,
                                 30 : 170,
                                 33 : 150 }
        self.simBriefData = SimBriefData(["HighSpeed", "LongRange"],
                                         ["M70", "MCR", "LRC"],
                                         ["HighSpeed", "LongRange"])
    @property
    def derateType(self):
        """Get the derate type for this type."""
        return DERATE_B462

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
             const.AIRCRAFT_B732  : B732,
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
             const.AIRCRAFT_YK40  : YK40,
             const.AIRCRAFT_B462  : B462 }

#---------------------------------------------------------------------------------------

def getClass(aircraftType):
    """Get the class representing the given aircraft types"""
    return _classes[aircraftType]

#---------------------------------------------------------------------------------------

if __name__ == "__main__":
    value = SmoothedValue()

    print("Adding 1, 12.0")
    value.add(1, 12.0)
    print(value.get())

    print("Adding 1, 15.0")
    value.add(1, 15.0)
    print(value.get())

    print("Adding 2, 18.0")
    value.add(2, 18.0)
    print(value.get())

    print("Adding 2, 20.0")
    value.add(2, 20.0)
    print(value.get())

    print("Adding 5, 22.0")
    value.add(5, 22.0)
    print(value.get())

    print("Adding 5, 25.0")
    value.add(5, 25.0)
    print(value.get())

    print("Adding 5, 29.0")
    value.add(5, 29.0)
    print(value.get())

    print("Adding 5, 21.0")
    value.add(5, 21.0)
    print(value.get())

    print("Adding 5, 26.0")
    value.add(5, 26.0)
    print(value.get())

    print("Adding 2, 30.0")
    value.add(2, 30.0)
    print(value.get())

    print("Adding 2, 55.0")
    value.add(2, 55.0)
    print(value.get())

#---------------------------------------------------------------------------------------
