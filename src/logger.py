# Module for the logging.

#--------------------------------------------------------------------------------------

import const

import sys
import time

#--------------------------------------------------------------------------------------

class Logger(object):
    """The class with the interface to log the various events."""
    # FIXME: shall we use const.stage2string() instead?
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

    _noGoScore = 10000

    def __init__(self, output = sys.stdout):
        """Construct the logger."""
        self._faults = {}
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

    def untimedMessage(self, msg):
        """Put an untimed message into the log."""
        print >> self._output, msg
        print msg        

    def debug(self, msg):
        """Log a debug message."""
        print >> self._output, "[DEBUG]", msg
        print "[DEBUG]", msg

    def stage(self, timestamp, stage):
        """Report a change in the flight stage."""
        s = Logger._stages[stage] if stage in Logger._stages else "<Unknown>"
        self.message(timestamp, "--- %s ---" % (s,))
        
    def fault(self, faultID, timestamp, what, score):
        """Report a fault.

        faultID as a unique ID for the given kind of fault. If another fault of
        this ID has been reported earlier, it will be reported again only if
        the score is greater than last time. This ID can be, e.g. the checker
        the report comes from."""
        if faultID in self._faults:
            if score<=self._faults[faultID]:
                return
        self._faults[faultID] = score
        if score==Logger._noGoScore:
            self.message(timestamp, "%s (NO GO)" % (what))
        else:
            self.message(timestamp, "%s (%.1f)" % (what, score))

    def noGo(self, faultID, timestamp, what, shortReason):
        """Report a No-Go fault."""
        self.fault(faultID, timestamp, what, Logger._noGoScore)

#--------------------------------------------------------------------------------------
