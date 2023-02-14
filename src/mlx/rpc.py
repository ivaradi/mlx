from . import const
from . import rpccommon

from .common import MAVA_BASE_URL, fixUnpickled

import jsonrpclib
import hashlib
import datetime
import calendar
import sys
import ssl
import certifi

#---------------------------------------------------------------------------------------

class RPCObject(object):
    """Base class for objects read from RPC calls.

    It is possible to construct it from a dictionary."""
    def __init__(self, value, instructions = {}):
        """Construct the object.

        value is the dictionary returned by the call.

        info is a mapping from names to 'instructions' on what to do with the
        corresponding values. If the instruction is None, it will be ignored.
        If the instruction is a function, the value will be passed to it and
        the return value will be stored in the object.

        For all other names, the value will be stored as the same-named
        attribute."""
        for (key, value) in value.items():
            if key in instructions:
                instruction = instructions[key]
                if instruction is None:
                    continue

                try:
                    value = instruction(value)
                except:
                    print("Failed to convert value '%s' of attribute '%s':" % \
                        (value, key), file=sys.stderr)
                    import traceback
                    traceback.print_exc()
            setattr(self, key, value)

#---------------------------------------------------------------------------------------

class Reply(RPCObject):
    """The generic reply structure."""

#---------------------------------------------------------------------------------------

class ScheduledFlight(RPCObject):
    """A scheduled flight in the time table."""
    # The instructions for the construction
    # Type: normal flight
    TYPE_NORMAL = 0

    # Type: VIP flight
    TYPE_VIP = 1

    _instructions = {
        "id" : int,
        "pairID": int,
        "typeCode": lambda value: BookedFlight._decodeAircraftType(value),
        "departureTime": lambda value: ScheduledFlight._decodeTime(value),
        "arrivalTime": lambda value: ScheduledFlight._decodeTime(value),
        "duration": lambda value: ScheduledFlight._decodeDuration(value),
        "spec": int,
        "validFrom": lambda value: ScheduledFlight._decodeDate(value),
        "validTo": lambda value: ScheduledFlight._decodeDate(value),
        "date": lambda value: ScheduledFlight._decodeDate(value)
        }

    @staticmethod
    def _decodeTime(value):
        """Decode the given value as a time value."""
        return datetime.datetime.strptime(value, "%H:%M:%S").time()

    @staticmethod
    def _decodeDate(value):
        """Decode the given value as a date value."""
        if not value or value=="0000-00-00":
            return const.defaultDate
        else:
            return datetime.datetime.strptime(value, "%Y-%m-%d").date()

    @staticmethod
    def _decodeDuration(value):
        """Decode the given value as a duration.

        A number of seconds will be returned."""
        t = datetime.datetime.strptime(value, "%H:%M:%S")
        return (t.hour*60 + t.minute) * 60 + t.second

    def __init__(self, value):
        """Construct the scheduled flight object from the given JSON value."""
        super(ScheduledFlight, self).__init__(value,
                                              ScheduledFlight._instructions)
        self.aircraftType = self.typeCode
        del self.typeCode

        self.type = ScheduledFlight.TYPE_VIP if self.spec==1 \
          else ScheduledFlight.TYPE_NORMAL
        del self.spec

    def compareBy(self, other, name):
        """Compare this flight with the other one according to the given
        attribute name."""
        if name=="callsign":
            try:
                cs1 = int(self.callsign[2:])
                cs2 = int(other.callsign[2:])
                return 0 if cs1==cs2 else -1 if cs1<cs2 else 1
            except:
                return 0 if self.callsign==other.callsign \
                    else -1 if self.callsign<other.callsign else 1
        else:
            v1 = getattr(self, name)
            v2 = getattr(other, name)
            return 0 if v1==v2 else -1 if v1<v2 else 1

    def __repr__(self):
        return "ScheduledFlight<%d, %d, %s, %s (%s) - %s (%s) -> %d, %d>" % \
          (self.id, self.pairID, BookedFlight.TYPE2TYPECODE[self.aircraftType],
           self.departureICAO, str(self.departureTime),
           self.arrivalICAO, str(self.arrivalTime),
           self.duration, self.type)

#---------------------------------------------------------------------------------------

