# Module handling the connection to FSUIPC

#------------------------------------------------------------------------------

import fs
import const
import util

import threading
import os
import time
import calendar
import sys

if os.name == "nt":
    import pyuipc
else:
    import pyuipc_emu as pyuipc

#------------------------------------------------------------------------------

class Handler(threading.Thread):
    """The thread to handle the FSUIPC requests."""
    @staticmethod
    def _callSafe(fun):
        """Call the given function and swallow any exceptions."""
        try:
            return fun()
        except Exception, e:
            print >> sys.stderr, str(e)
            return None

    class Request(object):
        """A simple, one-shot request."""
        def __init__(self, forWrite, data, callback, extra):
            """Construct the request."""
            self._forWrite = forWrite
            self._data = data
            self._callback = callback
            self._extra = extra
            
        def process(self, time):
            """Process the request."""            
            if self._forWrite:
                pyuipc.write(self._data)
                Handler._callSafe(lambda: self._callback(True, self._extra))
            else:
                values = pyuipc.read(self._data)
                Handler._callSafe(lambda: self._callback(values, self._extra))

            return True

        def fail(self):
            """Handle the failure of this request."""
            if self._forWrite:
                Handler._callSafe(lambda: self._callback(False, self._extra))
            else:
                Handler._callSafe(lambda: self._callback(None, self._extra))

    class PeriodicRequest(object):
        """A periodic request."""
        def __init__(self, id,  period, data, callback, extra):
            """Construct the periodic request."""
            self._id = id
            self._period = period
            self._nextFire = time.time() + period
            self._data = data
            self._preparedData = None
            self._callback = callback
            self._extra = extra
            
        @property
        def id(self):
            """Get the ID of this periodic request."""
            return self._id

        @property
        def nextFire(self):
            """Get the next firing time."""
            return self._nextFire

        def process(self, time):
            """Check if this request should be executed, and if so, do so.

            Return a boolean indicating if the request was executed."""
            if time < self._nextFire: 
                return False

            if self._preparedData is None:
                self._preparedData = pyuipc.prepare_data(self._data)
                self._data = None
                
            values = pyuipc.read(self._preparedData)

            Handler._callSafe(lambda: self._callback(values, self._extra))

            while self._nextFire <= time:
                self._nextFire += self._period
            
            return True

        def fail(self):
            """Handle the failure of this request."""
            pass

        def __cmp__(self, other):
            """Compare two periodic requests. They are ordered by their next
            firing times."""
            return cmp(self._nextFire, other._nextFire)

    def __init__(self, connectionListener):
        """Construct the handler with the given connection listener."""
        threading.Thread.__init__(self)

        self._connectionListener = connectionListener

        self._requestCondition = threading.Condition()
        self._connectionRequested = False

        self._requests = []
        self._nextPeriodicID = 1
        self._periodicRequests = []

        self.daemon = True

    def requestRead(self, data, callback, extra = None):
        """Request the reading of some data.

        data is a list of tuples of the following items:
        - the offset of the data as an integer
        - the type letter of the data as a string

        callback is a function that receives two pieces of data:
        - the values retrieved or None on error
        - the extra parameter

        It will be called in the handler's thread!
        """
        with self._requestCondition:
            self._requests.append(Handler.Request(False, data, callback, extra))
            self._requestCondition.notify()

    def requestWrite(self, data, callback, extra = None):
        """Request the writing of some data.

        data is a list of tuples of the following items:
        - the offset of the data as an integer
        - the type letter of the data as a string
        - the data to write

        callback is a function that receives two pieces of data:
        - a boolean indicating if writing was successful
        - the extra data
        It will be called in the handler's thread!
        """
        with self._requestCondition:
            self._requests.append(Handler.Request(True, data, callback, extra))
            self._requestCondition.notify()

    @staticmethod
    def _readWriteCallback(data, extra):
        """Callback for the read() and write() calls below."""
        extra.append(data)
        with extra[0] as condition:
            condition.notify()

    def read(self, data):
        """Read the given data synchronously.

        If a problem occurs, an exception is thrown."""
        with threading.Condition() as condition:
            extra = [condition]
            self._requestRead(data, self._readWriteCallback, extra)
            while len(extra)<2:
                condition.wait()
            if extra[1] is None:
                raise fs.SimulatorException("reading failed")
            else:
                return extra[1]

    def write(self, data):
        """Write the given data synchronously.

        If a problem occurs, an exception is thrown."""
        with threading.Condition() as condition:
            extra = [condition]
            self._requestWrite(data, self._writeCallback, extra)
            while len(extra)<2:
                condition.wait()
            if extra[1] is None:
                raise fs.SimulatorException("writing failed")

    def requestPeriodicRead(self, period, data, callback, extra = None):
        """Request a periodic read of data.

        period is a floating point number with the period in seconds.

        This function returns an identifier which can be used to cancel the
        request."""
        with self._requestCondition:
            id = self._nextPeriodicID
            self._nextPeriodicID += 1
            request = Handler.PeriodicRequest(id, period, data, callback, extra)
            self._periodicRequests.append(request)
            self._requestCondition.notify()
            return id

    def clearPeriodic(self, id):
        """Clear the periodic request with the given ID."""
        with self._requestCondition:
            for i in range(0, len(self._periodicRequests)):
                if self._periodicRequests[i].id==id:
                    del self._periodicRequests[i]
                    return True
        return False

    def connect(self):
        """Initiate the connection to the flight simulator."""
        with self._requestCondition:
            if not self._connectionRequested:
                self._connectionRequested = True
                self._requestCondition.notify()
        
    def disconnect(self):
        """Disconnect from the flight simulator."""
        with self._requestCondition:
            if self._connectionRequested:
                self._connectionRequested = False
                self._requestCondition.notify()

    def run(self):
        """Perform the operation of the thread."""
        while True:
            self._waitConnectionRequest()
            
            if self._connect():
                self._handleConnection()

            self._disconnect()
            
    def _waitConnectionRequest(self):
        """Wait for a connection request to arrive."""
        with self._requestCondition:
            while not self._connectionRequested:
                self._requestCondition.wait()
            
    def _connect(self):
        """Try to connect to the flight simulator via FSUIPC"""
        while self._connectionRequested:
            try:
                pyuipc.open(pyuipc.SIM_FS2K4)
                description = "(FSUIPC version: 0x%04x, library version: 0x%04x, FS version: %d)" % \
                    (pyuipc.fsuipc_version, pyuipc.lib_version, 
                     pyuipc.fs_version)
                Handler._callSafe(lambda:     
                                  self._connectionListener.connected(const.SIM_MSFS9, 
                                                                     description))
                return True
            except Exception, e:
                print "fsuipc.Handler._connect: connection failed: " + str(e)
                time.sleep(0.1)

        return False
                
    def _handleConnection(self):
        """Handle a living connection."""
        with self._requestCondition:
            while self._connectionRequested:
                if not self._processRequests(): 
                    return
                timeout = None
                if self._periodicRequests:
                    self._periodicRequests.sort()
                    timeout = self._periodicRequests[0].nextFire - time.time()
                if timeout is None or timeout > 0.0:
                    self._requestCondition.wait(timeout)
                
    def _disconnect(self):
        """Disconnect from the flight simulator."""
        pyuipc.close()
        Handler._callSafe(lambda: self._connectionListener.disconnected())

    def _failRequests(self, request):
        """Fail the outstanding, single-shot requuests."""
        request.fail()
        with self._requestCondition:
            for request in self._requests:
                try:
                    self._requestCondition.release()
                    request.fail()
                finally:
                    self._requestCondition.acquire()
            self._requests = []        

    def _processRequest(self, request, time):
        """Process the given request. 

        If an exception occurs, we try to reconnect.
        
        Returns what the request's process() function returned or None if
        reconnection failed."""
        
        self._requestCondition.release()

        try:
            return request.process(time)
        except Exception as e:
            print "fsuipc.Handler._processRequest: FSUIPC connection failed (" + \
                str(e) + ") reconnecting."
            self._disconnect()
            self._failRequests(request)
            if not self._connect(): return None
            else: return True
        finally:
            self._requestCondition.acquire()
        
    def _processRequests(self):
        """Process any pending requests.

        Will be called with the request lock held."""
        while self._connectionRequested and self._periodicRequests:
            self._periodicRequests.sort()
            request = self._periodicRequests[0]
            result = self._processRequest(request, time.time())
            if result is None: return False
            elif not result: break

        while self._connectionRequested and self._requests:
            request = self._requests[0]
            del self._requests[0]

            if self._processRequest(request, None) is None:
                return False

        return self._connectionRequested

