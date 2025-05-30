
from . import const
from . import util
from .rpc import Registration, BookedFlight
from . import rpc
from . import rpccommon

from .common import MAVA_BASE_URL, sslContext
from .pirep import PIREP

import threading
import sys
import urllib.request, urllib.parse, urllib.error
import urllib.request, urllib.error, urllib.parse
import hashlib
import time
import re
import datetime
import codecs
import traceback
import xml.sax
import xmlrpc.client
import html.parser
import certifi
import base64
import os.path
import ssl

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
# retrieved or sent via HTTP. \ref Fleet and \ref Plane represents the MAVA
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
            print("Plane string is invalid: '" + s + "'", file=sys.stderr)
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

class PilotsWebNOTAMsParser(html.parser.HTMLParser):
    """XML handler for the NOTAM query results on the PilotsWeb website."""
    def __init__(self):
        """Construct the handler."""
        html.parser.HTMLParser.__init__(self)

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
        except Exception as e:
            print("Error parsing current NOTAM: " + str(e))

        if notam is None:
            print("Could not parse NOTAM: " + self._currentNOTAM)
            if self._currentNOTAM:
                self._notams.append(self._currentNOTAM + "\n")
        else:
            self._notams.append(notam)

    def _parseCurrentNOTAM(self):
        """Parse the current NOTAM, if possible, and return a NOTAM object."""
        lines = self._currentNOTAM.splitlines()
        lines = [line.strip() for line in lines]

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
        self._currentNOTAM = self._currentNOTAM.replace("\\n", "\n")
        lines = self._currentNOTAM.splitlines()
        if len(lines)==1:
            lines = lines[0].splitlines()
        lines = [line.strip() for line in lines]

        if not lines:
            return None

        ident = lines[0].split()[0]

        lines = lines[1:]
        for i in range(0, 2):
            l = lines[-1].lower()
            if l.startswith("created:") or l.startswith("source:"):
                lines = lines[:-1]

        lines = [line.strip() for line in lines]
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

        def parseTime(item):
            item = re.sub("([0-9]+).*", "\\1", item)
            try:
                return datetime.datetime.strptime(item, "%y%m%d%H%M")
            except ValueError:
                return datetime.datetime.strptime(item, "%Y%m%d%H%M")

        basic = items["Q)"]
        begin = parseTime(items["B)"])

        end = None
        permanent = False
        if items["C)"]:
            endItem = items["C)"]
            if endItem in ["PERM", "UFN"]:
                permanent = True
            else:
                end = parseTime(items["C)"])
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
        for (key, value) in self.__dict__.items():
            s += " " + key + "=" + str(value)
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
        except Exception as e:
            traceback.print_exc()
            result = e
            returned = False

        try:
            self._callback(returned, result)
        except Exception as e:
            print("web.Handler.Request.perform: callback throwed an exception: " + util.utf2unicode(str(e)), file=sys.stderr)
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
            LoginRPC.setupLoginResult(result, self._client, pilotID,
                                      registrationData.password)

        result.invalidData = \
          resultCode==rpc.Client.RESULT_INVALID_DATA
        result.emailAlreadyRegistered = \
          resultCode==rpc.Client.RESULT_EMAIL_ALREADY_REGISTERED

        return result

#------------------------------------------------------------------------------

