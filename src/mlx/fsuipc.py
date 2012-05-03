# Module handling the connection to FSUIPC

#------------------------------------------------------------------------------

import fs
import const
import util
import acft

import threading
import os
import time
import calendar
import sys
import codecs

if os.name == "nt":
    import pyuipc
else:
    import pyuipc_sim as pyuipc

#------------------------------------------------------------------------------

# The mapping of tank types to FSUIPC offsets
_tank2offset = { const.FUELTANK_CENTRE : 0x0b74,
                 const.FUELTANK_LEFT : 0x0b7c,
                 const.FUELTANK_RIGHT : 0x0b94,
                 const.FUELTANK_LEFT_AUX : 0x0b84,
                 const.FUELTANK_RIGHT_AUX : 0x0b9c,
                 const.FUELTANK_LEFT_TIP : 0x0b8c,
                 const.FUELTANK_RIGHT_TIP : 0x0ba4,
                 const.FUELTANK_EXTERNAL1 : 0x1254,
                 const.FUELTANK_EXTERNAL2 : 0x125c,
                 const.FUELTANK_CENTRE2 : 0x1244 }

#------------------------------------------------------------------------------

class Handler(threading.Thread):
    """The thread to handle the FSUIPC requests."""
    @staticmethod
    def fsuipc2VS(data):
        """Convert the given vertical speed data read from FSUIPC into feet/min."""
        return data*60.0/const.FEETTOMETRES/256.0

    @staticmethod
    def fsuipc2radioAltitude(data):
        """Convert the given radio altitude data read from FSUIPC into feet."""
        return data/const.FEETTOMETRES/65536.0

    @staticmethod
    def fsuipc2Degrees(data):
        """Convert the given data into degrees."""
        return data * 360.0 / 65536.0 / 65536.0

    @staticmethod
    def fsuipc2PositiveDegrees(data):
        """Convert the given data into positive degrees."""
        degrees = Handler.fsuipc2Degrees(data)
        if degrees<0.0: degrees += 360.0
        return degrees

    @staticmethod
    def fsuipc2IAS(data):
        """Convert the given data into indicated airspeed."""
        return data / 128.0

    @staticmethod
    def _callSafe(fun):
        """Call the given function and swallow any exceptions."""
        try:
            return fun()
        except Exception, e:
            print >> sys.stderr, str(e)
            return None

    # The number of times a read is attempted
    NUM_READATTEMPTS = 3

    # The number of connection attempts
    NUM_CONNECTATTEMPTS = 3

    # The interval between successive connect attempts
    CONNECT_INTERVAL = 0.25

    @staticmethod
    def _performRead(data, callback, extra, validator):
        """Perform a read request.

        If there is a validator, that will be called with the return values,
        and if the values are wrong, the request is retried at most a certain
        number of times.

        Return True if the request has succeeded, False if validation has
        failed during all attempts. An exception may also be thrown if there is
        some lower-level communication problem."""
        attemptsLeft = Handler.NUM_READATTEMPTS
        while attemptsLeft>0:
            values = pyuipc.read(data)
            if validator is None or \
               Handler._callSafe(lambda: validator(values, extra)):
                Handler._callSafe(lambda: callback(values, extra))
                return True
            else:
                attemptsLeft -= 1
        return False

    class Request(object):
        """A simple, one-shot request."""
        def __init__(self, forWrite, data, callback, extra, validator = None):
            """Construct the request."""
            self._forWrite = forWrite
            self._data = data
            self._callback = callback
            self._extra = extra
            self._validator = validator
            
        def process(self, time):
            """Process the request.

            Return True if the request has succeeded, False if data validation
            has failed for a reading request. An exception may also be thrown
            if there is some lower-level communication problem."""            
            if self._forWrite:
                pyuipc.write(self._data)
                Handler._callSafe(lambda: self._callback(True, self._extra))
                return True
            else:
                return Handler._performRead(self._data, self._callback,
                                            self._extra, self._validator)

        def fail(self):
            """Handle the failure of this request."""
            if self._forWrite:
                Handler._callSafe(lambda: self._callback(False, self._extra))
            else:
                Handler._callSafe(lambda: self._callback(None, self._extra))

    class PeriodicRequest(object):
        """A periodic request."""
        def __init__(self, id,  period, data, callback, extra, validator):
            """Construct the periodic request."""
            self._id = id
            self._period = period
            self._nextFire = time.time() + period
            self._data = data
            self._preparedData = None
            self._callback = callback
            self._extra = extra
            self._validator = validator
            
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

            time is the time at which the request is being executed. If this
            function is called too early, nothing is done, and True is
            returned.

            Return True if the request has succeeded, False if data validation
            has failed. An exception may also be thrown if there is some
            lower-level communication problem."""
            if time<self._nextFire:
                return True
            
            if self._preparedData is None:
                self._preparedData = pyuipc.prepare_data(self._data)
                self._data = None

            isOK = Handler._performRead(self._preparedData, self._callback,
                                        self._extra, self._validator)

            if isOK:
                while self._nextFire <= time:
                    self._nextFire += self._period
            
            return isOK

        def fail(self):
            """Handle the failure of this request."""
            pass

        def __cmp__(self, other):
            """Compare two periodic requests. They are ordered by their next
            firing times."""
            return cmp(self._nextFire, other._nextFire)

    def __init__(self, connectionListener,
                 connectAttempts = -1, connectInterval = 0.2):
        """Construct the handler with the given connection listener."""
        threading.Thread.__init__(self)

        self._connectionListener = connectionListener
        self._connectAttempts = connectAttempts
        self._connectInterval = connectInterval

        self._requestCondition = threading.Condition()
        self._connectionRequested = False
        self._connected = False        

        self._requests = []
        self._nextPeriodicID = 1
        self._periodicRequests = []

        self.daemon = True

    def requestRead(self, data, callback, extra = None, validator = None):
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
            self._requests.append(Handler.Request(False, data, callback, extra,
                                                  validator))
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

    def requestPeriodicRead(self, period, data, callback, extra = None,
                            validator = None):
        """Request a periodic read of data.

        period is a floating point number with the period in seconds.

        This function returns an identifier which can be used to cancel the
        request."""
        with self._requestCondition:
            id = self._nextPeriodicID
            self._nextPeriodicID += 1
            request = Handler.PeriodicRequest(id, period, data, callback,
                                              extra, validator)
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
            self._requests = []
            if self._connectionRequested:
                self._connectionRequested = False                
                self._requestCondition.notify()

    def clearRequests(self):
        """Clear the outstanding one-shot requests."""
        with self._requestCondition:
            self._requests = []

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
            
    def _connect(self, autoReconnection = False):
        """Try to connect to the flight simulator via FSUIPC

        Returns True if the connection has been established, False if it was
        not due to no longer requested.
        """
        attempts = 0
        while self._connectionRequested:
            try:
                attempts += 1
                pyuipc.open(pyuipc.SIM_ANY)
                description = "(FSUIPC version: 0x%04x, library version: 0x%04x, FS version: %d)" % \
                    (pyuipc.fsuipc_version, pyuipc.lib_version, 
                     pyuipc.fs_version)
                if not autoReconnection:
                    Handler._callSafe(lambda:     
                                      self._connectionListener.connected(const.SIM_MSFS9, 
                                                                         description))
                self._connected = True
                return True
            except Exception, e:
                print "fsuipc.Handler._connect: connection failed: " + str(e)
                if attempts<self.NUM_CONNECTATTEMPTS:
                    time.sleep(self.CONNECT_INTERVAL)
                else:
                    self._connectionRequested = False
                    if autoReconnection:
                        Handler._callSafe(lambda:     
                                          self._connectionListener.disconnected())
                    else:
                        Handler._callSafe(lambda:     
                                          self._connectionListener.connectionFailed())

        return False
                
    def _handleConnection(self):
        """Handle a living connection."""
        with self._requestCondition:
            while self._connectionRequested:
                self._processRequests()
                self._waitRequest()

    def _waitRequest(self):
        """Wait for the time of the next request.

        Returns also, if the connection is no longer requested.

        Should be called with the request condition lock held."""
        while self._connectionRequested:
            timeout = None
            if self._periodicRequests:
                self._periodicRequests.sort()
                timeout = self._periodicRequests[0].nextFire - time.time()

            if timeout is not None and timeout <= 0.0:
                return
            
            self._requestCondition.wait(timeout)
                
    def _disconnect(self):
        """Disconnect from the flight simulator."""
        if self._connected:
            pyuipc.close()
            self._connected = False
            
    def _processRequest(self, request, time):
        """Process the given request. 

        If an exception occurs or invalid data is read too many times, we try
        to reconnect.

        This function returns only if the request has succeeded, or if a
        connection is no longer requested.

        This function is called with the request lock held, but is relased
        whole processing the request and reconnecting."""
        self._requestCondition.release()

        needReconnect = False
        try:
            try:
                if not request.process(time):
                    print "fsuipc.Handler._processRequest: FSUIPC returned invalid data too many times, reconnecting"
                    needReconnect = True
            except Exception as e:
                print "fsuipc.Handler._processRequest: FSUIPC connection failed (" + \
                      str(e) + "), reconnecting."
                needReconnect = True

            if needReconnect:
                with self._requestCondition:
                    self._requests.insert(0, request)
                self._disconnect()
                self._connect(autoReconnection = True)
        finally:
            self._requestCondition.acquire()
        
    def _processRequests(self):
        """Process any pending requests.

        Will be called with the request lock held."""
        while self._connectionRequested and self._periodicRequests:
            self._periodicRequests.sort()
            request = self._periodicRequests[0]

            t = time.time()

            if request.nextFire>t:
                break
            
            self._processRequest(request, t)

        while self._connectionRequested and self._requests:
            request = self._requests[0]
            del self._requests[0]

            self._processRequest(request, None)

        return self._connectionRequested

#------------------------------------------------------------------------------

class Simulator(object):
    """The simulator class representing the interface to the flight simulator
    via FSUIPC."""
    # The basic data that should be queried all the time once we are connected
    timeData = [ (0x0240, "H"),            # Year
                 (0x023e, "H"),            # Number of day in year
                 (0x023b, "b"),            # UTC hour
                 (0x023c, "b"),            # UTC minute
                 (0x023a, "b") ]           # seconds
    
    normalData = timeData + \
                 [ (0x3d00, -256),           # The name of the current aircraft
                   (0x3c00, -256),           # The path of the current AIR file
                   (0x1274, "h") ]           # Text display mode

    flareData1 = [ (0x023a, "b"),            # Seconds of time
                   (0x31e4, "d"),            # Radio altitude
                   (0x02c8, "d") ]           # Vertical speed
                   
    flareStartData = [ (0x0e90, "H"),        # Ambient wind speed
                       (0x0e92, "H"),        # Ambient wind direction
                       (0x0e8a, "H") ]       # Visibility
                       
    flareData2 = [ (0x023a, "b"),            # Seconds of time
                   (0x0366, "H"),            # On the ground
                   (0x02c8, "d"),            # Vertical speed
                   (0x030c, "d"),            # Touch-down rate
                   (0x02bc, "d"),            # IAS
                   (0x0578, "d"),            # Pitch
                   (0x057c, "d"),            # Bank
                   (0x0580, "d") ]           # Heading

    TIME_SYNC_INTERVAL = 3.0

    @staticmethod
    def _getTimestamp(data):
        """Convert the given data into a timestamp."""
        timestamp = calendar.timegm(time.struct_time([data[0],
                                                      1, 1, 0, 0, 0, -1, 1, 0]))
        timestamp += data[1] * 24 * 3600
        timestamp += data[2] * 3600
        timestamp += data[3] * 60
        timestamp += data[4]        

        return timestamp

    def __init__(self, connectionListener, connectAttempts = -1,
                 connectInterval = 0.2):
        """Construct the simulator.
        
        The aircraft object passed must provide the following members:
        - type: one of the AIRCRAFT_XXX constants from const.py
        - modelChanged(aircraftName, modelName): called when the model handling
        the aircraft has changed.
        - handleState(aircraftState): handle the given state.
        - flareStarted(windSpeed, windDirection, visibility, flareStart,
                       flareStartFS): called when the flare has
          started. windSpeed is in knots, windDirection is in degrees and
          visibility is in metres. flareStart and flareStartFS are two time
          values expressed in seconds that can be used to calculate the flare
          time. 
       - flareFinished(flareEnd, flareEndFS, tdRate, tdRateCalculatedByFS,
                       ias, pitch, bank, heading): called when the flare has
         finished, i.e. the aircraft is on the ground. flareEnd and flareEndFS
         are the two time values corresponding to the touchdown time. tdRate is
         the touch-down rate, tdRateCalculatedBySim indicates if the data comes
         from the simulator or was calculated by the adapter. The other data
         are self-explanatory and expressed in their 'natural' units."""
        self._aircraft = None

        self._handler = Handler(connectionListener,
                                connectAttempts = connectAttempts,
                                connectInterval = connectInterval)
        self._handler.start()

        self._scroll = False

        self._syncTime = False
        self._nextSyncTime = -1
        
        self._normalRequestID = None

        self._monitoringRequested = False
        self._monitoring = False

        self._aircraftName = None
        self._aircraftModel = None

        self._flareRequestID = None
        self._flareRates = []
        self._flareStart = None
        self._flareStartFS = None
    
        self._latin1decoder = codecs.getdecoder("iso-8859-1")

    def connect(self, aircraft):
        """Initiate a connection to the simulator."""
        self._aircraft = aircraft
        self._aircraftName = None
        self._aircraftModel = None
        self._handler.connect()
        if self._normalRequestID is None:
            self._nextSyncTime = -1
            self._startDefaultNormal()

    def reconnect(self):
        """Initiate a reconnection to the simulator.

        It does not reset already set up data, just calls connect() on the
        handler."""
        self._handler.connect()

    def requestZFW(self, callback):
        """Send a request for the ZFW."""
        self._handler.requestRead([(0x3bfc, "d")], self._handleZFW, extra = callback)

    def requestWeights(self, callback):
        """Request the following weights: DOW, ZFW, payload.

        These values will be passed to the callback function in this order, as
        separate arguments."""        
        self._handler.requestRead([(0x13fc, "d")], self._handlePayloadCount,
                                  extra = callback)

    def requestTime(self, callback):
        """Request the time from the simulator."""
        self._handler.requestRead(Simulator.timeData, self._handleTime,
                                  extra = callback)
                                                            
    def startMonitoring(self):
        """Start the periodic monitoring of the aircraft and pass the resulting
        state to the aircraft object periodically."""
        assert not self._monitoringRequested         
        self._monitoringRequested = True

    def stopMonitoring(self):
        """Stop the periodic monitoring of the aircraft."""
        assert self._monitoringRequested 
        self._monitoringRequested = False

    def startFlare(self):
        """Start monitoring the flare time.

        At present it is assumed to be called from the FSUIPC thread, hence no
        protection."""
        #self._aircraft.logger.debug("startFlare")
        if self._flareRequestID is None:
            self._flareRates = []
            self._flareRequestID = self._handler.requestPeriodicRead(0.1,
                                                                     Simulator.flareData1,
                                                                     self._handleFlare1)

    def cancelFlare(self):
        """Cancel monitoring the flare time.

        At present it is assumed to be called from the FSUIPC thread, hence no
        protection."""
        if self._flareRequestID is not None:
            self._handler.clearPeriodic(self._flareRequestID)
            self._flareRequestID = None

    def sendMessage(self, message, duration = 3):
        """Send a message to the pilot via the simulator.

        duration is the number of seconds to keep the message displayed."""
        
        if self._scroll:
            if duration==0: duration = -1
            elif duration == 1: duration = -2
            else: duration = -duration

        data = [(0x3380, -1 - len(message), message),
                (0x32fa, 'h', duration)]

        self._handler.requestWrite(data, self._handleMessageSent)

    def getFuel(self, tanks, callback):
        """Get the fuel from the given tanks.

        The callback will be called with a list of two-tuples, where the tuples
        have the following items:
        - the current weight of the fuel in the tank (in kgs)
        - the current total capacity of the tank (in kgs)."""
        data = [(0x0af4, "H")]     # Fuel weight
        for tank in tanks:
            offset = _tank2offset[tank]
            data.append( (offset, "u") )     # tank level
            data.append( (offset+4, "u") )   # tank capacity

        self._handler.requestRead(data, self._handleFuelRetrieved,
                                  extra = callback)

    def setFuelLevel(self, levels):
        """Set the fuel level to the given ones.

        levels is an array of two-tuples, where each tuple consists of the
        following:
        - the const.FUELTANK_XXX constant denoting the tank that must be set,
        - the requested level of the fuel as a floating-point value between 0.0
        and 1.0."""
        data = []
        for (tank, level) in levels:
            offset = _tank2offset[tank]
            data.append( (offset, "u", long(level * 128.8 * 65536.0)) )
        self._handler.requestWrite(data, self._handleFuelWritten)

    def enableTimeSync(self):
        """Enable the time synchronization."""
        self._nextSyncTime = -1
        self._syncTime = True
            
    def disableTimeSync(self):
        """Enable the time synchronization."""
        self._syncTime = False
        self._nextSyncTime = -1
            
    def disconnect(self):
        """Disconnect from the simulator."""
        assert not self._monitoringRequested 
        
        self._stopNormal()
        self._handler.disconnect()

    def _startDefaultNormal(self):
        """Start the default normal periodic request."""
        assert self._normalRequestID is None
        self._normalRequestID = \
             self._handler.requestPeriodicRead(1.0,
                                               Simulator.normalData,
                                               self._handleNormal,
                                               validator = self._validateNormal)

    def _stopNormal(self):
        """Stop the normal period request."""
        assert self._normalRequestID is not None
        self._handler.clearPeriodic(self._normalRequestID)
        self._normalRequestID = None
        self._monitoring = False

    def _validateNormal(self, data, extra):
        """Validate the normal data."""
        return data[0]!=0 and data[1]!=0 and len(data[5])>0 and len(data[6])>0

    def _handleNormal(self, data, extra):
        """Handle the reply to the normal request.

        At the beginning the result consists the data for normalData. When
        monitoring is started, it contains the result also for the
        aircraft-specific values.
        """
        timestamp = Simulator._getTimestamp(data)

        createdNewModel = self._setAircraftName(timestamp, data[5], data[6])

        self._scroll = data[7]!=0

        self._checkTimeSync()
        
        if self._monitoringRequested and not self._monitoring:
            self._stopNormal()
            self._startMonitoring()
        elif self._monitoring and not self._monitoringRequested:
            self._stopNormal()
            self._startDefaultNormal()
        elif self._monitoring and self._aircraftModel is not None and \
             not createdNewModel:
            aircraftState = self._aircraftModel.getAircraftState(self._aircraft, 
                                                                 timestamp, data)
            self._aircraft.handleState(aircraftState)

    def _checkTimeSync(self):
        """Check if we need to synchronize the FS time."""
        if not self._syncTime: return

        now = time.time()
        seconds = time.gmtime(now).tm_sec

        if seconds>30 and seconds<59:
            if self._nextSyncTime > (now - 0.49):
                return
            
            self._handler.requestWrite([(0x023a, "b", int(seconds))],
                                       self._handleTimeSynced)
            
            #print "Set the seconds to ", seconds

            if self._nextSyncTime<0:
                self._nextSyncTime = now
                
            self._nextSyncTime += Simulator.TIME_SYNC_INTERVAL
        else:
            self._nextSyncTime = -1

    def _handleTimeSynced(self, success, extra):
        """Callback for the time sync result."""
        pass
        
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
 
        
        self._aircraft.modelChanged(timestamp, self._latin1decoder(name)[0],
                                    self._aircraftModel.name)        

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
        data = Simulator.normalData[:]
        self._aircraftModel.addMonitoringData(data)
        
        self._normalRequestID = \
            self._handler.requestPeriodicRead(1.0, data, 
                                              self._handleNormal,
                                              validator = self._validateNormal)
        self._monitoring = True

    def _addFlareRate(self, data):
        """Append a flare rate to the list of last rates."""
        if len(self._flareRates)>=3:
            del self._flareRates[0]
        self._flareRates.append(Handler.fsuipc2VS(data))

    def _handleFlare1(self, data, normal):
        """Handle the first stage of flare monitoring."""
        #self._aircraft.logger.debug("handleFlare1: " + str(data))
        if Handler.fsuipc2radioAltitude(data[1])<=50.0:
            self._flareStart = time.time()
            self._flareStartFS = data[0]
            self._handler.clearPeriodic(self._flareRequestID)
            self._flareRequestID = \
                self._handler.requestPeriodicRead(0.1, 
                                                  Simulator.flareData2,
                                                  self._handleFlare2)
            self._handler.requestRead(Simulator.flareStartData,
                                      self._handleFlareStart)
                
        self._addFlareRate(data[2])

    def _handleFlareStart(self, data, extra):
        """Handle the data need to notify the aircraft about the starting of
        the flare."""
        #self._aircraft.logger.debug("handleFlareStart: " + str(data))
        if data is not None:
            windDirection = data[1]*360.0/65536.0
            if windDirection<0.0: windDirection += 360.0
            self._aircraft.flareStarted(data[0], windDirection,
                                        data[2]*1609.344/100.0,
                                        self._flareStart, self._flareStartFS)

    def _handleFlare2(self, data, normal):
        """Handle the first stage of flare monitoring."""
        #self._aircraft.logger.debug("handleFlare2: " + str(data))
        if data[1]!=0:
            flareEnd = time.time()
            self._handler.clearPeriodic(self._flareRequestID)
            self._flareRequestID = None

            flareEndFS = data[0]
            if flareEndFS<self._flareStartFS:
                flareEndFS += 60

            tdRate = Handler.fsuipc2VS(data[3])
            tdRateCalculatedByFS = True
            if tdRate==0 or tdRate>1000.0 or tdRate<-1000.0:
                tdRate = min(self._flareRates)
                tdRateCalculatedByFS = False

            self._aircraft.flareFinished(flareEnd, flareEndFS,
                                         tdRate, tdRateCalculatedByFS,
                                         Handler.fsuipc2IAS(data[4]),
                                         Handler.fsuipc2Degrees(data[5]),
                                         Handler.fsuipc2Degrees(data[6]),
                                         Handler.fsuipc2PositiveDegrees(data[7]))
        else:
            self._addFlareRate(data[2])

    def _handleZFW(self, data, callback):
        """Callback for a ZFW retrieval request."""
        zfw = data[0] * const.LBSTOKG / 256.0
        callback(zfw)
                                                  
    def _handleTime(self, data, callback):
        """Callback for a time retrieval request."""
        callback(Simulator._getTimestamp(data))

    def _handlePayloadCount(self, data, callback):
        """Callback for the payload count retrieval request."""
        payloadCount = data[0]
        data = [(0x3bfc, "d"), (0x30c0, "f")]
        for i in range(0, payloadCount):
            data.append((0x1400 + i*48, "f"))
        
        self._handler.requestRead(data, self._handleWeights,
                                  extra = callback)

    def _handleWeights(self, data, callback):
        """Callback for the weights retrieval request."""
        zfw = data[0] * const.LBSTOKG / 256.0
        grossWeight = data[1] * const.LBSTOKG
        payload = sum(data[2:]) * const.LBSTOKG
        dow = zfw - payload
        callback(dow, payload, zfw, grossWeight)

    def _handleMessageSent(self, success, extra):
        """Callback for a message sending request."""
        pass

    def _handleFuelRetrieved(self, data, callback):
        """Callback for a fuel retrieval request."""
        fuelWeight = data[0] / 256.0
        result = []
        for i in range(1, len(data), 2):
            capacity = data[i+1] * fuelWeight * const.LBSTOKG
            amount = data[i] * capacity / 128.0 / 65536.0
            result.append( (amount, capacity) )

        callback(result)
                                                  
    def _handleFuelWritten(self, success, extra):
        """Callback for a fuel setting request."""
        pass
                                                  
#------------------------------------------------------------------------------

class AircraftModel(object):
    """Base class for the aircraft models.

    Aircraft models handle the data arriving from FSUIPC and turn it into an
    object describing the aircraft's state."""
    monitoringData = [("paused", 0x0264, "H"),
                      ("latitude", 0x0560, "l"),
                      ("longitude", 0x0568, "l"),
                      ("frozen", 0x3364, "H"),
                      ("replay", 0x0628, "d"),
                      ("slew", 0x05dc, "H"),
                      ("overspeed", 0x036d, "b"),
                      ("stalled", 0x036c, "b"),
                      ("onTheGround", 0x0366, "H"),
                      ("zfw", 0x3bfc, "d"),
                      ("grossWeight", 0x30c0, "f"),
                      ("heading", 0x0580, "d"),
                      ("pitch", 0x0578, "d"),
                      ("bank", 0x057c, "d"),
                      ("ias", 0x02bc, "d"),
                      ("mach", 0x11c6, "H"),
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
                      ("squawk", 0x0354, "H"),
                      ("windSpeed", 0x0e90, "H"),
                      ("windDirection", 0x0e92, "H"),
                      ("visibility", 0x0e8a, "H")]


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

        state.latitude = data[self._monidx_latitude] * \
                         90.0 / 10001750.0 / 65536.0 / 65536.0

        state.longitude = data[self._monidx_longitude] * \
                          360.0 / 65536.0 / 65536.0 / 65536.0 / 65536.0
        if state.longitude>180.0: state.longitude = 360.0 - state.longitude
        
        state.paused = data[self._monidx_paused]!=0 or \
            data[self._monidx_frozen]!=0 or \
            data[self._monidx_replay]!=0
        state.trickMode = data[self._monidx_slew]!=0

        state.overspeed = data[self._monidx_overspeed]!=0
        state.stalled = data[self._monidx_stalled]!=0
        state.onTheGround = data[self._monidx_onTheGround]!=0

        state.zfw = data[self._monidx_zfw] * const.LBSTOKG / 256.0
        state.grossWeight = data[self._monidx_grossWeight] * const.LBSTOKG
        
        state.heading = Handler.fsuipc2PositiveDegrees(data[self._monidx_heading])

        state.pitch = Handler.fsuipc2Degrees(data[self._monidx_pitch])
        state.bank = Handler.fsuipc2Degrees(data[self._monidx_bank])

        state.ias = Handler.fsuipc2IAS(data[self._monidx_ias])
        state.mach = data[self._monidx_mach] / 20480.0
        state.groundSpeed = data[self._monidx_groundSpeed]* 3600.0/65536.0/1852.0
        state.vs = Handler.fsuipc2VS(data[self._monidx_vs])

        state.radioAltitude = \
            Handler.fsuipc2radioAltitude(data[self._monidx_radioAltitude])
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
        state.flaps = self._flapsNotches[-1]*flapsLeft/16383.0
        
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

        state.windSpeed = data[self._monidx_windSpeed]
        state.windDirection = data[self._monidx_windDirection]*360.0/65536.0
        if state.windDirection<0.0: state.windDirection += 360.0

        state.visibility = data[self._monidx_visibility]*1609.344/100.0
        
        return state

