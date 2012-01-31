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
                                  self._connectionListener.connected(const.TYPE_MSFS9, 
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
    normalData = [ (0x3d00, -256) ]

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
        self._setAircraftName(data[0])
        if self._monitoringRequested and not self._monitoring:
            self._monitoring = True
            self._stopNormal()
            self._startMonitoring()
        elif self._monitoring and not self._monitoringRequested:
            self._monitoring = False
            self._stopNormal()
            self._startDefaultNormal()
        elif self._monitoring and self._aircraftModel is not None:
            aircraftState = self._aircraftModel.getAircraftState(self._aircraft, data)
            self._aircraft.handleState(aircraftState)

    def _setAircraftName(self, name):
        """Set the name of the aicraft and if it is different from the
        previous, create a new model for it.
        
        If so, also notifty the aircraft about the change."""
        if name==self._aircraftName:
            return

        self._aircraftName = name
        if self._aircraftModel is None or \
           not self._aircraftModel.doesHandle(name):            
            self._setAircraftModel(AircraftModel.create(self._aircraft, name))
        
        self._aircraft.modelChanged(self._aircraftName, 
                                    self._aircraftModel.name)

    def _setAircraftModel(self, model):
        """Set a new aircraft model.

        It will be queried for the data to monitor and the monitoring request
        will be replaced by a new one."""
        self._aircraftModel = model
        
        if self._monitoring:
            self._handler.clearPeriodic(self._normalRequestID)            
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
    monitoringData = [("year", 0x0240, "H"),
                      ("dayOfYear", 0x023e, "H"),
                      ("zuluHour", 0x023b, "b"),
                      ("zuluMinute", 0x023c, "b"),
                      ("seconds", 0x023a, "b"),
                      ("paused", 0x0264, "H"),
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
                      ("altitude", 0x0570, "l"),
                      ("gLoad", 0x11ba, "H"),
                      ("flapsControl", 0x0bdc, "d"),
                      ("flapsLeft", 0x0be0, "d"),
                      ("flapsRight", 0x0be4, "d"),
                      ("lights", 0x0d0c, "H"),
                      ("pitot", 0x029c, "b"),
                      ("noseGear", 0x0bec, "d"),
                      ("spoilersArmed", 0x0bcc, "d"),
                      ("spoilers", 0x0bd0, "d"),
                      ("altimeter", 0x0330, "H"),
                      ("nav1", 0x0350, "H"),
                      ("nav2", 0x0352, "H")]

    @staticmethod
    def create(aircraft, aircraftName):
        """Create the model for the given aircraft name, and notify the
        aircraft about it."""        
        return AircraftModel([0, 10, 20, 30])

    @staticmethod
    def convertFrequency(data):
        """Convert the given frequency data to a string."""
        frequency = ""
        for i in range(0, 4):
            digit = chr(ord('0') + (data&0x0f))
            data >>= 4
            frequency = digit + frequency
            if i==1:
                frequency = "." + frequency
        return "1" + frequency            

    def __init__(self, flapsNotches):
        """Construct the aircraft model.
        
        flapsNotches is a list of degrees of flaps that are available on the aircraft."""
        self._flapsNotches = flapsNotches
    
    @property
    def name(self):
        """Get the name for this aircraft model."""
        return "FSUIPC/Generic"
    
    def doesHandle(self, aircraftName):
        """Determine if the model handles the given aircraft name.
        
        This default implementation returns True."""
        return True

    def addDataWithIndexMembers(self, dest, prefix, data):
        """Add FSUIPC data to the given array and also corresponding index
        member variables with the given prefix.

        data is a list of triplets of the following items:
        - the name of the data item. The index member variable will have a name
        created by prepending the given prefix to this name.
        - the FSUIPC offset
        - the FSUIPC type
        
        The latter two items will be appended to dest."""
        index = len(dest)
        for (name, offset, type) in data:
            setattr(self, prefix + name, index)
            dest.append((offset, type))
            index += 1
            
    def addMonitoringData(self, data):
        """Get the data specification for monitoring.
        
        Add the model-specific monitoring data to the given array."""
        self.addDataWithIndexMembers(data, "_monidx_",
                                     AircraftModel.monitoringData)
    
    def getAircraftState(self, aircraft, data):
        """Get an aircraft state object for the given monitoring data."""
        state = fs.AircraftState()
        
        timestamp = calendar.timegm(time.struct_time([data[self._monidx_year],
                                                      1, 1, 0, 0, 0, -1, 1, 0]))
        timestamp += data[self._monidx_dayOfYear] * 24 * 3600
        timestamp += data[self._monidx_zuluHour] * 3600
        timestamp += data[self._monidx_zuluMinute] * 60
        timestamp += data[self._monidx_seconds]        
        state.timestamp = timestamp
        
        state.paused = data[self._monidx_paused]!=0 or \
            data[self._monidx_frozen]!=0 or \
            data[self._monidx_replay]!=0
        state.trickMode = data[self._monidx_slew]!=0

        state.overspeed = data[self._monidx_overspeed]!=0
        state.stalled = data[self._monidx_stalled]!=0
        state.onTheGround = data[self._monidx_onTheGround]!=0

        state.grossWeight = data[self._monidx_grossWeight] * util.LBSTOKG
        
        state.heading = data[self._monidx_heading]*360.0/65536.0/65536.0
        if state.heading<0.0: state.heading += 360.0

        state.pitch = data[self._monidx_pitch]*360.0/65536.0/65536.0
        state.bank = data[self._monidx_bank]*360.0/65536.0/65536.0

        state.ias = data[self._monidx_ias]/128.0
        state.groundSpeed = data[self._monidx_groundSpeed]* 3600.0/65536.0/1852.0
        state.vs = data[self._monidx_vs]*60.0*3.28984/256.0

        state.altitude = data[self._monidx_altitude]*3.28084/65536.0/65536.0

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
        
        return state

#------------------------------------------------------------------------------