class LoginRPC(RPCRequest):
    """An RPC-based login request."""
    @staticmethod
    def setupLoginResult(result, client, pilotID, password):
        """Setup the login result with the given client, pilot ID and
        password."""
        loginResult = client.login()
        result.loggedIn = loginResult is not None
        if result.loggedIn:
            result.pilotID = pilotID
            result.pilotName = loginResult[0]
            result.rank = loginResult[1]
            result.types = loginResult[2]
            result.sessionID = loginResult[3]
            result.password = password
            result.fleet = client.getFleet()
            result.gates = client.getGates()
            flights = client.getFlights()
            result.flights = flights[0]
            result.reportedFlights = flights[1]
            result.rejectedFlights = flights[2]
            if result.rank=="STU":
                reply = client.getEntryExamStatus()
                result.entryExamPassed = reply[0]
                result.entryExamLink = reply[1]
                result.checkFlightStatus = reply[2]
                if reply[3]:
                    result.rank = "FO"


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
        LoginRPC.setupLoginResult(result, self._client,
                                  self._pilotID, self._password)

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

            f = urllib.request.urlopen(url, timeout = 10.0)
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

            request = urllib.request.Request(url, headers = {
                "cookie": "akamai_pilotweb_access=true;"
            });
            f = urllib.request.urlopen(request, timeout = 10.0,
                                       context = sslContext)
            try:
                data = f.read(16384)
                while data:
                    parser.feed(str(data))
                    data = f.read(16384)
            finally:
                f.close()

            return parser.getNOTAMs()

        except Exception as e:
            traceback.print_exc()
            print("mlx.web.GetNOTAMs.getPilotsWebNOTAMs: failed to get NOTAMs for '%s': %s" % \
                  (icao, str(e)))
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
        url = "https://aviationweather.gov/cgi-bin/data/metar.php?"
        data = urllib.parse.urlencode([ ("ids", ",".join(self._airports)),
                                        ("hours", "0"),
                                        ("format", "raw") ])
        result = Result()
        result.metars = {}
        try:
            url += data
            f = urllib.request.urlopen(url, timeout = 10.0,
                                       context = sslContext)
            try:
                for line in f.readlines():
                    line = str(line, "iso-8859-1")
                    if len(line)>5 and line[4]==' ':
                        icao = line[0:4]
                        if icao in self._airports:
                            result.metars[icao] = line.strip().split(",")[0]
            finally:
                f.close()
        except Exception as e:
            traceback.print_exc()
            print("mlx.web.GetMETARs.run: failed to get METARs for %s: %s" % \
                  (self._airports, str(e)))

        return result

#------------------------------------------------------------------------------

class SendPIREPRPC(RPCRequest):
    """A request to send a PIREP to the MAVA website via the RPC interface."""

    def __init__(self, client, callback, pirep, update):
        """Construct the sending of the PIREP."""
        super(SendPIREPRPC, self).__init__(client, callback)
        self._pirep = pirep
        self._update = update

    def run(self):
        """Perform the sending of the PIREP."""
        pirep = self._pirep
        resultCode = self._client.addPIREP(pirep.bookedFlight.id, pirep,
                                           self._update)

        result = Result()
        result.success = resultCode==rpc.Client.RESULT_OK
        result.alreadyFlown = resultCode==rpc.Client.RESULT_FLIGHT_ALREADY_REPORTED
        result.notAvailable = resultCode==rpc.Client.RESULT_FLIGHT_NOT_EXISTS

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
        print("Sending the online ACARS via JSON-RPC")

        self._client.updateOnlineACARS(self._acars)
        return Result()

#------------------------------------------------------------------------------

class BugReportPasswordManager:
    """Password manager for the Trac XML-RPC server"""
    def __init__(self, programDirectory):
        """Construct the password manager by reading the password from
        the bugreport.txt file"""
        with open(os.path.join(programDirectory, "bugreport.txt")) as f:
            self._password = f.read().strip()

    def add_password(self, realm, uri, username, password):
        pass

    def find_user_password(self, realm, uri):
        return ("mlxbugreport", self._password)

#------------------------------------------------------------------------------

class BugReportTransport(xmlrpc.client.Transport):
    """A transport for digest authentication towards the Trac XML-RPC server"""
    verbose = True

    def __init__(self, programDirectory):
        """Construct the transport for the given program directory."""
        super().__init__()

        sslContext = ssl.create_default_context(ssl.Purpose.SERVER_AUTH,
                                                cafile = certifi.where())
        sslContext.set_alpn_protocols(['http/1.1'])
        httpsHandler = urllib.request.HTTPSHandler(context = sslContext)

        authHandler = urllib.request.HTTPDigestAuthHandler(
            BugReportPasswordManager(programDirectory))

        self._opener = urllib.request.build_opener(httpsHandler, authHandler)

    def single_request(self, host, handler, request_body, verbose=False):
        """Perform a single request"""
        url = "https://" + host + handler
        request = urllib.request.Request(url, data = request_body)
        request.add_header("User-Agent", self.user_agent)
        request.add_header("Content-Type", "text/xml")

        with self._opener.open(request) as f:
            if f.status==200:
                return self.parse_response(f)
            else:
                raise xmlrpc.client.ProtocolError(
                    host + handler,
                    f.status, f.reason,
                    f.getheaders())

