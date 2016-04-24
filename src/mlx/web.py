
import const
import util
from rpc import Registration
import rpc
import rpccommon

from common import MAVA_BASE_URL

import threading
import sys
import urllib
import urllib2
import hashlib
import time
import datetime
import codecs
import traceback
import xml.sax
import xmlrpclib
import HTMLParser

#---------------------------------------------------------------------------------------

## @package mlx.web
#
# Web interface.
#
# This module implements a thread that can perform (HTTP) requests
# asynchronously. When the request is performed, a callback is called. The main
# interface is the \ref Handler class. Each of its functions creates a \ref
# Request subclass instance and puts it to the request queue. The handler
# thread then takes the requests one by one, and executes them.
#
# This module also defines some data classes the contents of which are
# retrieved or sent via HTTP. \ref BookedFlight contains data of a flight
# booked on the MAVA website, \ref Fleet and \ref Plane represents the MAVA
# fleet and the gates at Ferihegy and \ref NOTAM is a NOTAM.

#---------------------------------------------------------------------------------------

def readline(f):
    """Read a line from the given file.

    The line is stripped and empty lines are discarded."""
    while True:
        line = f.readline()
        if not line: return ""
        line = line.strip()
        if line:
            return line

#---------------------------------------------------------------------------------------

class BookedFlight(object):
    """A flight that was booked."""
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

    TYPE2TYPECODE = { const.AIRCRAFT_B736  : "736",
                      const.AIRCRAFT_B737  : "73G",
                      const.AIRCRAFT_B738  : "738",
                      const.AIRCRAFT_B738C : "73H",
                      const.AIRCRAFT_B733  : "733",
                      const.AIRCRAFT_B734  : "734",
                      const.AIRCRAFT_B735  : "735",
                      const.AIRCRAFT_DH8D  : "DH4",
                      const.AIRCRAFT_B762  : "762",
                      const.AIRCRAFT_B763  : "763",
                      const.AIRCRAFT_CRJ2  : "CR2",
                      const.AIRCRAFT_F70   : "F70",
                      const.AIRCRAFT_DC3   : "LI2",
                      const.AIRCRAFT_T134  : "TU3",
                      const.AIRCRAFT_T154  : "TU5",
                      const.AIRCRAFT_YK40  : "YK4",
                      const.AIRCRAFT_B462  : "146" }

    checkFlightTypes = [ const.AIRCRAFT_B736, const.AIRCRAFT_B737,
                         const.AIRCRAFT_B738, const.AIRCRAFT_DH8D ]

    @staticmethod
    def getDateTime(date, time):
        """Get a datetime object from the given textual date and time."""
        return datetime.datetime.strptime(date + " " + time,
                                          "%Y-%m-%d %H:%M:%S")

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
        flight.numCrew = 2
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

    def __init__(self, id = None):
        """Construct a booked flight with the given ID."""
        self.id = id

    def readFromWeb(self, f):
        """Read the data of the flight from the web via the given file
        object."""
        self.callsign = readline(f)

        date = readline(f)
        print "web.BookedFlight.readFromWeb: date:", date
        if date=="0000-00-00": date = "0001-01-01"

        self.departureICAO = readline(f)
        self.arrivalICAO = readline(f)

        self._readAircraftType(f)
        self.tailNumber = readline(f)
        self.numPassengers = int(readline(f))
        self.numCrew = int(readline(f))
        self.bagWeight = int(readline(f))
        self.cargoWeight = int(readline(f))
        self.mailWeight = int(readline(f))
        self.route = readline(f)

        departureTime = readline(f)
        self.departureTime = BookedFlight.getDateTime(date, departureTime)

        arrivalTime = readline(f)
        self.arrivalTime = BookedFlight.getDateTime(date, arrivalTime)
        if self.arrivalTime<self.departureTime:
            self.arrivalTime += datetime.timedelta(days = 1)

        if not readline(f)==".NEXT.":
            raise Exception("Invalid line in flight data")

    def readFromFile(self, f):
        """Read the data of the flight from a file via the given file
        object."""
        date = None
        departureTime = None
        arrivalTime = None

        line = f.readline()
        lineNumber = 0
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
                         self._decodeAircraftType(value)
                    elif key=="planetype": self.aircraftTypeName = value
                    elif key=="tail_nr": self.tailNumber = value
                    elif key=="passenger": self.numPassengers = int(value)
                    elif key=="crew": self.numCrew = int(value)
                    elif key=="bag": self.bagWeight = int(value)
                    elif key=="cargo": self.cargoWeight = int(value)
                    elif key=="mail": self.mailWeight = int(value)
                    elif key=="flight_route": self.route = value
                    elif key=="departure_time": departureTime = value
                    elif key=="arrival_time": arrivalTime = value
                    elif key=="foglalas_id":
                        self.id = None if value=="0" else value
                    else: lineOK = False

                if not lineOK:
                    print "web.BookedFlight.readFromFile: line %d is invalid" % \
                          (lineNumber,)

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
                          "numPassengers", "numCrew",
                          "bagWeight", "cargoWeight", "mailWeight",
                          "route", "departureTime", "arrivalTime"]:
            if attribute not in d:
                raise Exception("Attribute %s could not be read" % (attribute,))

        if "aircraftTypeName" not in d:
            self.aircraftTypeName = \
                BookedFlight.TYPE2TYPECODE[self.aircraftType]

    def writeIntoFile(self, f):
        """Write the flight into a file."""
        print >> f, "callsign=%s" % (self.callsign,)
        date = self.departureTime.date()
        print >> f, "date=%04d-%02d-%0d" % (date.year, date.month, date.day)
        print >> f, "dep_airport=%s" % (self.departureICAO,)
        print >> f, "dest_airport=%s" % (self.arrivalICAO,)
        print >> f, "planecode=%s" % \
              (BookedFlight.TYPE2TYPECODE[self.aircraftType],)
        print >> f, "planetype=%s" % (self.aircraftTypeName,)
        print >> f, "tail_nr=%s" % (self.tailNumber,)
        print >> f, "passenger=%d" % (self.numPassengers,)
        print >> f, "crew=%d" % (self.numCrew,)
        print >> f, "bag=%d" % (self.bagWeight,)
        print >> f, "cargo=%d" % (self.cargoWeight,)
        print >> f, "mail=%d" % (self.mailWeight,)
        print >> f, "flight_route=%s" % (self.route,)
        departureTime = self.departureTime
        print >> f, "departure_time=%02d\\:%02d\\:%02d" % \
              (departureTime.hour, departureTime.minute, departureTime.second)
        arrivalTime = self.arrivalTime
        print >> f, "arrival_time=%02d\\:%02d\\:%02d" % \
              (arrivalTime.hour, arrivalTime.minute, arrivalTime.second)
        print >> f, "foglalas_id=%s" % ("0" if self.id is None else self.id,)

    def _readAircraftType(self, f):
        """Read the aircraft type from the given file."""
        line = readline(f)
        typeCode = line[:3]
        self.aircraftType = self._decodeAircraftType(typeCode)
        self.aircraftTypeName = line[3:]

    def _decodeAircraftType(self, typeCode):
        """Decode the aircraft type from the given typeCode."""
        if typeCode in self.TYPECODE2TYPE:
            return self.TYPECODE2TYPE[typeCode]
        else:
            raise Exception("Invalid aircraft type code: '" + typeCode + "'")

    def __repr__(self):
        """Get a representation of the flight."""
        s = "<Flight: %s-%s, %s, %s-%s," % (self.departureICAO,
                                           self.arrivalICAO,
                                           self.route,
                                           self.departureTime, self.arrivalTime)
        s += " %d %s," % (self.aircraftType, self.tailNumber)
        s += " pax=%d, crew=%d, bag=%d, cargo=%d, mail=%d" % \
             (self.numPassengers, self.numCrew,
              self.bagWeight, self.cargoWeight, self.mailWeight)
        s += ">"
        return s