#------------------------------------------------------------------------------

class Simulator(object):
    """The simulator class representing the interface to the flight simulator
    via FSUIPC."""
    # The basic data that should be queried all the time once we are connected
    normalData = [ (0x0240, "H"),
                   (0x023e, "H"),
                   (0x023b, "b"),
                   (0x023c, "b"),
                   (0x023a, "b"),
                   (0x3d00, -256),
                   (0x3c00, -256) ]
    
    def __init__(self, connectionListener, aircraft):
        """Construct the simulator.
        
        The aircraft object passed must provide the following members:
        - type: one of the AIRCRAFT_XXX constants from const.py
        - modelChanged(aircraftName, modelName): called when the model handling
        the aircraft has changed.
        - handleState(aircraftState): handle the given state."""
        self._aircraft = aircraft

        self._handler = Handler(connectionListener)
        self._handler.start()

        self._normalRequestID = None

        self._monitoringRequested = False
        self._monitoring = False

        self._aircraftName = None
        self._aircraftModel = None

    def connect(self):
        """Initiate a connection to the simulator."""
        self._handler.connect()
        self._startDefaultNormal()
                                                            
    def startMonitoring(self):
        """Start the periodic monitoring of the aircraft and pass the resulting
        state to the aircraft object periodically."""
        assert not self._monitoringRequested         
        self._monitoringRequested = True

    def stopMonitoring(self):
        """Stop the periodic monitoring of the aircraft."""
        assert self._monitoringRequested 
        self._monitoringRequested = False

    def disconnect(self):
        """Disconnect from the simulator."""
        assert not self._monitoringRequested 
        
        self._stopNormal()
        self._handler.disconnect()

    def _startDefaultNormal(self):
        """Start the default normal periodic request."""
        assert self._normalRequestID is None
        self._normalRequestID = self._handler.requestPeriodicRead(1.0,
                                                                  Simulator.normalData,
                                                                  self._handleNormal)

    def _stopNormal(self):
        """Stop the normal period request."""
        assert self._normalRequestID is not None
        self._handler.clearPeriodic(self._normalRequestID)
        self._normalRequestID = None

    def _handleNormal(self, data, extra):
        """Handle the reply to the normal request.

        At the beginning the result consists the data for normalData. When
        monitoring is started, it contains the result also for the
        aircraft-specific values.
        """
        timestamp = calendar.timegm(time.struct_time([data[0],
                                                      1, 1, 0, 0, 0, -1, 1, 0]))
        timestamp += data[1] * 24 * 3600
        timestamp += data[2] * 3600
        timestamp += data[3] * 60
        timestamp += data[4]        

        createdNewModel = self._setAircraftName(timestamp, data[5], data[6])
        
        if self._monitoringRequested and not self._monitoring:
            self._monitoring = True
            self._stopNormal()
            self._startMonitoring()
        elif self._monitoring and not self._monitoringRequested:
            self._monitoring = False
            self._stopNormal()
            self._startDefaultNormal()
        elif self._monitoring and self._aircraftModel is not None and \
             not createdNewModel:
            aircraftState = self._aircraftModel.getAircraftState(self._aircraft, 
                                                                 timestamp, data)
            self._aircraft.handleState(aircraftState)

    def _setAircraftName(self, timestamp, name, airPath):
        """Set the name of the aicraft and if it is different from the
        previous, create a new model for it.
        
        If so, also notifty the aircraft about the change.

        Return if a new model was created."""
        aircraftName = (name, airPath)
        if aircraftName==self._aircraftName:
            return False

        self._aircraftName = aircraftName
        needNew = self._aircraftModel is None
        needNew = needNew or\
            not self._aircraftModel.doesHandle(self._aircraft, aircraftName)
        if not needNew:
            specialModel = AircraftModel.findSpecial(self._aircraft, aircraftName)
            needNew = specialModel is not None and \
                specialModel is not self._aircraftModel.__class__

        if needNew:
            self._setAircraftModel(AircraftModel.create(self._aircraft, aircraftName))
        
        self._aircraft.modelChanged(timestamp, name, self._aircraftModel.name)        

        return needNew

    def _setAircraftModel(self, model):
        """Set a new aircraft model.

        It will be queried for the data to monitor and the monitoring request
        will be replaced by a new one."""
        self._aircraftModel = model
        
        if self._monitoring:
            self._stopNormal()
            self._startMonitoring()
            
    def _startMonitoring(self):
        """Start monitoring with the current aircraft model."""
        assert self._monitoring

        data = Simulator.normalData[:]
        self._aircraftModel.addMonitoringData(data)
        
        self._normalRequestID = \
            self._handler.requestPeriodicRead(1.0, data, 
                                              self._handleNormal)

