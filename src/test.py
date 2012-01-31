# Test module

import fs
import acft
import const
import time

def callback(data, extra):
    print data

def main():
    simulator = fs.createSimulator(const.SIM_MSFS9, fs.ConnectionListener(),
                                   acft.Aircraft(const.AIRCRAFT_B737))
    simulator.connect()

    time.sleep(10)
    simulator.startMonitoring()

    while True:
        time.sleep(1000)
    simulator.stopMonitoring()
    simulator.disconnect()

    time.sleep(5)

if __name__ == "__main__":
    main()
