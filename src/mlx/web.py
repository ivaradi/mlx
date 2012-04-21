# Interface towards the websites used

#------------------------------------------------------------------------------

import const
import util

import threading
import sys
import urllib
import urllib2
import hashlib
import time
import datetime
import codecs
import xml.sax

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
    TYPECODE2TYPE = { "736" : const.AIRCRAFT_B736,
                      "73G" : const.AIRCRAFT_B737,
                      "738" : const.AIRCRAFT_B738,
                      "733" : const.AIRCRAFT_B733,
                      "734" : const.AIRCRAFT_B734,
                      "735" : const.AIRCRAFT_B735,
                      "DH4" : const.AIRCRAFT_DH8D,
                      "762" : const.AIRCRAFT_B762,
                      "763" : const.AIRCRAFT_B763,
                      "CR2" : const.AIRCRAFT_CRJ2,
                      "F70" : const.AIRCRAFT_F70,
                      "LI2" : const.AIRCRAFT_DC3,
                      "TU3" : const.AIRCRAFT_T134,
                      "TU5" : const.AIRCRAFT_T154,
                      "YK4" : const.AIRCRAFT_YK40 }

    def __init__(self, id, f):
        """Construct a booked flight with the given ID.

        The rest of the data is read from the given file."""

        self.id = id
        self.callsign = readline(f)

        date = readline(f)

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
        self.departureTime = datetime.datetime.strptime(date + " " + departureTime,
                                                        "%Y-%m-%d %H:%M:%S")
                                               
        arrivalTime = readline(f)
        self.arrivalTime = datetime.datetime.strptime(date + " " + arrivalTime,
                                                      "%Y-%m-%d %H:%M:%S")

        if not readline(f)==".NEXT.":
            raise Exception("Invalid line in flight data")

    def _readAircraftType(self, f):
        """Read the aircraft type from the given file."""
        line = readline(f)
        typeCode = line[:3]
        if typeCode in self.TYPECODE2TYPE:
            self.aircraftType = self.TYPECODE2TYPE[typeCode]
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

class Plane(object):
    """Information about an airplane in the fleet."""
    def __init__(self, s):
        """Build a plane info based on the given string.

        The string consists of three, space-separated fields.
        The first field is the tail number, the second field is the gate
        number, the third field is the plane's status as a character."""
        try:
            words = s.split(" ")
            tailNumber = words[0]
            self.tailNumber = tailNumber

            status = words[2] if len(words)>2 else None
            self.status = const.PLANE_HOME if status=="H" else \
                          const.PLANE_AWAY if status=="A" else \
                          const.PLANE_PARKING if status=="P" else \
                          const.PLANE_UNKNOWN

            gateNumber = words[1] if len(words)>1 else ""
            self.gateNumber = gateNumber if gateNumber else None

        except:
            print >> sys.stderr, "Plane string is invalid: '" + s + "'"
            self.tailNumber = None

    def __repr__(self):
        """Get the representation of the plane object."""
        s = "<Plane: %s %s" % (self.tailNumber, 
                               "home" if self.status==const.PLANE_HOME else \
                               "away" if self.status==const.PLANE_AWAY else \
                               "parking" if self.status==const.PLANE_PARKING \
                               else "unknown")
        if self.gateNumber is not None:
            s += " (gate " + self.gateNumber + ")"
        s += ">"
        return s
        

#------------------------------------------------------------------------------

class Fleet(object):
    """Information about the whole fleet."""
    def __init__(self, f):
        """Construct the fleet information by reading the given file object."""
        self._planes = {}
        while True:
            line = readline(f)
            if not line or line == "#END": break

            plane = Plane(line)
            if plane.tailNumber is not None:
                self._planes[plane.tailNumber] = plane        

    def isGateConflicting(self, plane):
        """Check if the gate of the given plane conflicts with another plane's
        position."""
        for p in self._planes.itervalues():
            if p.tailNumber!=plane.tailNumber and \
               p.status==const.PLANE_HOME and \
               p.gateNumber==plane.gateNumber:
                return True

        return False

    def getOccupiedGateNumbers(self):
        """Get a set containing the numbers of the gates occupied by planes."""
        gateNumbers = set()
        for p in self._planes.itervalues():
            if p.status==const.PLANE_HOME and p.gateNumber:
                gateNumbers.add(p.gateNumber)
        return gateNumbers
        
    def __getitem__(self, tailNumber):
        """Get the plane with the given tail number.

        If the plane is not in the fleet, None is returned."""
        return self._planes[tailNumber] if tailNumber in self._planes else None

    def __repr__(self):
        """Get the representation of the fleet object."""
        return self._planes.__repr__()
        
#------------------------------------------------------------------------------