#------------------------------------------------------------------------------

class SendBugReport(Request):
    """A request to send a bug report to the project homepage."""
    _latin2Encoder = codecs.getencoder("iso-8859-2")

    def __init__(self, callback, summary, description, email, debugLog,
                 transport):
        """Construct the request for the given bug report."""
        super(SendBugReport, self).__init__(callback)
        self._summary = summary
        self._description = description
        self._email = email
        self._debugLog = debugLog
        self._transport = transport

    def run(self):
        """Perform the sending of the bug report."""
        serverProxy = xmlrpc.client.ServerProxy("https://mlx.varadiistvan.hu/login/rpc",
                                                transport = self._transport)
        result = Result()
        result.success = False

        attributes = {}
        if self._email:
            attributes["reporter"] = self._email

        result.ticketID = serverProxy.ticket.create(self._summary, self._description,
                                                    attributes, True)
        print("Created ticket with ID:", result.ticketID)
        if self._debugLog:
            serverProxy.ticket.putAttachment(result.ticketID, "debug.log",
                                             "Debug log",
                                             bytes(self._debugLog, "utf-8"))


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

class GetPIREP(RPCRequest):
    """A request to retrieve the PIREP of a certain flight."""
    def __init__(self, client, callback, flightID):
        """Construct the request."""
        super(GetPIREP, self).__init__(client, callback)
        self._flightID = flightID

    def run(self):
        """Perform the update."""
        result = Result()

        pirepData = self._client.getPIREP(self._flightID)
        print("pirepData:", pirepData)

        bookedFlight = BookedFlight(id = self._flightID)
        bookedFlight.setupFromPIREPData(pirepData)

        result.pirep = PIREP(None)
        result.pirep.setupFromPIREPData(pirepData, bookedFlight)

        return result

#------------------------------------------------------------------------------

class ReflyFlights(RPCRequest):
    """A request to mark certain flights for reflying."""
    def __init__(self, client, callback, flightIDs):
        """Construct the request."""
        super(ReflyFlights, self).__init__(client, callback)
        self._flightIDs = flightIDs

    def run(self):
        """Perform the update."""
        self._client.reflyFlights(self._flightIDs)
        return Result()

#------------------------------------------------------------------------------

class DeleteFlights(RPCRequest):
    """A request to delete certain flights."""
    def __init__(self, client, callback, flightIDs):
        """Construct the request."""
        super(DeleteFlights, self).__init__(client, callback)
        self._flightIDs = flightIDs

    def run(self):
        """Perform the update."""
        self._client.deleteFlights(self._flightIDs)
        return Result()

#------------------------------------------------------------------------------

class GetAcceptedFlights(RPCRequest):
    """Request to get the accepted flights."""
    def __init__(self, client, callback):
        """Construct the request with the given client and callback function."""
        super(GetAcceptedFlights, self).__init__(client, callback)

    def run(self):
        """Perform the login request."""
        result = Result()

        result.flights = self._client.getAcceptedFlights()

        return result

#------------------------------------------------------------------------------

class GetTimetable(RPCRequest):
    """Request to get the timetable."""
    def __init__(self, client, callback, date, types):
        """Construct the request with the given client and callback function."""
        super(GetTimetable, self).__init__(client, callback)
        self._date = date
        self._types = types

    def run(self):
        """Perform the login request."""
        result = Result()

        result.flightPairs = self._client.getTimetable(self._date, self._types)

        return result

#------------------------------------------------------------------------------

class BookFlights(RPCRequest):
    """Request to book flights."""
    def __init__(self, client, callback, flightIDs, date, tailNumber):
        """Construct the request with the given client and callback function."""
        super(BookFlights, self).__init__(client, callback)
        self._flightIDs = flightIDs
        self._date = date
        self._tailNumber = tailNumber

    def run(self):
        """Perform the login request."""
        result = Result()

        result.bookedFlights = self._client.bookFlights(self._flightIDs,
                                                        self._date,
                                                        self._tailNumber)

        return result

#------------------------------------------------------------------------------