#------------------------------------------------------------------------------

class GenericAircraftModel(AircraftModel):
    """A generic aircraft model that can handle the fuel levels, the N1 or RPM
    values and some other common parameters in a generic way."""
    
    def __init__(self, flapsNotches, fuelTanks, numEngines, isN1 = True):
        """Construct the generic aircraft model with the given data.

        flapsNotches is an array of how much degrees the individual flaps
        notches mean.

        fuelTanks is an array of const.FUELTANK_XXX constants about the
        aircraft's fuel tanks. They will be converted to offsets.

        numEngines is the number of engines the aircraft has.

        isN1 determines if the engines have an N1 value or an RPM value
        (e.g. pistons)."""
        super(GenericAircraftModel, self).__init__(flapsNotches = flapsNotches)

        self._fuelTanks = fuelTanks
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
        for tank in self._fuelTanks:
            offset = _tank2offset[tank]
            self._addOffsetWithIndexMember(data, offset, "u")    # tank level
            self._addOffsetWithIndexMember(data, offset+4, "u")  # tank capacity

        if self._isN1:
            self._engineStartIndex = len(data)
            for i in range(0, self._numEngines):
                self._addOffsetWithIndexMember(data, 0x2000 + i * 0x100, "f")  # N1
                self._addOffsetWithIndexMember(data, 0x088c + i * 0x98, "h")  # throttle lever
        
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
                       self._fuelStartIndex + 2*len(self._fuelTanks), 2):
            fuel = data[i+1]*data[i]*fuelWeight*const.LBSTOKG/128.0/65536.0
            state.fuel.append(fuel)

        state.n1 = []
        state.reverser = []
        for i in range(self._engineStartIndex,
                       self._engineStartIndex + 2*self._numEngines, 2):
            state.n1.append(data[i])
            state.reverser.append(data[i+1]<0)

        return state