#------------------------------------------------------------------------------

class AircraftModel(object):
    """Base class for the aircraft models.

    Aircraft models handle the data arriving from FSUIPC and turn it into an
    object describing the aircraft's state."""
    monitoringData = [("paused", 0x0264, "H"),
                      ("frozen", 0x3364, "H"),
                      ("replay", 0x0628, "d"),
                      ("slew", 0x05dc, "H"),
                      ("overspeed", 0x036d, "b"),
                      ("stalled", 0x036c, "b"),
                      ("onTheGround", 0x0366, "H"),
                      ("grossWeight", 0x30c0, "f"),
                      ("heading", 0x0580, "d"),
                      ("pitch", 0x0578, "d"),
                      ("bank", 0x057c, "d"),
                      ("ias", 0x02bc, "d"),
                      ("groundSpeed", 0x02b4, "d"),
                      ("vs", 0x02c8, "d"),
                      ("radioAltitude", 0x31e4, "d"),
                      ("altitude", 0x0570, "l"),
                      ("gLoad", 0x11ba, "H"),
                      ("flapsControl", 0x0bdc, "d"),
                      ("flapsLeft", 0x0be0, "d"),
                      ("flapsRight", 0x0be4, "d"),
                      ("lights", 0x0d0c, "H"),
                      ("pitot", 0x029c, "b"),
                      ("parking", 0x0bc8, "H"),
                      ("noseGear", 0x0bec, "d"),
                      ("spoilersArmed", 0x0bcc, "d"),
                      ("spoilers", 0x0bd0, "d"),
                      ("altimeter", 0x0330, "H"),
                      ("nav1", 0x0350, "H"),
                      ("nav2", 0x0352, "H"),
                      ("squawk", 0x0354, "H")]

    specialModels = []

    @staticmethod
    def registerSpecial(clazz):
        """Register the given class as a special model."""
        AircraftModel.specialModels.append(clazz)

    @staticmethod
    def findSpecial(aircraft, aircraftName):
        for specialModel in AircraftModel.specialModels:
            if specialModel.doesHandle(aircraft, aircraftName):
                return specialModel
        return None

    @staticmethod
    def create(aircraft, aircraftName):
        """Create the model for the given aircraft name, and notify the
        aircraft about it."""
        specialModel = AircraftModel.findSpecial(aircraft, aircraftName)
        if specialModel is not None:
            return specialModel()
        if aircraft.type in _genericModels:
            return _genericModels[aircraft.type]()
        else:
            return GenericModel()

    @staticmethod
    def convertBCD(data, length):
        """Convert a data item encoded as BCD into a string of the given number
        of digits."""
        bcd = ""
        for i in range(0, length):
            digit = chr(ord('0') + (data&0x0f))
            data >>= 4
            bcd = digit + bcd
        return bcd

    @staticmethod
    def convertFrequency(data):
        """Convert the given frequency data to a string."""
        bcd = AircraftModel.convertBCD(data, 4)
        return "1" + bcd[0:2] + "." + bcd[2:4]

    def __init__(self, flapsNotches):
        """Construct the aircraft model.
        
        flapsNotches is a list of degrees of flaps that are available on the aircraft."""
        self._flapsNotches = flapsNotches
    
    @property
    def name(self):
        """Get the name for this aircraft model."""
        return "FSUIPC/Generic"
    
    def doesHandle(self, aircraft, aircraftName):
        """Determine if the model handles the given aircraft name.
        
        This default implementation returns False."""
        return False

    def _addOffsetWithIndexMember(self, dest, offset, type, attrName = None):
        """Add the given FSUIPC offset and type to the given array and a member
        attribute with the given name."""        
        dest.append((offset, type))
        if attrName is not None:
            setattr(self, attrName, len(dest)-1)

    def _addDataWithIndexMembers(self, dest, prefix, data):
        """Add FSUIPC data to the given array and also corresponding index
        member variables with the given prefix.

        data is a list of triplets of the following items:
        - the name of the data item. The index member variable will have a name
        created by prepending the given prefix to this name.
        - the FSUIPC offset
        - the FSUIPC type
        
        The latter two items will be appended to dest."""
        for (name, offset, type) in data:
            self._addOffsetWithIndexMember(dest, offset, type, prefix + name)
            
    def addMonitoringData(self, data):
        """Add the model-specific monitoring data to the given array."""
        self._addDataWithIndexMembers(data, "_monidx_",
                                      AircraftModel.monitoringData)
    
    def getAircraftState(self, aircraft, timestamp, data):
        """Get an aircraft state object for the given monitoring data."""
        state = fs.AircraftState()
        
        state.timestamp = timestamp
        
        state.paused = data[self._monidx_paused]!=0 or \
            data[self._monidx_frozen]!=0 or \
            data[self._monidx_replay]!=0
        state.trickMode = data[self._monidx_slew]!=0

        state.overspeed = data[self._monidx_overspeed]!=0
        state.stalled = data[self._monidx_stalled]!=0
        state.onTheGround = data[self._monidx_onTheGround]!=0

        state.grossWeight = data[self._monidx_grossWeight] * const.LBSTOKG
        
        state.heading = data[self._monidx_heading]*360.0/65536.0/65536.0
        if state.heading<0.0: state.heading += 360.0

        state.pitch = data[self._monidx_pitch]*360.0/65536.0/65536.0
        state.bank = data[self._monidx_bank]*360.0/65536.0/65536.0

        state.ias = data[self._monidx_ias]/128.0
        state.groundSpeed = data[self._monidx_groundSpeed]* 3600.0/65536.0/1852.0
        state.vs = data[self._monidx_vs]*60.0/const.FEETTOMETRES/256.0

        state.radioAltitude = data[self._monidx_radioAltitude]/const.FEETTOMETRES/65536.0
        state.altitude = data[self._monidx_altitude]/const.FEETTOMETRES/65536.0/65536.0

        state.gLoad = data[self._monidx_gLoad] / 625.0
        
        numNotchesM1 = len(self._flapsNotches) - 1
        flapsIncrement = 16383 / numNotchesM1
        flapsControl = data[self._monidx_flapsControl]
        flapsIndex = flapsControl / flapsIncrement
        if flapsIndex < numNotchesM1:
            if (flapsControl - (flapsIndex*flapsIncrement) >
                (flapsIndex+1)*flapsIncrement - flapsControl):
                flapsIndex += 1
        state.flapsSet = self._flapsNotches[flapsIndex]
        
        flapsLeft = data[self._monidx_flapsLeft]
        flapsIndex = flapsLeft / flapsIncrement
        state.flaps = self._flapsNotches[flapsIndex]
        if flapsIndex != numNotchesM1:
            thisNotch = flapsIndex * flapsIncrement
            nextNotch = thisNotch + flapsIncrement
            
            state.flaps += (self._flapsNotches[flapsIndex+1] - state.flaps) * \
                (flapsLeft - thisNotch) / (nextNotch - thisNotch)
        
        lights = data[self._monidx_lights]
        
        state.navLightsOn = (lights&0x01) != 0
        state.antiCollisionLightsOn = (lights&0x02) != 0
        state.landingLightsOn = (lights&0x04) != 0
        state.strobeLightsOn = (lights&0x10) != 0
        
        state.pitotHeatOn = data[self._monidx_pitot]!=0

        state.parking = data[self._monidx_parking]!=0

        state.gearsDown = data[self._monidx_noseGear]==16383

        state.spoilersArmed = data[self._monidx_spoilersArmed]!=0
        
        spoilers = data[self._monidx_spoilers]
        if spoilers<=4800:
            state.spoilersExtension = 0.0
        else:
            state.spoilersExtension = (spoilers - 4800) * 100.0 / (16383 - 4800)

        state.altimeter = data[self._monidx_altimeter] / 16.0
           
        state.nav1 = AircraftModel.convertFrequency(data[self._monidx_nav1])
        state.nav2 = AircraftModel.convertFrequency(data[self._monidx_nav2])
        state.squawk = AircraftModel.convertBCD(data[self._monidx_squawk], 4)
        
        return state

