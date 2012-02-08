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
    def __init__(self, logger):
        """Construct the flight."""
        self._stage = None
        self.logger = logger

        self.cruiseAltitude = None
        self.flareTimeFromFS = False
        self.entranceExam = False
        self.zfw = 50000

        self.options = Options()

        self.aircraftType = None
        self.aircraft = None
        self.simulator = None

        self._endCondition = threading.Condition()

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
            if stage==const.STAGE_END:
                with self._endCondition:
                    self._endCondition.notify()
            return True
        else:
            return False

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
                self._endCondition.wait()

#---------------------------------------------------------------------------------------
