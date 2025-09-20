
from .soundsched import SoundScheduler, ChecklistScheduler
from .checks import SpeedChecker

from . import const
from . import util
import time

import threading

#---------------------------------------------------------------------------------------

## @package mlx.flight
#
# The global flight state.
#
# This module defines a single class, \ref mlx.flight.Flight "Flight", which
# represents the flight in progress.

#---------------------------------------------------------------------------------------

class Flight(object):
    """The object with the global flight state.

    It is also the hub for the other main objects participating in the handling of
    the flight."""

    # The difference in minutes from the schedule which is considered a bit big
    TIME_WARNING_DIFFERENCE = 5

    # The difference in minutes from the schedule which is considered too big
    TIME_ERROR_DIFFERENCE = 15

    @staticmethod
    def canLogCruiseAltitude(stage):
        """Determine if the cruise altitude can be logged in the given
        stage."""
        return stage in [const.STAGE_CRUISE, const.STAGE_DESCENT,
                         const.STAGE_LANDING]

    @staticmethod
    def getMinutesDifference(minutes1, minutes2):
        """Get the difference in minutes between the given two time
        instances."""
        diff1 = minutes1 - minutes2
        diff2 = -1 * diff1

        if diff1 < 0: diff1 += 60*24
        else: diff2 += 60*24

        diff = min(diff1, diff2)

        return -1*diff if diff2<diff1 else diff

    @staticmethod
    def isTimeDifferenceTooMuch(scheduledTime, realTimestamp,
                                earlyOnlyWarning = False,
                                earlyOK = False):
        """Determine if the given real time differs to much from the scheduled
        time.

        Returns a tuple of:
        - a boolean indicating if the difference is enough to warrant at least
          a warning
        - a boolean indicating if the difference is too big, i. e. unacceptable
          without explanation."""
        realTime = time.gmtime(realTimestamp)

        scheduledMinute = scheduledTime.hour * 60 + scheduledTime.minute
        realMinute = realTime.tm_hour * 60 + realTime.tm_min

        diff = Flight.getMinutesDifference(scheduledMinute, realMinute)

        return (diff<-Flight.TIME_WARNING_DIFFERENCE or
                (not earlyOK and diff>Flight.TIME_WARNING_DIFFERENCE),
                diff<-Flight.TIME_ERROR_DIFFERENCE or
                (not earlyOK and not earlyOnlyWarning
                 and diff>Flight.TIME_ERROR_DIFFERENCE))

    def __init__(self, logger, gui):
        """Construct the flight."""
        self._stage = None
        self.logger = logger
        self._gui = gui

        gui.resetFlightStatus()

        self._pilotHotkeyPressed = False
        self._checklistHotkeyPressed = False

        self.flareTimeFromFS = False

        self.aircraftType = None
        self.aircraft = None
        self.simulator = None

        self.blockTimeStart = None
        self.flightTimeStart = None
        self.climbTimeStart = None
        self.cruiseTimeStart = None
        self.descentTimeStart = None
        self.flightTimeEnd = None
        self.blockTimeEnd = None

        self._rtoState = None
        self._rtoLogEntryID = None

        self._lastDistanceTime = None
        self._previousLatitude = None
        self._previousLongitude = None
        self.flownDistance = 0.0

        self.startFuel = None
        self.endFuel = None

        self._endCondition = threading.Condition()

        self._flareStart = None
        self._flareStartFS = None

        self._tdRate = None

        self._soundScheduler = SoundScheduler(self)
        self._checklistScheduler = ChecklistScheduler(self)

        self._maxAltitude = 0

        self.departureGateIsTaxiThrough = True

    @property
    def config(self):
        """Get the configuration."""
        return self._gui.config

    @property
    def stage(self):
        """Get the flight stage."""
        return self._stage

    @property
    def fsType(self):
        """Get the flight simulator type."""
        return self._gui.fsType

    @property
    def loggedIn(self):
        """Indicate if the user has logged in properly."""
        return self._gui.loggedIn

    @property
    def entranceExam(self):
        """Get whether an entrance exam is being performed."""
        return self._gui.entranceExam

    @property
    def bookedFlight(self):
        """Get the booked flight."""
        return self._gui.bookedFlight

    @property
    def numCockpitCrew(self):
        """Get the number of cockpit crew members on the flight."""
        return self._gui.numCockpitCrew

    @property
    def numCabinCrew(self):
        """Get the number of cabin crew members on the flight."""
        return self._gui.numCabinCrew

    @property
    def numPassengers(self):
        """Get the number of passengers on the flight."""
        return self._gui.numPassengers

    @property
    def numChildren(self):
        """Get the number of child passengers on the flight."""
        return self._gui.numChildren

    @property
    def numInfants(self):
        """Get the number of infant passengers on the flight."""
        return self._gui.numInfants

    @property
    def bagWeight(self):
        """Get the baggage weight for the flight."""
        return self._gui.bagWeight

    @property
    def cargoWeight(self):
        """Get the cargo weight for the flight."""
        return self._gui.cargoWeight

    @property
    def mailWeight(self):
        """Get the mail weight for the flight."""
        return self._gui.mailWeight

    @property
    def zfw(self):
        """Get the Zero-Fuel Weight of the flight."""
        return self._gui.zfw

    @property
    def filedCruiseAltitude(self):
        """Get the filed cruise altitude."""
        return self._gui.filedCruiseAltitude

    @property
    def cruiseAltitude(self):
        """Get the cruise altitude of the flight."""
        return self._gui.cruiseAltitude

    @property
    def maxAltitude(self):
        """Get the maximal altitude ever reached during the flight."""
        return self._maxAltitude

    @property
    def cruiseAltitudeForDescent(self):
        """Get the cruise altitude to check for descending.

        This is the minimum of current maximal altitude and the cruise
        altitude."""
        return min(self._maxAltitude, self.cruiseAltitude)

    @property
    def route(self):
        """Get the route of the flight."""
        return self._gui.route

    @property
    def departureMETAR(self):
        """Get the departure METAR of the flight."""
        return self._gui.departureMETAR

    @property
    def arrivalMETAR(self):
        """Get the arrival METAR of the flight."""
        return self._gui.arrivalMETAR

    @property
    def departureRunway(self):
        """Get the departure runway."""
        return self._gui.departureRunway

    @property
    def sid(self):
        """Get the SID followed."""
        return self._gui.sid

    @property
    def v1(self):
        """Get the V1 speed of the flight."""
        return self._gui.v1

    @property
    def vr(self):
        """Get the Vr speed of the flight."""
        return self._gui.vr

    @property
    def v2(self):
        """Get the V2 speed of the flight."""
        return self._gui.v2

    @property
    def takeoffAntiIceOn(self):
        """Get whether the anti-ice system was on during takeoff."""
        return self._gui.takeoffAntiIceOn

    @takeoffAntiIceOn.setter
    def takeoffAntiIceOn(self, value):
        """Set whether the anti-ice system was on during takeoff."""
        self._gui.takeoffAntiIceOn = value

    @property
    def derate(self):
        """Get the derate value of the flight."""
        return self._gui.derate

    @property
    def star(self):
        """Get the STAR planned."""
        return self._gui.star

    @property
    def transition(self):
        """Get the transition planned."""
        return self._gui.transition

    @property
    def approachType(self):
        """Get the approach type."""
        return self._gui.approachType

    @property
    def arrivalRunway(self):
        """Get the arrival runway."""
        return self._gui.arrivalRunway

    @property
    def vref(self):
        """Get the VRef speed of the flight."""
        return self._gui.vref

    @property
    def landingAntiIceOn(self):
        """Get whether the anti-ice system was on during landing."""
        return self._gui.landingAntiIceOn

    @landingAntiIceOn.setter
    def landingAntiIceOn(self, value):
        """Set whether the anti-ice system was on during landing."""
        self._gui.landingAntiIceOn = value

    @property
    def tdRate(self):
        """Get the touchdown rate if known, None otherwise."""
        return self._tdRate

    @property
    def flightType(self):
        """Get the type of the flight."""
        return self._gui.flightType

    @property
    def online(self):
        """Get whether the flight was an online flight."""
        return self._gui.online

    @property
    def comments(self):
        """Get the comments made by the pilot."""
        return self._gui.comments

    @property
    def flightDefects(self):
        """Get the flight defects reported by the pilot."""
        return self._gui.flightDefects

    @property
    def delayCodes(self):
        """Get the delay codes."""
        return self._gui.delayCodes

    @property
    def speedInKnots(self):
        """Determine if the speeds for the flight are to be expressed in
        knots."""
        return self.aircraft.speedInKnots if self.aircraft is not None \
               else True

    @property
    def aglInFeet(self):
        """Determine if the AGL altutides for the flight are to be expressed in
        feet."""
        return self.aircraft.aglInFeet if self.aircraft is not None \
               else True

    @property
    def hasRTO(self):
        """Determine if we have an RTO state."""
        return self._rtoState is not None

    @property
    def rtoState(self):
        """Get the RTO state."""
        return self._rtoState

    @property
    def blockTimeStartWrong(self):
        """Determine if the block time start is wrong compared to the scheduled
        departure time.

        Returns a tuple of:
        - a boolean indicating if the difference warrants a warning
        - a boolean indicating if the difference warrants not only a warning,
          but an error as well."""
        return self.isTimeDifferenceTooMuch(self.bookedFlight.departureTime,
                                            self.blockTimeStart)

    @property
    def blockTimeEndWrong(self):
        """Determine if the block time end is wrong compared to the scheduled
        arrival time.

        Returns a tuple of:
        - a boolean indicating if the difference warrants a warning
        - a boolean indicating if the difference warrants not only a warning,
          but an error as well."""
        return self.isTimeDifferenceTooMuch(self.bookedFlight.arrivalTime,
                                            self.blockTimeEnd,
                                            earlyOK = True)

    def disconnected(self):
        """Called when the connection to the simulator has failed."""
        if self.aircraft is not None and self.aircraft.state is not None:
            self.logger.message(self.aircraft.state.timestamp,
                                "The connection to the simulator has failed")

    def handleState(self, oldState, currentState):
        """Handle a new state information."""
        self._updateFlownDistance(currentState)

        self.endFuel = currentState.totalFuel
        if self.startFuel is None:
            self.startFuel = self.endFuel

        self._soundScheduler.schedule(currentState,
                                      self._pilotHotkeyPressed)
        self._pilotHotkeyPressed = False

        self._maxAltitude = max(currentState.altitude, self._maxAltitude)

        if self._checklistHotkeyPressed:
            self._checklistScheduler.hotkeyPressed()
            self._checklistHotkeyPressed = False

    def setStage(self, timestamp, stage):
        """Set the flight stage.

        Returns if the stage has really changed."""
        if stage!=self._stage:
            self._logStageDuration(timestamp, stage)
            self._stage = stage
            self._gui.setStage(stage)
            self.logger.stage(timestamp, stage)
            if stage==const.STAGE_PUSHANDTAXI:
                self.blockTimeStart = timestamp
            elif stage==const.STAGE_TAKEOFF:
                self.flightTimeStart = timestamp
            elif stage==const.STAGE_CLIMB:
                self.climbTimeStart = timestamp
            elif stage==const.STAGE_CRUISE:
                self.cruiseTimeStart = timestamp
            elif stage==const.STAGE_DESCENT:
                self.descentTimeStart = timestamp
            elif stage==const.STAGE_TAXIAFTERLAND:
                self.flightTimeEnd = timestamp
            # elif stage==const.STAGE_PARKING:
            #     self.blockTimeEnd = timestamp
            elif stage==const.STAGE_END:
                self.blockTimeEnd = timestamp
                with self._endCondition:
                    self._endCondition.notify()
            return True
        else:
            return False

    def handleFault(self, faultID, timestamp, what, score,
                    updatePrevious = False, updateID = None):
        """Handle the given fault.

        faultID as a unique ID for the given kind of fault. If another fault of
        this ID has been reported earlier, it will be reported again only if
        the score is greater than last time. This ID can be, e.g. the checker
        the report comes from."""
        id = self.logger.fault(faultID, timestamp, what, score,
                               updatePrevious = updatePrevious,
                               updateID = updateID)
        self._gui.setRating(self.logger.getRating())
        return id

    def handleNoGo(self, faultID, timestamp, what, shortReason):
        """Handle a No-Go fault."""
        self.logger.noGo(faultID, timestamp, what)
        self._gui.setNoGo(shortReason)

    def setRTOState(self, state):
        """Set the state that might be used as the RTO state.

        If there has been no RTO state, the GUI is notified that from now on
        the user may select to report an RTO."""
        hadNoRTOState = self._rtoState is None

        self._rtoState = state
        self._rtoLogEntryID = \
            SpeedChecker.logSpeedFault(self, state,
                                       stage = const.STAGE_PUSHANDTAXI)

        if hadNoRTOState:
            self._gui.updateRTO()

    def rtoToggled(self, indicated):
        """Called when the user has toggled the RTO indication."""
        if self._rtoState is not None:
            if indicated:
                self.logger.clearFault(self._rtoLogEntryID,
                                       "RTO at %d knots" %
                                       (self._rtoState.groundSpeed,))
                self._gui.setRating(self.logger.getRating())
                if self._stage == const.STAGE_PUSHANDTAXI:
                    self.setStage(self.aircraft.state.timestamp,
                                  const.STAGE_RTO)
            else:
                SpeedChecker.logSpeedFault(self, self._rtoState,
                                           stage = const.STAGE_PUSHANDTAXI,
                                           updateID = self._rtoLogEntryID)
                if self._stage == const.STAGE_RTO:
                    self.setStage(self.aircraft.state.timestamp,
                                  const.STAGE_PUSHANDTAXI)

    def flareStarted(self, flareStart, flareStartFS):
        """Called when the flare time has started."""
        self._flareStart = flareStart
        self._flareStartFS = flareStartFS

    def flareFinished(self, flareEnd, flareEndFS, tdRate):
        """Called when the flare time has ended.

        Return a tuple of the following items:
        - a boolean indicating if FS time is used
        - the flare time
        """
        self._tdRate = tdRate
        if self.flareTimeFromFS:
            return (True, flareEndFS - self._flareStartFS)
        else:
            return (False, flareEnd - self._flareStart)

    def wait(self):
        """Wait for the flight to end."""
        with self._endCondition:
            while self._stage!=const.STAGE_END:
                self._endCondition.wait(1)

    def getFleet(self, callback, force = False):
        """Get the fleet and call the given callback."""
        self._gui.getFleetAsync(callback = callback, force = force)

    def pilotHotkeyPressed(self):
        """Called when the pilot hotkey is pressed."""
        self._pilotHotkeyPressed = True

    def checklistHotkeyPressed(self):
        """Called when the checklist hotkey is pressed."""
        self._checklistHotkeyPressed = True

    def speedFromKnots(self, knots):
        """Convert the given speed value expressed in knots into the flight's
        speed unit."""
        return knots if self.speedInKnots else knots * const.KNOTSTOKMPH

    def aglFromFeet(self, feet):
        """Convert the given AGL altitude value expressed in feet into the
        flight's AGL altitude unit."""
        return feet if self.aglInFeet else feet * const.FEETTOMETRES

    def speedToKnots(self, speed):
        """Convert the given speed expressed in the flight's speed unit into
        knots."""
        return speed if self.speedInKnots else speed * const.KMPHTOKNOTS

    def getEnglishSpeedUnit(self):
        """Get the English name of the speed unit used by the flight."""
        return "knots" if self.speedInKnots else "km/h"

    def getEnglishAGLUnit(self):
        """Get the English name of the AGL unit used by the flight."""
        return "ft" if self.aglInFeet else "m"

    def getI18NSpeedUnit(self):
        """Get the speed unit suffix for i18n message identifiers."""
        return "_knots" if self.speedInKnots else "_kmph"

    def logFuel(self, aircraftState):
        """Log the amount of fuel"""
        fuelStr = ""
        for (tank, amount) in aircraftState.fuel:
            if fuelStr: fuelStr += " - "
            fuelStr += "%s=%.0f kg" % (const.fuelTank2logString(tank), amount)

        self.logger.message(aircraftState.timestamp, "Fuel: " + fuelStr)
        self.logger.message(aircraftState.timestamp,
                            "Total fuel: %.0f kg" % (aircraftState.totalFuel,))

    def cruiseLevelChanged(self):
        """Called when the cruise level hass changed."""
        if self.canLogCruiseAltitude(self._stage):
            message = "Cruise altitude modified to %d feet" % \
                      (self._gui.loggableCruiseAltitude,)
            self.logger.message(self.aircraft.timestamp, message)
            return True
        else:
            return False

    def _updateFlownDistance(self, currentState):
        """Update the flown distance."""
        if not currentState.onTheGround:
            updateData = False
            if self._lastDistanceTime is None or \
               self._previousLatitude is None or \
               self._previousLongitude is None:
                updateData = True
            elif currentState.timestamp >= (self._lastDistanceTime + 30.0):
                updateData = True
                self.flownDistance += self._getDistance(currentState)

            if updateData:
                self._previousLatitude = currentState.latitude
                self._previousLongitude = currentState.longitude
                self._lastDistanceTime = currentState.timestamp
        else:
            if self._lastDistanceTime is not None and \
               self._previousLatitude is not None and \
               self._previousLongitude is not None:
                self.flownDistance += self._getDistance(currentState)

            self._lastDistanceTime = None

    def _getDistance(self, currentState):
        """Get the distance between the previous and the current state."""
        return util.getDistCourse(self._previousLatitude, self._previousLongitude,
                                  currentState.latitude, currentState.longitude)[0]

    def _logStageDuration(self, timestamp, stage):
        """Log the duration of the stage preceding the given one."""
        what = None
        startTime = None

        if stage==const.STAGE_TAKEOFF:
            what = "Pushback and taxi"
            startTime = self.blockTimeStart
        elif stage==const.STAGE_CRUISE:
            what = "Climb"
            startTime = self.climbTimeStart
        elif stage==const.STAGE_DESCENT:
            what = "Cruise"
            startTime = self.cruiseTimeStart
        elif stage==const.STAGE_LANDING:
            what = "Descent"
            startTime = self.descentTimeStart
        elif stage==const.STAGE_END:
            what = "Taxi after landing"
            startTime = self.flightTimeEnd

        if what is not None and startTime is not None:
            duration = timestamp - startTime
            self.logger.message(timestamp,
                                "%s time: %s" % \
                                (what, util.getTimeIntervalString(duration)))

#---------------------------------------------------------------------------------------