#------------------------------------------------------------------------------

class Plane(rpccommon.Plane):
    """Information about an airplane in the fleet."""
    def __init__(self, s):
        """Build a plane info based on the given string.

        The string consists of three, space-separated fields.
        The first field is the tail number, the second field is the gate
        number, the third field is the plane's status as a character."""
        super(Plane, self).__init__()

        try:
            words = s.split(" ")
            tailNumber = words[0]
            self.tailNumber = tailNumber

            status = words[2] if len(words)>2 else None
            self._setStatus(status)

            gateNumber = words[1] if len(words)>1 else ""
            self.gateNumber = gateNumber if gateNumber else None

        except:
            print >> sys.stderr, "Plane string is invalid: '" + s + "'"
            self.tailNumber = None

#------------------------------------------------------------------------------

class Fleet(rpccommon.Fleet):
    """Information about the whole fleet."""
    def __init__(self, f):
        """Construct the fleet information by reading the given file object."""
        super(Fleet, self).__init__()

        while True:
            line = readline(f)
            if not line or line == "#END": break

            plane = Plane(line)
            self._addPlane(plane)

#------------------------------------------------------------------------------

class NOTAM(object):
    """A NOTAM for an airport."""
    def __init__(self, ident, basic,
                 begin, notice, end = None, permanent = False,
                 repeatCycle = None):
        """Construct the NOTAM."""
        self.ident = ident
        self.basic = basic
        self.begin = begin
        self.notice = notice
        self.end = end
        self.permanent = permanent
        self.repeatCycle = repeatCycle

    def __repr__(self):
        """Get the representation of the NOTAM."""
        s = "<NOTAM " + str(self.begin)
        if self.end:
            s += " - " + str(self.end)
        elif self.permanent:
            s += " - PERMANENT"
        if self.repeatCycle:
            s += " (" + self.repeatCycle + ")"
        s += ": " + self.notice
        s += ">"
        return s

    def __str__(self):
        """Get the string representation of the NOTAM."""
        s = ""
        s += str(self.ident) + " " + str(self.basic) + "\n"
        s += str(self.begin)
        if self.end is not None:
            s += " - " + str(self.end)
        elif self.permanent:
            s += " - PERMANENT"
        s += "\n"
        if self.repeatCycle:
            s += "Repeat cycle: " + self.repeatCycle + "\n"
        s += self.notice + "\n"
        return s

