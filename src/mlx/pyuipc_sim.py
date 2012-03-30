# Simulator for the pyuipc module
#------------------------------------------------------------------------------

import time

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
    result = []
    for (offset, type) in data:
        if offset==0x023a:         # Second of time
            result.append(time.gmtime().tm_sec)
        elif offset==0x023b:       # Hour of Zulu time
            result.append(time.gmtime().tm_hour)
        elif offset==0x023c:       # Minute of Zulu time
            result.append(time.gmtime().tm_min)
        elif offset==0x023e:       # Day number on year
            result.append(time.gmtime().tm_yday)
        elif offset==0x0240:       # Year in FS
            result.append(time.gmtime().tm_year)
        elif offset==0x3c00:       # Path of the current AIR file
            result.append("c:\\Program Files\\Microsoft Games\\FS9\\Aircraft\\kutya")
        elif offset==0x3d00:       # Name of the current aircraft
            result.append("Cessna 172")
        else:
            print "Unhandled offset: %04x" % (offset,)
            raise FSUIPCException(ERR_DATA)
    return result
            
#------------------------------------------------------------------------------

def close():
    """Close the connection."""
    pass

#------------------------------------------------------------------------------
