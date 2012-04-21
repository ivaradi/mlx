# The PIREP class collecting all information needed for a PIREP

#------------------------------------------------------------------------------

import const

#------------------------------------------------------------------------------

class PIREP(object):
    """A pilot's report of a flight."""
    _delayCodeNames = { const.DELAYCODE_LOADING : "Loading Problems",
                        const.DELAYCODE_NETWORK : "Net Problems",
                        const.DELAYCODE_SYSTEM : "System Crash/Freezing",
                        const.DELAYCODE_TRAFFIC : "Traffic Problems",
                        const.DELAYCODE_WEATHER : "Weather Problems",
                        const.DELAYCODE_VATSIM : "VATSIM Problem",
                        const.DELAYCODE_CONTROLLER : "Controller's Fault",
                        const.DELAYCODE_NAVIGATION : "Navigation Problem",
                        const.DELAYCODE_APRON : "Apron Navigation Problems",
                        const.DELAYCODE_PERSONAL : "Personal Reasons" }

    @staticmethod
    def _formatLine(timeStr, line):
        """Format the given time string and line as needed for the ACARS and
        some other things."""
        return "[" + timeStr + "]-[" + line + "]"
        
    def __init__(self, gui):
        """Initialize the PIREP from the given GUI."""
        self.bookedFlight = gui.bookedFlight
        self.cargoWeight = gui.cargoWeight
        
        self.filedCruiseAltitude = gui.filedCruiseAltitude
        self.cruiseAltitude = gui.cruiseAltitude
        self.route = gui.route

        self.departureMETAR = gui.departureMETAR.upper()
        self.arrivalMETAR = gui.arrivalMETAR.upper()

        self.departureRunway = gui.departureRunway.upper()
        self.sid = gui.sid.upper()

        self.star = gui.star
        self.transition = gui.transition
        self.approachType = gui.approachType.upper()
        self.arrivalRunway = gui.arrivalRunway.upper()

        self.flightType = gui.flightType
        self.online = gui.online

        self.comments = gui.comments
        self.flightDefects = gui.flightDefects
        self.delayCodes = gui.delayCodes
        
        flight = gui.flight
        self.blockTimeStart = flight.blockTimeStart
        self.flightTimeStart = flight.flightTimeStart
        self.flightTimeEnd = flight.flightTimeEnd
        self.blockTimeEnd = flight.blockTimeEnd
        self.flownDistance = flight.flownDistance
        self.fuelUsed = flight.startFuel - flight.endFuel

        logger = gui.logger
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
                s += PIREP._delayCodeNames[code]
            return s

    def getSTAR(self):
        """Get the STAR and/or the transition."""
        star = self.star if self.star is not None else ""
        if self.transition is not None:
            if star: star += ", "
            star += self.transition
        return star.upper()