#------------------------------------------------------------------------------

class GenericModel(GenericAircraftModel):
    """Generic aircraft model for an unknown type."""
    def __init__(self):
        """Construct the model."""
        super(GenericModel, self). \
            __init__(flapsNotches = [0, 10, 20, 30],
                     fuelTanks = [const.FUELTANK_LEFT, const.FUELTANK_RIGHT],
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
                     fuelTanks = acft.Boeing737.fuelTanks,
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
                     fuelTanks = acft.Boeing767.fuelTanks,
                     numEngines = 2)

    @property
    def name(self):
        """Get the name for this aircraft model."""
        return "FSUIPC/Generic Boeing 767"

#------------------------------------------------------------------------------

class DH8DModel(GenericAircraftModel):
    """Generic model for the Bombardier  Dash 8-Q400 aircraft."""
    def __init__(self):
        """Construct the model."""
        super(DH8DModel, self). \
            __init__(flapsNotches = [0, 5, 10, 15, 35],
                     fuelTanks = acft.DH8D.fuelTanks,
                     numEngines = 2)

    @property
    def name(self):
        """Get the name for this aircraft model."""
        return "FSUIPC/Generic Bombardier Dash 8-Q400"

#------------------------------------------------------------------------------

class DreamwingsDH8DModel(DH8DModel):
    """Model handler for the Dreamwings Dash 8-Q400."""
    @staticmethod
    def doesHandle(aircraft, (name, airPath)):
        """Determine if this model handler handles the aircraft with the given
        name."""
        return aircraft.type==const.AIRCRAFT_DH8D and \
            (name.find("Dreamwings")!=-1 or airPath.find("Dreamwings")!=-1) and \
            (name.find("Dash")!=-1 or airPath.find("Dash")!=-1) and \
            (name.find("Q400")!=-1 or airPath.find("Q400")!=-1) and \
            airPath.find("Dash8Q400")!=-1

    @property
    def name(self):
        """Get the name for this aircraft model."""
        return "FSUIPC/Dreamwings Bombardier Dash 8-Q400"

    def getAircraftState(self, aircraft, timestamp, data):
        """Get the aircraft state.

        Get it from the parent, and then invert the pitot heat state."""
        state = super(DreamwingsDH8DModel, self).getAircraftState(aircraft,
                                                                  timestamp,
                                                                  data)
        state.pitotHeatOn = not state.pitotHeatOn

        return state
#------------------------------------------------------------------------------

class CRJ2Model(GenericAircraftModel):
    """Generic model for the Bombardier CRJ-200 aircraft."""
    def __init__(self):
        """Construct the model."""
        super(CRJ2Model, self). \
            __init__(flapsNotches = [0, 8, 20, 30, 45],
                     fuelTanks = acft.CRJ2.fuelTanks,
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
                     fuelTanks = acft.F70.fuelTanks,
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
                     fuelTanks = acft.DC3.fuelTanks,
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
                     fuelTanks = acft.T134.fuelTanks,
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
                     fuelTanks = acft.T154.fuelTanks,
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
                     fuelTanks = acft.YK40.fuelTanks,
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
AircraftModel.registerSpecial(DreamwingsDH8DModel)

#------------------------------------------------------------------------------