class NOTAM(object):
    """A NOTAM for an airport."""
    def __init__(self, begin, notice, end = None, permanent = False,
                 repeatCycle = None):
        """Construct the NOTAM."""
        self.begin = begin
        self.notice = notice
        self.end = end
        self.permanent = permanent
        self.repeatCycle = None

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

        self._notams[icao].append(NOTAM(begin, attrs["E"], end = end,
                                        permanent = permanent,
                                        repeatCycle = repeatCycle))

    def get(self, icao):
        """Get the NOTAMs for the given ICAO code."""
        return self._notams[icao] if icao in self._notams else []

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
            result = e
            returned = False

        try:
            self._callback(returned, result)
        except Exception, e:
            print >> sys.stderr, "web.Handler.Request.perform: callback throwed an exception: " + str(e)

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

        url = "http://www.virtualairlines.hu/leker2.php?pid=%s&psw=%s" % \
              (pilotID, password)

        result = Result()

        f = urllib2.urlopen(url, timeout = 10.0)

        status = readline(f)
        result.loggedIn = status == ".OK."

        if result.loggedIn:
            result.pilotName = self.iso88592decoder(readline(f))[0]
            result.exams = readline(f)
            result.flights = []

            while True:
                line = readline(f)
                if not line or line == "#ENDPIREP": break

                flight = BookedFlight(line, f)
                result.flights.append(flight)

            result.flights.sort(cmp = lambda flight1, flight2:
                                cmp(flight1.departureTime,
                                    flight2.departureTime))

        f.close()

        return result
        
#------------------------------------------------------------------------------

class GetFleet(Request):
    """Request to get the fleet from the website."""
    
    def __init__(self, callback):
        """Construct the fleet request."""
        super(GetFleet, self).__init__(callback)

    def run(self):
        """Perform the login request."""
        url = "http://www.virtualairlines.hu/onlinegates_get.php"

        f = urllib2.urlopen(url, timeout = 10.0)
        result = Result()
        result.fleet = Fleet(f)
        f.close()
        
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
        url = "http://www.virtualairlines.hu/onlinegates_set.php"

        status = "H" if self._status==const.PLANE_HOME else \
                 "A" if self._status==const.PLANE_AWAY else \
                 "P" if self._status==const.PLANE_PARKING else ""

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
        xmlParser = xml.sax.make_parser()
        notamHandler = NOTAMHandler([self._departureICAO, self._arrivalICAO])
        xmlParser.setContentHandler(notamHandler)

        url = "http://notams.euroutepro.com/notams.xml"

        f = urllib2.urlopen(url, timeout = 10.0)
        try:
            xmlParser.parse(f)
        finally:
            f.close()

        result = Result()
        result.departureNOTAMs = notamHandler.get(self._departureICAO)
        result.arrivalNOTAMs = notamHandler.get(self._arrivalICAO)

        return result

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
    _flightTypes = { const.FLIGHTTYPE_SCHEDULED : "SCHEDULED",
                     const.FLIGHTTYPE_OLDTIMER : "OT",
                     const.FLIGHTTYPE_VIP : "VIP",
                     const.FLIGHTTYPE_CHARTER : "CHARTER" }

    _latin2Encoder = codecs.getencoder("iso-8859-2")

    def __init__(self, callback, pirep):
        """Construct the request for the given PIREP."""
        super(SendPIREP, self).__init__(callback)
        self._pirep = pirep

    def run(self):
        """Perform the retrieval opf the METARs."""
        url = "http://www.virtualairlines.hu/malevacars.php"

        pirep = self._pirep

        data = {}
        data["acarsdata"] = pirep.getACARSText()

        bookedFlight = pirep.bookedFlight
        data["foglalas_id"] = bookedFlight.id
        data["repdate"] = bookedFlight.departureTime.date().strftime("%Y-%m-%d")
        data["fltnum"] = bookedFlight.callsign
        data["depap"] = bookedFlight.departureICAO
        data["arrap"] = bookedFlight.arrivalICAO
        data["pass"] = str(bookedFlight.numPassengers)
        data["crew"] = str(bookedFlight.numCrew)
        data["cargo"] = str(pirep.cargoWeight)
        data["bag"] = str(bookedFlight.bagWeight)
        data["mail"] = str(bookedFlight.mailWeight)
        
        data["flttype"] = SendPIREP._flightTypes[pirep.flightType]
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
        data["fuel"] = "%.0f" % (pirep.fuelUsed,)
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
        data["flightRating"] = "%.1f" % (max(0.0, pirep.rating),)
        data["distance"] = "%.3f" % (pirep.flownDistance,)
        data["insdate"] = datetime.date.today().strftime("%Y-%m-%d")

        f = urllib2.urlopen(url, urllib.urlencode(data), timeout = 10.0)
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

class Handler(threading.Thread):
    """The handler for the web services.

    It can process one request at a time. The results are passed to a callback
    function."""
    def __init__(self):
        """Construct the handler."""
        super(Handler, self).__init__()

        self._requests = []
        self._requestCondition = threading.Condition()

        self.daemon = True

    def login(self, callback, pilotID, password):
        """Enqueue a login request."""
        self._addRequest(Login(callback, pilotID, password))

    def getFleet(self, callback):
        """Enqueue a fleet retrieval request."""
        self._addRequest(GetFleet(callback))
        
    def updatePlane(self, callback, tailNumber, status, gateNumber = None):
        """Update the status of the given plane."""        
        self._addRequest(UpdatePlane(callback, tailNumber, status, gateNumber))

    def getNOTAMs(self, callback, departureICAO, arrivalICAO):
        """Get the NOTAMs for the given two airports."""
        self._addRequest(GetNOTAMs(callback, departureICAO, arrivalICAO))
        
    def getMETARs(self, callback, airports):
        """Get the METARs for the given airports."""
        self._addRequest(GetMETARs(callback, airports))

    def sendPIREP(self, callback, pirep):
        """Send the given PIREP."""
        self._addRequest(SendPIREP(callback, pirep))
        
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
    handler.getMETARs(callback, ["LHBP", "EPWA"])
    time.sleep(5)
    

#------------------------------------------------------------------------------
