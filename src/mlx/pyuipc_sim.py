# Simulator for the pyuipc module
#------------------------------------------------------------------------------

import const

import cmd
import threading
import socket
import time
import calendar
import sys
import struct
import cPickle

#------------------------------------------------------------------------------

# Version constants
SIM_ANY=0
SIM_FS98=1
SIM_FS2K=2
SIM_CFS2=3
SIM_CFS1=4
SIM_FLY=5
SIM_FS2K2=6
SIM_FS2K4=7

#------------------------------------------------------------------------------

# Error constants
ERR_OK=0
ERR_OPEN=1
ERR_NOFS=2
ERR_REGMSG=3
ERR_ATOM=4
ERR_MAP=5
ERR_VIEW=6
ERR_VERSION=7
ERR_WRONGFS=8
ERR_NOTOPEN=9
ERR_NODATA=10
ERR_TIMEOUT=11
ERR_SENDMSG=12
ERR_DATA=13
ERR_RUNNING=14
ERR_SIZE=15

#------------------------------------------------------------------------------

# The version of FSUIPC
fsuipc_version=0x0401
lib_version=0x0302
fs_version=SIM_FS2K4

#------------------------------------------------------------------------------

class FSUIPCException(Exception):
    """FSUIPC exception class.

    It contains a member variable named errorCode. The string is a text
    describing the error."""

    errors=["OK",
            "Attempt to Open when already Open",
            "Cannot link to FSUIPC or WideClient",
            "Failed to Register common message with Windows",
            "Failed to create Atom for mapping filename",
            "Failed to create a file mapping object",
            "Failed to open a view to the file map",
            "Incorrect version of FSUIPC, or not FSUIPC",
            "Sim is not version requested",
            "Call cannot execute, link not Open",
            "Call cannot execute: no requests accumulated",
            "IPC timed out all retries",
            "IPC sendmessage failed all retries",
            "IPC request contains bad data",
            "Maybe running on WideClient, but FS not running on Server, or wrong FSUIPC",
            "Read or Write request cannot be added, memory for Process is full"]

    def __init__(self, errorCode):
        """
        Construct the exception
        """
        if errorCode<len(self.errors):
            self.errorString =  self.errors[errorCode]
        else:
            self.errorString = "Unknown error"
        Exception.__init__(self, self.errorString)
        self.errorCode = errorCode

    def __str__(self):
        """
        Convert the excption to string
        """
        return "FSUIPC error: %d (%s)" % (self.errorCode, self.errorString)

#------------------------------------------------------------------------------