#------------------------------------------------------------------------------

class GenericAircraftModel(AircraftModel):
    """A generic aircraft model that can handle the fuel levels, the N1 or RPM
    values and some other common parameters in a generic way."""
    def __init__(self, flapsNotches, fuelInfo, numEngines, isN1 = True):
        """Construct the generic aircraft model with the given data.

        flapsNotches is an array of how much degrees the individual flaps
        notches mean.

        fuelInfo is an array of FSUIPC offsets for the levels of the fuel
        tanks. It is assumed to be a 4-byte value, followed by another 4-byte
        value, which is the fuel tank capacity.

        numEngines is the number of engines the aircraft has.

        isN1 determines if the engines have an N1 value or an RPM value
        (e.g. pistons)."""
        super(GenericAircraftModel, self).__init__(flapsNotches = flapsNotches)

        self._fuelInfo = fuelInfo
        self._fuelStartIndex = None
        self._numEngines = numEngines
        self._engineStartIndex = None
        self._isN1 = isN1

    def doesHandle(self, aircraft, aircraftName):
        """Determine if the model handles the given aircraft name.
        
        This implementation returns True."""
        return True

    def addMonitoringData(self, data):
        """Add the model-specific monitoring data to the given array."""
        super(GenericAircraftModel, self).addMonitoringData(data)
        
        self._addOffsetWithIndexMember(data, 0x0af4, "H", "_monidx_fuelWeight")

        self._fuelStartIndex = len(data)
        for offset in self._fuelInfo:
            self._addOffsetWithIndexMember(data, offset, "u")    # tank level
            self._addOffsetWithIndexMember(data, offset+4, "u")  # tank capacity

        if self._isN1:
            self._engineStartIndex = len(data)
            for i in range(0, self._numEngines):
                self._addOffsetWithIndexMember(data, 0x0898 + i * 0x98, "u")  # N1
                self._addOffsetWithIndexMember(data, 0x088c + i * 0x98, "d")  # throttle lever
        
    def getAircraftState(self, aircraft, timestamp, data):
        """Get the aircraft state.

        Get it from the parent, and then add the data about the fuel levels and 
        the engine parameters."""
        state = super(GenericAircraftModel, self).getAircraftState(aircraft,
                                                                   timestamp,
                                                                   data)

        fuelWeight = data[self._monidx_fuelWeight]/256.0
        state.fuel = []
        for i in range(self._fuelStartIndex, 
                       self._fuelStartIndex + 2*len(self._fuelInfo), 2):
            fuel = data[i+1]*data[i]*fuelWeight*const.LBSTOKG/128.0/65536.0
            state.fuel.append(fuel)

        state.n1 = []
        state.reverser = []
        for i in range(self._engineStartIndex,
                       self._engineStartIndex + 2*self._numEngines, 2):
            state.n1.append(data[i]*100.0/16384.0)
            state.reverser.append(data[i+1]<0)

        return state

