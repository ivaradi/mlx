# Module for the logging.

#--------------------------------------------------------------------------------------

import const

import sys
import time

#--------------------------------------------------------------------------------------

class Logger(object):
    """The class with the interface to log the various events."""
    _stages = { const.STAGE_BOARDING : "Boarding",
                const.STAGE_PUSHANDTAXI : "Pushback and Taxi",
                const.STAGE_TAKEOFF : "Takeoff",
                const.STAGE_RTO : "RTO",
                const.STAGE_CLIMB : "Climb",
                const.STAGE_CRUISE : "Cruise",
                const.STAGE_DESCENT : "Descent",
                const.STAGE_LANDING : "Landing",
                const.STAGE_TAXIAFTERLAND : "Taxi",
                const.STAGE_PARKING : "Parking",
                const.STAGE_GOAROUND : "Go-Around",
                const.STAGE_END : "End" }

    def __init__(self, output = sys.stdout):
        """Construct the logger."""
        self._score = 100.0
        self._output = output

    @staticmethod
    def _getTimeStr(timestamp):
        """Get the string representation of the given timestamp."""
        return time.strftime("%H:%M:%S", time.gmtime(timestamp))
                
    def message(self, timestamp, msg):
        """Put a simple textual message into the log with the given timestamp."""
        timeStr = Logger._getTimeStr(timestamp)
        print >> self._output, timeStr + ":", msg
        print timeStr + ":", msg        

    def debug(self, timestamp, msg):
        """Log a debug message."""
        timeStr = Logger._getTimeStr(timestamp)
        print >> self._output, timeStr + ": [DEBUG] ", msg
        print timeStr + ": [DEBUG]", msg        

    def stage(self, timestamp, stage):
        """Report a change in the flight stage."""
        s = Logger._stages[stage] if stage in Logger._stages else "<Unknown>"
        self.message(timestamp, "--- %s ---" % (s,))
        
    def fault(self, timestamp, what, score):
        """Report a fault."""
        self._score -= score
        self.message(timestamp, "%s (%f)" % (what, score))

    def noGo(self, timestamp, what):
        """Report a No-Go fault."""
        self._score = -1
        self.message(timestamp, "%s (NO GO)" % (what,))

#--------------------------------------------------------------------------------------
