
import time

#------------------------------------------------------------------------------

## @package mlx.pyuipc_emu
#
# A very simple PyUIPC emulator.
#
# This is not used currently.

#------------------------------------------------------------------------------

## The ratio between kg and lbs
KGTOLBS=1/0.4536

## Feet to metres
FEETTOMETRES=0.3048

#------------------------------------------------------------------------------

def interpolate_proportion(proportion, value0, value1):
    """
    Interpolate between value0 and value1 using the given proportion.
    """
    return value0 + (value1-value0)*1.0*proportion

#------------------------------------------------------------------------------

def interpolate(point0, point, point1, value0, value1):
    """
    Interpolate linearly between the given points for the given
    values.
    """
    if point0==point1:
        if point>=point1: return value1
        else: return value0
    else:
        return interpolate_proportion((point-point0)*1.0/(point1-point0),
                                      value0, value1)

#------------------------------------------------------------------------------

## Version constants
SIM_ANY=0
SIM_FS98=1
SIM_FS2K=2
SIM_CFS2=3
SIM_CFS1=4
SIM_FLY=5
SIM_FS2K2=6
SIM_FS2K4=7

#------------------------------------------------------------------------------

## Error constants
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

## The version of FSUIPC
fsuipc_version=0x0401
lib_version=0x0302
fs_version=SIM_FS2K4

#------------------------------------------------------------------------------

class FSUIPCException(Exception):
    """
    FSUIPC exception class. It contains a member variable named
    errorCode. The string is a text describing the error.
    """

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

open_count=0
read_count=0

#------------------------------------------------------------------------------

def open(request):
    """
    Open the connection.
    """

    global open_count, read_count
    
    open_count += 1
    if open_count<5:
        raise FSUIPCException(open_count+2)
    elif open_count==5:
        return True
    else:
        raise FSUIPCException(ERR_OPEN)

#------------------------------------------------------------------------------

def prepare_data(pattern, forRead = True):
    """
    Prepate the given pattern for reading and/or writing
    """
    return pattern

#------------------------------------------------------------------------------

flight=None
schedule_points=None

#------------------------------------------------------------------------------

def set_flight(f):
    """
    Set the flight to use for providing the data
    """

    global flight, schedule_points, read_count

    flight=f
    schedule_points=flight.get_schedule_points()
    read_count = 0

#------------------------------------------------------------------------------

fuel_weight=4.5
centre_tank_capacity=12900
side_tank_capacity=3900

def read(data):
    """
    Read the given data.
    """

    global open_count, read_count
    if open_count<5:
        raise FSUIPCException(ERR_NOTOPEN)
    
    global flight, schedule_points

    tm=time.gmtime()

    if read_count<=10:
        latitude = 0
        longitude = 0
        altitude = 0
        tas = 0
        vs = 0.0
        fuel_flow = 0.0
        fuel_remaining = 1000
        ground_altitude = 0
    else:
        dist = read_count - 10

        latitude = 0
        longitude = 0
        altitude = dist*20
        tas = 100+dist*20
        vs = dist*100.0
        fuel_flow = 3.0
        fuel_remaining = 1000 - dist*2

        ground_altitude = 0
        
    results=[]
    for (offset, type) in data:
        if offset==0x02b8:    # True airspeed (128*knots)
            results.append(int(tas*128))
        elif offset==0x02c8:    # Vertical speed (256*m/s)
            results.append(int(vs / 60.0 * 0.3048 * 256))
        elif offset==0x0560:  # Latitude
            results.append(int(latitude*10001750.0*65536.0*65536.0/90.0))
        elif offset==0x0568:  # Longitude
            results.append(int(longitude*65536.9*65536.0*65536.0*65536.0/360.0))
        elif offset==0x0570:  # Aircraft altitude in metres (fractional part)
            results.append(int( (altitude*0.3048*65536*65536)%(65536*65536)))
        elif offset==0x0574:  # Aircraft altitude in metres (whole part)
            results.append(int(altitude*.3048))
        elif offset==0x0918 or \
             offset==0x09b0:  # Engine 1 and 2 fuel flow (pounds per hour)
            results.append(fuel_flow*KGTOLBS/2.0)
        elif offset==0x0a48 or \
             offset==0x0ae0:  # Engine 3 and 4 fuel flow (pounds per hour)
            results.append(0.0)
        elif offset==0x0aec:  # Number of engines
            results.append(2)
        elif offset==0x0af4:  # Fuel weight (pounds per gallon)
            results.append(int(round(fuel_weight * 256)))
        elif offset==0x0b74:  # Centre tank level (%*128*65536)
            centre_fuel = fuel_remaining - 2*side_tank_capacity
            if centre_fuel<0: centre_fuel = 0.0
            results.append(int(round(centre_fuel/centre_tank_capacity*128.0*65536.0)))
        elif offset==0x0b78:  # Centre tank capacity (gallons)
            results.append(int(round(centre_tank_capacity*KGTOLBS/fuel_weight)))
        elif offset==0x0b7c or \
             offset==0x0b94:  # Left and right main tank level (%*128*65536)
            fuel = fuel_remaining/2
            if fuel>side_tank_capacity: fuel = side_tank_capacity
            results.append(int(round(fuel/side_tank_capacity*128.0*65536.0)))
        elif offset==0x0b80 or \
             offset==0x0b98:  # Left and right main tank capacity (gallons)
            results.append(int(round(side_tank_capacity*KGTOLBS/fuel_weight)))
        elif offset in [0x0b84, 0x0b88, 0x0b8c, 0x0b90,
                        0x0b9c, 0x0ba0, 0x0ba4, 0x0ba8,
                        0x1244, 0x1248, 0x124c, 0x1250,
                        0x1254, 0x1258, 0x125c, 0x1260]:
                              # Other tank capacities and levels
            results.append(int(0))
        elif offset==0x023a:  # Second of time
            results.append(int(tm[5]))
        elif offset==0x023b:  # Hour of UTC time
            results.append(int(tm[3]))
        elif offset==0x023c:  # Minute of UTC time
            results.append(int(tm[4]))
        elif offset==0x023e:  # Day number in year
            results.append(int(tm[7]))
        elif offset==0x0240:  # Year
            results.append(int(tm[0]))
        elif offset==0x0020:  # Ground altitude (metres*256)
            results.append(int(round(ground_altitude*FEETTOMETRES*256.0)))
        else:
            raise FSUIPCException(ERR_DATA)

    read_count += 1

    return results
                

#------------------------------------------------------------------------------

def close():
    """
    Close the connection
    """
    global open_count
    open_count = 0

#------------------------------------------------------------------------------