class ScheduledFlightPair(object):
    """A pair of scheduled flights.

    Occasionally, one of the flights may be missing."""
    @staticmethod
    def scheduledFlights2Pairs(scheduledFlights, date):
        """Convert the given list of scheduled flights into a list of flight
        pairs."""
        weekday = str(date.weekday()+1)

        flights = {}
        weekdayFlights = {}
        for flight in scheduledFlights:
            flights[flight.id] = flight
            if (flight.type==ScheduledFlight.TYPE_NORMAL and
                flight.arrivalICAO!="LHBP" and weekday in flight.days and
                flight.validFrom<=date and flight.validTo>=date) or \
               flight.type==ScheduledFlight.TYPE_VIP:
                weekdayFlights[flight.id] = flight

        flightPairs = []

        while weekdayFlights:
            (id, flight) = weekdayFlights.popitem()
            if flight.type==ScheduledFlight.TYPE_NORMAL:
                pairID = flight.pairID
                if pairID in flights:
                    pairFlight = flights[pairID]
                    if flight.departureICAO=="LHBP" or \
                      (pairFlight.departureICAO!="LHBP" and
                       flight.callsign<pairFlight.callsign):
                        flightPairs.append(ScheduledFlightPair(flight, pairFlight))
                    else:
                        flightPairs.append(ScheduledFlightPair(pairFlight, flight))
                    del flights[pairID]
                    if pairID in weekdayFlights:
                        del weekdayFlights[pairID]
            elif flight.type==ScheduledFlight.TYPE_VIP:
                flightPairs.append(ScheduledFlightPair(flight))

        flightPairs.sort(key = lambda pair: pair.flight0.date)

        return flightPairs

    def __init__(self, flight0, flight1 = None):
        """Construct the pair with the given flights."""
        self.flight0 = flight0
        self.flight1 = flight1

    def compareBy(self, other, name):
        """Compare this flight pair with the other one according to the given
        attribute name, considering the first flights."""
        return self.flight0.compareBy(other.flight0, name)

    def __repr__(self):
        return "ScheduledFlightPair<%s, %s, %s>" % \
          (self.flight0.callsign, self.flight0.departureICAO,
           self.flight0.arrivalICAO)

#---------------------------------------------------------------------------------------

