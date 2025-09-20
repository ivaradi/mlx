
from . import const

#------------------------------------------------------------------------------

## @package mlx.acars
#
# The handling of the ACARS.
#
# This module defines the \ref mlx.acars.ACARS "ACARS" class that is used
# to extract and contain the data needed to send ACARS information to the
# MAVA server.

#------------------------------------------------------------------------------

class ACARS(object):
    """The ACARS object."""
    def __init__(self, gui, state):
        """Construct the acars."""
        self.pid = gui.config.pilotID
        self.pilotName = gui.loginResult.pilotName

        self._gui = gui
        flight = gui.flight
        aircraft = flight.aircraft

        self.state = state
        self.bookedFlight = gui.bookedFlight

        self.blockTime = 0 if flight.blockTimeStart is None \
                         else aircraft.state.timestamp - flight.blockTimeStart
        self.stage = flight.stage

    def getBlockTimeText(self):
        """Get the block time in HH:MM format"""
        hours = int(self.blockTime / 3600)
        minutes = int((self.blockTime / 60)) % 60
        return "%02d:%02d" % (hours, minutes)

    def getEventText(self):
        """Get the 'event', i.e. the stage."""
        if self.stage==const.STAGE_BOARDING: return "Boarding"
        elif self.stage==const.STAGE_PUSHANDTAXI: return "Taxiing"
        elif self.stage==const.STAGE_TAKEOFF: return "Departing"
        elif self.stage==const.STAGE_CLIMB: return "Climbing"
        elif self.stage==const.STAGE_CRUISE: return "Cruising"
        elif self.stage==const.STAGE_DESCENT:
            return "Descending" if self.state.altitude>=10000 \
                   else "Approaching"
        else:
            return "Landed"

    def _serialize(self):
        """Serialize the ACARS object for JSON-RPC."""
        bookedFlight = self.bookedFlight
        state = self.state

        attrs = {}
        attrs["longitude"] = state.longitude
        attrs["latitude"] = state.latitude
        attrs["pilotName"] = self.pilotName
        attrs["numPassengers"] = \
            self._gui.numPassengers + \
            self._gui.numChildren + \
            self._gui.numInfants
        attrs["blockTime"] = self.getBlockTimeText()
        attrs["callsign"] = bookedFlight.callsign
        attrs["aircraftTypeName"] = bookedFlight.aircraftTypeName
        attrs["departureICAO"] = bookedFlight.departureICAO
        attrs["arrivalICAO"] = bookedFlight.arrivalICAO
        attrs["altitude"] = state.altitude
        attrs["groundSpeed"] = state.groundSpeed
        attrs["event"] = self.getEventText()
        attrs["tailNumber"] = bookedFlight.tailNumber

        return ([], attrs)

#------------------------------------------------------------------------------
