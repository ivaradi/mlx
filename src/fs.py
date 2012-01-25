# Module for generic flight-simulator interfaces

# Flight simulator type: MS Flight Simulator 2004
TYPE_FS2K4 = 1

# Flight simulator type: MS Flight Simulator X
TYPE_FSX = 2

# Flight simulator type: X-Plane 9
TYPE_XPLANE9 = 3

# Flight simulator type: X-Plane 10
TYPE_XPLANE10 = 4

class ConnectionListener:
    """Base class for listeners on connections to the flight simulator."""
    def connected(self, fsType, descriptor):
        """Called when a connection has been established to the flight
        simulator of the given type."""
        print "fs.ConnectionListener.connected, fsType:", fsType, ", descriptor:", descriptor

    def disconnected(self):
        """Called when a connection to the flight simulator has been broken."""
        print "fs.ConnectionListener.disconnected"

