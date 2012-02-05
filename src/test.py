# Test module

import fs
import flight
import logger
import acft
import const

import time
import sys

def callback(data, extra):
    print data

def main():
    with open(sys.argv[1], "wt") as output:
        fl = flight.Flight(logger.Logger(output = output))
        fl.cruiseAltitude = 18000
        fl.aircraftType = const.AIRCRAFT_B736
        fl.aircraft = acft.Aircraft.create(fl)
        #fl._stage = const.STAGE_LANDING
        simulator = fs.createSimulator(const.SIM_MSFS9, fs.ConnectionListener(),
                                       fl.aircraft)
        fl.simulator = simulator

        simulator.connect()
        simulator.startMonitoring()
        
        fl.wait()

        simulator.stopMonitoring()
        simulator.disconnect()

if __name__ == "__main__":
    main()