#------------------------------------------------------------------------------

class GenericModel(GenericAircraftModel):
    """Generic aircraft model for an unknown type."""
    def __init__(self):
        """Construct the model."""
        super(GenericModel, self). \
            __init__(flapsNotches = [0, 10, 20, 30],
                     fuelInfo = [0x0b74, 0x0b7c, 0xb94], 
                     numEngines = 2)

    @property
    def name(self):
        """Get the name for this aircraft model."""
        return "FSUIPC/Generic"    

#------------------------------------------------------------------------------

class B737Model(GenericAircraftModel):
    """Generic model for the Boeing 737 Classing and NG aircraft."""
    def __init__(self):
        """Construct the model."""
        super(B737Model, self). \
            __init__(flapsNotches = [0, 1, 2, 5, 10, 15, 25, 30, 40],
                     fuelInfo = [0x0b74, 0x0b7c, 0xb94], 
                     numEngines = 2)

    @property
    def name(self):
        """Get the name for this aircraft model."""
        return "FSUIPC/Generic Boeing 737"

#------------------------------------------------------------------------------

class PMDGBoeing737NGModel(B737Model):
    """A model handler for the PMDG Boeing 737NG model."""
    @staticmethod
    def doesHandle(aircraft, (name, airPath)):
        """Determine if this model handler handles the aircraft with the given
        name."""
        return aircraft.type in [const.AIRCRAFT_B736,
                                 const.AIRCRAFT_B737,
                                 const.AIRCRAFT_B738] and \
            (name.find("PMDG")!=-1 or airPath.find("PMDG")!=-1) and \
            (name.find("737")!=-1 or airPath.find("737")!=-1) and \
            (name.find("600")!=-1 or airPath.find("600")!=-1 or \
             name.find("700")!=-1 or airPath.find("700")!=-1 or \
             name.find("800")!=-1 or airPath.find("800")!=-1 or \
             name.find("900")!=-1 or airPath.find("900")!=-1)

    @property
    def name(self):
        """Get the name for this aircraft model."""
        return "FSUIPC/PMDG Boeing 737NG"

    def addMonitoringData(self, data):
        """Add the model-specific monitoring data to the given array."""
        super(PMDGBoeing737NGModel, self).addMonitoringData(data)
                
        self._addOffsetWithIndexMember(data, 0x6202, "b", "_pmdgidx_switches")

    def getAircraftState(self, aircraft, timestamp, data):
        """Get the aircraft state.

        Get it from the parent, and then check some PMDG-specific stuff."""
        state = super(PMDGBoeing737NGModel, self).getAircraftState(aircraft,
                                                                   timestamp,
                                                                   data)
        if data[self._pmdgidx_switches]&0x01==0x01:
            state.altimeter = 1013.25

        return state