#------------------------------------------------------------------------------

class NOTAMHandler(xml.sax.handler.ContentHandler):
    """A handler for the NOTAM database."""
    def __init__(self, airportICAOs):
        """Construct the handler for the airports with the given ICAO code."""
        self._notams = {}
        for icao in airportICAOs:
            self._notams[icao] = []

    def startElement(self, name, attrs):
        """Start an element."""
        if name!="notam" or \
           "ident" not in attrs or not attrs["ident"] or \
           "Q" not in attrs or not attrs["Q"] or \
           "A" not in attrs or not attrs["A"] or \
           "B" not in attrs or not attrs["B"] or \
           "E" not in attrs or not attrs["E"]:
            return

        icao = attrs["A"]
        if icao not in self._notams:
            return

        begin = datetime.datetime.strptime(attrs["B"], "%Y-%m-%d %H:%M:%S")

        c = attrs["C"] if "C" in attrs else None
        end = datetime.datetime.strptime(c, "%Y-%m-%d %H:%M:%S") if c else None

        permanent = attrs["C_flag"]=="PERM" if "C_flag" in attrs else False

        repeatCycle = attrs["D"] if "D" in attrs else None

        self._notams[icao].append(NOTAM(attrs["ident"], attrs["Q"],
                                        begin, attrs["E"], end = end,
                                        permanent = permanent,
                                        repeatCycle = repeatCycle))

    def get(self, icao):
        """Get the NOTAMs for the given ICAO code."""
        return self._notams[icao] if icao in self._notams else []

#------------------------------------------------------------------------------

class PilotsWebNOTAMsParser(HTMLParser.HTMLParser):
    """XML handler for the NOTAM query results on the PilotsWeb website."""
    def __init__(self):
        """Construct the handler."""
        HTMLParser.HTMLParser.__init__(self)

        self._notams = []
        self._currentNOTAM = ""
        self._stage = 0

    def handle_starttag(self, name, attrs):
        """Start an element."""
        if (self._stage==0 and name=="div" and ("id", "notamRight") in attrs) or \
           (self._stage==1 and name=="span") or \
           (self._stage==2 and name=="pre"):
            self._stage += 1
            if self._stage==1:
                self._currentNOTAM = ""

    def handle_data(self, content):
        """Handle characters"""
        if self._stage==3:
            self._currentNOTAM += content

    def handle_endtag(self, name):
        """End an element."""
        if (self._stage==3 and name=="pre") or \
           (self._stage==2 and name=="span") or \
           (self._stage==1 and name=="div"):
            self._stage -= 1
            if self._stage==0:
                self._processCurrentNOTAM()

    def getNOTAMs(self):
        """Get the NOTAMs collected"""
        return self._notams

    def _processCurrentNOTAM(self):
        """Parse the current NOTAM and append its contents to the list of
        NOTAMS."""
        notam = None
        try:
            notam = self._parseCurrentNOTAM2()
        except Exception, e:
            print "Error parsing current NOTAM: " + str(e)

        if notam is None:
            print "Could not parse NOTAM: " + self._currentNOTAM
            if self._currentNOTAM:
                self._notams.append(self._currentNOTAM + "\n")
        else:
            self._notams.append(notam)

    def _parseCurrentNOTAM(self):
        """Parse the current NOTAM, if possible, and return a NOTAM object."""
        lines = self._currentNOTAM.splitlines()
        lines = map(lambda line: line.strip(), lines)

        if len(lines)<4:
            return None

        if not lines[1].startswith("Q)") or \
           not lines[2].startswith("A)") or \
           not (lines[3].startswith("E)") or
                (lines[3].startswith("D)") and lines[4].startswith("E)"))):
            return None

        ident = lines[0].split()[0]
        basic = lines[1][2:].strip()

        words = lines[2].split()
        if len(words)<4 or words[0]!="A)" or words[2]!="B)":
            return None

        begin = datetime.datetime.strptime(words[3], "%y%m%d%H%M")
        end = None
        permanent = False
        if words[4]=="C)" and len(words)>=6:
            if words[5] in ["PERM", "UFN"]:
                permanent = True
            else:
                end = datetime.datetime.strptime(words[5], "%y%m%d%H%M")
        else:
            permanent = True

        repeatCycle = None
        noticeStartIndex = 3
        if lines[3].startswith("D)"):
            repeatCycle = lines[3][2:].strip()
            noticeStartIndex = 4

        notice = ""
        for index in range(noticeStartIndex, len(lines)):
            line = lines[index][2:] if index==noticeStartIndex else lines[index]
            line = line.strip()

            if line.lower().startswith("created:") or \
               line.lower().startswith("source:"):
               break

            if notice: notice += " "
            notice += line

        return NOTAM(ident, basic, begin, notice, end = end,
                     permanent = permanent, repeatCycle = repeatCycle)

    def _parseCurrentNOTAM2(self):
        """Parse the current NOTAM with a second, more flexible method."""
        lines = self._currentNOTAM.splitlines()
        lines = map(lambda line: line.strip(), lines)

        if not lines:
            return None

        ident = lines[0].split()[0]

        lines = lines[1:]
        for i in range(0, 2):
            l = lines[-1].lower()
            if l.startswith("created:") or l.startswith("source:"):
                lines = lines[:-1]

        lines = map(lambda line: line.strip(), lines)
        contents = " ".join(lines).split()

        items = {}
        for i in ["Q)", "A)", "B)", "C)", "D)", "E)"]:
            items[i] = ""

        currentItem = None
        for word in contents:
            if word in items:
                currentItem = word
            elif currentItem in items:
                s = items[currentItem]
                if s: s+= " "
                s += word
                items[currentItem] = s

        if not items["Q)"] or not items["A)"] or not items["B)"] or \
           not items["E)"]:
            return None

        basic = items["Q)"]
        begin = datetime.datetime.strptime(items["B)"], "%y%m%d%H%M")

        end = None
        permanent = False
        if items["C)"]:
            endItem = items["C)"]
            if endItem in ["PERM", "UFN"]:
                permanent = True
            else:
                end = datetime.datetime.strptime(items["C)"], "%y%m%d%H%M")
        else:
            permanent = True

        repeatCycle = None
        if items["D)"]:
            repeatCycle = items["D)"]

        notice = items["E)"]

        return NOTAM(ident, basic, begin, notice, end = end,
                     permanent = permanent, repeatCycle = repeatCycle)