class BookedFlight(RPCObject):
    """A booked flight."""
    TYPECODE2TYPE = { "B736"  : const.AIRCRAFT_B736,
                      "736"   : const.AIRCRAFT_B736,
                      "B737"  : const.AIRCRAFT_B737,
                      "73G"   : const.AIRCRAFT_B737,
                      "B738"  : const.AIRCRAFT_B738,
                      "738"   : const.AIRCRAFT_B738,
                      "B73H"  : const.AIRCRAFT_B738C,
                      "73H"   : const.AIRCRAFT_B738C,
                      "B732"  : const.AIRCRAFT_B732,
                      "732"   : const.AIRCRAFT_B732,
                      "B733"  : const.AIRCRAFT_B733,
                      "733"   : const.AIRCRAFT_B733,
                      "B734"  : const.AIRCRAFT_B734,
                      "734"   : const.AIRCRAFT_B734,
                      "B735"  : const.AIRCRAFT_B735,
                      "735"   : const.AIRCRAFT_B735,
                      "DH8D"  : const.AIRCRAFT_DH8D,
                      "DH4"   : const.AIRCRAFT_DH8D,
                      "B762"  : const.AIRCRAFT_B762,
                      "762"   : const.AIRCRAFT_B762,
                      "B763"  : const.AIRCRAFT_B763,
                      "763"   : const.AIRCRAFT_B763,
                      "CRJ2"  : const.AIRCRAFT_CRJ2,
                      "CR2"   : const.AIRCRAFT_CRJ2,
                      "F70"   : const.AIRCRAFT_F70,
                      "LI2"   : const.AIRCRAFT_DC3,
                      "T134"  : const.AIRCRAFT_T134,
                      "TU3"   : const.AIRCRAFT_T134,
                      "T154"  : const.AIRCRAFT_T154,
                      "TU5"   : const.AIRCRAFT_T154,
                      "YK40"  : const.AIRCRAFT_YK40,
                      "YK4"   : const.AIRCRAFT_YK40,
                      "B462"  : const.AIRCRAFT_B462,
                      "146"   : const.AIRCRAFT_B462,
                      "IL62"  : const.AIRCRAFT_IL62 }

    TYPE2TYPECODE = { const.AIRCRAFT_B736  : "B736",
                      const.AIRCRAFT_B737  : "B737",
                      const.AIRCRAFT_B738  : "B738",
                      const.AIRCRAFT_B738C : "B73H",
                      const.AIRCRAFT_B732  : "B732",
                      const.AIRCRAFT_B733  : "B733",
                      const.AIRCRAFT_B734  : "B734",
                      const.AIRCRAFT_B735  : "B735",
                      const.AIRCRAFT_DH8D  : "DH8D",
                      const.AIRCRAFT_B762  : "B762",
                      const.AIRCRAFT_B763  : "B763",
                      const.AIRCRAFT_CRJ2  : "CRJ2",
                      const.AIRCRAFT_F70   : "F70",
                      const.AIRCRAFT_DC3   : "LI2",
                      const.AIRCRAFT_T134  : "T134",
                      const.AIRCRAFT_T154  : "T155",
                      const.AIRCRAFT_YK40  : "YK40",
                      const.AIRCRAFT_B462  : "B462",
                      const.AIRCRAFT_IL62  : "IL62" }

    checkFlightTypes = [ const.AIRCRAFT_B736, const.AIRCRAFT_B737,
                         const.AIRCRAFT_B738, const.AIRCRAFT_DH8D ]

    @staticmethod
    def _decodeAircraftType(typeCode):
        """Decode the aircraft type from the given typeCode."""
        if typeCode in BookedFlight.TYPECODE2TYPE:
            return BookedFlight.TYPECODE2TYPE[typeCode]
        else:
            raise Exception("Invalid aircraft type code: '" + typeCode + "'")

    @staticmethod
    def _decodeStatus(status):
        """Decode the status from the status string."""
        if status=="booked":
            return BookedFlight.STATUS_BOOKED
        elif status=="reported":
            return BookedFlight.STATUS_REPORTED
        elif status=="accepted":
            return BookedFlight.STATUS_ACCEPTED
        elif status=="rejected":
            return BookedFlight.STATUS_REJECTED
        else:
            raise Exception("Invalid flight status code: '" + status + "'")

    @staticmethod
    def _convertFlightType(ft):
        """Convert the in-database flight-type to one of our constants."""
        ft = int(ft)
        if ft==0:
            return const.FLIGHTTYPE_SCHEDULED
        elif ft==1:
            return const.FLIGHTTYPE_VIP
        elif ft==2:
            return const.FLIGHTTYPE_CHARTER
        else:
            return const.FLIGHTTYPE_SCHEDULED

    @staticmethod
    def getDateTime(date, time):
        """Get a datetime object from the given textual date and time."""
        return datetime.datetime.strptime(date + " " + time,
                                          "%Y-%m-%d %H:%M:%S")

    STATUS_BOOKED = 1

    STATUS_REPORTED = 2

    STATUS_ACCEPTED = 3

    STATUS_REJECTED = 4

    @staticmethod
    def forCheckFlight(aircraftType):
        """Create a booked flight for a check flight with the given aircraft
        type."""
        flight = BookedFlight()

        flight.departureICAO = "LHBP"
        flight.arrivalICAO = "LHBP"

        flight.aircraftType = aircraftType
        flight.aircraftTypeName = BookedFlight.TYPE2TYPECODE[aircraftType]

        # FIXME: perhaps find one for the type
        flight.tailNumber = "HA-CHK"
        flight.callsign = "HA-CHK"

        flight.numPassengers = 0
        flight.numChildren = 0
        flight.numInfants = 0
        flight.numCabinCrew = 0
        flight.bagWeight = 0
        flight.cargoWeight = 0
        flight.mailWeight = 0
        flight.route = "DCT"

        t = datetime.datetime.now() + datetime.timedelta(minutes = 20)
        flight.departureTime = datetime.datetime(t.year, t.month, t.day,
                                                 t.hour, t.minute)
        t = flight.departureTime + datetime.timedelta(minutes = 30)
        flight.arrivalTime = datetime.datetime(t.year, t.month, t.day,
                                               t.hour, t.minute)

        return flight

    # The instructions for the construction
    _instructions = {
        "numPassengers" : int,
        "numChildren" : int,
        "numInfants" : int,
        "numCabinCrew" : int,
        "dowNumCabinCrew" : int,
        "numCockpitCrew" : int,
        "bagWeight" : int,
        "cargoWeight" : int,
        "mailWeight" : int,
        "flightType" : lambda value: BookedFlight._convertFlightType(value),
        "dow": int,
        "maxPassengers": int,
        "aircraftType" : lambda value: BookedFlight._decodeAircraftType(value),
        "status" : lambda value: BookedFlight._decodeStatus(value)
        }

    def __init__(self, value = None, id = None):
        """Construct the booked flight object from the given RPC result
        value."""
        self.status = BookedFlight.STATUS_BOOKED
        if value is None:
            self.id = id
        else:
            super(BookedFlight, self).__init__(value, BookedFlight._instructions)
            self.departureTime = \
              BookedFlight.getDateTime(self.date, self.departureTime)
            self.arrivalTime = \
              BookedFlight.getDateTime(self.date, self.arrivalTime)
            if self.arrivalTime<self.departureTime:
                self.arrivalTime += datetime.timedelta(days = 1)

    @property
    def payload(self):
        """Get the default payload of the flight."""
        payload= (self.numCabinCrew - self.dowNumCabinCrew) *  \
            const.WEIGHT_CABIN_CREW
        payload += self.numPassengers * \
            (const.WEIGHT_PASSENGER_CHARTER
             if self.flightType==const.FLIGHTTYPE_CHARTER
             else const.WEIGHT_PASSENGER)
        payload += self.numChildren * const.WEIGHT_CHILD
        payload += self.numInfants * const.WEIGHT_INFANT
        payload += self.bagWeight
        payload += self.cargoWeight
        payload += self.mailWeight
        return payload

    def readFromFile(self, f, fleet):
        """Read the data of the flight from a file via the given file
        object."""
        date = None
        departureTime = None
        arrivalTime = None

        line = f.readline()
        lineNumber = 0
        self.numChildren = 0
        self.numInfants = 0
        self.numCockpitCrew = 2
        self.flightType = const.FLIGHTTYPE_SCHEDULED
        while line:
            lineNumber += 1
            line = line.strip()

            hashIndex = line.find("#")
            if hashIndex>=0: line = line[:hashIndex]
            if line:
                equalIndex = line.find("=")
                lineOK = equalIndex>0

                if lineOK:
                    key = line[:equalIndex].strip()
                    value = line[equalIndex+1:].strip().replace("\:", ":")

                    lineOK = key and value

                if lineOK:
                    if key=="callsign": self.callsign = value
                    elif key=="date": date = value
                    elif key=="dep_airport": self.departureICAO = value
                    elif key=="dest_airport": self.arrivalICAO = value
                    elif key=="planecode": self.aircraftType = \
                         BookedFlight._decodeAircraftType(value)
                    elif key=="planetype": self.aircraftTypeName = value
                    elif key=="tail_nr": self.tailNumber = value
                    elif key=="passenger": self.numPassengers = int(value)
                    elif key=="child": self.numChildren = int(value)
                    elif key=="infant": self.numInfants = int(value)
                    elif key=="crew": self.numCabinCrew = int(value) - 2
                    elif key=="cabin_crew": self.numCabinCrew = int(value)
                    elif key=="cockpit_crew": self.numCockpitCrew = int(value)
                    elif key=="bag": self.bagWeight = int(value)
                    elif key=="cargo": self.cargoWeight = int(value)
                    elif key=="mail": self.mailWeight = int(value)
                    elif key=="flight_route": self.route = value
                    elif key=="departure_time": departureTime = value
                    elif key=="arrival_time": arrivalTime = value
                    elif key=="foglalas_id":
                        self.id = None if value=="0" else value
                    elif key=="flight_type": self.flightType = int(value)
                    else: lineOK = False

                if not lineOK:
                    print("web.BookedFlight.readFromFile: line %d is invalid" % \
                          (lineNumber,))

            line = f.readline()

        if date is not None:
            if departureTime is not None:
                self.departureTime = BookedFlight.getDateTime(date,
                                                              departureTime)
            if arrivalTime is not None:
                self.arrivalTime = BookedFlight.getDateTime(date,
                                                            arrivalTime)

        d = dir(self)
        for attribute in ["callsign", "departureICAO", "arrivalICAO",
                          "aircraftType", "tailNumber",
                          "numPassengers", "numCockpitCrew", "numCabinCrew",
                          "bagWeight", "cargoWeight", "mailWeight",
                          "route", "departureTime", "arrivalTime"]:
            if attribute not in d:
                raise Exception("Attribute %s could not be read" % (attribute,))

        if "aircraftTypeName" not in d:
            self.aircraftTypeName = \
                BookedFlight.TYPE2TYPECODE[self.aircraftType]

        plane = fleet[self.tailNumber]
        if plane is None:
            self.dow = 0
            self.maxPassengers = 0
            self.dowNumCabinCrew = 0
        else:
            self.dow = plane.dow
            self.maxPassengers = plane.maxPassengers
            self.dowNumCabinCrew = plane.dowNumCabinCrew

    def setupFromPIREPData(self, pirepData):
        """Setup the booked flight from the given PIREP data."""
        bookedFlightData = pirepData["bookedFlight"]

        self.callsign = bookedFlightData["callsign"]

        date = bookedFlightData["date"]

        departureTime = bookedFlightData["departureTime"]
        self.departureTime = BookedFlight.getDateTime(date, departureTime)

        arrivalTime = bookedFlightData["arrivalTime"]
        self.arrivalTime = BookedFlight.getDateTime(date, arrivalTime)
        if self.arrivalTime<self.departureTime:
            self.arrivalTime += datetime.timedelta(days = 1)

        self.departureICAO = bookedFlightData["departureICAO"]
        self.arrivalICAO = bookedFlightData["arrivalICAO"]

        self.aircraftType = \
            BookedFlight._decodeAircraftType(bookedFlightData["aircraftType"])
        self.tailNumber = bookedFlightData["tailNumber"]
        self.numPassengers = int(bookedFlightData["numPassengers"])
        self.numChildren = int(bookedFlightData["numChildren"])
        self.numInfants = int(bookedFlightData["numInfants"])
        self.maxPassengers = int(bookedFlightData["maxPassengers"])
        self.numCockpitCrew = int(bookedFlightData["numCockpitCrew"])
        self.numCabinCrew = int(bookedFlightData["numCabinCrew"])
        self.bagWeight = int(bookedFlightData["bagWeight"])
        self.cargoWeight = int(bookedFlightData["cargoWeight"])
        self.mailWeight = int(bookedFlightData["mailWeight"])
        self.route = bookedFlightData["route"]
        self.flightType = BookedFlight._convertFlightType(bookedFlightData["flightType"])

    def writeIntoFile(self, f):
        """Write the flight into a file."""
        print("callsign=%s" % (self.callsign,), file=f)
        date = self.departureTime.date()
        print("date=%04d-%02d-%0d" % (date.year, date.month, date.day), file=f)
        print("dep_airport=%s" % (self.departureICAO,), file=f)
        print("dest_airport=%s" % (self.arrivalICAO,), file=f)
        print("planecode=%s" % \
              (BookedFlight.TYPE2TYPECODE[self.aircraftType],), file=f)
        print("planetype=%s" % (self.aircraftTypeName,), file=f)
        print("tail_nr=%s" % (self.tailNumber,), file=f)
        print("passenger=%d" % (self.numPassengers,), file=f)
        print("child=%d" % (self.numChildren,), file=f)
        print("infant=%d" % (self.numInfants,), file=f)
        print("cockpit_crew=%d" % (self.numCockpitCrew,), file=f)
        print("cabin_crew=%d" % (self.numCabinCrew,), file=f)
        print("bag=%d" % (self.bagWeight,), file=f)
        print("cargo=%d" % (self.cargoWeight,), file=f)
        print("mail=%d" % (self.mailWeight,), file=f)
        print("flight_route=%s" % (self.route,), file=f)
        departureTime = self.departureTime
        print("departure_time=%02d\\:%02d\\:%02d" % \
              (departureTime.hour, departureTime.minute, departureTime.second), file=f)
        arrivalTime = self.arrivalTime
        print("arrival_time=%02d\\:%02d\\:%02d" % \
              (arrivalTime.hour, arrivalTime.minute, arrivalTime.second), file=f)
        print("foglalas_id=%s" % ("0" if self.id is None else self.id,), file=f)
        print("flight_type=%d" % (self.flightType,))

    def __setstate__(self, state):
        """Set the state from the given unpickled dictionary."""
        self.__dict__.update(fixUnpickled(state))

    def __repr__(self):
        """Get a representation of the flight."""
        s = "<Flight: %s-%s, %s, %s-%s," % (self.departureICAO,
                                           self.arrivalICAO,
                                           self.route,
                                           self.departureTime, self.arrivalTime)
        s += " %d %s," % (self.aircraftType, self.tailNumber)
        s += " pax=%d+%d+%d, crew=%d+%d, bag=%d, cargo=%d, mail=%d" % \
             (self.numPassengers, self.numChildren, self.numInfants,
              self.numCockpitCrew, self.numCabinCrew,
              self.bagWeight, self.cargoWeight, self.mailWeight)
        s += ">"
        return s

