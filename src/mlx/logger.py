# Module for the logging.

#--------------------------------------------------------------------------------------

from fs import sendMessage
import const
import util

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
    
    NO_GO_SCORE = 10000

    def __init__(self, output):
        """Construct the logger."""
        self._lines = []
        self._faults = {}
        self._faultLineIndexes = []
        self._output = output

    @property
    def lines(self):
        """Get the lines of the log."""
        return self._lines

    @property
    def faultLineIndexes(self):
        """Get the array of the indexes of the log line that contains a
        fault."""
        return self._faultLineIndexes

    def reset(self):
        """Reset the logger.

        The faults logged so far will be cleared."""
        self._lines = []
        self._faults.clear()
        self._faultLineIndexes = []
                
    def message(self, timestamp, msg):
        """Put a simple textual message into the log with the given timestamp."""
        timeStr = util.getTimestampString(timestamp)
        return self._logLine(msg, timeStr)

    def untimedMessage(self, msg):
        """Put an untimed message into the log."""
        return self._logLine(msg)

    def debug(self, msg):
        """Log a debug message."""
        print "[DEBUG]", msg

    def stage(self, timestamp, stage):
        """Report a change in the flight stage."""
        s = Logger._stages[stage] if stage in Logger._stages else "<Unknown>"
        self.message(timestamp, "--- %s ---" % (s,))
        if stage==const.STAGE_END:
            self.untimedMessage("Rating: %.0f" % (self.getRating(),))
        else:
            sendMessage(const.MESSAGETYPE_INFORMATION, "Flight stage: " + s, 3)
        
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
        text = "%s (NO GO)" % (what) if score==Logger.NO_GO_SCORE \
               else "%s (%.1f)" % (what, score)
        lineIndex = self.message(timestamp, text)
        self._faultLineIndexes.append(lineIndex)
        (messageType, duration) = (const.MESSAGETYPE_NOGO, 10) \
                                  if score==Logger.NO_GO_SCORE \
                                  else (const.MESSAGETYPE_FAULT, 5)
        sendMessage(messageType, text, duration)            

    def noGo(self, faultID, timestamp, what):
        """Report a No-Go fault."""
        self.fault(faultID, timestamp, what, Logger.NO_GO_SCORE)

    def getRating(self):
        """Get the rating of the flight so far."""
        totalScore = 100
        for (id, score) in self._faults.iteritems():
            if score==Logger.NO_GO_SCORE:
                return -score
            else:
                totalScore -= score
        return totalScore

    def updateLine(self, index, line):
        """Update the line at the given index with the given string."""
        (timeStr, _line) = self._lines[index]
        self._lines[index] = (timeStr, line)
        self._output.updateFlightLogLine(index, timeStr, line)

    def _logLine(self, line, timeStr = None):
        """Log the given line."""
        index = len(self._lines)
        self._lines.append((timeStr, line))
        self._output.addFlightLogLine(timeStr, line)
        return index
        
#--------------------------------------------------------------------------------------