#------------------------------------------------------------------------------

class Result(object):
    """A result object.

    An instance of this filled with the appropriate data is passed to the
    callback function on each request."""

    def __repr__(self):
        """Get a representation of the result."""
        s = "<Result:"
        for (key, value) in self.__dict__.iteritems():
            s += " " + key + "=" + unicode(value)
        s += ">"
        return s

#------------------------------------------------------------------------------

class Request(object):
    """Base class for requests.

    It handles any exceptions and the calling of the callback.

    If an exception occurs during processing, the callback is called with
    the two parameters: a boolean value of False, and the exception object.

    If no exception occurs, the callback is called with True and the return
    value of the run() function.

    If the callback function throws an exception, that is caught and logged
    to the debug log."""
    def __init__(self, callback):
        """Construct the request."""
        self._callback = callback

    def perform(self):
        """Perform the request.

        The object's run() function is called. If it throws an exception,
        the callback is called with False, and the exception. Otherwise the
        callback is called with True and the return value of the run()
        function. Any exceptions thrown by the callback are caught and
        reported."""
        try:
            result = self.run()
            returned = True
        except Exception, e:
            traceback.print_exc()
            result = e
            returned = False

        try:
            self._callback(returned, result)
        except Exception, e:
            print >> sys.stderr, "web.Handler.Request.perform: callback throwed an exception: " + util.utf2unicode(str(e))
            #traceback.print_exc()

#------------------------------------------------------------------------------

class RPCRequest(Request):
    """Common base class for RPC requests.

    It stores the RPC client received from the handler."""
    def __init__(self, client, callback):
        """Construct the request."""
        super(RPCRequest, self).__init__(callback)
        self._client = client

#------------------------------------------------------------------------------

class Register(RPCRequest):
    """A registration request."""
    def __init__(self, client, callback, registrationData):
        """Construct the request."""
        super(Register, self).__init__(client, callback)
        self._registrationData = registrationData

    def run(self):
        """Perform the registration."""

        registrationData = self._registrationData

        (resultCode, pilotID) = self._client.register(registrationData)
        result = Result()
        result.registered = resultCode==rpc.Client.RESULT_OK
        if result.registered:
            result.pilotID = pilotID

            self._client.setCredentials(pilotID, registrationData.password)
            loginResult = self._client.login()
            result.loggedIn = loginResult is not None

        result.invalidData = \
          resultCode==rpc.Client.RESULT_INVALID_DATA
        result.emailAlreadyRegistered = \
          resultCode==rpc.Client.RESULT_EMAIL_ALREADY_REGISTERED

        return result

#------------------------------------------------------------------------------

class Login(Request):
    """A login request."""
    iso88592decoder = codecs.getdecoder("iso-8859-2")

    def __init__(self, callback, pilotID, password):
        """Construct the login request with the given pilot ID and
        password."""
        super(Login, self).__init__(callback)

        self._pilotID = pilotID
        self._password = password

    def run(self):
        """Perform the login request."""
        md5 = hashlib.md5()
        md5.update(self._pilotID)
        pilotID = md5.hexdigest()

        md5 = hashlib.md5()
        md5.update(self._password)
        password = md5.hexdigest()

        url = MAVA_BASE_URL + "/leker2.php?pid=%s&psw=%s" %  (pilotID, password)

        result = Result()

        f = urllib2.urlopen(url, timeout = 10.0)

        status = readline(f)
        result.loggedIn = status == ".OK."

        if result.loggedIn:
            result.pilotID = self._pilotID
            result.password = self._password
            result.rank = "FO"
            result.flights = []

            result.pilotName = self.iso88592decoder(readline(f))[0]
            result.exams = readline(f)

            while True:
                line = readline(f)
                if not line or line == "#ENDPIREP": break

                flight = BookedFlight(line)
                flight.readFromWeb(f)
                result.flights.append(flight)

            result.flights.sort(cmp = lambda flight1, flight2:
                                cmp(flight1.departureTime,
                                    flight2.departureTime))

        f.close()

        return result

