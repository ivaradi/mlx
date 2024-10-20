#--------------------------------------------------------------------------------------

## @package mlx.gates
#
# The module to handle the LHBP gate information.
#

#--------------------------------------------------------------------------------------

class Gate(object):
    """Information about a gate."""
    @staticmethod
    def fromJSON(data):
        """Create the gate from the given JSON data."""
        return Gate(data["number"], data["terminal"],
                    data["type"],
                    maxSpan = data["maxSpan"],
                    maxLength = data["maxLength"])

    def __init__(self, number, terminal, type,
                 availableFn = None, taxiThrough = False,
                 maxSpan = 0.0, maxLength = 0.0):
        """Construct the gate with the given information.

        number is the gate's number as a string (as it can contain letters).
        terminal is the terminal the gate belongs to (not used currently).
        type is the gate's type: G for gate, S for stand.
        availableFn is a function that can determine if the gate is available based on
        the statuses of other gates. Its arguments are:
        - a collection of the gates, and
        - a set of occupied gate numbers."""
        self.number = number
        self.terminal = terminal
        self.type = type
        self._availableFn = availableFn
        self.taxiThrough = taxiThrough
        self.maxSpan = maxSpan
        self.maxLength = maxLength

    def isAvailable(self, plane, gates, occupiedGateNumbers):
        """Determine if this gate is available for the given plane and the
        given the set of gates and occupied gate numbers."""
        if self.number in occupiedGateNumbers:
            return False
        if self._availableFn is None or \
           self._availableFn(gates, occupiedGateNumbers):
            return plane is None or \
                ((self.maxSpan<0.1 or plane.wingSpan <= self.maxSpan) and
                 (self.maxLength<0.1 or plane.fuselageLength <= self.maxLength) and
                 (not plane.hasStairs or self.type!="G"))
        else:
            return False

    def toJSON(self):
        """Create a JSON representation of the gate."""
        data = {}
        for attributeName in ["number", "terminal", "type",
                              "maxSpan", "maxLength"]:
            data[attributeName] = getattr(self, attributeName)
        return data

#--------------------------------------------------------------------------------------

class Gates(object):
    """A collection of gates."""
    # Display info type: a gate (number)
    DISPLAY_GATE=1

    # Display info type: a space
    DISPLAY_SPACE=2

    # Display info type: a new column
    DISPLAY_NEW_COLUMN=3

    @staticmethod
    def fromJSON(data):
        """Create a gates object from the given JSON data."""
        gates = Gates()
        for gateData in data:
            gates.add(Gate.fromJSON(gateData))
        return gates

    def __init__(self):
        """Construct the gate collection."""
        self._gates = []
        self._displayInfos = []
        self._numColumns = 1
        self._numRows = 0
        self._numRowsInColumn = 0

    @property
    def gates(self):
        """Get an iterator over the gates."""
        return iter(self._gates)

    @property
    def displayInfos(self):
        """Get an iterator over the display info tuples.

        Each tuple consists of
        - a type (one of the DISPLAY_XXX constants), and
        - an additional data (the gate for DISPLAY_GATE, None for others)."""
        return iter(self._displayInfos)

    @property
    def numRows(self):
        """Get the number of rows."""
        return self._numRows

    @property
    def numColumns(self):
        """Get the number of columns."""
        return self._numColumns

    def add(self, gate):
        """Add a gate to the collection."""
        self._gates.append(gate)
        self._displayInfos.append((Gates.DISPLAY_GATE, gate))
        self._addRow()

    def find(self, gateNumber):
        """Find a gate by its number."""
        for gate in self._gates:
            if gate.number == gateNumber:
                return gate

    def addSpace(self):
        """Add a space between subsequent gates."""
        self._displayInfos.append((Gates.DISPLAY_SPACE, None))
        self._addRow()

    def addNewColumn(self):
        """Start a new column of gates."""
        self._displayInfos.append((Gates.DISPLAY_NEW_COLUMN, None))
        self._numRowsInColumn = 0
        self._numColumns += 1

    def merge(self, otherGates):
        """Merge the information from the given gate list (retrieved from the
        MAVA server) into this gate list."""
        for otherGate in otherGates.gates:
            gate = self.find(otherGate.number)
            if gate is None:
                print("Received data for gate %s, but it does not exist locally!" %
                      (otherGate.number,))
            else:
                if gate.terminal != otherGate.terminal:
                    print("The terminal for gate %s is received as: %s" %
                          (gate.number, otherGate.terminal))
                    gate.terminal = otherGate.terminal
                if gate.type != otherGate.type:
                    print("The type for gate %s is received as: %s" %
                          (gate.number, otherGate.type))
                    gate.type = otherGate.type

                gate.maxSpan = otherGate.maxSpan
                gate.maxLength = otherGate.maxLength

        for gate in self.gates:
            if gate.maxSpan==0.0 or gate.maxLength==0.0:
                    print("Gate %s has no maximal dimensions from the database" %
                          (gate.number,))

    def toJSON(self):
        """Convert the list of gates into a JSON data."""
        return [gate.toJSON() for gate in self._gates]

    def _addRow(self):
        """Add a new row."""
        self._numRowsInColumn += 1
        if self._numRowsInColumn > self._numRows:
            self._numRows = self._numRowsInColumn

