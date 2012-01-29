# Test module

import fs
import acft
import const
import time

def callback(data, extra):
    print data

class ConnectionListener(fs.ConnectionListener):
    def __init__(self):
        self._simulator = None
        self._monitoring = False

    def connected(self, fsType, descriptor):
        print "fs.ConnectionListener.connected, fsType:", fsType, ", descriptor:", descriptor
        if not self._monitoring:
            self._simulator.startMonitoring(acft.Aircraft(const.AIRCRAFT_B737))

def main():
    connectionListener = ConnectionListener()
    simulator = fs.createSimulator(const.TYPE_MSFS9, connectionListener)
    connectionListener._simulator = simulator
    simulator.connect()

    while True:
        time.sleep(1000)

if __name__ == "__main__":
    main()