#------------------------------------------------------------------------------

class LoginRPC(RPCRequest):
    """An RPC-based login request."""
    def __init__(self, client, callback, pilotID, password):
        """Construct the login request with the given pilot ID and
        password."""
        super(LoginRPC, self).__init__(client, callback)

        self._pilotID = pilotID
        self._password = password

    def run(self):
        """Perform the login request."""
        result = Result()

        self._client.setCredentials(self._pilotID, self._password)
        loginResult = self._client.login()
        result.loggedIn = loginResult is not None
        if result.loggedIn:
            result.pilotID = self._pilotID
            result.pilotName = loginResult[0]
            result.rank = loginResult[1]
            result.password = self._password
            result.flights = self._client.getFlights()
            if result.rank=="STU":
                reply = self._client.getEntryExamStatus()
                result.entryExamPassed = reply[0]
                result.entryExamLink = reply[1]
                result.checkFlightStatus = reply[2]
                if reply[3]:
                    result.rank = "FO"

        return result

#------------------------------------------------------------------------------

class GetEntryExamStatus(RPCRequest):
    """A request to get the entry exam status."""
    def __init__(self, client, callback):
        """Construct the request."""
        super(GetEntryExamStatus, self).__init__(client, callback)

    def run(self):
        """Perform the query."""
        result = Result()

        reply = self._client.getEntryExamStatus()

        result.entryExamPassed = reply[0]
        result.entryExamLink = reply[1]
        result.checkFlightStatus = reply[2]
        result.madeFO = reply[3]

        return result

#------------------------------------------------------------------------------

class GetFleet(Request):
    """Request to get the fleet from the website."""

    def __init__(self, callback):
        """Construct the fleet request."""
        super(GetFleet, self).__init__(callback)

    def run(self):
        """Perform the login request."""
        url = MAVA_BASE_URL + "/onlinegates_get.php"

        f = urllib2.urlopen(url, timeout = 10.0)
        result = Result()
        result.fleet = Fleet(f)
        f.close()

        return result

#------------------------------------------------------------------------------

class GetFleetRPC(RPCRequest):
    """Request to get the fleet from the website using RPC."""
    def __init__(self, client, callback):
        """Construct the request with the given client and callback function."""
        super(GetFleetRPC, self).__init__(client, callback)

    def run(self):
        """Perform the login request."""
        result = Result()

        result.fleet = self._client.getFleet()

        return result

#------------------------------------------------------------------------------

class UpdatePlane(Request):
    """Update the status of one of the planes in the fleet."""
    def __init__(self, callback, tailNumber, status, gateNumber = None):
        """Construct the request."""
        super(UpdatePlane, self).__init__(callback)
        self._tailNumber = tailNumber
        self._status = status
        self._gateNumber = gateNumber

    def run(self):
        """Perform the plane update."""
        url = MAVA_BASE_URL + "/onlinegates_set.php"

        status = Plane.status2str(self._status)

        gateNumber = self._gateNumber if self._gateNumber else ""

        data = urllib.urlencode([("lajstrom", self._tailNumber),
                                 ("status", status),
                                 ("kapu", gateNumber)])

        f = urllib2.urlopen(url, data, timeout = 10.0)
        line = readline(f)

        result = Result()
        result.success = line == "OK"

        return result

#------------------------------------------------------------------------------

class UpdatePlaneRPC(RPCRequest):
    """RPC request to update the status and the position of a plane in the
    fleet."""
    def __init__(self, client, callback, tailNumber, status, gateNumber = None):
        """Construct the request."""
        super(UpdatePlaneRPC, self).__init__(client, callback)
        self._tailNumber = tailNumber
        self._status = status
        self._gateNumber = gateNumber

    def run(self):
        """Perform the plane update."""
        self._client.updatePlane(self._tailNumber, self._status, self._gateNumber)

        # Otherwise an exception is thrown
        result = Result()
        result.success = True

        return result

#------------------------------------------------------------------------------