#--------------------------------------------------------------------------------------

def availableIf(occupiedGateNumbers, othersAvailable = []):
    """Determine if a gate is available.

    othersAvailable is a list of numbers of gates, that must be available so
    that the one we are considering is available."""
    for otherNumber in othersAvailable:
        if otherNumber in occupiedGateNumbers:
            return False
    return True

#--------------------------------------------------------------------------------------

def getAvailableIf(othersAvailable = []):
    """Get a function that determines if a gate is available based on the
    statuses of other gates."""
    return lambda gates, occupiedGateNumbers: availableIf(occupiedGateNumbers,
                                                          othersAvailable =
                                                          othersAvailable)

#--------------------------------------------------------------------------------------

# The gates at LHBP
lhbpGates = Gates()

lhbpGates.add(Gate("R101", "1", "S", taxiThrough = True))
lhbpGates.add(Gate("R102", "1", "S"))
lhbpGates.add(Gate("R103", "1", "S"))
lhbpGates.add(Gate("R104", "1", "S",
                   availableFn = getAvailableIf(othersAvailable = ["R105"])))
lhbpGates.add(Gate("R105", "1", "S",
                   availableFn = getAvailableIf(othersAvailable = ["R104", "R106"])))
lhbpGates.add(Gate("R106", "1", "S",
                   availableFn = getAvailableIf(othersAvailable = ["R105", "R108"])))
lhbpGates.add(Gate("R107", "1", "S",
                   availableFn = getAvailableIf(othersAvailable = ["R108"])))
lhbpGates.add(Gate("R108", "1", "S",
                   availableFn = getAvailableIf(othersAvailable = ["R106", "R107"])))

lhbpGates.addSpace()
lhbpGates.add(Gate("R110", "1", "S",
                   availableFn = getAvailableIf(othersAvailable = ["R111"])))
lhbpGates.add(Gate("R111", "1", "S",
                   availableFn = getAvailableIf(othersAvailable = ["R110", "R112"])))
lhbpGates.add(Gate("R112", "1", "S",
                   availableFn = getAvailableIf(othersAvailable = ["R111"])))
lhbpGates.add(Gate("R113", "1", "S",
                   availableFn = getAvailableIf(othersAvailable = ["R112", "R114"])))
lhbpGates.add(Gate("R114", "1", "S",
                   availableFn = getAvailableIf(othersAvailable = ["R113"])))
lhbpGates.add(Gate("R115", "1", "S"))
lhbpGates.add(Gate("R116", "1", "S",
                   availableFn = getAvailableIf(othersAvailable = ["R117"]),
                   taxiThrough = True))
lhbpGates.add(Gate("R117", "1", "S",
                   availableFn = getAvailableIf(othersAvailable = ["R116", "R117A"])))
lhbpGates.add(Gate("R117A", "1", "S",
                   availableFn = getAvailableIf(othersAvailable = ["R116", "R117"])))
lhbpGates.addNewColumn()

lhbpGates.add(Gate("G150", "1", "S"))
lhbpGates.add(Gate("G151", "1", "S"))
lhbpGates.add(Gate("G152", "1", "S"))
lhbpGates.add(Gate("G153", "1", "S"))
lhbpGates.add(Gate("G154", "1", "S"))
lhbpGates.add(Gate("G155", "1", "S"))

lhbpGates.addSpace()
lhbpGates.add(Gate("G170", "1", "S", taxiThrough = True))
lhbpGates.add(Gate("G171", "1", "S", taxiThrough = True))
lhbpGates.add(Gate("G172", "1", "S", taxiThrough = True))
lhbpGates.addNewColumn()

