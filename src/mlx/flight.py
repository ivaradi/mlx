# Module related to the high-level tracking of the flight

#---------------------------------------------------------------------------------------

import const

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

        self.cruiseAltitude = None
        self.flareTimeFromFS = False
        self.entranceExam = False
        self.zfw = None

        self.options = Options()

        self.aircraftType = None
        self.aircraft = None
        self.simulator = None

        self._endCondition = threading.Condition()

        self.v1 = None
        self.vr = None
        self.v2 = None

        self._flareStart = None
        self._flareStartFS = None

    @property
    def stage(self):
        """Get the flight stage."""
        return self._stage

    def setStage(self, timestamp, stage):
        """Set the flight stage.

        Returns if the stage has really changed."""
        if stage!=self._stage:
            self._stage = stage
            self.logger.stage(timestamp, stage)
            self._gui.setStage(stage)
            if stage==const.STAGE_END:
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

    def flareFinished(self, flareEnd, flareEndFS):
        """Called when the flare time has ended.
        
        Return a tuple of the following items:
        - a boolean indicating if FS time is used
        - the flare time
        """
        if self.flareTimeFromFS:
            return (True, flareEndFS - self._flareStartFS)
        else:
            return (False, flareEnd - self._flareStart)

    def wait(self):
        """Wait for the flight to end."""
        with self._endCondition:
            while self._stage!=const.STAGE_END:
                self._endCondition.wait(1)

#---------------------------------------------------------------------------------------
