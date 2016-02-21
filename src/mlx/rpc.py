import const
import rpccommon

from common import MAVA_BASE_URL

import jsonrpclib
import hashlib
import datetime

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
        for (key, value) in value.iteritems():
            if key in instructions:
                instruction = instructions[key]
                if instruction is None:
                    continue

                value = instruction(value)
            setattr(self, key, value)

#---------------------------------------------------------------------------------------

class Reply(RPCObject):
    """The generic reply structure."""

#---------------------------------------------------------------------------------------

class BookedFlight(RPCObject):
    """A booked flight."""
    # FIXME: copied from web.BookedFlight
    TYPECODE2TYPE = { "736"  : const.AIRCRAFT_B736,
                      "73G"  : const.AIRCRAFT_B737,
                      "738"  : const.AIRCRAFT_B738,
                      "73H"  : const.AIRCRAFT_B738C,
                      "733"  : const.AIRCRAFT_B733,
                      "734"  : const.AIRCRAFT_B734,
                      "735"  : const.AIRCRAFT_B735,
                      "DH4"  : const.AIRCRAFT_DH8D,
                      "762"  : const.AIRCRAFT_B762,
                      "763"  : const.AIRCRAFT_B763,
                      "CR2"  : const.AIRCRAFT_CRJ2,
                      "F70"  : const.AIRCRAFT_F70,
                      "LI2"  : const.AIRCRAFT_DC3,
                      "TU3"  : const.AIRCRAFT_T134,
                      "TU5"  : const.AIRCRAFT_T154,
                      "YK4"  : const.AIRCRAFT_YK40,
                      "146"  : const.AIRCRAFT_B462 }

    # FIXME: copied from web.BookedFlight
    @staticmethod
    def _decodeAircraftType(typeCode):
        """Decode the aircraft type from the given typeCode."""
        if typeCode in BookedFlight.TYPECODE2TYPE:
            return BookedFlight.TYPECODE2TYPE[typeCode]
        else:
            raise Exception("Invalid aircraft type code: '" + typeCode + "'")

    # FIXME: copied from web.BookedFlight
    @staticmethod
    def getDateTime(date, time):
        """Get a datetime object from the given textual date and time."""
        return datetime.datetime.strptime(date + " " + time,
                                          "%Y-%m-%d %H:%M:%S")

    # The instructions for the construction
    _instructions = {
        "numPassengers" : int,
        "numCrew" : int,
        "bagWeight" : int,
        "cargoWeight" : int,
        "mailWeight" : int,
        "aircraftType" : lambda value: BookedFlight._decodeAircraftType(value)
        }

    def __init__(self, value):
        """Construct the booked flight object from the given RPC result
        value."""
        super(BookedFlight, self).__init__(value, BookedFlight._instructions)
        self.departureTime = \
          BookedFlight.getDateTime(self.date, self.departureTime)
        self.arrivalTime = \
          BookedFlight.getDateTime(self.date, self.arrivalTime)
        if self.arrivalTime<self.departureTime:
            self.arrivalTime += datetime.timedelta(days = 1)

#---------------------------------------------------------------------------------------

class Plane(rpccommon.Plane, RPCObject):
    """An airplane in the fleet."""
    _instructions = {
        "status" : lambda value: rpccommon.Plane.str2status(value),
        "gateNumber" : lambda value: value if value else None
        }

    def __init__(self, value):
        """Construct the plane."""
        RPCObject.__init__(self, value, instructions = Plane._instructions)

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

        self._server = jsonrpclib.Server(MAVA_BASE_URL + "/jsonrpc.php")

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
        md5.update(password)
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

        reply = Reply(self._server.login(self._userName, self._passwordHash))
        if reply.result == Client.RESULT_OK:
            self._loginCount += 1
            self._sessionID = reply.value["sessionID"]
            return (reply.value["name"], reply.value["rank"])
        else:
            return None

    def getFlights(self):
        """Get the flights available for performing."""
        flights = []

        value = self._performCall(lambda sessionID:
                                  self._server.getFlights(sessionID))
        for flightData in value:
            flights.append(BookedFlight(flightData))

        flights.sort(cmp = lambda flight1, flight2:
                     cmp(flight1.departureTime, flight2.departureTime))

        return flights

    def getEntryExamStatus(self):
        """Get the status of the exams needed for joining MAVA."""
        value = self._performCall(lambda sessionID:
                                  self._server.getEntryExamStatus(sessionID))
        return (value["entryExamPassed"], value["entryExamLink"],
                value["checkFlightStatus"])

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

    def addPIREP(self, flightID, pirep):
        """Add the PIREP for the given flight."""
        (result, _value) = \
          self._performCall(lambda sessionID:
                            self._server.addPIREP(sessionID, flightID, pirep),
                            acceptResults = [Client.RESULT_FLIGHT_ALREADY_REPORTED,
                                             Client.RESULT_FLIGHT_NOT_EXISTS])
        return result

    def updateOnlineACARS(self, acars):
        """Update the online ACARS from the given data."""
        self._performCall(lambda sessionID:
                          self._server.updateOnlineACARS(sessionID, acars))

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