lhbpGates.add(Gate("31", "2B", "G"))
lhbpGates.add(Gate("32", "2B", "G"))
lhbpGates.add(Gate("33", "2B", "G"))
lhbpGates.add(Gate("34", "2B", "G",
                   availableFn = getAvailableIf(othersAvailable = ["34L", "34R"])))
lhbpGates.add(Gate("34L", "2B", "G",
                   availableFn = getAvailableIf(othersAvailable = ["34", "34R"])))
lhbpGates.add(Gate("34R", "2B", "G",
                   availableFn = getAvailableIf(othersAvailable = ["34L", "34"])))
lhbpGates.add(Gate("35", "2B", "G",
                   availableFn = getAvailableIf(othersAvailable = ["35L", "35R"])))
lhbpGates.add(Gate("35L", "2B", "G",
                   availableFn = getAvailableIf(othersAvailable = ["35", "35R"])))
lhbpGates.add(Gate("35R", "2B", "G",
                   availableFn = getAvailableIf(othersAvailable = ["35L", "35"])))
lhbpGates.add(Gate("36", "2B", "G",
                   availableFn = getAvailableIf(othersAvailable = ["36L", "36R"])))
lhbpGates.add(Gate("36L", "2B", "G",
                   availableFn = getAvailableIf(othersAvailable = ["36", "36R"])))
lhbpGates.add(Gate("36R", "2B", "G",
                   availableFn = getAvailableIf(othersAvailable = ["36L", "36"])))
lhbpGates.addSpace()

lhbpGates.add(Gate("37", "2B", "G"))
lhbpGates.add(Gate("38", "2B", "G"))
lhbpGates.add(Gate("39", "2B", "G",
                   availableFn = getAvailableIf(othersAvailable = ["37L", "37R"])))
lhbpGates.add(Gate("39L", "2B", "G",
                   availableFn = getAvailableIf(othersAvailable = ["37", "37R"])))
lhbpGates.add(Gate("39R", "2B", "G",
                   availableFn = getAvailableIf(othersAvailable = ["37L", "37"])))
lhbpGates.addNewColumn()

lhbpGates.add(Gate("42", "2A", "G"))
lhbpGates.add(Gate("43", "2A", "G"))
lhbpGates.add(Gate("44", "2A", "G"))
lhbpGates.add(Gate("45", "2A", "G"))
lhbpGates.addSpace()

lhbpGates.add(Gate("R210", "2A", "S",
                   availableFn = getAvailableIf(othersAvailable = ["R212A"]),
                   taxiThrough = True))
lhbpGates.add(Gate("R211", "2A", "S",
                   availableFn = getAvailableIf(othersAvailable = ["R212A"]),
                   taxiThrough = True))
lhbpGates.add(Gate("R212", "2A", "S",
                   availableFn = getAvailableIf(othersAvailable = ["R212A"]),
                   taxiThrough = True))
lhbpGates.add(Gate("R212A", "2A", "S",
                   availableFn = getAvailableIf(othersAvailable = ["R210", "R211", "R212"]),
                   taxiThrough = True))
lhbpGates.addSpace()

lhbpGates.add(Gate("R220", "2B", "S"))
lhbpGates.add(Gate("R221", "2B", "S"))
lhbpGates.add(Gate("R222", "2B", "S"))
lhbpGates.add(Gate("R223", "2B", "S"))
lhbpGates.addSpace()

lhbpGates.add(Gate("R224", "2A", "S"))
lhbpGates.add(Gate("R225", "2A", "S"))
lhbpGates.add(Gate("R226", "2A", "S"))
lhbpGates.add(Gate("R227", "2A", "S"))
lhbpGates.addNewColumn()

lhbpGates.add(Gate("R270", "2A", "S"))
lhbpGates.add(Gate("R271", "2A", "S"))
lhbpGates.add(Gate("R272", "2A", "S"))
lhbpGates.add(Gate("R273", "2A", "S"))
lhbpGates.add(Gate("R274", "2A", "S"))
lhbpGates.add(Gate("R275", "2A", "S"))
lhbpGates.add(Gate("R276", "2A", "S"))
lhbpGates.add(Gate("R277", "2A", "S"))
lhbpGates.add(Gate("R278", "2A", "S",
                   availableFn = getAvailableIf(othersAvailable = ["R278A"]),
                   taxiThrough = True))
lhbpGates.add(Gate("R278A", "2A", "S",
                   availableFn = getAvailableIf(othersAvailable = ["R278", "R279"])))
lhbpGates.add(Gate("R279", "2A", "S",
                   availableFn = getAvailableIf(othersAvailable = ["R278A"]),
                   taxiThrough = True))