class GetNOTAMs(Request):
    """Get the NOTAMs from EURoutePro and select the ones we are interested
    in."""
    def __init__(self, callback, departureICAO, arrivalICAO):
        """Construct the request for the given airports."""
        super(GetNOTAMs, self).__init__(callback)
        self._departureICAO = departureICAO
        self._arrivalICAO = arrivalICAO

    def run(self):
        """Perform the retrieval of the NOTAMs."""
        departureNOTAMs = self.getPilotsWebNOTAMs(self._departureICAO)
        arrivalNOTAMs = self.getPilotsWebNOTAMs(self._arrivalICAO)

        icaos = []
        if not departureNOTAMs: icaos.append(self._departureICAO)
        if not arrivalNOTAMs: icaos.append(self._arrivalICAO)

        if icaos:
            xmlParser = xml.sax.make_parser()
            notamHandler = NOTAMHandler(icaos)
            xmlParser.setContentHandler(notamHandler)

            url = "http://notams.euroutepro.com/notams.xml"

            f = urllib2.urlopen(url, timeout = 10.0)
            try:
                xmlParser.parse(f)
            finally:
                f.close()

            for icao in icaos:
                if icao==self._departureICAO:
                    departureNOTAMs = notamHandler.get(icao)
                else:
                    arrivalNOTAMs = notamHandler.get(icao)

        result = Result()
        result.departureNOTAMs = departureNOTAMs
        result.arrivalNOTAMs = arrivalNOTAMs

        return result

    def getPilotsWebNOTAMs(self, icao):
        """Try to get the NOTAMs from FAA's PilotsWeb site for the given ICAO
        code.

        Returns a list of PilotsWEBNOTAM objects, or None in case of an error."""
        try:
            parser = PilotsWebNOTAMsParser()

            url = "https://pilotweb.nas.faa.gov/PilotWeb/notamRetrievalByICAOAction.do?method=displayByICAOs&formatType=ICAO&retrieveLocId=%s&reportType=RAW&actionType=notamRetrievalByICAOs" % \
              (icao.upper(),)

            f = urllib2.urlopen(url, timeout = 10.0)
            try:
                data = f.read(16384)
                while data:
                    parser.feed(data)
                    data = f.read(16384)
            finally:
                f.close()

            return parser.getNOTAMs()

        except Exception, e:
            traceback.print_exc()
            print "mlx.web.GetNOTAMs.getPilotsWebNOTAMs: failed to get NOTAMs for '%s': %s" % \
                  (icao, str(e))
            return None

#------------------------------------------------------------------------------

class GetMETARs(Request):
    """Get the METARs from the NOAA website for certain airport ICAOs."""

    def __init__(self, callback, airports):
        """Construct the request for the given airports."""
        super(GetMETARs, self).__init__(callback)
        self._airports = airports

    def run(self):
        """Perform the retrieval opf the METARs."""
        url = "http://www.aviationweather.gov/adds/dataserver_current/httpparam?"
        data = urllib.urlencode([ ("dataSource" , "metars"),
                                  ("requestType",  "retrieve"),
                                  ("format", "csv"),
                                  ("stationString", " ".join(self._airports)),
                                  ("hoursBeforeNow", "24"),
                                  ("mostRecentForEachStation", "constraint")])
        url += data
        f = urllib2.urlopen(url, timeout = 10.0)
        try:
            result = Result()
            result.metars = {}
            for line in iter(f.readline, ""):
                if len(line)>5 and line[4]==' ':
                    icao = line[0:4]
                    if icao in self._airports:
                        result.metars[icao] = line.strip().split(",")[0]
        finally:
            f.close()

        return result

#------------------------------------------------------------------------------

class SendPIREP(Request):
    """A request to send a PIREP to the MAVA website."""
    _latin2Encoder = codecs.getencoder("iso-8859-2")

    def __init__(self, callback, pirep):
        """Construct the sending of the PIREP."""
        super(SendPIREP, self).__init__(callback)
        self._pirep = pirep

    def run(self):
        """Perform the sending of the PIREP."""
        url = MAVA_BASE_URL + "/malevacars.php"

        pirep = self._pirep

        data = {}
        data["acarsdata"] = SendPIREP._latin2Encoder(pirep.getACARSText())[0]

        bookedFlight = pirep.bookedFlight
        data["foglalas_id"] = bookedFlight.id
        data["repdate"] = bookedFlight.departureTime.date().strftime("%Y-%m-%d")
        data["fltnum"] = bookedFlight.callsign
        data["depap"] = bookedFlight.departureICAO
        data["arrap"] = bookedFlight.arrivalICAO
        data["pass"] = str(pirep.numPassengers)
        data["crew"] = str(pirep.numCrew)
        data["cargo"] = str(pirep.cargoWeight)
        data["bag"] = str(pirep.bagWeight)
        data["mail"] = str(pirep.mailWeight)

        data["flttype"] = pirep.flightTypeText
        data["onoff"] = "1" if pirep.online else "0"
        data["bt_dep"] = util.getTimestampString(pirep.blockTimeStart)
        data["bt_arr"] = util.getTimestampString(pirep.blockTimeEnd)
        data["bt_dur"] = util.getTimeIntervalString(pirep.blockTimeEnd -
                                                    pirep.blockTimeStart)
        data["ft_dep"] = util.getTimestampString(pirep.flightTimeStart)
        data["ft_arr"] = util.getTimestampString(pirep.flightTimeEnd)
        data["ft_dur"] = util.getTimeIntervalString(pirep.flightTimeEnd -
                                                    pirep.flightTimeStart)
        data["timecomm"] = pirep.getTimeComment()
        data["fuel"] = "%.2f" % (pirep.fuelUsed,)
        data["dep_rwy"] = pirep.departureRunway
        data["arr_rwy"] = pirep.arrivalRunway
        data["wea_dep"] = pirep.departureMETAR
        data["wea_arr"] = pirep.arrivalMETAR
        data["alt"] = "FL%.0f" % (pirep.filedCruiseAltitude/100.0,)
        if pirep.filedCruiseAltitude!=pirep.cruiseAltitude:
            data["mod_alt"] = "FL%.0f" % (pirep.cruiseAltitude/100.0,)
        else:
            data["mod_alt"] = ""
        data["sid"] = pirep.sid
        data["navroute"] = pirep.route
        data["star"] = pirep.getSTAR()
        data["aprtype"] = pirep.approachType
        data["diff"] = "2"
        data["comment"] = SendPIREP._latin2Encoder(pirep.comments)[0]
        data["flightdefect"] = SendPIREP._latin2Encoder(pirep.flightDefects)[0]
        data["kritika"] = pirep.getRatingText()
        data["flightrating"] = "%.1f" % (max(0.0, pirep.rating),)
        data["distance"] = "%.3f" % (pirep.flownDistance,)
        data["insdate"] = datetime.date.today().strftime("%Y-%m-%d")

        postData = urllib.urlencode(data)
        f = urllib2.urlopen(url, postData, timeout = 10.0)
        try:
            result = Result()
            line = f.readline().strip()
            print "PIREP result from website:", line
            result.success = line=="OK"
            result.alreadyFlown = line=="MARVOLT"
            result.notAvailable = line=="NOMORE"
        finally:
            f.close()

        return result