#------------------------------------------------------------------------------

class B767Model(GenericAircraftModel):
    """Generic model for the Boeing 767 aircraft."""
    def __init__(self):
        """Construct the model."""
        super(B767Model, self). \
            __init__(flapsNotches = [0, 1, 5, 15, 20, 25, 30],
                     fuelInfo = [0x0b74, 0x0b7c, 0xb94], 
                     numEngines = 2)

    @property
    def name(self):
        """Get the name for this aircraft model."""
        return "FSUIPC/Generic Boeing 767"

#------------------------------------------------------------------------------

class DH8DModel(GenericAircraftModel):
    """Generic model for the Boeing 737 NG aircraft."""
    def __init__(self):
        """Construct the model."""
        super(DH8DModel, self). \
            __init__(flapsNotches = [0, 5, 10, 15, 35],
                     fuelInfo = [0x0b74, 0x0b7c, 0xb94], 
                     numEngines = 2)

    @property
    def name(self):
        """Get the name for this aircraft model."""
        return "FSUIPC/Generic Bombardier Dash-8 Q400"

#------------------------------------------------------------------------------

class CRJ2Model(GenericAircraftModel):
    """Generic model for the Bombardier CRJ-200 aircraft."""
    def __init__(self):
        """Construct the model."""
        super(CRJ2Model, self). \
            __init__(flapsNotches = [0, 8, 20, 30, 45],
                     fuelInfo = [0x0b74, 0x0b7c, 0xb94], 
                     numEngines = 2)

    @property
    def name(self):
        """Get the name for this aircraft model."""
        return "FSUIPC/Generic Bombardier CRJ-200"

