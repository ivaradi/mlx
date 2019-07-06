
import math
import time
import sys
import codecs

#------------------------------------------------------------------------------

## @package mlx.util
#
# Utilities.

#------------------------------------------------------------------------------

## The average of the radius at the poles and a the equator, in metres
#EARTH_RADIUS=6367467.4
EARTH_RADIUS=6371000
#EARTH_RADIUS=6378137

#------------------------------------------------------------------------------

def getDegMinSec(degrees):
    """Break up the given floating point degrees value into a tuple.

    The tuple contains 4 items:
    - the degrees as an integer
    - the minutes as an integer
    - the seconds as an integer
    - 1.0 if the value was non-negative, -1.0 if it was negative."""

    if degrees<0:
        degrees = -degrees
        mul = -1.0
    else:
        mul = 1.0

    deg = int(degrees)
    min = int((degrees*60.0)%60.0)
    sec = int((degrees*3600.0)%60.0)

    return (deg, min, sec, mul)

#------------------------------------------------------------------------------

def getCoordinateString(coordinates):
    """Get the string representation of the given coordinate pair."""
    (latitude, longitude) = coordinates
    latitude_str = getLatitudeString(latitude)
    longitude_str = getLongitudeString(longitude)

    return latitude_str + " " + longitude_str

#------------------------------------------------------------------------------

def getLatitudeString(latitude):
    """Get a string representation of the given latitude."""
    return getDegreeString(latitude, ["N", "S"])

#------------------------------------------------------------------------------

def getLongitudeString(longitude):
    """Get a string representation of the given longitude."""

    return getDegreeString(longitude, ["E", "W"])

#------------------------------------------------------------------------------

def getDegreeString(degree, prefixes):
    """Get a string representation of the given degree.

    If the sign is positive, prefixes[0], otherwise prefixes[1] will be
    prepended to the string."""

    if degree<0:
        prefix = prefixes[1]
    else:
        prefix = prefixes[0]

    (deg, min, sec, _sign) = getDegMinSec(degree)

    return "%s%d\u00b0%02d\u2032%02d\u2033" % (prefix, deg, min, sec)

#------------------------------------------------------------------------------

def getTimestampString(timestamp):
    """Get the string representation of the given timestamp."""
    return time.strftime("%H:%M:%S", time.gmtime(timestamp))

#------------------------------------------------------------------------------

def getTimeIntervalString(seconds):
    """Get a more human-friendly representation of the given time interval
    expressed in seconds."""
    hours = int(seconds / 3600)
    minutes = int((seconds / 60) % 60)
    seconds = int(seconds % 60)
    return "%02d:%02d:%02d" % (hours, minutes, seconds)

#------------------------------------------------------------------------------

def km2nm(km):
    """Convert the given kilometres into nautical miles."""
    return km/1.852

#------------------------------------------------------------------------------

def nm2km(nm):
    """Convert the given nautical miles into kilometres."""
    return nm*1.852

#------------------------------------------------------------------------------

def radians2km(radians):
    """Convert the given radians into kilometres"""
    return radians * EARTH_RADIUS / 1000.0

#------------------------------------------------------------------------------

def radians2nm(radians):
    """Convert the given radians into nautical miles."""
    return km2nm(radians2km(radians))

#------------------------------------------------------------------------------

def getDistCourse(latitude1, longitude1, latitude2, longitude2):
    """Get the distance and course between the two geographical coordinates.

    This function calculates the rhumb distance."""

    latitude1 = math.radians(latitude1)
    longitude1 = math.radians(longitude1)

    latitude2 = math.radians(latitude2)
    longitude2 = math.radians(longitude2)

    dlon_W = (longitude1 - longitude2) % (math.pi*2)
    dlon_E = (longitude2 - longitude1) % (math.pi*2)

    dphi = math.log(math.tan(latitude2/2 + math.pi/4)/
                    math.tan(latitude1/2 + math.pi/4))

    if abs(latitude1-latitude2) < math.sqrt(1e-15):
        q = math.cos(latitude1)
    else:
        q = (latitude1-latitude2)/dphi

    if dlon_W < dlon_E:
        tc = math.atan2(-dlon_W, dphi) % (math.pi*2)
        d = math.sqrt(math.pow(q*dlon_W, 2) +
                      math.pow(latitude1-latitude2, 2))
    else:
        tc = math.atan2(dlon_E, dphi) % (math.pi*2)
        d = math.sqrt(math.pow(q*dlon_E, 2) +
                      math.pow(latitude1-latitude2, 2))

    return (radians2nm(d), math.degrees(tc))

#------------------------------------------------------------------------------

def visibility2String(visibility):
    """Convert the given visibility expressed in metres into a string."""
    return "%.0f metres" % (visibility,) if visibility<10000 \
           else "%.1f kilometres" % (visibility/1000.0,)

#------------------------------------------------------------------------------

secondaryInstallation="secondary" in sys.argv

#------------------------------------------------------------------------------

_utf8decoder = codecs.getdecoder("utf-8")
_latin2decoder = codecs.getdecoder("iso8859-2")

def utf2unicode(text):
    """Convert the given text from UTF-8 encoding to unicode."""
    if isinstance(text, str):
        if text.startswith("list indices must be"):
            import traceback
            traceback.print_exc()

        return text

    try:
        return str(_utf8decoder(text)[0])
    except:
        import traceback
        traceback.print_exc()
        try:
            return str(_latin2decoder(text)[0])
        except:
            return str(list(text))