#---------------------------------------------------------------------------------------

class AcceptedFlight(RPCObject):
    """A flight that has been already accepted."""
    # The instructions for the construction
    @staticmethod
    def parseTimestamp(s):
        """Parse the given RPC timestamp."""
        dt = datetime.datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
        return calendar.timegm(dt.utctimetuple())

    _instructions = {
        "bookedFlight" : lambda value: BookedFlight(value),
        "numPassengers" : int,
        "numChildren" : int,
        "numInfants" : int,
        "fuelUsed" : int,
        "rating" : lambda value: float(value) if value else 0.0
        }

    def __init__(self, value):
        """Construct the booked flight object from the given RPC result
        value."""
        super(AcceptedFlight, self).__init__(value, AcceptedFlight._instructions)
        self.flightTimeStart = \
          AcceptedFlight.parseTimestamp(self.flightDate + " " +
                                        self.flightTimeStart)
        self.flightTimeEnd = \
          AcceptedFlight.parseTimestamp(self.flightDate + " " +
                                        self.flightTimeEnd)
        if self.flightTimeEnd<self.flightTimeStart:
            self.flightTimeEnd += 24*60*60

        self.totalNumPassengers = self.numPassengers + self.numChildren + self.numInfants

#---------------------------------------------------------------------------------------

