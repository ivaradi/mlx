
from .util import utf2unicode
from .flight import Flight
from .common import fixUnpickled

from . import const
import pickle as pickle
import calendar
import datetime
import time

#------------------------------------------------------------------------------

## @package mlx.pirep
#
# The PIREP module.
#
# This module defines only one class, \ref PIREP. It is used to extract and
# store the information needed for a PIREP. The saved PIREPs are pickled
# instances of this class.

#------------------------------------------------------------------------------

class PIREP(object):
    """A pilot's report of a flight."""
    class Message(object):
        """A message belonging to the PIREP."""
        @staticmethod
        def fromMessageData(messageData):
            """Construct a message from a JSON message data."""
            message = messageData["message"]
            senderPID = messageData["senderPID"]
            senderName = messageData["senderName"]

            return PIREP.Message(message, senderPID, senderName)

        def __init__(self, message, senderPID, senderName):
            """Construct the message object."""
            self.message = message
            self.senderPID = senderPID
            self.senderName = senderName

    _flightTypes = { const.FLIGHTTYPE_SCHEDULED : "SCHEDULED",
                     const.FLIGHTTYPE_OLDTIMER : "OT",
                     const.FLIGHTTYPE_VIP : "VIP",
                     const.FLIGHTTYPE_CHARTER : "CHARTER" }

    @staticmethod
    def _formatLine(timeStr, line):
        """Format the given time string and line as needed for the ACARS and
        some other things."""
        return "[" + timeStr + "]-[" + line + "]"

    @staticmethod
    def formatTimestampForRPC(t):
        """Format the given timestamp for RPC."""
        return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(t))

    @staticmethod
    def parseTimestampFromRPC(s):
        """Format the given timestamp for RPC."""
        dt = datetime.datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
        return calendar.timegm(dt.utctimetuple())

    @staticmethod
    def decodeFlightTypeText(s):
        """Decode the given flight type text."""
        for (flighType, text) in PIREP._flightTypes.items():
            if s==text:
                return flighType
        return const.FLIGHTTYPE_SCHEDULED

    @staticmethod
    def parseLogFromRPC(log):
        """Parse the given log coming from the RPC."""
        index = 0
        entries = []

        inTimeStr = False
        inEntry = False

        timestr = ""
        entry = ""

        while index<len(log):
            c = log[index]
            index += 1

            if c==']':
                if inEntry:
                    entries.append((timestr, entry))
                    timestr = ""
                    entry = ""

                inTimeStr = False
                inEntry = False
            elif not inTimeStr and not inEntry:
                if c=='[':
                    if timestr:
                        inEntry = True
                    else:
                        inTimeStr = True
            elif inTimeStr:
                timestr += c
            elif inEntry:
                entry += c

        return entries

    @staticmethod
    def load(path):
        """Load a PIREP from the given path.

        Returns the PIREP object, or None on error."""
        try:
            with open(path, "rb") as f:
                pirep = pickle.load(f, fix_imports = True, encoding = "bytes")
                if "numCrew" not in dir(pirep):
                    pirep.numCrew = pirep.bookedFlight.numCrew
                if "numPassengers" not in dir(pirep):
                    pirep.numPassengers = pirep.bookedFlight.numPassengers
                if "bagWeight" not in dir(pirep):
                    pirep.bagWeight = pirep.bookedFlight.bagWeight
                if "mailWeight" not in dir(pirep):
                    pirep.mailWeight = pirep.bookedFlight.mailWeight
                return pirep
        except Exception as e:
            print("Failed loading PIREP from %s: %s" % (path,
                                                        utf2unicode(str(e))))
            return None

    def __init__(self, flight):
        """Initialize the PIREP from the given flight."""
        if flight is None:
            return

        self.bookedFlight = flight.bookedFlight

        self.numCrew = flight.numCrew
        self.numPassengers = flight.numPassengers
        self.bagWeight = flight.bagWeight
        self.cargoWeight = flight.cargoWeight
        self.mailWeight = flight.mailWeight

        self.filedCruiseAltitude = flight.filedCruiseAltitude
        self.cruiseAltitude = flight.cruiseAltitude
        self.route = flight.route

        self.departureMETAR = flight.departureMETAR.upper()
        self.arrivalMETAR = flight.arrivalMETAR.upper()

        self.departureRunway = flight.departureRunway.upper()
        self.sid = flight.sid.upper()

        self.star = flight.star
        self.transition = flight.transition
        self.approachType = flight.approachType.upper()
        self.arrivalRunway = flight.arrivalRunway.upper()

        self.flightType = flight.flightType
        self.online = flight.online

        self.comments = flight.comments
        self.flightDefects = flight.flightDefects
        self.delayCodes = flight.delayCodes

        self.blockTimeStart = flight.blockTimeStart
        self.flightTimeStart = flight.flightTimeStart
        self.flightTimeEnd = flight.flightTimeEnd
        self.blockTimeEnd = flight.blockTimeEnd
        self.flownDistance = flight.flownDistance
        self.fuelUsed = flight.startFuel - flight.endFuel

        logger = flight.logger
        self.rating = logger.getRating()
        self.logLines = logger.lines
        self.faultLineIndexes = logger.faultLineIndexes

        self.messages = []

    def setupFromPIREPData(self, pirepData, bookedFlight):

        self.bookedFlight = bookedFlight

        self.numCrew = int(pirepData["numCrew"])
        self.numPassengers = int(pirepData["numPassengers"])
        self.bagWeight = int(pirepData["bagWeight"])
        self.cargoWeight = int(pirepData["cargoWeight"])
        self.mailWeight = int(pirepData["mailWeight"])

        filedCruiseLevel = pirepData["filedCruiseLevel"].strip()
        if filedCruiseLevel:
            if filedCruiseLevel.startswith("FL"):
                filedCruiseLevel = filedCruiseLevel[2:]
        if filedCruiseLevel:
            self.filedCruiseAltitude = int(filedCruiseLevel)*100
        else:
            self.filedCruiseAltitude = 10000;

        cruiseLevel = pirepData["cruiseLevel"].strip()
        if cruiseLevel:
            if cruiseLevel.startswith("FL"):
                cruiseLevel = cruiseLevel[2:]
        if cruiseLevel:
            self.cruiseAltitude = int(cruiseLevel[2:])*100
        else:
            self.cruiseAltitude = self.filedCruiseAltitude
        self.route = pirepData["route"]

        self.departureMETAR = pirepData["departureMETAR"]
        self.arrivalMETAR = pirepData["arrivalMETAR"]

        self.departureRunway = pirepData["departureRunway"]
        self.sid = pirepData["sid"]

        star = pirepData["star"].split(",")
        self.star = star[0]
        self.star.strip()

        if len(star)>1:
            self.transition = star[1]
            self.transition.strip()
        else:
            self.transition = ""
        self.approachType = pirepData["approachType"]
        self.arrivalRunway = pirepData["arrivalRunway"]

        self.flightType = PIREP.decodeFlightTypeText(pirepData["flightType"])
        self.online = int(pirepData["online"])!=0

        self.comments = pirepData["comments"]
        self.flightDefects = pirepData["flightDefects"]
        self.delayCodes = pirepData["timeComment"]
        if self.delayCodes=="UTC":
            self.delayCodes = []
        else:
            self.delayCodes = self.delayCodes.split(", ")

        flightDate = pirepData["flightDate"] + " "

        self.blockTimeStart = \
          PIREP.parseTimestampFromRPC(flightDate + pirepData["blockTimeStart"])
        self.flightTimeStart = \
          PIREP.parseTimestampFromRPC(flightDate + pirepData["flightTimeStart"])
        self.flightTimeEnd = \
          PIREP.parseTimestampFromRPC(flightDate + pirepData["flightTimeEnd"])
        self.blockTimeEnd = \
          PIREP.parseTimestampFromRPC(flightDate + pirepData["blockTimeEnd"])
        self.flownDistance = float(pirepData["flownDistance"])
        self.fuelUsed = float(pirepData["fuelUsed"])

        # logger = flight.logger
        self.rating = float(pirepData["rating"])

        log = pirepData["log"]

        self.logLines = PIREP.parseLogFromRPC(log)[1:]
        if self.logLines and \
           (self.logLines[0][0]=="LOGGER NG LOG" or
            self.logLines[0][0]=="MAVA LOGGER X"):
            self.logLines = self.logLines[1:]
        numLogLines = len(self.logLines)

        lastFaultLineIndex = 0
        self.faultLineIndexes = []
        for ratingText in pirepData["ratingText"].splitlines()[:-1]:
            faultLines = PIREP.parseLogFromRPC(ratingText)
            for (timeStr, entry) in faultLines:
                for i in range(lastFaultLineIndex, numLogLines-1):
                    if timeStr>=self.logLines[i][0] and \
                       timeStr<self.logLines[i+1][0]:
                        self.logLines = self.logLines[:i+1] + \
                          [(timeStr, entry)] + self.logLines[i+1:]
                        self.faultLineIndexes.append(i+1)
                        lastFaultLineIndex = i+1
                        numLogLines += 1
                        break

        self.messages = []
        for messageData in pirepData["messages"]:
            self.messages.append(PIREP.Message.fromMessageData(messageData))

    @property
    def flightDateText(self):
        """Get the text version of the booked flight's departure time."""
        return self.bookedFlight.departureTime.strftime("%Y-%m-%d")

    @property
    def flightTypeText(self):
        """Get the text representation of the flight type."""
        return PIREP._flightTypes[self.flightType]

    @property
    def blockTimeStartText(self):
        """Get the beginning of the block time in string format."""
        return PIREP.formatTimestampForRPC(self.blockTimeStart)

    @property
    def flightTimeStartText(self):
        """Get the beginning of the flight time in string format."""
        return PIREP.formatTimestampForRPC(self.flightTimeStart)

    @property
    def flightTimeEndText(self):
        """Get the end of the flight time in string format."""
        return PIREP.formatTimestampForRPC(self.flightTimeEnd)

    @property
    def blockTimeEndText(self):
        """Get the end of the block time in string format."""
        return PIREP.formatTimestampForRPC(self.blockTimeEnd)

    def getACARSText(self):
        """Get the ACARS text.

        This is a specially formatted version of the log without the faults."""
        text = "[MAVA LOGGER X LOG]-[%s]" % (const.VERSION,)
        for index in range(0, len(self.logLines)):
            if index not in self.faultLineIndexes:
                (timeStr, line) = self.logLines[index]
                if timeStr is not None:
                    text += PIREP._formatLine(timeStr, line)
        return text

    def getRatingText(self):
        """Get the rating text.

        This is a specially formatted version of the lines containing the
        faults."""
        text = ""
        for index in self.faultLineIndexes:
            (timeStr, line) = self.logLines[index]
            if timeStr is not None:
                text += PIREP._formatLine(timeStr, line)
                text += "\n"

        text += "\n[Flight Rating: %.1f]" % (max(0.0, self.rating),)

        return text

    def getTimeComment(self):
        """Get the time comment.

        This is basically a collection of the delay codes, if any."""
        if not self.delayCodes:
            return "UTC"
        else:
            s = ""
            for code in self.delayCodes:
                if s: s += ", "
                s += code
            return s

    def getSTAR(self):
        """Get the STAR and/or the transition."""
        star = self.star if self.star is not None else ""
        if self.transition is not None:
            if star: star += ", "
            star += self.transition
        return star.upper()

    def save(self, path):
        """Save the PIREP to the given file.

        Returns whether the saving has succeeded."""
        try:
            with open(path, "wb") as f:
                pickle.dump(self, f)
            return None
        except Exception as e:
            error = utf2unicode(str(e))
            print("Failed saving PIREP to %s: %s" % (path, error))
            return error

    def _serialize(self):
        """Serialize the PIREP for JSON-RPC."""
        attrs = {}
        attrs["log"] = self.getACARSText()
        attrs["flightDate"] = self.flightDateText
        attrs["callsign"] = self.bookedFlight.callsign
        attrs["departureICAO"] = self.bookedFlight.departureICAO
        attrs["arrivalICAO"] = self.bookedFlight.arrivalICAO
        attrs["numPassengers"] = self.numPassengers
        attrs["numCrew"] = self.numCrew
        attrs["cargoWeight"] = self.cargoWeight
        attrs["bagWeight"] = self.bagWeight
        attrs["mailWeight"] = self.mailWeight
        attrs["flightType"] = self.flightTypeText
        attrs["online"] = 1 if self.online else 0
        attrs["blockTimeStart"] = self.blockTimeStartText
        attrs["blockTimeEnd"] = self.blockTimeEndText
        attrs["flightTimeStart"] = self.flightTimeStartText
        attrs["flightTimeEnd"] = self.flightTimeEndText
        attrs["timeComment"] = self.getTimeComment()
        attrs["fuelUsed"] = self.fuelUsed
        attrs["departureRunway"] = self.departureRunway
        attrs["arrivalRunway"] = self.arrivalRunway
        attrs["departureMETAR"] = self.departureMETAR
        attrs["arrivalMETAR"] = self.arrivalMETAR
        attrs["filedCruiseLevel"] = self.filedCruiseAltitude / 100.0
        attrs["cruiseLevel"] = self.cruiseAltitude / 100.0
        attrs["sid"] = self.sid
        attrs["route"] = self.route
        attrs["star"] = self.star
        attrs["approachType"] = self.approachType
        attrs["comments"] = self.comments
        attrs["flightDefects"] = self.flightDefects
        attrs["ratingText"] = self.getRatingText()
        attrs["rating"] = max(0.0, self.rating)
        attrs["flownDistance"] = "%.2f" % (self.flownDistance,)
        # FIXME: it should be stored in the PIREP when it is sent later
        attrs["performDate"] = datetime.date.today().strftime("%Y-%m-%d")

        return ([], attrs)

    def __setstate__(self, state):
        """Set the state from the given unpickled dictionary."""
        self.__dict__.update(fixUnpickled(state))