#------------------------------------------------------------------------------

class F70Model(GenericAircraftModel):
    """Generic model for the Fokker F70 aircraft."""
    def __init__(self):
        """Construct the model."""
        super(F70Model, self). \
            __init__(flapsNotches = [0, 8, 15, 25, 42],
                     fuelInfo = [0x0b74, 0x0b7c, 0xb94], 
                     numEngines = 2)

    @property
    def name(self):
        """Get the name for this aircraft model."""
        return "FSUIPC/Generic Fokker 70"

#------------------------------------------------------------------------------

class DC3Model(GenericAircraftModel):
    """Generic model for the Lisunov Li-2 (DC-3) aircraft."""
    def __init__(self):
        """Construct the model."""
        super(DC3Model, self). \
            __init__(flapsNotches = [0, 15, 30, 45],
                     fuelInfo = [0x0b7c, 0x0b84, 0x0b94, 0x0b9c], 
                     numEngines = 2)

    @property
    def name(self):
        """Get the name for this aircraft model."""
        return "FSUIPC/Generic Lisunov Li-2"

#------------------------------------------------------------------------------

class T134Model(GenericAircraftModel):
    """Generic model for the Tupolev Tu-134 aircraft."""
    def __init__(self):
        """Construct the model."""
        super(T134Model, self). \
            __init__(flapsNotches = [0, 10, 20, 30],
                     fuelInfo = [0x0b74, 
                                 0x0b8c, 0x0b84, 
                                 0x0ba4, 0x0b9c,
                                 0x1254, 0x125c], 
                     numEngines = 2)

    @property
    def name(self):
        """Get the name for this aircraft model."""
        return "FSUIPC/Generic Tupolev Tu-134"

