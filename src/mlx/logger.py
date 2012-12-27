
from fs import sendMessage
import const
import util

import sys
import time
import bisect

#--------------------------------------------------------------------------------------

## @package mlx.logger
#
# The module for the logger.
#
# While the program itself is "logger", it contains an internal logger, which
# maintains the textual log containing information on the various events and is
# the reason why the program is called "logger".
#
# The log is made up of lines containing an optional timestamp and the text of
# the message. A line can be updated after having been put into the log by
# referring to its index.
#
# The logger object also maintains a separate set of faults and ensures that
# one fault type has only one score, even if that fault has been reported
# multiple times.

#--------------------------------------------------------------------------------------

class Logger(object):
    """The class with the interface to log the various events.

    It contains a list of entries ordered by their timestamps and their ever
    increasing IDs."""

    class Entry(object):
        """An entry in the log."""

        # The ID of the next entry to be created
        _nextID = 1

        def __init__(self, timestamp, text, showTimestamp = True,
                     faultID = None, faultScore = 0, id = None):
            """Construct the entry."""
            if id is None:
                self._id = self._nextID
                Logger.Entry._nextID += 1
            else:
                self._id = id

            self._timestamp = timestamp
            self._text = text
            self._showTimestamp = showTimestamp

            self._faultID = faultID
            self._faultScore = faultScore

        @property
        def id(self):
            """Get the ID of the entry."""
            return self._id

        @property
        def timestamp(self):
            """Get the timestamp of this entry."""
            return self._timestamp

        @property
        def timestampString(self):
            """Get the timestamp string of this entry.

            It returns None, if the timestamp of the entry is not visible."""
            return util.getTimestampString(self._timestamp) \
                   if self._showTimestamp else None

        @property
        def text(self):
            """Get the text of this entry."""
            return self._text

        @property
        def isFault(self):
            """Determine if this is a log entry about a fault."""
            return self._faultID is not None

        @property
        def faultID(self):
            """Get the fault ID of the entry.

            It may be None, if the entry is not a fault entry."""
            return self._faultID

        @property
        def faultScore(self):
            """Get the fault score of the entry, if it is a fault."""
            return self._faultScore

        def copy(self, timestamp = None, clearTimestamp = False, text = None,
                 faultID = None, faultScore = None, clearFault = False):
            """Create a copy of this entry with the given values changed."""
            return Logger.Entry(None if clearTimestamp
                                else self._timestamp if timestamp is None
                                else timestamp,

                                self._text if text is None else text,

                                showTimestamp = self._showTimestamp,

                                faultID =
                                None if clearFault
                                else self._faultID if faultID is None
                                else faultID,

                                faultScore =
                                None if clearFault
                                else self._faultScore if faultScore is None
                                else faultScore,

                                id = self._id)

        def __cmp__(self, other):
            """Compare two entries

            First their timestamps are compared, and if those are equal, then
            their IDs."""
            result = cmp(self._timestamp, other.timestamp)
            if result==0:
                result = cmp(self._id, other._id)
            return result

    class Fault(object):
        """Information about a fault.

        It contains the list of log entries that belong to this fault. The list
        is ordered so that the first element contains the entry with the
        highest score, so that it should be easy to find the actual score."""
        def __init__(self, entry):
            """Construct the fault info with the given log entry as its only
            one."""
            self._entries = [entry]

        @property
        def score(self):
            """Get the score of this fault, i.e. the score of the entry with
            the highest score."""
            return self._entries[0].faultScore if self._entries else 0

        def addEntry(self, entry):
            """Add an entry to this fault.

            The entries will be sorted."""
            entries = self._entries
            entries.append(entry)
            entries.sort(key = lambda entry: entry.faultScore, reverse = True)

        def removeEntry(self, entry):
            """Remove the given entry.

            Returns True if at least one entry remains, False otherwise."""
            entries = self._entries
            for index in range(0, len(entries)):
                if entry is entries[index]:
                    del entries[index]
                    break

            return len(entries)>0

        def getLatestEntry(self):
            """Get the entry with the highest score."""
            return self._entries[0]

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
        self._entries = {}
        self._lines = []

        self._faults = {}

        self._output = output

    @property
    def lines(self):
        """Get the lines of the log."""
        return [(entry.timestampString, entry.text) for entry in self._lines]

    @property
    def faultLineIndexes(self):
        """Get the sorted array of the indexes of those log lines that contain
        a fault."""
        faultLineIndexes = []
        lines = self._lines
        for index in range(0, len(lines)):
            if lines[index].isFault:
                faultLineIndexes.append(index)
        return faultLineIndexes

    def reset(self):
        """Reset the logger.

        The faults logged so far will be cleared."""
        self._entries = {}
        self._lines = []
        self._faults = {}

    def message(self, timestamp, msg):
        """Put a simple textual message into the log with the given timestamp.

        Returns an ID of the message so that it could be referred to later."""
        return self._addEntry(Logger.Entry(timestamp, msg))

    def untimedMessage(self, msg):
        """Put an untimed message into the log."""
        timestamp = self._lines[-1].timestamp if self._lines else 0
        return self._addEntry(Logger.Entry(timestamp, msg,
                                           showTimestamp = False))

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
            messageType = \
               const.MESSAGETYPE_INFLIGHT  if stage in \
               [const.STAGE_CLIMB, const.STAGE_CRUISE, \
                const.STAGE_DESCENT, const.STAGE_LANDING] \
                else const.MESSAGETYPE_INFORMATION
            sendMessage(messageType, "Flight stage: " + s, 3)

    def fault(self, faultID, timestamp, what, score,
              updatePrevious = False, updateID = None):
        """Report a fault.

        faultID as a unique ID for the given kind of fault. If another fault of
        this ID has been reported earlier, it will be reported again only if
        the score is greater than last time. This ID can be, e.g. the checker
        the report comes from.

        If updatePrevious is True, and an instance of the given fault is
        already in the log, only that instance will be updated with the new
        timestamp and score. If there are several instances, the latest one
        (with the highest score) will be updated. If updatePrevious is True,
        and the new score is not greater than the latest one, the ID of the
        latest one is returned.

        If updateID is given, the log entry with the given ID will be
        'upgraded' to be a fault with the given data.

        Returns an ID of the fault, or -1 if it was not logged."""
        fault = self._faults[faultID] if faultID in self._faults else None

        if fault is not None and score<=fault.score:
            return fault.getLatestEntry().id if updatePrevious else -1

        text = "%s (NO GO)" % (what) if score==Logger.NO_GO_SCORE \
               else "%s (%.1f)" % (what, score)

        if updatePrevious and fault is not None:
            latestEntry = fault.getLatestEntry()
            id = latestEntry.id
            newEntry = latestEntry.copy(timestamp = timestamp,
                                        text = text,
                                        faultScore = score)
            self._updateEntry(id, newEntry)
        elif updateID is not None:
            id = updateID
            newEntry = self._entries[id].copy(timestamp = timestamp,
                                              text = text, faultID = faultID,
                                              faultScore = score)
            self._updateEntry(id, newEntry)
        else:
            id = self._addEntry(Logger.Entry(timestamp, text, faultID = faultID,
                                             faultScore = score))

        if updateID is None:
            (messageType, duration) = (const.MESSAGETYPE_NOGO, 10) \
                                      if score==Logger.NO_GO_SCORE \
                                      else (const.MESSAGETYPE_FAULT, 5)
            sendMessage(messageType, text, duration)

        return id

    def noGo(self, faultID, timestamp, what):
        """Report a No-Go fault."""
        return self.fault(faultID, timestamp, what, Logger.NO_GO_SCORE)

    def getRating(self):
        """Get the rating of the flight so far."""
        totalScore = 100
        for fault in self._faults.itervalues():
            score = fault.score
            if score==Logger.NO_GO_SCORE:
                return -score
            else:
                totalScore -= score
        return totalScore

    def updateLine(self, id, line):
        """Update the line with the given ID with the given string.

        Note, that it does not change the status of the line as a fault!"""
        self._updateEntry(id, self._entries[id].copy(text = line))

    def clearFault(self, id, text):
        """Update the line with the given ID to contain the given string,
        and clear its fault state."""
        newEntry = self._entries[id].copy(text = text, clearFault = True)
        self._updateEntry(id, newEntry)

    def _addEntry(self, entry):
        """Add the given entry to the log.

        @return the ID of the new entry."""
        assert entry.id not in self._entries

        self._entries[entry.id] = entry

        if not self._lines or entry>self._lines[-1]:
            index = len(self._lines)
            self._lines.append(entry)
        else:
            index = bisect.bisect_left(self._lines, entry)
            self._lines.insert(index, entry)

        if entry.isFault:
            self._addFault(entry)

        self._output.insertFlightLogLine(index, entry.timestampString,
                                         entry.text, entry.isFault)

        return entry.id

    def _updateEntry(self, id, newEntry):
        """Update the entry with the given ID from the given new entry."""
        self._removeEntry(id)
        self._addEntry(newEntry)

    def _removeEntry(self, id):
        """Remove the entry with the given ID."""
        assert id in self._entries

        entry = self._entries[id]
        del self._entries[id]

        for index in range(len(self._lines)-1, -1, -1):
            if self._lines[index] is entry:
                break
        del self._lines[index]

        if entry.isFault:
            faultID = entry.faultID
            fault = self._faults[faultID]
            if not fault.removeEntry(entry):
                del self._faults[faultID]

        self._output.removeFlightLogLine(index)

    def _addFault(self, entry):
        """Add the given fault entry to the fault with the given ID."""
        faultID = entry.faultID
        if faultID in self._faults:
            self._faults[faultID].addEntry(entry)
        else:
            self._faults[faultID] = Logger.Fault(entry)

#--------------------------------------------------------------------------------------