class Plane(rpccommon.Plane, RPCObject):
    """An airplane in the fleet."""
    _instructions = {
        "status" : lambda value: rpccommon.Plane.str2status(value),
        "gateNumber" : lambda value: value if value else None,
        "typeCode": lambda value: BookedFlight._decodeAircraftType(value),
        "dow": int,
        "dowNumCabinCrew": int,
        "maxPassengers": int,
        }

    def __init__(self, value):
        """Construct the plane."""
        RPCObject.__init__(self, value, instructions = Plane._instructions)
        self.aircraftType = self.typeCode
        del self.typeCode

#---------------------------------------------------------------------------------------

class Fleet(rpccommon.Fleet):
    """The fleet."""
    def __init__(self, value):
        """Construct the fleet."""
        super(Fleet, self).__init__()
        for planeValue in value:
            self._addPlane(Plane(planeValue))

#---------------------------------------------------------------------------------------

class Registration(object):
    """Data for registration."""
    def __init__(self, surName, firstName, nameOrder,
                 yearOfBirth, emailAddress, emailAddressPublic,
                 vatsimID, ivaoID, phoneNumber, nationality, password):
        """Construct the registration data."""
        self.surName = surName
        self.firstName = firstName
        self.nameOrder = nameOrder
        self.yearOfBirth = yearOfBirth
        self.emailAddress = emailAddress
        self.emailAddressPublic = 1 if emailAddressPublic is True else \
          0 if emailAddressPublic is False else emailAddressPublic
        self.vatsimID = "" if vatsimID is None else vatsimID
        self.ivaoID = "" if ivaoID is None else ivaoID
        self.phoneNumber = phoneNumber
        self.nationality = nationality
        self.password = password