#------------------------------------------------------------------------------

class SendPIREPRPC(RPCRequest):
    """A request to send a PIREP to the MAVA website via the RPC interface."""

    def __init__(self, client, callback, pirep):
        """Construct the sending of the PIREP."""
        super(SendPIREPRPC, self).__init__(client, callback)
        self._pirep = pirep

    def run(self):
        """Perform the sending of the PIREP."""
        pirep = self._pirep
        resultCode = self._client.addPIREP(pirep.bookedFlight.id, pirep)

        result = Result()
        result.success = resultCode==rpc.Client.RESULT_OK
        result.alreadyFlown = resultCode==rpc.Client.RESULT_FLIGHT_ALREADY_REPORTED
        result.notAvailable = resultCode==rpc.Client.RESULT_FLIGHT_NOT_EXISTS

        return result

#------------------------------------------------------------------------------

class SendACARS(Request):
    """A request to send an ACARS to the MAVA website."""
    _latin2Encoder = codecs.getencoder("iso-8859-2")

    def __init__(self, callback, acars):
        """Construct the request for the given PIREP."""
        super(SendACARS, self).__init__(callback)
        self._acars = acars

    def run(self):
        """Perform the sending of the ACARS."""
        print "Sending the online ACARS"

        url = MAVA_BASE_URL  + "/acars2/acarsonline.php"

        acars = self._acars
        bookedFlight = acars.bookedFlight

        data = {}
        data["pid"] = acars.pid
        data["pilot"] = SendACARS._latin2Encoder(acars.pilotName)[0]

        data["pass"] = str(bookedFlight.numPassengers)
        data["callsign"] = bookedFlight.callsign
        data["airplane"] = bookedFlight.aircraftTypeName
        data["from"] = bookedFlight.departureICAO
        data["to"] = bookedFlight.arrivalICAO
        data["lajstrom"] = bookedFlight.tailNumber

        data["block_time"] = acars.getBlockTimeText()
        data["longitude"] = str(acars.state.longitude)
        data["latitude"] = str(acars.state.latitude)
        data["altitude"] = str(acars.state.altitude)
        data["speed"] = str(acars.state.groundSpeed)

        data["event"] = acars.getEventText()

        f = urllib2.urlopen(url, urllib.urlencode(data), timeout = 10.0)
        try:
            result = Result()
        finally:
            f.close()

        return result

#------------------------------------------------------------------------------

class SendACARSRPC(RPCRequest):
    """A request to send an ACARS to the MAVA website via JSON-RPC."""
    def __init__(self, client, callback, acars):
        """Construct the request for the given PIREP."""
        super(SendACARSRPC, self).__init__(client, callback)
        self._acars = acars

    def run(self):
        """Perform the sending of the ACARS."""
        print "Sending the online ACARS via JSON-RPC"

        self._client.updateOnlineACARS(self._acars)
        return Result()

#------------------------------------------------------------------------------

