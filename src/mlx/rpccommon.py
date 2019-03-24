# Some common objects for RPC communication

#------------------------------------------------------------------------------

from . import const

#------------------------------------------------------------------------------

class Plane(object):
    """Information about an airplane in the fleet."""
    @staticmethod
    def str2status(letter):
        """Convert the given letter into a plane status."""
        return const.PLANE_HOME if letter=="H" else \
               const.PLANE_AWAY if letter=="A" else \
               const.PLANE_PARKING if letter=="P" else \
               const.PLANE_UNKNOWN

    @staticmethod
    def status2str(status):
        """Convert the given status into the corresponding letter code."""
        return "H" if status==const.PLANE_HOME else \
               "A" if status==const.PLANE_AWAY else \
               "P" if status==const.PLANE_PARKING else ""

    def _setStatus(self, letter):
        """Set the status from the given letter."""
        self.status = Plane.str2status(letter)

    def __repr__(self):
        """Get the representation of the plane object."""
        s = "<Plane: %s %s" % (self.tailNumber,
                               "home" if self.status==const.PLANE_HOME else \
                               "away" if self.status==const.PLANE_AWAY else \
                               "parking" if self.status==const.PLANE_PARKING \
                               else "unknown")
        if self.gateNumber is not None:
            s += " (gate " + self.gateNumber + ")"
        s += ">"
        return s

#------------------------------------------------------------------------------

class Fleet(object):
    """Information about the whole fleet."""
    def __init__(self):
        """Construct the fleet information by reading the given file object."""
        self._planes = {}

    def isGateConflicting(self, plane):
        """Check if the gate of the given plane conflicts with another plane's
        position."""
        for p in self._planes.values():
            if p.tailNumber!=plane.tailNumber and \
               p.status==const.PLANE_HOME and \
               p.gateNumber==plane.gateNumber:
                return True

        return False

    def getOccupiedGateNumbers(self):
        """Get a set containing the numbers of the gates occupied by planes."""
        gateNumbers = set()
        for p in self._planes.values():
            if p.status==const.PLANE_HOME and p.gateNumber:
                gateNumbers.add(p.gateNumber)
        return gateNumbers

    def updatePlane(self, tailNumber, status, gateNumber = None):
        """Update the status of the given plane."""
        if tailNumber in self._planes:
            plane = self._planes[tailNumber]
            plane.status = status
            plane.gateNumber = gateNumber

    def _addPlane(self, plane):
        """Add the given plane to the fleet."""
        self._planes[plane.tailNumber] = plane

    def __iter__(self):
        """Get an iterator over the planes."""
        for plane in self._planes.values():
            yield plane

    def __getitem__(self, tailNumber):
        """Get the plane with the given tail number.

        If the plane is not in the fleet, None is returned."""
        return self._planes[tailNumber] if tailNumber in self._planes else None

    def __repr__(self):
        """Get the representation of the fleet object."""
        return self._planes.__repr__()