class Values(object):
    """The values that can be read from 'FSUIPC'."""
    # Fuel data index: centre tank
    FUEL_CENTRE = 0

    # Fuel data index: left main tank
    FUEL_LEFT = 1

    # Fuel data index: right main tank
    FUEL_RIGHT = 2

    # Fuel data index: left aux tank
    FUEL_LEFT_AUX = 3

    # Fuel data index: right aux tank
    FUEL_RIGHT_AUX = 4

    # Fuel data index: left tip tank
    FUEL_LEFT_TIP = 5

    # Fuel data index: right tip tank
    FUEL_RIGHT_AUX = 6

    # Fuel data index: external 1 tank
    FUEL_EXTERNAL_1 = 7

    # Fuel data index: external 2 tank
    FUEL_EXTERNAL_2 = 8

    # Fuel data index: centre 2 tank
    FUEL_CENTRE_2 = 9

    # The number of fuel tank entries
    NUM_FUEL = FUEL_CENTRE_2 + 1

    # Engine index: engine #1
    ENGINE_1 = 0

    # Engine index: engine #2
    ENGINE_2 = 1

    # Engine index: engine #3
    ENGINE_3 = 2

    @staticmethod
    def _readFrequency(frequency):
        """Convert the given frequency into BCD."""
        return Values._readBCD(int(frequency*100.0))

    @staticmethod
    def _readBCD(value):
        """Convert the given value into BCD format."""
        bcd = (value/1000) % 10
        bcd <<= 4
        bcd |= (value/100) % 10
        bcd <<= 4
        bcd |= (value/10) % 10
        bcd <<= 4
        bcd |= value % 10
        return bcd
        
    @staticmethod
    def _writeFrequency(value):
        """Convert the given value into a frequency."""
        return (Values._writeBCD(value) + 10000) / 100.0

    @staticmethod
    def _writeBCD(value):
        """Convert the given BCD value into a real value."""
        bcd = (value>>24) & 0xf
        bcd *= 10
        bcd += (value>>16) & 0xf
        bcd *= 10
        bcd += (value>>8) & 0xf
        bcd *= 10
        bcd += (value>>0) & 0xf

        return bcd
        
    def __init__(self):
        """Construct the values with defaults."""
        self._timeOffset = 0
        self.airPath = "C:\\Program Files\\Microsoft Games\\" \
                       "FS9\\Aircraft\\Cessna\\cessna172.air"
        self.aircraftName = "Cessna 172SP"
        self.flapsNotches = [0, 1, 2, 5, 10, 15, 25, 30, 40]
        self.fuelCapacities = [10000.0, 5000.0, 5000.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        
        self.paused = False
        self.frozen = False
        self.replay = False
        self.slew = False
        self.overspeed = False
        self.stalled = False
        self.onTheGround = True
        
        self.zfw = 50000.0
        
        self.fuelWeights = [0.0, 3000.0, 3000.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        # FIXME: check for realistic values
        self.fuelWeight = 3.5

        self.heading = 220.0
        self.pitch = 0.0
        self.bank = 0.0

        self.ias = 0.0
        self.vs = 0.0

        self.radioAltitude = None
        self.altitude = 513.0

        self.gLoad = 1.0

        self.flapsControl = 0.0
        self.flaps = 0.0

        self.navLightsOn = True
        self.antiCollisionLightsOn = False
        self.landingLightsOn = False
        self.strobeLightsOn = False

        self.pitot = False
        self.parking = True

        self.noseGear = 1.0

        self.spoilersArmed = False
        self.spoilers = 0.0

        self.altimeter = 1013.0

        self.nav1 = 117.3
        self.nav2 = 109.5
        self.squawk = 2200

        self.windSpeed = 8.0
        self.windDirection = 300.0
        
        self.n1 = [0.0, 0.0, 0.0]
        self.throttles = [0.0, 0.0, 0.0]

    def read(self, offset):
        """Read the value at the given offset."""
        try:
            return self._read(offset)
        except Exception, e:
            print "failed to read offset %04x: %s" % (offset, str(e))
            raise FSUIPCException(ERR_DATA)

    def _read(self, offset):
        """Read the value at the given offset."""
        if offset==0x023a:         # Second of time
            return self._readUTC().tm_sec
        elif offset==0x023b:       # Hour of Zulu time
            return self._readUTC().tm_hour
        elif offset==0x023c:       # Minute of Zulu time
            return self._readUTC().tm_min
        elif offset==0x023e:       # Day number on year
            return self._readUTC().tm_yday
        elif offset==0x0240:       # Year in FS
            return self._readUTC().tm_year
        elif offset==0x0264:       # Paused
            return 1 if self.paused else 0
        elif offset==0x029c:       # Pitot
            return 1 if self.pitot else 0
        elif offset==0x02b4:       # Ground speed
            # FIXME: calculate TAS first, then from the heading and
            # wind the GS
            return int(self.ias * 65536.0 * 1852.0 / 3600.0)
        elif offset==0x02bc:       # IAS
            return int(self.ias * 128.0)
        elif offset==0x02c8:       # VS
            return int(self.vs * const.FEETTOMETRES * 256.0 / 60.0)
        elif offset==0x0330:       # Altimeter
            return int(self.altimeter * 16.0)
        elif offset==0x0350:       # NAV1
            return Values._readFrequency(self.nav1)
        elif offset==0x0352:       # NAV2
            return Values._readFrequency(self.nav2)
        elif offset==0x0354:       # Squawk
            return Values._readBCD(self.squawk)
        elif offset==0x0366:       # On the ground
            return 1 if self.onTheGround else 0
        elif offset==0x036c:       # Stalled
            return 1 if self.stalled else 0
        elif offset==0x036d:       # Overspeed
            return 1 if self.overspeed else 0
        elif offset==0x0570:       # Altitude
            return long(self.altitude * const.FEETTOMETRES * 65536.0 * 65536.0)
        elif offset==0x0578:       # Pitch
            return int(self.pitch * 65536.0 * 65536.0 / 360.0)
        elif offset==0x057c:       # Bank
            return int(self.bank * 65536.0 * 65536.0 / 360.0)
        elif offset==0x0580:       # Heading
            return int(self.heading * 65536.0 * 65536.0 / 360.0)
        elif offset==0x05dc:       # Slew
            return 1 if self.slew else 0
        elif offset==0x0628:       # Replay
            return 1 if self.replay else 0
        elif offset==0x088c:       # Engine #1 throttle
            return self._getThrottle(self.ENGINE_1)
        elif offset==0x0924:       # Engine #2 throttle
            return self._getThrottle(self.ENGINE_2)
        elif offset==0x09bc:       # Engine #3 throttle
            return self._getThrottle(self.ENGINE_3)
        elif offset==0x0af4:       # Fuel weight
            return int(self.fuelWeight * 256.0)
        elif offset==0x0b74:       # Centre tank level
            return self._getFuelLevel(self.FUEL_CENTRE)
        elif offset==0x0b78:       # Centre tank capacity
            return self._getFuelCapacity(self.FUEL_CENTRE)
        elif offset==0x0b7c:       # Left tank level
            return self._getFuelLevel(self.FUEL_LEFT)
        elif offset==0x0b80:       # Left tank capacity
            return self._getFuelCapacity(self.FUEL_LEFT)
        elif offset==0x0b84:       # Left aux tank level
            return self._getFuelLevel(self.FUEL_LEFT_AUX)
        elif offset==0x0b88:       # Left aux tank capacity
            return self._getFuelCapacity(self.FUEL_LEFT_AUX)
        elif offset==0x0b8c:       # Left tip tank level
            return self._getFuelLevel(self.FUEL_LEFT_TIP)
        elif offset==0x0b90:       # Left tip tank capacity
            return self._getFuelCapacity(self.FUEL_LEFT_TIP)
        elif offset==0x0b94:       # Right aux tank level
            return self._getFuelLevel(self.FUEL_RIGHT)
        elif offset==0x0b98:       # Right aux tank capacity
            return self._getFuelCapacity(self.FUEL_RIGHT)
        elif offset==0x0b9c:       # Right tank level
            return self._getFuelLevel(self.FUEL_RIGHT_AUX)
        elif offset==0x0ba0:       # Right tank capacity
            return self._getFuelCapacity(self.FUEL_RIGHT_AUX)
        elif offset==0x0ba4:       # Right tip tank level
            return self._getFuelLevel(self.FUEL_RIGHT_TIP)
        elif offset==0x0ba8:       # Right tip tank capacity
            return self._getFuelCapacity(self.FUEL_RIGHT_TIP)
        elif offset==0x0bc8:       # Parking
            return 1 if self.parking else 0
        elif offset==0x0bcc:       # Spoilers armed
            return 1 if self.spoilersArmed else 0
        elif offset==0x0bd0:       # Spoilers
            return 0 if self.spoilers == 0 \
                else int(self.spoilers * (16383 - 4800) + 4800)
        elif offset==0x0bdc:       # Flaps control
            numNotchesM1 = len(self.flapsNotches) - 1
            flapsIncrement = 16383.0 / numNotchesM1
            index = 0
            while index<numNotchesM1 and \
                  self.flapsControl<self.flapsNotches[index]:
                index += 1
                
            if index==numNotchesM1:
                return 16383
            else:
                return int((self.flapsControl-self.flapsNotches[index]) * \
                           flapsIncrement / \
                           (self.flapsNotches[index+1] - self.flapsNotches[index]))
        elif offset==0x0be0 or offset==0x0be4:    # Flaps left and  right
            return self.flaps * 16383.0 / self.flapsNotches[-1]        
        elif offset==0x0bec:       # Nose gear
            return int(self.noseGear * 16383.0)
        elif offset==0x0d0c:       # Lights
            lights = 0
            if self.navLightsOn: lights |= 0x01
            if self.antiCollisionLightsOn: lights |= 0x02
            if self.landingLightsOn: lights |= 0x04
            if self.strobeLightsOn: lights |= 0x10
            return lights
        elif offset==0x0e90:       # Wind speed
            return int(self.windSpeed)
        elif offset==0x0e92:       # Wind direction
            return int(self.windDirection * 65536.0 / 360.0)
        elif offset==0x11ba:       # G-Load
            return int(self.gLoad * 625.0)
        elif offset==0x11c6:       # Mach
            # FIXME: calculate from IAS, altitude and QNH
            return int(self.ias * 0.05 * 20480.)
        elif offset==0x1244:       # Centre 2 tank level
            return self._getFuelLevel(self.FUEL_CENTRE_2)
        elif offset==0x1248:       # Centre 2 tank capacity
            return self._getFuelCapacity(self.FUEL_CENTRE_2)
        elif offset==0x1254:       # External 1 tank level
            return self._getFuelLevel(self.FUEL_EXTERNAL_1)
        elif offset==0x1258:       # External 1 tank capacity
            return self._getFuelCapacity(self.FUEL_EXTERNAL_1)
        elif offset==0x125c:       # External 2 tank level
            return self._getFuelLevel(self.FUEL_EXTERNAL_2)
        elif offset==0x1260:       # External 2 tank capacity
            return self._getFuelCapacity(self.FUEL_EXTERNAL_2)
        elif offset==0x2000:       # Engine #1 N1
            return self.n1[self.ENGINE_1]
        elif offset==0x2100:       # Engine #2 N1
            return self.n1[self.ENGINE_2]
        elif offset==0x2200:       # Engine #3 N1
            return self.n1[self.ENGINE_3]
        elif offset==0x30c0:       # Grossweight
            return int((self.zfw + sum(self.fuelWeights)) * const.KGSTOLB)
        elif offset==0x31e4:       # Radio altitude
            # FIXME: if self.radioAltitude is None, calculate from the 
            # altitude with some, perhaps random, ground altitude
            # value
            radioAltitude = (self.altitude - 517) \
                if self.radioAltitude is None else self.radioAltitude
            return (radioAltitude * const.FEETTOMETRES * 65536.0)
        elif offset==0x3364:       # Frozen
            return 1 if self.frozen else 0
        elif offset==0x3bfc:       # ZFW
            return int(self.zfw * 256.0 * const.KGSTOLB)
        elif offset==0x3c00:       # Path of the current AIR file
            return self.airPath
        elif offset==0x3d00:       # Name of the current aircraft
            return self.aircraftName
        else:
            print "Unhandled offset: %04x" % (offset,)
            raise FSUIPCException(ERR_DATA)

    def write(self, offset, value):
        """Write the value at the given offset."""
        try:
            return self._write(offset, value)
        except Exception, e:
            print "failed to write offset %04x: %s" % (offset, str(e))
            raise FSUIPCException(ERR_DATA)

    def _write(self, offset, value):
        """Write the given value at the given offset."""
        if offset==0x023a:         # Second of time
            self._updateTimeOffset(5, value)
        elif offset==0x023b:       # Hour of Zulu time
            self._updateTimeOffset(3, value)
        elif offset==0x023c:       # Minute of Zulu time
            self._updateTimeOffset(4, value)
        elif offset==0x023e:       # Day number in the year
            self._updateTimeOffset(7, value)
        elif offset==0x0240:       # Year in FS
            self._updateTimeOffset(0, value)
        elif offset==0x0264:       # Paused
            self.paused = value!=0
        elif offset==0x029c:       # Pitot
            self.pitot = value!=0
        elif offset==0x02b4:       # Ground speed
            # FIXME: calculate TAS using the heading and the wind, and
            # then IAS based on the altitude
            self.ias = value * 3600.0 / 65536.0 / 1852.0
        elif offset==0x02bc:       # IAS
            self.ias = value / 128.0
        elif offset==0x02c8:       # VS
            self.vs = value * 60.0 / const.FEETTOMETRES / 256.0
        elif offset==0x0330:       # Altimeter
            self.altimeter = value / 16.0
        elif offset==0x0350:       # NAV1
            self.nav1 = Values._writeFrequency(value)
        elif offset==0x0352:       # NAV2
            self.nav2 = Values._writeFrequency(value)
        elif offset==0x0354:       # Squawk
            self.squawk = Values._writeBCD(value)
        elif offset==0x0366:       # Stalled
            self.onTheGround = value!=0
        elif offset==0x036c:       # Stalled
            self.stalled = value!=0
        elif offset==0x036d:       # Overspeed
            self.overspeed = value!=0
        elif offset==0x0570:       # Altitude
            self.altitude = value / const.FEETTOMETRES / 65536.0 / 65536.0
        elif offset==0x0578:       # Pitch
            self.pitch = value * 360.0 / 65536.0 / 65536.0
        elif offset==0x057c:       # Bank
            self.bank = value * 360.0 / 65536.0 / 65536.0
        elif offset==0x0580:       # Heading
            self.heading = value * 360.0 / 65536.0 / 65536.0
        elif offset==0x05dc:       # Slew
            self.slew = value!=0
        elif offset==0x0628:       # Replay
            self.replay = value!=0
        elif offset==0x088c:       # Engine #1 throttle
            self._setThrottle(self.ENGINE_1, value)
        elif offset==0x0924:       # Engine #2 throttle
            self._setThrottle(self.ENGINE_2, value)
        elif offset==0x09bc:       # Engine #3 throttle
            self._setThrottle(self.ENGINE_3, value)
        elif offset==0x0af4:       # Fuel weight
            self.fuelWeight = value / 256.0
        elif offset==0x0b74:       # Centre tank level
            self._setFuelLevel(self.FUEL_CENTRE, value)
        elif offset==0x0b78:       # Centre tank capacity
            self._setFuelCapacity(self.FUEL_CENTRE, value)
        elif offset==0x0b7c:       # Left tank level
            self._setFuelLevel(self.FUEL_LEFT, value)
        elif offset==0x0b80:       # Left tank capacity
            self._setFuelCapacity(self.FUEL_LEFT, value)
        elif offset==0x0b84:       # Left aux tank level
            self._setFuelLevel(self.FUEL_LEFT_AUX, value)
        elif offset==0x0b88:       # Left aux tank capacity
            self._setFuelCapacity(self.FUEL_LEFT_AUX, value)
        elif offset==0x0b8c:       # Left tip tank level
            self._setFuelLevel(self.FUEL_LEFT_TIP, value)
        elif offset==0x0b90:       # Left tip tank capacity
            self._setFuelCapacity(self.FUEL_LEFT_TIP, value)
        elif offset==0x0b94:       # Right aux tank level
            self._setFuelLevel(self.FUEL_RIGHT, value)
        elif offset==0x0b98:       # Right aux tank capacity
            self._setFuelCapacity(self.FUEL_RIGHT, value)
        elif offset==0x0b9c:       # Right tank level
            self._setFuelLevel(self.FUEL_RIGHT_AUX, value)
        elif offset==0x0ba0:       # Right tank capacity
            self._setFuelCapacity(self.FUEL_RIGHT_AUX, value)
        elif offset==0x0ba4:       # Right tip tank level
            self._setFuelLevel(self.FUEL_RIGHT_TIP, value)
        elif offset==0x0ba8:       # Right tip tank capacity
            self._setFuelCapacity(self.FUEL_RIGHT_TIP, value)
        elif offset==0x0bc8:       # Parking
            self.parking = value!=0
        elif offset==0x0bcc:       # Spoilers armed
            self.spoilersArmed = value!=0
        elif offset==0x0bd0:       # Spoilers
            self.spoilters = 0 if value==0 \
                             else (value - 4800) / (16383 - 4800)
        elif offset==0x0bdc:       # Flaps control
            numNotchesM1 = len(self.flapsNotches) - 1
            flapsIncrement = 16383.0 / numNotchesM1
            index = value / flapsIncrement
            if index>=numNotchesM1:
                self.flapsControl = self.flapsNotches[-1]
            else:
                self.flapsControl = self.flapsNotches[index]
                self.flapsControl += value * \
                    (self.flapsNotches[index+1] - self.flapsNotches[index]) / \
                    flapsIncrement
        elif offset==0x0be0 or offset==0x0be4:    # Flaps left and  right
            self.flaps = value * self.flapsNotches[-1] / 16383.0
        elif offset==0x0bec:       # Nose gear
            self.noseGear = value / 16383.0
        elif offset==0x0d0c:       # Lights
            self.navLightsOn = (lights&0x01)!=0
            self.antiCollisionLightsOn = (lights&0x02)!=0
            self.landingLightsOn = (lights&0x04)!=0 
            self.strobeLightsOn = (lights&0x10)!=0 
        elif offset==0x0e90:       # Wind speed
            self.windSpeed = value
        elif offset==0x0e92:       # Wind direction
            self.windDirection = value * 360.0 / 65536.0
        elif offset==0x11ba:       # G-Load
            self.gLoad = value / 625.0
        elif offset==0x11c6:       # Mach
            # FIXME: calculate IAS using the altitude and QNH
            self.ias = value / 0.05 / 20480
        elif offset==0x1244:       # Centre 2 tank level
            self._setFuelLevel(self.FUEL_CENTRE_2, value)
        elif offset==0x1248:       # Centre 2 tank capacity
            self._setFuelCapacity(self.FUEL_CENTRE_2, value)
        elif offset==0x1254:       # External 1 tank level
            self._setFuelLevel(self.FUEL_EXTERNAL_1, value)
        elif offset==0x1258:       # External 1 tank capacity
            self._setFuelCapacity(self.FUEL_EXTERNAL_1, value)
        elif offset==0x125c:       # External 2 tank level
            self._setFuelLevel(self.FUEL_EXTERNAL_2, value)
        elif offset==0x1260:       # External 2 tank capacity
            self._setFuelCapacity(self.FUEL_EXTERNAL_2, value)
        elif offset==0x2000:       # Engine #1 N1
            self.n1[self.ENGINE_1] = value
        elif offset==0x2100:       # Engine #2 N1
            self.n1[self.ENGINE_2] = value
        elif offset==0x2200:       # Engine #3 N1
            self.n1[self.ENGINE_3] = value
        elif offset==0x30c0:       # Grossweight
            raise FSUIPCException(ERR_DATA)
        elif offset==0x31e4:       # Radio altitude
            raise FSUIPCException(ERR_DATA)
        elif offset==0x3364:       # Frozen
            self.frozen = value!=0
        elif offset==0x3bfc:       # ZFW
            self.zfw = value * const.LBSTOKG / 256.0
            print "ZFW:", self.zfw
        elif offset==0x3c00:       # Path of the current AIR file
            self.airPath = value
        elif offset==0x3d00:       # Name of the current aircraft
            self.aircraftName = value
        else:
            print "Unhandled offset: %04x" % (offset,)
            raise FSUIPCException(ERR_DATA)
        
    def _readUTC(self):
        """Read the UTC time.
        
        The current offset is added to it."""
        return time.gmtime(time.time() + self._timeOffset)
        
    def _getFuelLevel(self, index):
        """Get the fuel level for the fuel tank with the given
        index."""
        return 0 if self.fuelCapacities[index]==0.0 else \
            int(self.fuelWeights[index] * 65536.0 * 128.0 / self.fuelCapacities[index])
    
    def _getFuelCapacity(self, index):
        """Get the capacity of the fuel tank with the given index."""
        return int(self.fuelCapacities[index] * const.KGSTOLB  / self.fuelWeight)

    def _getThrottle(self, index):
        """Get the throttle value for the given index."""
        return int(self.throttles[index] * 16383.0)

    def _updateTimeOffset(self, index, value):
        """Update the time offset if the value in the tm structure is replaced
        by the given value."""
        tm = self._readUTC()
        tm1 = tm[:index] + (value,) + tm[(index+1):]
        self._timeOffset += calendar.timegm(tm1) - calendar.timegm(tm)
    
    def _setThrottle(self, index, value):
        """Set the throttle value for the given index."""
        self.throttles[index] = value / 16383.0

    def _setFuelLevel(self, index, value):
        """Set the fuel level for the fuel tank with the given index."""
        self.fuelWeights[index] = self.fuelCapacities[index] * float(value) / \
                                  65536.0 / 128.0
    
    def _setFuelCapacity(self, index, value):
        """Set the capacity of the fuel tank with the given index."""
        self.fuelCapacities[index] = value * self.fuelWeight * const.LBSTOKG


#------------------------------------------------------------------------------

values = Values()

#------------------------------------------------------------------------------

def open(request):
    """Open the connection."""
    return True

#------------------------------------------------------------------------------

def prepare_data(pattern, forRead = True):
    """Prepare the given pattern for reading and/or writing."""
    return pattern

#------------------------------------------------------------------------------

def read(data):
    """Read the given data."""
    return [values.read(offset) for (offset, type) in data]
            
#------------------------------------------------------------------------------

def write(data):
    """Write the given data."""
    for (offset, type, value) in data:
        values.write(offset, value)
            
#------------------------------------------------------------------------------

def close():
    """Close the connection."""
    pass

#------------------------------------------------------------------------------

PORT=15015

CALL_READ=1
CALL_WRITE=2
CALL_CLOSE=3

RESULT_RETURNED=1
RESULT_EXCEPTION=2

#------------------------------------------------------------------------------

class Server(threading.Thread):
    """The server thread."""
    def __init__(self):
        """Construct the thread."""
        super(Server, self).__init__()
        self.daemon = True

    def run(self):
        """Perform the server's operation."""
        serverSocket = socket.socket()

        serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        serverSocket.bind(("", PORT))
    
        serverSocket.listen(5)
    
        while True:
            (clientSocket, clientAddress) = serverSocket.accept()
            thread = threading.Thread(target = self._process, args=(clientSocket,))
            thread.start()

    def _process(self, clientSocket):
        """Process the commands arriving on the given socket."""
        socketFile = clientSocket.makefile()
        try:
            while True:                
                (length,) = struct.unpack("I", clientSocket.recv(4))
                data = clientSocket.recv(length)
                (call, args) = cPickle.loads(data)
                exception = None
                
                try:
                    if call==CALL_READ:
                        result = read(args[0])
                    elif call==CALL_WRITE:
                        result = write(args[0])
                    else:
                        break
                except Exception, e:
                    exception = e

                if exception is None:
                    data = cPickle.dumps((RESULT_RETURNED, result))
                else:
                    data = cPickle.dumps((RESULT_EXCEPTION, exception))
                clientSocket.send(struct.pack("I", len(data)) + data)
        except Exception, e:
            print >> sys.stderr, "pyuipc_sim.Server._process: failed with exception:", str(e)
        finally:
            try:
                socketFile.close()
            except:
                pass
            clientSocket.close()
                   
#------------------------------------------------------------------------------

class Client(object):
    """Client to the server."""
    def __init__(self, serverHost):
        """Construct the client and connect to the given server
        host."""
        self._socket = socket.socket()
        self._socket.connect((serverHost, PORT))

        self._socketFile = self._socket.makefile()

    def read(self, data):
        """Read the given data."""
        return self._call(CALL_READ, data)

    def write(self, data):
        """Write the given data."""
        return self._call(CALL_WRITE, data)

    def _call(self, command, data):
        """Perform a call with the given command and data."""
        data = cPickle.dumps((command, [data]))
        self._socket.send(struct.pack("I", len(data)) + data)
        (length,) = struct.unpack("I", self._socket.recv(4))
        data = self._socket.recv(length)
        (resultCode, result) = cPickle.loads(data)
        if resultCode==RESULT_RETURNED:
            return result
        else:
            raise result        

#------------------------------------------------------------------------------
#------------------------------------------------------------------------------

# FIXME: implement proper completion and history
class CLI(threading.Thread, cmd.Cmd):
    """The command-line interpreter."""
    def __init__(self, clientSocket):
        """Construct the CLI."""
        self._socket = clientSocket
        self._socketFile = clientSocket.makefile("rwb")
        
        threading.Thread.__init__(self)
        cmd.Cmd.__init__(self,
                         stdin = self._socketFile, stdout = self._socketFile)
        
        self.use_rawinput = False
        self.intro = "\nPyUIPC simulator command prompt\n"
        self.prompt = "PyUIPC> "

        self.daemon = True

    def run(self):
        """Execute the thread."""
        try:
            self.cmdloop()
        except Exception, e:
            print "pyuipc_sim.CLI.run: command loop terminated abnormally: " + str(e)
            
        try:
            self._socketFile.close()
        except:
            pass
        
        self._socket.close()

    def do_set(self, args):
        """Handle the set command."""
        words = args.split()
        if len(words)==2:
            variable = words[0]
            if variable in ["zfw"]:
                values.__setattr__(variable, float(words[1]))
            else:
                print >> self._socketFile, "Unhandled variable: " + variable
        return False

    def help_set(self):
        """Print help for the set command."""
        print >> self._socketFile, "set <variable> <value>"

    def do_quit(self, args):
        """Handle the quit command."""
        return True

#------------------------------------------------------------------------------

if __name__ == "__main__":
    client = Client("127.0.0.1")
    # print client.write([(0x3bfc, "d", 1000 * 256.0 * const.KGSTOLB)])
    # print client.read([(0x3bfc, "d")])
    print client.write([(0x023c, "d", 30)])
    print client.read([(0x023c, "d")])
else:
    server = Server()
    server.start()    

#------------------------------------------------------------------------------