class SendBugReport(Request):
    """A request to send a bug report to the project homepage."""
    _latin2Encoder = codecs.getencoder("iso-8859-2")

    def __init__(self, callback, summary, description, email):
        """Construct the request for the given bug report."""
        super(SendBugReport, self).__init__(callback)
        self._summary = summary
        self._description = description
        self._email = email

    def run(self):
        """Perform the sending of the bug report."""
        serverProxy = xmlrpclib.ServerProxy("http://mlx.varadiistvan.hu/rpc")

        result = Result()
        result.success = False

        attributes = {}
        if self._email:
            attributes["reporter"] = self._email

        result.ticketID = serverProxy.ticket.create(self._summary, self._description,
                                                    attributes, True)
        print "Created ticket with ID:", result.ticketID
        result.success = True

        return result

#------------------------------------------------------------------------------

class SetCheckFlightPassed(RPCRequest):
    """A request to mark the user as one having passed the check flight."""
    def __init__(self, client, callback, aircraftType):
        """Construct the request for the given type."""
        super(SetCheckFlightPassed, self).__init__(client, callback)
        self._aircraftType = aircraftType

    def run(self):
        """Perform the update."""
        aircraftType = BookedFlight.TYPE2TYPECODE[self._aircraftType]
        self._client.setCheckFlightPassed(aircraftType)
        return Result()

#------------------------------------------------------------------------------

class Handler(threading.Thread):
    """The handler for the web services.

    It can process one request at a time. The results are passed to a callback
    function."""
    def __init__(self, config, getCredentialsFn):
        """Construct the handler."""
        super(Handler, self).__init__()

        self._requests = []
        self._requestCondition = threading.Condition()

        self.daemon = True
        self._config = config
        self._rpcClient = rpc.Client(getCredentialsFn)
        if config.rememberPassword:
            self._rpcClient.setCredentials(config.pilotID, config.password)

    def register(self, callback, registrationData):
        """Enqueue a registration request."""
        self._addRequest(Register(self._rpcClient, callback, registrationData))

    def login(self, callback, pilotID, password):
        """Enqueue a login request."""
        request = \
          LoginRPC(self._rpcClient, callback, pilotID, password) \
          if self._config.useRPC else Login(callback, pilotID, password)

        self._addRequest(request)

    def getEntryExamStatus(self, callback):
        """Get the entry exam status."""
        self._addRequest(GetEntryExamStatus(self._rpcClient, callback))

    def getFleet(self, callback):
        """Enqueue a fleet retrieval request."""
        request = \
          GetFleetRPC(self._rpcClient, callback,) if self._config.useRPC \
          else GetFleet(callback)
        self._addRequest(request)

    def updatePlane(self, callback, tailNumber, status, gateNumber = None):
        """Update the status of the given plane."""
        request = \
          UpdatePlaneRPC(self._rpcClient, callback,
                         tailNumber, status, gateNumber) \
          if self._config.useRPC \
          else UpdatePlane(callback, tailNumber, status, gateNumber)
        self._addRequest(request)

    def getNOTAMs(self, callback, departureICAO, arrivalICAO):
        """Get the NOTAMs for the given two airports."""
        self._addRequest(GetNOTAMs(callback, departureICAO, arrivalICAO))

    def getMETARs(self, callback, airports):
        """Get the METARs for the given airports."""
        self._addRequest(GetMETARs(callback, airports))

    def sendPIREP(self, callback, pirep):
        """Send the given PIREP."""
        request = \
          SendPIREPRPC(self._rpcClient, callback, pirep) if self._config.useRPC \
          else SendPIREP(callback, pirep)
        self._addRequest(request)

    def sendACARS(self, callback, acars):
        """Send the given ACARS"""
        request = \
          SendACARSRPC(self._rpcClient, callback, acars) if self._config.useRPC \
          else SendACARS(callback, acars)
        self._addRequest(request)

    def sendBugReport(self, callback, summary, description, email):
        """Send a bug report with the given data."""
        self._addRequest(SendBugReport(callback, summary, description, email))

    def setCheckFlightPassed(self, callback, aircraftType):
        """Mark the check flight as passed."""
        self._addRequest(SetCheckFlightPassed(self._rpcClient,
                                              callback, aircraftType))

    def run(self):
        """Process the requests."""
        while True:
            with self._requestCondition:
                while not self._requests:
                    self._requestCondition.wait()
                request = self._requests[0]
                del self._requests[0]

            request.perform()

    def _addRequest(self, request):
        """Add the given request to the queue."""
        with self._requestCondition:
            self._requests.append(request)
            self._requestCondition.notify()

#------------------------------------------------------------------------------

if __name__ == "__main__":
    import time

    def callback(returned, result):
        print returned, unicode(result)

    handler = Handler()
    handler.start()

    #handler.login(callback, "P096", "V5fwj")
    #handler.getFleet(callback)
    # Plane: HA-LEG home (gate 67)
    #handler.updatePlane(callback, "HA-LQC", const.PLANE_AWAY, "72")
    #time.sleep(3)
    #handler.getFleet(callback)
    #time.sleep(3)

    #handler.getNOTAMs(callback, "LHBP", "EPWA")
    #handler.getMETARs(callback, ["LHBP", "EPWA"])
    #time.sleep(5)

    handler.updatePlane(callback, "HA-LON", const.PLANE_AWAY, "")
    time.sleep(3)

#------------------------------------------------------------------------------