#------------------------------------------------------------------------------

class T154Model(GenericAircraftModel):
    """Generic model for the Tupolev Tu-134 aircraft."""
    def __init__(self):
        """Construct the model."""
        super(T154Model, self). \
            __init__(flapsNotches = [0, 15, 28, 45],
                     fuelInfo = [0x0b74, 0x0b7c, 0x0b94, 
                                 0x1244, 0x0b84, 0x0b9c],
                     numEngines = 3)

    @property
    def name(self):
        """Get the name for this aircraft model."""
        return "FSUIPC/Generic Tupolev Tu-154"

    def getAircraftState(self, aircraft, timestamp, data):
        """Get an aircraft state object for the given monitoring data.

        This removes the reverser value for the middle engine."""
        state = super(T154Model, self).getAircraftState(aircraft, timestamp, data)
        del state.reverser[1]
        return state

#------------------------------------------------------------------------------

class YK40Model(GenericAircraftModel):
    """Generic model for the Yakovlev Yak-40 aircraft."""
    def __init__(self):
        """Construct the model."""
        super(YK40Model, self). \
            __init__(flapsNotches = [0, 20, 35],
                     fuelInfo = [0x0b7c, 0x0b94],
                     numEngines = 2)

    @property
    def name(self):
        """Get the name for this aircraft model."""
        return "FSUIPC/Generic Yakovlev Yak-40"

#------------------------------------------------------------------------------

_genericModels = { const.AIRCRAFT_B736 : B737Model,
                   const.AIRCRAFT_B737 : B737Model,
                   const.AIRCRAFT_B738 : B737Model,
                   const.AIRCRAFT_B733 : B737Model,
                   const.AIRCRAFT_B734 : B737Model,
                   const.AIRCRAFT_B735 : B737Model,
                   const.AIRCRAFT_DH8D : DH8DModel,
                   const.AIRCRAFT_B762 : B767Model,
                   const.AIRCRAFT_B763 : B767Model,
                   const.AIRCRAFT_CRJ2 : B767Model,
                   const.AIRCRAFT_F70  : F70Model,
                   const.AIRCRAFT_DC3  : DC3Model,
                   const.AIRCRAFT_T134 : T134Model,
                   const.AIRCRAFT_T154 : T154Model,
                   const.AIRCRAFT_YK40 : YK40Model }

#------------------------------------------------------------------------------

AircraftModel.registerSpecial(PMDGBoeing737NGModel)

#------------------------------------------------------------------------------

