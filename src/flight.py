# Module related to the high-level tracking of the flight

#---------------------------------------------------------------------------------------

import const

import threading

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
        self.aircraftType = None
        self.aircraft = None
        self.simulator = None

        self._endCondition = threading.Condition()

    @property
    def stage(self):
        """Get the flight stage."""
        return self._stage

    def setStage(self, timestamp, stage):
        """Set the flight stage."""
        if stage!=self._stage:
            self._stage = stage
            self.logger.stage(timestamp, stage)
            if stage==const.STAGE_END:
                with self._endCondition:
                    self._endCondition.notify()

    def wait(self):
        """Wait for the flight to end."""
        with self._endCondition:
            while self._stage!=const.STAGE_END:
                self._endCondition.wait()

#---------------------------------------------------------------------------------------