#---------------------------------------------------------------------------------------

class RPCException(Exception):
    """An exception thrown by RPC operations."""
    def __init__(self, result, message = None):
        """Construct the exception."""
        self._result = result
        if message is None:
            message = "RPC call failed with result code: %d" % (result,)
        super(RPCException, self).__init__(message)

    @property
    def result(self):
        """Get the result code."""
        return self._result

#---------------------------------------------------------------------------------------

class Client(object):
    """The RPC client interface."""
    # The client protocol version
    VERSION = 2

    # Result code: OK
    RESULT_OK = 0

    # Result code: the login has failed
    RESULT_LOGIN_FAILED = 1

    # Result code: the given session ID is unknown (it might have expired).
    RESULT_SESSION_INVALID = 2

    # Result code: some database error
    RESULT_DATABASE_ERROR = 3

    # Result code: invalid data
    RESULT_INVALID_DATA = 4

    # Result code: the flight does not exist
    RESULT_FLIGHT_NOT_EXISTS = 101

    # Result code: the flight has already been reported.
    RESULT_FLIGHT_ALREADY_REPORTED = 102

    # Result code: a user with the given e-mail address already exists
    RESULT_EMAIL_ALREADY_REGISTERED = 103

    def __init__(self, getCredentialsFn):
        """Construct the client."""
        self._getCredentialsFn = getCredentialsFn

        sslContext = ssl.SSLContext()
        sslContext.load_verify_locations(cafile = certifi.where())
        transport = jsonrpclib.jsonrpc.SafeTransport(jsonrpclib.config.DEFAULT,
                                                     sslContext)

        self._server = jsonrpclib.Server(MAVA_BASE_URL + "/jsonrpc.php",
                                         transport = transport)

        self._userName = None
        self._passwordHash = None
        self._sessionID = None
        self._loginCount = 0

    @property
    def valid(self):
        """Determine if the client is valid, i.e. there is a session ID
        stored."""
        return self._sessionID is not None

    def setCredentials(self, userName, password):
        """Set the credentials for future logins."""

        self._userName = userName

        md5 = hashlib.md5()
        md5.update(password.encode("utf-8"))
        self._passwordHash = md5.hexdigest()

        self._sessionID = None

    def register(self, registrationData):
        """Register with the given data.

        Returns a tuple of:
        - the error code,
        - the PID if there is no error."""
        reply = Reply(self._server.register(registrationData))

        return (reply.result,
                reply.value["pid"] if reply.result==Client.RESULT_OK else None)

    def login(self):
        """Login using the given previously set credentials.

        The session ID is stored in the object and used for later calls.

        Returns the name of the pilot on success, or None on error."""
        self._sessionID = None

        reply = Reply(self._server.login(self._userName, self._passwordHash,
                                         Client.VERSION))
        if reply.result == Client.RESULT_OK:
            self._loginCount += 1
            self._sessionID = reply.value["sessionID"]

            types = [BookedFlight.TYPECODE2TYPE[typeCode]
                     for typeCode in reply.value["typeCodes"]]

            return (reply.value["name"], reply.value["rank"], types,
                    self._sessionID)
        else:
            return None

    def getFlights(self):
        """Get the flights available for performing."""
        bookedFlights = []
        reportedFlights = []
        rejectedFlights = []

        value = self._performCall(lambda sessionID:
                                  self._server.getFlights(sessionID))
        for flightData in value:
            flight = BookedFlight(flightData)
            if flight.status == BookedFlight.STATUS_BOOKED:
                bookedFlights.append(flight)
            elif flight.status == BookedFlight.STATUS_REPORTED:
                reportedFlights.append(flight)
            elif flight.status == BookedFlight.STATUS_REJECTED:
                rejectedFlights.append(flight)

        for flights in [bookedFlights, reportedFlights, rejectedFlights]:
            flights.sort(key = lambda flight: flight.departureTime)

        return (bookedFlights, reportedFlights, rejectedFlights)

    def getAcceptedFlights(self):
        """Get the flights that are already accepted."""
        value = self._performCall(lambda sessionID:
                                  self._server.getAcceptedFlights(sessionID))
        flights = []
        for flight in value:
            flights.append(AcceptedFlight(flight))
        return flights

    def getEntryExamStatus(self):
        """Get the status of the exams needed for joining MAVA."""
        value = self._performCall(lambda sessionID:
                                  self._server.getEntryExamStatus(sessionID))
        return (value["entryExamPassed"], value["entryExamLink"],
                value["checkFlightStatus"], value["madeFO"])

    def getFleet(self):
        """Query and return the fleet."""
        value = self._performCall(lambda sessionID:
                                  self._server.getFleet(sessionID))

        return Fleet(value)

    def updatePlane(self, tailNumber, status, gateNumber):
        """Update the state and position of the plane with the given tail
        number."""
        status = rpccommon.Plane.status2str(status)
        self._performCall(lambda sessionID:
                          self._server.updatePlane(sessionID, tailNumber,
                                                   status, gateNumber))

    def addPIREP(self, flightID, pirep, update = False):
        """Add the PIREP for the given flight."""
        (result, _value) = \
          self._performCall(lambda sessionID:
                            self._server.addPIREP(sessionID, flightID, pirep,
                                                  update),
                            acceptResults = [Client.RESULT_FLIGHT_ALREADY_REPORTED,
                                             Client.RESULT_FLIGHT_NOT_EXISTS])
        return result

    def updateOnlineACARS(self, acars):
        """Update the online ACARS from the given data."""
        self._performCall(lambda sessionID:
                          self._server.updateOnlineACARS(sessionID, acars))

    def setCheckFlightPassed(self, type):
        """Mark the check flight of the user passed with the given type."""
        self._performCall(lambda sessionID:
                          self._server.setCheckFlightPassed(sessionID, type))

    def getPIREP(self, flightID):
        """Get the PIREP data for the flight with the given ID."""
        value = self._performCall(lambda sessionID:
                                  self._server.getPIREP(sessionID, flightID))
        return value

    def reflyFlights(self, flightIDs):
        """Mark the flights with the given IDs for reflying."""
        self._performCall(lambda sessionID:
                          self._server.reflyFlights(sessionID, flightIDs))

    def deleteFlights(self, flightIDs):
        """Delete the flights with the given IDs."""
        self._performCall(lambda sessionID:
                          self._server.deleteFlights(sessionID, flightIDs))

    def getTimetable(self, date, types = None):
        """Get the time table for the given date restricted to the given list
        of type codes, if any."""
        typeCodes = None if types is None else \
            [BookedFlight.TYPE2TYPECODE[type] for type in types]

        values = self._performCall(lambda sessionID:
                                   self._server.getTimetable(sessionID,
                                                             date.strftime("%Y-%m-%d"),
                                                             date.weekday()+1,
                                                             typeCodes))
        return ScheduledFlightPair.scheduledFlights2Pairs([ScheduledFlight(value)
                                                          for value in values],
                                                          date)

    def bookFlights(self, flightIDs, date, tailNumber):
        """Book the flights with the given IDs on the given date to be flown
        with the plane of the given tail number."""
        values = self._performCall(lambda sessionID:
                                   self._server.bookFlights(sessionID,
                                                            flightIDs,
                                                            date.strftime("%Y-%m-%d"),
                                                            tailNumber))
        return [BookedFlight(value) for value in values]

    def getSimBriefResult(self, timestamp):
        """Get the SimBrief results for the given timestamp."""
        return self._performCall(lambda sessionID:
                                 self._server.getSimBriefResult(sessionID,
                                                                timestamp))

    def _performCall(self, callFn, acceptResults = []):
        """Perform a call using the given call function.

        acceptResults should be a list of result codes that should be accepted
        besides RESULT_OK. If this list is not empty, the returned value is a
        tuple of the result code and the corresponding value. Otherwise only
        RESULT_OK is accepted, and the value is returned.

        All other error codes are converted to exceptions."""
        numAttempts = 0
        while True:
            reply = Reply(callFn(self._ensureSession()))
            numAttempts += 1
            result = reply.result
            if result==Client.RESULT_SESSION_INVALID:
                self._sessionID = None
                if numAttempts==3:
                    raise RPCException(result)
            elif result!=Client.RESULT_OK and result not in acceptResults:
                raise RPCException(result)
            elif acceptResults:
                return (result, reply.value)
            else:
                return reply.value

    def _ensureSession(self):
        """Ensure that there is a valid session ID."""
        while self._sessionID is None:
            if self._userName is not None and self._passwordHash is not None:
                if not self.login():
                    self._userName = self._passwordHash = None

            if self._userName is None or self._passwordHash is None:
                (self._userName, password) = self._getCredentialsFn()
                if self._userName is None:
                    raise RPCException(Client.RESULT_LOGIN_FAILED)

                md5 = hashlib.md5()
                md5.update(password)
                self._passwordHash = md5.hexdigest()

        return self._sessionID

#---------------------------------------------------------------------------------------
