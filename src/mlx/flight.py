# Module related to the high-level tracking of the flight

#---------------------------------------------------------------------------------------

from soundsched import SoundScheduler, ChecklistScheduler

import const
import util

import threading

#---------------------------------------------------------------------------------------

class Options(object):
    """Various configuration options."""
    def __init__(self):
        """Construct the object with default values."""
        self.fs2Crew = False
        self.compensation = None        

#---------------------------------------------------------------------------------------

class Flight(object):
    """The object with the global flight state.
    
    It is also the hub for the other main objects participating in the handling of
    the flight."""
    def __init__(self, logger, gui):
        """Construct the flight."""
        self._stage = None
        self.logger = logger
        self._gui = gui

        gui.resetFlightStatus()

        self._pilotHotkeyPressed = False
        self._checklistHotkeyPressed = False

        self.flareTimeFromFS = False
        self.entranceExam = False

        self.options = Options()

        self.aircraftType = None
        self.aircraft = None
        self.simulator = None

        self.blockTimeStart = None
        self.flightTimeStart = None
        self.flightTimeEnd = None
        self.blockTimeEnd = None

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

    @property
    def config(self):
        """Get the configuration."""
        return self._gui.config

    @property
    def stage(self):
        """Get the flight stage."""
        return self._stage

    @property
    def bookedFlight(self):
        """Get the booked flight."""
        return self._gui.bookedFlight

    @property
    def zfw(self):
        """Get the Zero-Fuel Weight of the flight."""
        return self._gui.zfw

    @property
    def cruiseAltitude(self):
        """Get the cruise altitude of the flight."""
        return self._gui.cruiseAltitude

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
    def vref(self):
        """Get the VRef speed of the flight."""
        return self._gui.vref

    @property
    def tdRate(self):
        """Get the touchdown rate if known, None otherwise."""
        return self._tdRate

    def handleState(self, oldState, currentState):
        """Handle a new state information."""
        self._updateFlownDistance(currentState)
        
        self.endFuel = sum(currentState.fuel)
        if self.startFuel is None:
            self.startFuel = self.endFuel
        
        self._soundScheduler.schedule(currentState,
                                      self._pilotHotkeyPressed)
        self._pilotHotkeyPressed = False

        if self._checklistHotkeyPressed:
            self._checklistScheduler.hotkeyPressed()
            self._checklistHotkeyPressed = False

    def setStage(self, timestamp, stage):
        """Set the flight stage.

        Returns if the stage has really changed."""
        if stage!=self._stage:
            self._stage = stage
            self._gui.setStage(stage)
            self.logger.stage(timestamp, stage)
            if stage==const.STAGE_PUSHANDTAXI:
                self.blockTimeStart = timestamp
            elif stage==const.STAGE_TAKEOFF:
                self.flightTimeStart = timestamp
            elif stage==const.STAGE_TAXIAFTERLAND:
                self.flightTimeEnd = timestamp
            elif stage==const.STAGE_PARKING:
                self.blockTimeEnd = timestamp
            elif stage==const.STAGE_END:
                with self._endCondition:
                    self._endCondition.notify()
            return True
        else:
            return False

    def handleFault(self, faultID, timestamp, what, score):
        """Handle the given fault.

        faultID as a unique ID for the given kind of fault. If another fault of
        this ID has been reported earlier, it will be reported again only if
        the score is greater than last time. This ID can be, e.g. the checker
        the report comes from."""
        self.logger.fault(faultID, timestamp, what, score)
        self._gui.setRating(self.logger.getRating())

    def handleNoGo(self, faultID, timestamp, what, shortReason):
        """Handle a No-Go fault."""
        self.logger.noGo(faultID, timestamp, what)
        self._gui.setNoGo(shortReason)

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

#---------------------------------------------------------------------------------------
