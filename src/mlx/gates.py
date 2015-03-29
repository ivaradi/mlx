#--------------------------------------------------------------------------------------

## @package mlx.gates
#
# The module to handle the LHBP gate information.
#

#--------------------------------------------------------------------------------------

class Gate(object):
    """Information about a gate."""
    def __init__(self, number, terminal, type,
                 availableFn = None):
        """Construct the gate with the given information.

        number is the gate's number as a string (as it can contain letters).
        terminal is the terminal the gate belongs to (not used currently).
        type is the gate's type: G for gate, S for stand.
        availableFn is a function that can determine if the gate is available based on
        the statuses of other gates. Its arguments are:
        - a collection of the gates, and
        - a set of occupied gate numbers."""
        self._number = number
        self._terminal = terminal
        self._type = type
        self._availableFn = availableFn

    @property
    def number(self):
        """Get the number of the gate."""
        return self._number

    def isAvailable(self, gates, occupiedGateNumbers):
        """Determine if this gate is available given the set of gates and
        occupied gate numbers."""
        if self._number in occupiedGateNumbers:
            return False
        return True if self._availableFn is None else \
               self._availableFn(gates, occupiedGateNumbers)

#--------------------------------------------------------------------------------------

class Gates(object):
    """A collection of gates."""
    # Display info type: a gate (number)
    DISPLAY_GATE=1

    # Display info type: a space
    DISPLAY_SPACE=2

    # Display info type: a new column
    DISPLAY_NEW_COLUMN=3

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

    def addSpace(self):
        """Add a space between subsequent gates."""
        self._displayInfos.append((Gates.DISPLAY_SPACE, None))
        self._addRow()

    def addNewColumn(self):
        """Start a new column of gates."""
        self._displayInfos.append((Gates.DISPLAY_NEW_COLUMN, None))
        self._numRowsInColumn = 0
        self._numColumns += 1

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

def getAvilableIf(othersAvailable = []):
    """Get a function that determines if a gate is available based on the
    statuses of other gates."""
    return lambda gates, occupiedGateNumbers: availableIf(occupiedGateNumbers,
                                                          othersAvailable =
                                                          othersAvailable)

#--------------------------------------------------------------------------------------

# The gates at LHBP
lhbpGates = Gates()

lhbpGates.add(Gate("1", "1", "S"))
lhbpGates.add(Gate("2", "1", "S"))
lhbpGates.add(Gate("3", "1", "S"))
lhbpGates.add(Gate("4", "1", "S"))
lhbpGates.add(Gate("5", "1", "S"))
lhbpGates.add(Gate("6", "1", "S"))
lhbpGates.add(Gate("25", "1", "S"))
lhbpGates.add(Gate("26", "1", "S"))
lhbpGates.add(Gate("27", "1", "S"))
lhbpGates.addSpace()

lhbpGates.add(Gate("31", "2B", "G"))
lhbpGates.add(Gate("32", "2B", "G"))
lhbpGates.add(Gate("33", "2B", "G"))
lhbpGates.addNewColumn()

lhbpGates.add(Gate("34", "2B", "G"))
lhbpGates.add(Gate("35", "2B", "G"))
lhbpGates.add(Gate("36", "2B", "G"))
lhbpGates.add(Gate("37", "2B", "G"))
lhbpGates.add(Gate("38", "2B", "G"))
lhbpGates.add(Gate("39", "2B", "G"))
lhbpGates.addSpace()

lhbpGates.add(Gate("42", "2A", "G"))
lhbpGates.add(Gate("43", "2A", "G"))
lhbpGates.add(Gate("44", "2A", "G"))
lhbpGates.add(Gate("45", "2A", "G"))
lhbpGates.addNewColumn()

lhbpGates.add(Gate("107", "1", "S"))
lhbpGates.add(Gate("108", "1", "S"))
lhbpGates.add(Gate("109", "1", "S"))
lhbpGates.add(Gate("R110", "1", "S",
                   availableFn = getAvilableIf(othersAvailable = ["R111"])))
lhbpGates.add(Gate("R111", "1", "S",
                   availableFn = getAvilableIf(othersAvailable = ["R110", "R112"])))
lhbpGates.add(Gate("R112", "1", "S",
                   availableFn = getAvilableIf(othersAvailable = ["R111"])))
lhbpGates.add(Gate("R113", "1", "S",
                   availableFn = getAvilableIf(othersAvailable = ["R114"])))
lhbpGates.add(Gate("R114", "1", "S",
                   availableFn = getAvilableIf(othersAvailable = ["R113"])))
lhbpGates.add(Gate("R115", "1", "S"))
lhbpGates.add(Gate("R116", "1", "S"))
lhbpGates.add(Gate("R117", "1", "S"))
lhbpGates.addNewColumn()

lhbpGates.add(Gate("R210", "2A", "S",
                   availableFn = getAvilableIf(othersAvailable = ["R212A"])))
lhbpGates.add(Gate("R211", "2A", "S",
                   availableFn = getAvilableIf(othersAvailable = ["R212A"])))
lhbpGates.add(Gate("R212", "2A", "S",
                   availableFn = getAvilableIf(othersAvailable = ["R212A"])))
lhbpGates.add(Gate("R212A", "2A", "S",
                   availableFn = getAvilableIf(othersAvailable = ["R210", "R211", "R212"])))
lhbpGates.addSpace()

lhbpGates.add(Gate("R220", "2B", "S"))
lhbpGates.add(Gate("R221", "2B", "S"))
lhbpGates.add(Gate("R222", "2B", "S"))
lhbpGates.add(Gate("R223", "2B", "S"))
lhbpGates.addSpace()

lhbpGates.add(Gate("R224", "2A", "R"))
lhbpGates.add(Gate("R225", "2A", "S"))
lhbpGates.add(Gate("R226", "2A", "S"))
lhbpGates.add(Gate("R227", "2A", "S"))
lhbpGates.addNewColumn()

lhbpGates.add(Gate("R270", "2A", "S"))
lhbpGates.add(Gate("R271", "2A", "S"))
lhbpGates.add(Gate("R272", "2A", "S"))
lhbpGates.add(Gate("R274", "2A", "S"))
lhbpGates.add(Gate("R275", "2A", "S"))
lhbpGates.add(Gate("R276", "2A", "S"))
lhbpGates.add(Gate("R277", "2A", "S"))
lhbpGates.add(Gate("R278", "2A", "S",
                   availableFn = getAvilableIf(othersAvailable = ["R278A"])))
lhbpGates.add(Gate("R278A", "2A", "S",
                   availableFn = getAvilableIf(othersAvailable = ["R278", "R279"])))
lhbpGates.add(Gate("R279", "2A", "S",
                   availableFn = getAvilableIf(othersAvailable = ["R278A"])))
