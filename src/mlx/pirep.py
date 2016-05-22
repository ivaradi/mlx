
from util import utf2unicode

import const
import cPickle as pickle
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
    def load(path):
        """Load a PIREP from the given path.

        Returns the PIREP object, or None on error."""
        try:
            with open(path, "rb") as f:
                pirep = pickle.load(f)
                if "numCrew" not in dir(pirep):
                    pirep.numCrew = pirep.bookedFlight.numCrew
                if "numPassengers" not in dir(pirep):
                    pirep.numPassengers = pirep.bookedFlight.numPassengers
                if "bagWeight" not in dir(pirep):
                    pirep.bagWeight = pirep.bookedFlight.bagWeight
                if "mailWeight" not in dir(pirep):
                    pirep.mailWeight = pirep.bookedFlight.mailWeight
                return pirep
        except Exception, e:
            print "Failed loading PIREP from %s: %s" % (path,
                                                        utf2unicode(str(e)))
            return None

    def __init__(self, flight):
        """Initialize the PIREP from the given flight."""
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
        except Exception, e:
            error = utf2unicode(str(e))
            print u"Failed saving PIREP to %s: %s" % (path, error)
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
        attrs["flownDistance"] = self.flownDistance
        # FIXME: it should be stored in the PIREP when it is sent later
        attrs["performDate"] = datetime.date.today().strftime("%Y-%m-%d")

        return ([], attrs)
