
from util import utf2unicode

import const
import cPickle as pickle

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
    @staticmethod
    def _formatLine(timeStr, line):
        """Format the given time string and line as needed for the ACARS and
        some other things."""
        return "[" + timeStr + "]-[" + line + "]"

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