class GetSimBriefResult(RPCRequest):
    """Request the SimBrief result."""
    def __init__(self, client, callback, timestamp):
        """Construct the request with the given client and callback function."""
        super(GetSimBriefResult, self).__init__(client, callback)
        self._timestamp = timestamp

    def run(self):
        """Perform the request."""
        result = Result()

        result.result = self._client.getSimBriefResult(self._timestamp)

        return result

#------------------------------------------------------------------------------

class Handler(threading.Thread):
    """The handler for the web services.

    It can process one request at a time. The results are passed to a callback
    function."""
    def __init__(self, config, getCredentialsFn, programDirectory):
        """Construct the handler."""
        super(Handler, self).__init__()

        self._requests = []
        self._requestCondition = threading.Condition()

        self.daemon = True
        self._config = config
        self._rpcClient = rpc.Client(getCredentialsFn)
        if config.rememberPassword:
            self._rpcClient.setCredentials(config.pilotID, config.password)
        self._bugReportTransport = BugReportTransport(programDirectory)

    def register(self, callback, registrationData):
        """Enqueue a registration request."""
        self._addRequest(Register(self._rpcClient, callback, registrationData))

    def login(self, callback, pilotID, password):
        """Enqueue a login request."""
        request = LoginRPC(self._rpcClient, callback, pilotID, password)

        self._addRequest(request)

    def getEntryExamStatus(self, callback):
        """Get the entry exam status."""
        self._addRequest(GetEntryExamStatus(self._rpcClient, callback))

    def getFleet(self, callback):
        """Enqueue a fleet retrieval request."""
        request = GetFleetRPC(self._rpcClient, callback,)
        self._addRequest(request)

    def updatePlane(self, callback, tailNumber, status, gateNumber = None):
        """Update the status of the given plane."""
        request = UpdatePlaneRPC(self._rpcClient, callback,
                                 tailNumber, status, gateNumber)
        self._addRequest(request)

    def getNOTAMs(self, callback, departureICAO, arrivalICAO):
        """Get the NOTAMs for the given two airports."""
        self._addRequest(GetNOTAMs(callback, departureICAO, arrivalICAO))

    def getMETARs(self, callback, airports):
        """Get the METARs for the given airports."""
        self._addRequest(GetMETARs(callback, airports))

    def sendPIREP(self, callback, pirep, update = False):
        """Send the given PIREP."""
        request = SendPIREPRPC(self._rpcClient, callback, pirep, update)
        self._addRequest(request)

    def sendACARS(self, callback, acars):
        """Send the given ACARS"""
        request = SendACARSRPC(self._rpcClient, callback, acars)
        self._addRequest(request)

    def sendBugReport(self, callback, summary, description, email, debugLog = None):
        """Send a bug report with the given data."""
        self._addRequest(SendBugReport(callback, summary, description, email,
                                       debugLog = debugLog,
                                       transport = self._bugReportTransport))

    def setCheckFlightPassed(self, callback, aircraftType):
        """Mark the check flight as passed."""
        self._addRequest(SetCheckFlightPassed(self._rpcClient,
                                              callback, aircraftType))

    def getPIREP(self, callback, flightID):
        """Query the PIREP for the given flight."""
        self._addRequest(GetPIREP(self._rpcClient, callback, flightID))

    def reflyFlights(self, callback, flightIDs):
        """Mark the flights with the given IDs for reflying."""
        self._addRequest(ReflyFlights(self._rpcClient, callback, flightIDs))

    def deleteFlights(self, callback, flightIDs):
        """Delete the flights with the given IDs."""
        self._addRequest(DeleteFlights(self._rpcClient, callback, flightIDs))

    def getAcceptedFlights(self, callback):
        """Enqueue a request to get the accepted flights."""
        self._addRequest(GetAcceptedFlights(self._rpcClient, callback))

    def getTimetable(self, callback, date, types):
        """Enqueue a request to get the timetable."""
        self._addRequest(GetTimetable(self._rpcClient, callback, date, types))

    def bookFlights(self, callback, flightIDs, date, tailNumber):
        """Enqueue a request to book some flights."""
        self._addRequest(BookFlights(self._rpcClient, callback,
                                     flightIDs, date, tailNumber))

    def getSimBriefResult(self, callback, timestamp):
        """Enqueue a request to get the SimBrief result."""
        self._addRequest(GetSimBriefResult(self._rpcClient, callback,
                                           timestamp))

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
        print(returned, str(result))

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
