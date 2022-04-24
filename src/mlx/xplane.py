
from . import fs
from . import const
from . import util
from .watchdog import Watchdog

import threading
import time
import calendar
import datetime
import sys
import codecs
import math
from functools import total_ordering

from xplra import XPlane, MultiGetter, MultiSetter, ProtocolException
from xplra import TYPE_INT, TYPE_FLOAT, TYPE_DOUBLE
from xplra import TYPE_FLOAT_ARRAY, TYPE_INT_ARRAY, TYPE_BYTE_ARRAY
from xplra import HOTKEY_MODIFIER_SHIFT, HOTKEY_MODIFIER_CONTROL

#------------------------------------------------------------------------------

## @package mlx.xplane
#
# The module towards X-Plane
#
# This module implements the simulator interface to X-Plane via the
# X-Plane Remote Access (xplra) plugin.

#------------------------------------------------------------------------------

_hgin2hpa = 1013.25 / 29.92

_mps2knots = 3600.0 / 1852

#------------------------------------------------------------------------------

class Request(object):
    """Base class for one-shot requests."""
    def __init__(self, handler, callback, extra):
        """Construct the request."""
        self._handler = handler
        self._callback = callback
        self._extra = extra
        self._result = None

    def process(self, time):
        """Process the request.

        Return True if the request has succeeded, False if data validation
        has failed for a reading request. An exception may also be thrown
        if there is some lower-level communication problem."""
        if self._process(time):
            Handler._callSafe(lambda: self._callback(self._result,
                                                     self._extra))
            return True
        else:
            return False

    def fail(self):
        """Handle the failure of this request."""
        Handler._callSafe(lambda: self._callback(False, self._extra))

class DataRequest(Request):
    """A simple, one-shot data read or write request."""
    def __init__(self, handler, forWrite, data, callback, extra,
                 validator = None):
        """Construct the request."""
        super(DataRequest, self).__init__(handler, callback, extra)

        self._forWrite = forWrite
        self._validator = validator

        xplane = handler._xplane
        self._multiBuffer = xplane.createMultiSetter() if forWrite \
                            else xplane.createMultiGetter()

        Handler._setupMultiBuffer(self._multiBuffer,
                                  [(d[0], d[1]) for d in data])

        if forWrite:
            index = 0
            for (_, _, value) in data:
                self._multiBuffer[index] = value
                index += 1


    def fail(self):
        """Handle the failure of this request."""
        if self._forWrite:
            super(DataRequest, self).fail()
        else:
            Handler._callSafe(lambda: self._callback(None, self._extra))

    def _process(self, time):
        """Process the request."""
        if self._forWrite:
            self._multiBuffer.execute()
            self._result = True
            return True

        try:
            if Handler._performRead(self._multiBuffer,
                                    self._extra, self._validator):
                self._result = self._multiBuffer
                return True
            else:
                return False
        except ProtocolException as e:
            self._result = None
            return True

class ShowMessageRequest(Request):
    """Request to show a message in the simulator window."""
    def __init__(self, handler, message, duration, callback, extra):
        """Construct the request."""
        super(ShowMessageRequest, self).__init__(handler,
                                                         callback, extra)
        self._message = message
        self._duration = duration

    def _process(self, time):
        """Process the request."""
        self._handler._xplane.showMessage(self._message, self._duration)
        self._result = True
        return True

class RegisterHotkeysRequest(Request):
    """Request to register hotkeys with the simulator."""
    def __init__(self, handler, hotkeyCodes, callback, extra):
        """Construct the request."""
        super(RegisterHotkeysRequest, self).__init__(handler,
                                                     callback,
                                                     extra)
        self._hotkeyCodes = hotkeyCodes

    def _process(self, time):
        """Process the request."""
        self._handler._xplane.registerHotkeys(self._hotkeyCodes)
        self._result = True
        return True

class UnregisterHotkeysRequest(Request):
    """Request to register hotkeys with the simulator."""
    def _process(self, time):
        """Process the request."""
        self._handler._xplane.unregisterHotkeys()
        self._result = True
        return True

@total_ordering
class PeriodicRequest(object):
    """A periodic request."""
    def __init__(self, handler, id, period, callback, extra):
        """Construct the periodic request."""
        self._handler = handler
        self._id = id
        self._period = period
        self._nextFire = time.time()
        self._callback = callback
        self._extra = extra
        self._result = None

    @property
    def id(self):
        """Get the ID of this periodic request."""
        return self._id

    @property
    def nextFire(self):
        """Get the next firing time."""
        return self._nextFire

    def process(self, now):
        """Check if this request should be executed, and if so, do so.

        now is the time at which the request is being executed. If this
        function is called too early, nothing is done, and True is
        returned.

        Return True if the request has succeeded, False if data validation
        has failed. An exception may also be thrown if there is some
        lower-level communication problem."""
        if now<self._nextFire:
            return True

        isOK = self._process(time)

        if isOK:
            Handler._callSafe(lambda: self._callback(self._result,
                                                     self._extra))
            now = time.time()
            while self._nextFire <= now:
                self._nextFire += self._period

        return isOK

    def fail(self):
        """Handle the failure of this request."""
        pass

    def __eq__(self, other):
        """Equality comparison by the firing times"""
        return self._nextFire == other._nextFire

    def __ne__(self, other):
        """Non-equality comparison by the firing times"""
        return self._nextFire != other._nextFire

    def __lt__(self, other):
        """Less-than comparison by the firing times"""
        return self._nextFire < other._nextFire

class PeriodicDataRequest(PeriodicRequest):
    """A periodic request."""
    def __init__(self, handler, id, period, data, callback, extra,
                 validator):
        """Construct the periodic request."""
        super(PeriodicDataRequest, self).__init__(handler, id, period,
                                                  callback, extra)
        self._validator = validator
        self._multiGetter = handler._xplane.createMultiGetter()
        Handler._setupMultiBuffer(self._multiGetter, data)

    def _process(self, now):
        """Process the request."""
        if Handler._performRead(self._multiGetter,
                                self._extra, self._validator):
            self._result = self._multiGetter
            return True
        else:
            return False

#------------------------------------------------------------------------------

class HotkeysStateRequest(PeriodicRequest):
    """Periodic hotkey query request."""
    def _process(self, now):
        """Process the request."""
        self._result = self._handler._xplane.queryHotkeys()
        return True

#------------------------------------------------------------------------------

class Handler(threading.Thread):
    """The thread to handle the requests towards X-Plane."""
    @staticmethod
    def _callSafe(fun):
        """Call the given function and swallow any exceptions."""
        try:
            return fun()
        except Exception as e:
            print(util.utf2unicode(str(e)), file=sys.stderr)
            return None

    # The number of times a read is attempted
    NUM_READATTEMPTS = 3

    # The number of connection attempts
    NUM_CONNECTATTEMPTS = 3

    # The interval between successive connect attempts
    CONNECT_INTERVAL = 0.25

    @staticmethod
    def _setupMultiBuffer(buffer, dataSpec):
        """Setup the given multi-dataref buffer for the given data
        specification.

        The specification is a list of tuples of two items:
        - the name of the dataref
        - the type of the dataref. It can be one of the following:
          - an integer denoting the type. If it denotes an array type, the
            length will be -1 (i.e. as many as returned when reading the
            value), and the offset will be 0
          - a tuple of two or three items:
            - the first item is the type constant
            - the second item is the length
            - the third item is the offset, which defaults to 0."""
        for (name, typeInfo) in dataSpec:
            length = -1
            offset = 0
            type = 0
            if isinstance(typeInfo, tuple):
                type = typeInfo[0]
                length = typeInfo[1]
                offset = 0 if len(typeInfo)<3 else typeInfo[2]
            else:
                type = typeInfo

            if type==TYPE_INT:
                buffer.addInt(name)
            elif type==TYPE_FLOAT:
                buffer.addFloat(name)
            elif type==TYPE_DOUBLE:
                buffer.addDouble(name)
            elif type==TYPE_FLOAT_ARRAY:
                buffer.addFloatArray(name, length = length, offset = offset)
            elif type==TYPE_INT_ARRAY:
                buffer.addIntArray(name, length = length, offset = offset)
            elif type==TYPE_BYTE_ARRAY:
                buffer.addByteArray(name, length = length, offset = offset)
            else:
                raise TypeError("xplane.Handler._setupMultiBuffer: invalid type info: %s for dataref '%s'" % (typeInfo, name))



    @staticmethod
    def _performRead(multiGetter, extra, validator):
        """Perform a read request.

        If there is a validator, that will be called with the return values,
        and if the values are wrong, the request is retried at most a certain
        number of times.

        Return True if the request has succeeded, False if validation has
        failed during all attempts. An exception may also be thrown if there is
        some lower-level communication problem."""
        attemptsLeft = Handler.NUM_READATTEMPTS
        while attemptsLeft>0:
            try:
                multiGetter.execute()
            except ProtocolException as e:
                print("xplane.Handler._performRead: " + str(e))
                raise

            if validator is None or \
               Handler._callSafe(lambda: validator(multiGetter, extra)):
                return True
            else:
                attemptsLeft -= 1
        return False

    def __init__(self, connectionListener,
                 connectAttempts = -1, connectInterval = 0.2):
        """Construct the handler with the given connection listener."""
        threading.Thread.__init__(self)

        self._connectionListener = connectionListener
        self._connectAttempts = connectAttempts
        self._connectInterval = connectInterval

        self._xplane = XPlane()

        self._requestCondition = threading.Condition()
        self._connectionRequested = False
        self._connected = False

        self._requests = []
        self._nextPeriodicID = 1
        self._periodicRequests = []

        self._watchdogClient = Watchdog.get().addClient(2.0, "xplane.Handler")

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
            self._requests.append(DataRequest(self, False, data,
                                              callback, extra,
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
            request = DataRequest(self, True, data, callback, extra)
            #print "xplane.Handler.requestWrite", request
            self._requests.append(request)
            self._requestCondition.notify()

    def requestPeriodicRead(self, period, data, callback, extra = None,
                            validator = None):
        """Request a periodic read of data.

        period is a floating point number with the period in seconds.

        This function returns an identifier which can be used to cancel the
        request."""
        with self._requestCondition:
            id = self._nextPeriodicID
            self._nextPeriodicID += 1
            request = PeriodicDataRequest(self, id, period,
                                          data, callback,
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

    def requestShowMessage(self, message, duration, callback, extra = None):
        """Request showing a message in the simulator."""
        with self._requestCondition:
            self._requests.append(ShowMessageRequest(self,
                                                     message, duration,
                                                     callback, extra))
            self._requestCondition.notify()

    def registerHotkeys(self, hotkeys, callback, extra = None):
        """Request registering the given hotkeys."""
        with self._requestCondition:
            self._requests.append(RegisterHotkeysRequest(self, hotkeys,
                                                         callback, extra))
            self._requestCondition.notify()

    def requestHotkeysState(self, period, callback, extra = None):
        """Request a periodic query of the hotkey status."""
        with self._requestCondition:
            id = self._nextPeriodicID
            self._nextPeriodicID += 1
            request = HotkeysStateRequest(self, id, period, callback, extra)
            self._periodicRequests.append(request)
            self._requestCondition.notify()
            return id

    def unregisterHotkeys(self, callback, extra = None):
        """Request unregistering the hotkeys."""
        with self._requestCondition:
            self._requests.append(UnregisterHotkeysRequest(self,
                                                           callback, extra))
            self._requestCondition.notify()

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

            if self._connect()>0:
                self._handleConnection()

            self._disconnect()

    def _waitConnectionRequest(self):
        """Wait for a connection request to arrive."""
        with self._requestCondition:
            while not self._connectionRequested:
                self._requestCondition.wait()

    def _connect(self, autoReconnection = False, attempts = 0):
        """Try to connect to the flight simulator via XPLRA

        Returns True if the connection has been established, False if it was
        not due to no longer requested.
        """
        while self._connectionRequested:
            if attempts>=self.NUM_CONNECTATTEMPTS:
                self._connectionRequested = False
                if autoReconnection:
                    Handler._callSafe(lambda:
                                      self._connectionListener.disconnected())
                else:
                    Handler._callSafe(lambda:
                                      self._connectionListener.connectionFailed())
                return 0

            try:
                attempts += 1
                self._xplane.connect()

                (xplaneVersion, xplmVersion, xplraVersion) = \
                  self._xplane.getVersions()

                description = "(X-Plane version: %d, XPLM version: %d, XPLRA version: %03d)" % \
                  (xplaneVersion, xplmVersion, xplraVersion)
                if not autoReconnection:
                    fsType = const.SIM_XPLANE11 if xplaneVersion>=11000 else \
                      (const.SIM_XPLANE10 if xplaneVersion>=10000 else const.SIM_XPLANE9)

                    Handler._callSafe(lambda:
                                      self._connectionListener.connected(fsType,
                                                                         description))
                self._connected = True
                return attempts
            except Exception as e:
                print("xplane.Handler._connect: connection failed: " + \
                      util.utf2unicode(str(e)) + \
                      " (attempts: %d)" % (attempts,))
                if attempts<self.NUM_CONNECTATTEMPTS:
                    time.sleep(self.CONNECT_INTERVAL)
                self._xplane.disconnect()

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

            if self._requests or \
               (timeout is not None and timeout <= 0.0):
                return

            self._requestCondition.wait(timeout)

    def _disconnect(self):
        """Disconnect from the flight simulator."""
        print("xplane.Handler._disconnect")
        if self._connected:
            try:
                self._xplane.disconnect()
            except:
                pass

            self._connected = False

    def _processRequest(self, request, time, attempts):
        """Process the given request.

        If an exception occurs or invalid data is read too many times, we try
        to reconnect.

        This function returns only if the request has succeeded, or if a
        connection is no longer requested.

        This function is called with the request lock held, but is relased
        whole processing the request and reconnecting."""
        self._requestCondition.release()

        #print "xplane.Handler._processRequest", request

        needReconnect = False
        try:
            self._watchdogClient.set()
            try:
                if not request.process(time):
                    print("xplane.Handler._processRequest: X-Plane returned invalid data too many times, reconnecting")
                    needReconnect = True
            except Exception as e:
                print("xplane.Handler._processRequest: X-Plane connection failed (" + \
                      util.utf2unicode(str(e)) + \
                      "), reconnecting (attempts=%d)." % (attempts,))
                needReconnect = True

            if needReconnect:
                with self._requestCondition:
                    self._requests.insert(0, request)
                self._disconnect()
                return self._connect(autoReconnection = True, attempts = attempts)
            else:
                return 0
        finally:
            self._watchdogClient.clear()
            self._requestCondition.acquire()

    def _processRequests(self):
        """Process any pending requests.

        Will be called with the request lock held."""
        attempts = 0
        while self._connectionRequested and self._periodicRequests:
            self._periodicRequests.sort()
            request = self._periodicRequests[0]

            t = time.time()

            if request.nextFire>t:
                break

            attempts = self._processRequest(request, t, attempts)

        while self._connectionRequested and self._requests:
            request = self._requests[0]
            del self._requests[0]

            attempts = self._processRequest(request, None, attempts)

        return self._connectionRequested

#------------------------------------------------------------------------------

class Simulator(object):
    """The simulator class representing the interface to the flight simulator
    via XPLRA."""
    # The basic data that should be queried all the time once we are connected
    timeData = [ ("sim/time/local_date_days", TYPE_INT),
                 ("sim/time/zulu_time_sec", TYPE_FLOAT) ]

    normalData = timeData + \
                 [ ("sim/aircraft/view/acf_tailnum", TYPE_BYTE_ARRAY),
                   ("sim/aircraft/view/acf_author", TYPE_BYTE_ARRAY),
                   ("sim/aircraft/view/acf_descrip", TYPE_BYTE_ARRAY),
                   ("sim/aircraft/view/acf_notes", TYPE_BYTE_ARRAY),
                   ("sim/aircraft/view/acf_ICAO", TYPE_BYTE_ARRAY),
                   ("sim/aircraft/view/acf_livery_path", TYPE_BYTE_ARRAY) ]

    flareData1 = [ ("sim/time/zulu_time_sec", TYPE_FLOAT),
                   ("sim/flightmodel/position/y_agl", TYPE_FLOAT),
                   ("sim/flightmodel/position/vh_ind_fpm2", TYPE_FLOAT) ]

    flareStartData = [ ("sim/weather/wind_speed_kt[0]", TYPE_FLOAT),
                       ("sim/weather/wind_direction_degt[0]", TYPE_FLOAT),
                       ("sim/weather/visibility_reported_m", TYPE_FLOAT) ]

    flareData2 = [ ("sim/time/zulu_time_sec", TYPE_FLOAT),
                   ("sim/flightmodel/failures/onground_any", TYPE_INT),
                   ("sim/flightmodel/position/vh_ind_fpm2", TYPE_FLOAT),
                   ("sim/flightmodel/position/indicated_airspeed2",
                    TYPE_FLOAT),
                   ("sim/flightmodel/position/theta", TYPE_FLOAT),
                   ("sim/flightmodel/position/phi", TYPE_FLOAT),
                   ("sim/flightmodel/position/psi", TYPE_FLOAT) ]

    TIME_SYNC_INTERVAL = 3.0

    @staticmethod
    def _getHotkeyCode(hotkey):
        """Get the hotkey code for the given hot key."""
        code = ord(hotkey.key)
        if hotkey.shift: code |= HOTKEY_MODIFIER_SHIFT
        if hotkey.ctrl: code |= HOTKEY_MODIFIER_CONTROL
        return code

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
        self._fsType = None
        self._aircraft = None

        self._handler = Handler(self,
                                connectAttempts = connectAttempts,
                                connectInterval = connectInterval)
        self._connectionListener = connectionListener
        self._handler.start()

        self._syncTime = False
        self._nextSyncTime = -1

        self._timestampBase = None
        self._timestampDaysOffset = 0
        self._lastZuluSeconds = None

        self._normalRequestID = None

        self._monitoringRequested = False
        self._monitoring = False

        self._aircraftInfo = None
        self._aircraftModel = None

        self._flareRequestID = None
        self._flareRates = []
        self._flareStart = None
        self._flareStartFS = None

        self._hotkeyLock = threading.Lock()
        self._hotkeyCodes = None
        self._hotkeySetID = 0
        self._hotkeySetGeneration = 0
        self._hotkeyOffets = None
        self._hotkeyRequestID = None
        self._hotkeyCallback = None

        self._fuelCallback = None

    def connect(self, aircraft):
        """Initiate a connection to the simulator."""
        self._aircraft = aircraft
        self._aircraftInfo = None
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
        data = [ ("sim/aircraft/weight/acf_m_empty", TYPE_FLOAT),
                 ("sim/flightmodel/weight/m_fixed", TYPE_FLOAT) ]
        self._handler.requestRead(data, self._handleZFW, extra = callback)

    def requestWeights(self, callback):
        """Request the following weights: DOW, ZFW, payload.

        These values will be passed to the callback function in this order, as
        separate arguments."""
        data = [ ("sim/aircraft/weight/acf_m_empty", TYPE_FLOAT),
                 ("sim/flightmodel/weight/m_fixed", TYPE_FLOAT),
                 ("sim/flightmodel/weight/m_total", TYPE_FLOAT) ]
        self._handler.requestRead(data, self._handleWeights,
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

        At present it is assumed to be called from the handler thread, hence no
        protection."""
        #self._aircraft.logger.debug("startFlare")
        if self._flareRequestID is None:
            self._flareRates = []
            self._flareRequestID = \
              self._handler.requestPeriodicRead(0.1,
                                                Simulator.flareData1,
                                                self._handleFlare1)

    def cancelFlare(self):
        """Cancel monitoring the flare time.

        At present it is assumed to be called from the handler thread, hence no
        protection."""
        if self._flareRequestID is not None:
            self._handler.clearPeriodic(self._flareRequestID)
            self._flareRequestID = None

    def sendMessage(self, message, duration = 3,
                    _disconnect = False):
        """Send a message to the pilot via the simulator.

        duration is the number of seconds to keep the message displayed."""
        print("xplra.Simulator.sendMessage:", message)
        self._handler.requestShowMessage(message, duration,
                                         self._handleMessageSent,
                                         extra = _disconnect)

    def getFuel(self, callback):
        """Get the fuel information for the current model.

        The callback will be called with a list of triplets with the following
        items:
        - the fuel tank identifier
        - the current weight of the fuel in the tank (in kgs)
        - the current total capacity of the tank (in kgs)."""
        if self._aircraftModel is None:
            self._fuelCallback = callback
        else:
            self._aircraftModel.getFuel(self._handler, callback)

    def setFuelLevel(self, levels):
        """Set the fuel level to the given ones.

        levels is an array of two-tuples, where each tuple consists of the
        following:
        - the const.FUELTANK_XXX constant denoting the tank that must be set,
        - the requested level of the fuel as a floating-point value between 0.0
        and 1.0."""
        if self._aircraftModel is not None:
            self._aircraftModel.setFuelLevel(self._handler, levels)

    def enableTimeSync(self):
        """Enable the time synchronization."""
        self._nextSyncTime = -1
        self._syncTime = True

    def disableTimeSync(self):
        """Enable the time synchronization."""
        self._syncTime = False
        self._nextSyncTime = -1

    def listenHotkeys(self, hotkeys, callback):
        """Start listening to the given hotkeys.

        callback is function expecting two arguments:
        - the ID of the hotkey set as returned by this function,
        - the list of the indexes of the hotkeys that were pressed."""
        with self._hotkeyLock:
            assert self._hotkeyCodes is None

            self._hotkeyCodes = \
              [self._getHotkeyCode(hotkey) for hotkey in hotkeys]
            self._hotkeySetID += 1
            self._hotkeySetGeneration = 0
            self._hotkeyCallback = callback

            self._handler.registerHotkeys(self._hotkeyCodes,
                                          self._handleHotkeysRegistered,
                                          (self._hotkeySetID,
                                           self._hotkeySetGeneration))

            return self._hotkeySetID

    def clearHotkeys(self):
        """Clear the current hotkey set.

        Note that it is possible, that the callback function set either
        previously or after calling this function by listenHotkeys() will be
        called with data from the previous hotkey set.

        Therefore it is recommended to store the hotkey set ID somewhere and
        check that in the callback function. Right before calling
        clearHotkeys(), this stored ID should be cleared so that the check
        fails for sure."""
        with self._hotkeyLock:
            if self._hotkeyCodes is not None:
                self._hotkeyCodes = None
                self._hotkeySetID += 1
                self._hotkeyCallback = None
                self._clearHotkeyRequest()

    def disconnect(self, closingMessage = None, duration = 3):
        """Disconnect from the simulator."""
        assert not self._monitoringRequested

        print("xplra.Simulator.disconnect", closingMessage, duration)

        self._stopNormal()
        self.clearHotkeys()
        if closingMessage is None:
            self._handler.disconnect()
        else:
            self.sendMessage(closingMessage, duration = duration,
                             _disconnect = True)

    def connected(self, fsType, descriptor):
        """Called when a connection has been established to the flight
        simulator of the given type."""
        self._fsType = fsType

        with self._hotkeyLock:
            if self._hotkeyCodes is not None:
                self._hotkeySetGeneration += 1

                self._handler.registerHotkeys(self._hotkeyCodes,
                                              self._handleHotkeysRegistered,
                                              (self._hotkeySetID,
                                               self._hotkeySetGeneration))

        self._connectionListener.connected(fsType, descriptor)

    def connectionFailed(self):
        """Called when the connection could not be established."""
        with self._hotkeyLock:
            self._clearHotkeyRequest()
        self._connectionListener.connectionFailed()

    def disconnected(self):
        """Called when a connection to the flight simulator has been broken."""
        with self._hotkeyLock:
            self._clearHotkeyRequest()
        self._connectionListener.disconnected()

    def _getTimestamp(self, data):
        """Convert the given data into a timestamp."""
        if self._timestampBase is None:
            year = datetime.date.today().year
            self._timestampBase  = \
              calendar.timegm(time.struct_time([year, 1, 1, 0, 0, 0, -1, 1, 0]))
            self._timestampBase += data[0] * 24 * 3600
            self._timestampDaysOffset = 0
            self._lastZuluSeconds = None

        zuluSeconds = data[1]
        if self._lastZuluSeconds is not None and \
           zuluSeconds<self._lastZuluSeconds:
            diff = self._lastZuluSeconds - zuluSeconds
            print("xplane.Simulator._getTimestamp: Zulu seconds have gone backwards: %f -> %f, diff: %f" % \
                  (self._lastZuluSeconds, zuluSeconds, diff))
            if diff>23*60*60:
                self._timestampDaysOffset += 1
            else:
                zuluSeconds = self._lastZuluSeconds

        self._lastZuluSeconds = zuluSeconds

        timestamp = self._timestampBase
        timestamp += self._timestampDaysOffset * 24 * 3600
        timestamp += zuluSeconds

        return timestamp

    def _startDefaultNormal(self):
        """Start the default normal periodic request."""
        assert self._normalRequestID is None
        self._timestampBase = None
        self._normalRequestID = \
             self._handler.requestPeriodicRead(1.0,
                                               Simulator.normalData,
                                               self._handleNormal)

    def _stopNormal(self):
        """Stop the normal period request."""
        assert self._normalRequestID is not None
        self._handler.clearPeriodic(self._normalRequestID)
        self._normalRequestID = None
        self._monitoring = False

    def _handleNormal(self, data, extra):
        """Handle the reply to the normal request.

        At the beginning the result consists the data for normalData. When
        monitoring is started, it contains the result also for the
        aircraft-specific values.
        """
        timestamp = self._getTimestamp(data)

        createdNewModel = self._setAircraftName(timestamp,
                                                data.getString(2),
                                                data.getString(3),
                                                data.getString(4),
                                                data.getString(5),
                                                data.getString(6),
                                                data.getString(7))
        if self._fuelCallback is not None:
            self._aircraftModel.getFuel(self._handler, self._fuelCallback)
            self._fuelCallback = None

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

    def _setAircraftName(self, timestamp, tailnum, author, description,
                         notes, icao, liveryPath):
        """Set the name of the aicraft and if it is different from the
        previous, create a new model for it.

        If so, also notifty the aircraft about the change.

        Return if a new model was created."""
        aircraftInfo = (tailnum, author, description, notes, icao, liveryPath)
        if aircraftInfo==self._aircraftInfo:
            return False

        print("xplane.Simulator: new data: %s, %s, %s, %s, %s, %s" % \
              (tailnum, author, description, notes, icao, liveryPath))

        self._aircraftInfo = aircraftInfo
        needNew = self._aircraftModel is None
        needNew = needNew or\
            not self._aircraftModel.doesHandle(self._aircraft, aircraftInfo)
        if not needNew:
            specialModel = AircraftModel.findSpecial(self._aircraft,
                                                     aircraftInfo)
            needNew = specialModel is not None and \
                specialModel is not self._aircraftModel.__class__

        if needNew:
            self._setAircraftModel(AircraftModel.create(self._aircraft,
                                                        aircraftInfo))

        self._aircraft.modelChanged(timestamp, description,
                                    self._aircraftModel.name)

        return needNew

    def _setAircraftModel(self, model):
        """Set a new aircraft model.

        It will be queried for the data to monitor and the monitoring request
        will be replaced by a new one."""
        self._aircraftModel = model
        model.simulator = self

        if self._monitoring:
            self._stopNormal()
            self._startMonitoring()

    def _startMonitoring(self):
        """Start monitoring with the current aircraft model."""
        data = Simulator.normalData[:]
        self._aircraftModel.addMonitoringData(data, self._fsType)

        self._normalRequestID = \
            self._handler.requestPeriodicRead(1.0, data,
                                              self._handleNormal)
        self._monitoring = True

    def _addFlareRate(self, data):
        """Append a flare rate to the list of last rates."""
        if len(self._flareRates)>=3:
            del self._flareRates[0]
        self._flareRates.append(data)

    def _handleFlare1(self, data, normal):
        """Handle the first stage of flare monitoring."""
        #self._aircraft.logger.debug("handleFlare1: " + str(data))
        if data[1]<=50.0*0.3048:
            self._flareStart = time.time()
            self._flareStartFS = data[0]
            self._handler.clearPeriodic(self._flareRequestID)
            self._handler.requestRead(Simulator.flareStartData,
                                      self._handleFlareStart)

        self._addFlareRate(data[2])

    def _handleFlareStart(self, data, extra):
        """Handle the data need to notify the aircraft about the starting of
        the flare."""
        #self._aircraft.logger.debug("handleFlareStart: " + str(data))
        if data is not None:
            windDirection = data[1]
            if windDirection<0.0: windDirection += 360.0
            self._aircraft.flareStarted(data[0], windDirection, data[2],
                                        self._flareStart, self._flareStartFS)

        self._flareRequestID = \
          self._handler.requestPeriodicRead(0.1,
                                            Simulator.flareData2,
                                            self._handleFlare2)

    def _handleFlare2(self, data, normal):
        """Handle the first stage of flare monitoring."""
        #self._aircraft.logger.debug("handleFlare2: " + str(data))
        if data[1]!=0:
            flareEnd = time.time()
            self._handler.clearPeriodic(self._flareRequestID)
            self._flareRequestID = None

            flareEndFS = data[0]
            if flareEndFS<self._flareStartFS:
                flareEndFS += 86400.0

            tdRate = min(self._flareRates)
            tdRateCalculatedByFS = False

            heading = data[6]
            if heading<0.0: heading += 360.0

            self._aircraft.flareFinished(flareEnd, flareEndFS,
                                         tdRate, tdRateCalculatedByFS,
                                         data[3], data[4], data[5], heading)
        else:
            self._addFlareRate(data[2])

    def _handleZFW(self, data, callback):
        """Callback for a ZFW retrieval request."""
        zfw = data[0] + data[1]
        callback(zfw)

    def _handleTime(self, data, callback):
        """Callback for a time retrieval request."""
        callback(self._getTimestamp(data))

    def _handleWeights(self, data, callback):
        """Callback for the weights retrieval request."""
        dow = data[0]
        payload = data[1]
        zfw = dow + payload
        grossWeight = data[2]
        callback(dow, payload, zfw, grossWeight)

    def _handleMessageSent(self, success, disconnect):
        """Callback for a message sending request."""
        #print "xplra.Simulator._handleMessageSent", disconnect
        if disconnect:
            self._handler.disconnect()

    def _handleHotkeysRegistered(self, success, hotkeySet):
        """Handle the result of the hotkeys having been written."""
        (id, generation) = hotkeySet
        with self._hotkeyLock:
            if success and id==self._hotkeySetID and \
            generation==self._hotkeySetGeneration:
                self._hotkeyRequestID = \
                  self._handler.requestHotkeysState(0.5,
                                                    self._handleHotkeys,
                                                    hotkeySet)

    def _handleHotkeys(self, data, hotkeySet):
        """Handle the hotkeys."""
        (id, generation) = hotkeySet
        with self._hotkeyLock:
            if id!=self._hotkeySetID or generation!=self._hotkeySetGeneration:
                return

            callback = self._hotkeyCallback
            offsets = self._hotkeyOffets

        hotkeysPressed = []
        for i in range(0, len(data)):
            if data[i]:
                hotkeysPressed.append(i)

        if hotkeysPressed:
            callback(id, hotkeysPressed)

    def _clearHotkeyRequest(self):
        """Clear the hotkey request in the handler if there is any."""
        if self._hotkeyRequestID is not None:
            self._handler.unregisterHotkeys(self._hotkeysUnregistered)
            self._handler.clearPeriodic(self._hotkeyRequestID)
            self._hotkeyRequestID = None

    def _hotkeysUnregistered(self, result, extra):
        """Called when the hotkeys have been unregistered."""
        pass

#------------------------------------------------------------------------------

class AircraftModel(object):
    """Base class for the aircraft models.

    Aircraft models handle the data arriving from X-Plane and turn it into an
    object describing the aircraft's state."""
    monitoringData = [ ("paused",
                        "sim/time/paused", TYPE_INT),
                       ("latitude",
                        "sim/flightmodel/position/latitude", TYPE_DOUBLE),
                       ("longitude",
                        "sim/flightmodel/position/longitude", TYPE_DOUBLE),
                       ("replay",
                        "sim/operation/prefs/replay_mode", TYPE_INT),
                       ("overspeed",
                        "sim/flightmodel/failures/over_vne", TYPE_INT),
                       ("stalled",
                        "sim/flightmodel/failures/stallwarning", TYPE_INT),
                       ("onTheGround",
                        "sim/flightmodel/failures/onground_any", TYPE_INT),
                       ("emptyWeight",
                        "sim/aircraft/weight/acf_m_empty", TYPE_FLOAT),
                       ("payloadWeight",
                        "sim/flightmodel/weight/m_fixed", TYPE_FLOAT),
                       ("grossWeight",
                        "sim/flightmodel/weight/m_total", TYPE_FLOAT),
                       ("heading",
                        "sim/flightmodel/position/psi", TYPE_FLOAT),
                       ("pitch",
                        "sim/flightmodel/position/theta", TYPE_FLOAT),
                       ("bank",
                        "sim/flightmodel/position/phi", TYPE_FLOAT),
                       ("ias",
                        "sim/flightmodel/position/indicated_airspeed2",
                        TYPE_FLOAT),
                       ("mach",
                        "sim/flightmodel/misc/machno", TYPE_FLOAT),
                       ("groundSpeed",
                        "sim/flightmodel/position/groundspeed", TYPE_FLOAT),
                       ("vs",
                        "sim/flightmodel/position/vh_ind_fpm2", TYPE_FLOAT),
                       ("radioAltitude",
                        "sim/flightmodel/position/y_agl", TYPE_FLOAT),
                       ("altitude",
                        "sim/flightmodel/position/elevation", TYPE_FLOAT),
                       ("gLoad",
                        "sim/flightmodel/forces/g_nrml", TYPE_FLOAT),
                       ("flapsControl",
                        "sim/flightmodel/controls/flaprqst", TYPE_FLOAT),
                       ("flapsLeft",
                        "sim/flightmodel/controls/flaprat", TYPE_FLOAT),
                       ("flapsRight",
                        "sim/flightmodel/controls/flap2rat", TYPE_FLOAT),
                       ("navLights",
                        "sim/cockpit/electrical/nav_lights_on", TYPE_INT),
                       ("beaconLights",
                        "sim/cockpit/electrical/beacon_lights_on", TYPE_INT),
                       ("strobeLights",
                        "sim/cockpit/electrical/strobe_lights_on", TYPE_INT),
                       ("landingLights",
                        "sim/cockpit/electrical/landing_lights_on", TYPE_INT),
                       ("pitot",
                        "sim/cockpit/switches/pitot_heat_on", TYPE_INT),
                       ("parking",
                        "sim/flightmodel/controls/parkbrake", TYPE_FLOAT),
                       ("gearControl",
                        "sim/cockpit2/controls/gear_handle_down", TYPE_INT),
                       ("noseGear",
                        "sim/flightmodel2/gear/deploy_ratio",
                        (TYPE_FLOAT_ARRAY, 1)),
                       ("spoilers",
                        "sim/flightmodel/controls/lsplrdef", TYPE_FLOAT),
                       ("altimeter",
                        "sim/cockpit/misc/barometer_setting", TYPE_FLOAT),
                       ("qnh",
                        "sim/physics/earth_pressure_p", TYPE_FLOAT),
                       ("nav1",
                        "sim/cockpit/radios/nav1_freq_hz", TYPE_INT),
                       ("nav1_obs",
                        "sim/cockpit/radios/nav1_obs_degm", TYPE_FLOAT),
                       ("nav2",
                        "sim/cockpit/radios/nav2_freq_hz", TYPE_INT),
                       ("nav2_obs",
                        "sim/cockpit/radios/nav2_obs_degm", TYPE_FLOAT),
                       ("adf1",
                        "sim/cockpit/radios/adf1_freq_hz", TYPE_INT),
                       ("adf2",
                        "sim/cockpit/radios/adf2_freq_hz", TYPE_INT),
                       ("squawk",
                        "sim/cockpit/radios/transponder_code", TYPE_INT),
                       ("windSpeed",
                        "sim/weather/wind_speed_kt[0]", TYPE_FLOAT),
                       ("windDirection",
                        "sim/weather/wind_direction_degt[0]", TYPE_FLOAT),
                       ("visibility",
                        "sim/weather/visibility_reported_m", TYPE_FLOAT),
                       ("cog",
                        "sim/flightmodel/misc/cgz_ref_to_default", TYPE_FLOAT),
                       ("xpdrC",
                        "sim/cockpit/radios/transponder_mode", TYPE_INT),
                       ("apMaster",
                        "sim/cockpit/autopilot/autopilot_mode", TYPE_INT),
                       ("apState",
                        "sim/cockpit/autopilot/autopilot_state", TYPE_INT),
                       ("apHeading",
                        "sim/cockpit/autopilot/heading_mag", TYPE_FLOAT),
                       ("apAltitude",
                        "sim/cockpit/autopilot/altitude", TYPE_FLOAT),
                       ("elevatorTrim",
                        "sim/flightmodel/controls/elv_trim", TYPE_FLOAT),
                       ("antiIceOn",
                        "sim/cockpit/switches/anti_ice_on", TYPE_INT),
                       ("surfaceHeat",
                        "sim/cockpit/switches/anti_ice_surf_heat", TYPE_INT),
                       ("propHeat",
                        "sim/cockpit/switches/anti_ice_prop_heat", TYPE_INT),
                       ("autopilotOn",
                        "sim/cockpit2/autopilot/autopilot_on", TYPE_INT),
                       ("apHeadingMode",
                        "sim/cockpit2/autopilot/heading_mode", TYPE_INT)]


    specialModels = []

    @staticmethod
    def registerSpecial(clazz):
        """Register the given class as a special model."""
        AircraftModel.specialModels.append(clazz)

    @staticmethod
    def findSpecial(aircraft, aircraftInfo):
        for specialModel in AircraftModel.specialModels:
            if specialModel.doesHandle(aircraft, aircraftInfo):
                return specialModel
        return None

    @staticmethod
    def create(aircraft, aircraftInfo):
        """Create the model for the given aircraft name, and notify the
        aircraft about it."""
        specialModel = AircraftModel.findSpecial(aircraft, aircraftInfo)
        if specialModel is not None:
            return specialModel()
        if aircraft.type in _genericModels:
            return _genericModels[aircraft.type]()
        else:
            return GenericModel()

    @staticmethod
    def _convertFrequency(value):
        """Convert the given frequency value into a string."""
        return "%.2f" % (value/100.0,)

    @staticmethod
    def _convertOBS(value):
        """Convert the given OBS value into an integer."""
        while value<0.0:
            value += 360.0
        return int(round(value))

    def __init__(self, flapsNotches):
        """Construct the aircraft model.

        flapsNotches is a list of degrees of flaps that are available on the aircraft."""
        self._flapsNotches = flapsNotches
        self._simulator = None

    @property
    def name(self):
        """Get the name for this aircraft model."""
        return "X-Plane/Generic"

    @property
    def simulator(self):
        """Get the simulator this aircraft model works for."""
        return self._simulator

    @simulator.setter
    def simulator(self, simulator):
        """Get the simulator this aircraft model works for."""
        self._simulator = simulator

    def doesHandle(self, aircraft, aircraftInfo):
        """Determine if the model handles the given aircraft name.

        This default implementation returns False."""
        return False

    def _addDatarefWithIndexMember(self, dest, name, type, attrName = None):
        """Add the given X-Plane dataref name and type to the given array and a
        member attribute with the given name."""
        dest.append((name, type))
        if attrName is not None:
            setattr(self, attrName, len(dest)-1)

    def _addDataWithIndexMembers(self, dest, prefix, data):
        """Add X-Plane dataref data to the given array and also corresponding
        index member variables with the given prefix.

        data is a list of triplets of the following items:
        - the name of the data item. The index member variable will have a name
        created by prepending the given prefix to this name.
        - the X-Plane dataref name
        - the dataref type

        The latter two items will be appended to dest."""
        for (name, datarefName, type) in data:
            self._addDatarefWithIndexMember(dest, datarefName, type,
                                            prefix + name)

    def addMonitoringData(self, data, fsType):
        """Add the model-specific monitoring data to the given array."""
        self._addDataWithIndexMembers(data, "_monidx_",
                                      AircraftModel.monitoringData)

    def getAircraftState(self, aircraft, timestamp, data):
        """Get an aircraft state object for the given monitoring data."""
        state = fs.AircraftState()

        lnavOn = data[self._monidx_autopilotOn]!=0 and \
                 data[self._monidx_apHeadingMode]==2

        state.timestamp = timestamp

        state.latitude = data[self._monidx_latitude]
        state.longitude = data[self._monidx_longitude]
        if state.longitude>180.0: state.longitude = 360.0 - state.longitude

        state.paused = data[self._monidx_paused]!=0 or \
            data[self._monidx_replay]!=0
        state.trickMode = data[self._monidx_replay]!=0

        state.overspeed = data[self._monidx_overspeed]!=0
        state.stalled = data[self._monidx_stalled]!=0
        state.onTheGround = data[self._monidx_onTheGround]!=0

        state.zfw = data[self._monidx_emptyWeight] + \
                    data[self._monidx_payloadWeight]
        state.grossWeight = data[self._monidx_grossWeight]

        state.heading = data[self._monidx_heading]

        state.pitch = -1.0 * data[self._monidx_pitch]
        state.bank = data[self._monidx_bank]

        state.ias = data[self._monidx_ias]
        state.mach = data[self._monidx_mach]
        state.groundSpeed = data[self._monidx_groundSpeed] * _mps2knots
        state.vs = data[self._monidx_vs]

        state.radioAltitude = data[self._monidx_radioAltitude]/.3048
        state.altitude = data[self._monidx_altitude]/.3048

        state.gLoad = data[self._monidx_gLoad]

        flapsControl = data[self._monidx_flapsControl]
        flapsIndex = int(round(flapsControl * (len(self._flapsNotches)-1)))
        state.flapsSet = 0 if flapsIndex<1 else self._flapsNotches[flapsIndex]

        state.flaps = self._flapsNotches[-1]*data[self._monidx_flapsLeft]

        state.navLightsOn = data[self._monidx_navLights] != 0
        state.antiCollisionLightsOn = data[self._monidx_beaconLights] != 0
        state.landingLightsOn = data[self._monidx_landingLights] != 0
        state.strobeLightsOn = data[self._monidx_strobeLights] != 0

        state.pitotHeatOn = data[self._monidx_pitot]!=0

        state.parking = data[self._monidx_parking]>=0.5

        state.gearControlDown = data[self._monidx_gearControl]!=0
        state.gearsDown = data[self._monidx_noseGear][0]>0.99

        state.spoilersArmed = None

        state.spoilersExtension = data[self._monidx_spoilers]*100.0

        state.altimeter = data[self._monidx_altimeter]* _hgin2hpa
        state.altimeterReliable = True
        state.qnh = data[self._monidx_qnh]/100.0

        state.ils = None
        state.ils_obs = None
        state.ils_manual = False
        state.nav1 = self._convertFrequency(data[self._monidx_nav1])
        state.nav1_obs = self._convertOBS(data[self._monidx_nav1_obs])
        state.nav1_manual = True
        state.nav2 = self._convertFrequency(data[self._monidx_nav2])
        state.nav2_obs = self._convertOBS(data[self._monidx_nav2_obs])
        state.nav2_manual = not lnavOn
        state.adf1 = str(data[self._monidx_adf1])
        state.adf2 = str(data[self._monidx_adf2])

        state.squawk = "%04d" % (data[self._monidx_squawk],)

        state.windSpeed = data[self._monidx_windSpeed]
        state.windDirection = data[self._monidx_windDirection]
        if state.windDirection<0.0: state.windDirection += 360.0

        state.visibility = data[self._monidx_visibility]

        state.cog = data[self._monidx_cog]

        state.xpdrC = data[self._monidx_xpdrC]==2
        state.autoXPDR = False

        state.apMaster = data[self._monidx_apMaster]==2
        apState = data[self._monidx_apState]
        if lnavOn:
           state.apHeadingHold = None
           state.apHeading = None
        else:
            state.apHeadingHold = (apState&0x00002)!=0
            state.apHeading = data[self._monidx_apHeading]

        state.apAltitudeHold = (apState&0x04000)!=0
        state.apAltitude = data[self._monidx_apAltitude]

        state.elevatorTrim = data[self._monidx_elevatorTrim] * 180.0 / math.pi

        state.antiIceOn = data[self._monidx_antiIceOn]!=0 or \
                          data[self._monidx_surfaceHeat]!=0 or \
                          data[self._monidx_propHeat]!=0

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
        self._fuelTankCapacities = [1.0] * len(fuelTanks)
        self._fuelIndex = None
        self._numEngines = numEngines
        self._engineStartIndex = None
        self._isN1 = isN1

    def doesHandle(self, aircraft, aircraftInfo):
        """Determine if the model handles the given aircraft name.

        This implementation returns True."""
        return True

    def addMonitoringData(self, data, fsType):
        """Add the model-specific monitoring data to the given array."""
        super(GenericAircraftModel, self).addMonitoringData(data, fsType)

        self._fuelIndex = self._addFuelData(data)

        self._engineStartIndex = len(data)
        if self._isN1:
            self._addDatarefWithIndexMember(data,
                                             "sim/flightmodel/engine/ENGN_N1_",
                                             (TYPE_FLOAT_ARRAY,
                                              self._numEngines))
        else:
            self._addDatarefWithIndexMember(data,
                                            "sim/flightmodel/engine/POINT_tacrad",
                                            (TYPE_FLOAT_ARRAY,
                                             self._numEngines))

        self._addDatarefWithIndexMember(data,
                                        "sim/flightmodel/engine/ENGN_propmode",
                                        (TYPE_INT_ARRAY, self._numEngines))

    def getAircraftState(self, aircraft, timestamp, data):
        """Get the aircraft state.

        Get it from the parent, and then add the data about the fuel levels and
        the engine parameters."""
        state = super(GenericAircraftModel, self).getAircraftState(aircraft,
                                                                   timestamp,
                                                                   data)

        state.fuel = []
        state.totalFuel = 0.0

        fuelAmounts = data[self._fuelIndex]
        for i in range(0, len(self._fuelTanks)):
            amount = fuelAmounts[i]
            state.fuel.append((self._fuelTanks[i], amount))
            state.totalFuel += amount

        power = data[self._engineStartIndex]

        state.n1 = power[:] if self._isN1 else None
        state.rpm = None if self._isN1 else power[:]

        propMode = data[self._engineStartIndex+1]
        state.reverser = [mode == 3 for mode in propMode]

        return state

    def getFuel(self, handler, callback):
        """Get the fuel information for this model.

        See Simulator.getFuel for more information. This
        implementation simply queries the fuel tanks given to the
        constructor."""
        data = []
        self._addFuelData(data)
        data.append( ("sim/aircraft/weight/acf_m_fuel_tot", TYPE_FLOAT) )
        data.append( ("sim/aircraft/overflow/acf_tank_rat",
                      (TYPE_FLOAT_ARRAY, len(self._fuelTanks)) ) )

        handler.requestRead(data, self._handleFuelRetrieved,
                            extra = callback)

    def setFuelLevel(self, handler, levels):
        """Set the fuel level.

        See the description of Simulator.setFuelLevel. This
        implementation simply sets the fuel tanks as given."""
        data = []
        for (tank, level) in levels:
            try:
                index = self._fuelTanks.index(tank)
                data.append( ("sim/flightmodel/weight/m_fuel",
                              (TYPE_FLOAT_ARRAY, 1, index),
                              [level * self._fuelTankCapacities[index]]) )
            except:
                print("xplane.Simulator.setFuelLevel: invalid tank constant: %d" % \
                  (tank,))

        handler.requestWrite(data, self._handleFuelWritten)

    def _addFuelData(self, data):
        """Add the fuel offsets to the given data array.

        Returns the index of the first fuel tank's data."""
        fuelStartIndex = len(data)
        data.append( ("sim/flightmodel/weight/m_fuel",
                      (TYPE_FLOAT_ARRAY, len(self._fuelTanks) ) ) )

        return fuelStartIndex

    def _convertFuelData(self, data, index = 0, addCapacities = False):
        """Convert the given data into a fuel info list.

        The list consists of two or three-tuples of the following
        items:
        - the fuel tank ID,
        - the amount of the fuel in kg,
        - if addCapacities is True, the total capacity of the tank."""
        fuelWeight = data[index] / 256.0
        index += 1

        result = []
        totalFuel = 0
        for fuelTank in self._fuelTanks:
            capacity = data[index+1] * fuelWeight * const.LBSTOKG
            if capacity>=1.0:
                amount = data[index] * capacity / 128.0 / 65536.0

                result.append( (fuelTank, amount, capacity) if addCapacities
                               else (fuelTank, amount))
                totalFuel += amount
            index += 2

        return (result, totalFuel)

    def _handleFuelRetrieved(self, data, callback):
        """Callback for a fuel retrieval request."""
        result = []
        totalCapacity = data[1]
        for index in range(0, len(self._fuelTanks)):
            amount = data[0][index]
            capacity = data[2][index] * totalCapacity
            self._fuelTankCapacities[index] = capacity
            result.append( (self._fuelTanks[index], amount, capacity) )

        callback(result)

    def _handleFuelWritten(self, success, extra):
        """Callback for a fuel setting request."""
        pass

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
        return "X-Plane/Generic"

#------------------------------------------------------------------------------

class B737Model(GenericAircraftModel):
    """Generic model for the Boeing 737 Classing and NG aircraft."""
    fuelTanks = [const.FUELTANK_LEFT, const.FUELTANK_CENTRE, const.FUELTANK_RIGHT]

    def __init__(self):
        """Construct the model."""
        super(B737Model, self). \
            __init__(flapsNotches = [0, 1, 2, 5, 10, 15, 25, 30, 40],
                     fuelTanks = B737Model.fuelTanks,
                     numEngines = 2)

    @property
    def name(self):
        """Get the name for this aircraft model."""
        return "X-Plane/Generic Boeing 737"

#------------------------------------------------------------------------------

class ZiboB737NGModel(B737Model):
    """Base model for the Zibo and LevelUp Boeing 737 models."""
    def __init__(self, flapsRatios = [0.0, 0.081633, 0.142857, 0.224490,
                                      0.285714, 0.367347, 0.551020, 0.714286,
                                      1.0]):
        super(ZiboB737NGModel, self).__init__()
        self._flapsRatios = flapsRatios

    def addMonitoringData(self, data, fsType):
        """Add the model-specific monitoring data to the given array."""
        super(ZiboB737NGModel, self).addMonitoringData(data, fsType)

        self._speedBrakeIndex = len(data)
        self._addDatarefWithIndexMember(data,
                                        "sim/flightmodel2/wing/speedbrake1_deg",
                                        (TYPE_FLOAT_ARRAY, 2))
        self._addDatarefWithIndexMember(data,
                                        "sim/flightmodel2/wing/speedbrake2_deg",
                                        (TYPE_FLOAT_ARRAY, 2))
        self._cgIndex = len(data)
        self._addDatarefWithIndexMember(data,
                                        "laminar/B738/tab/cg_pos",
                                        TYPE_FLOAT)
        self._wingHeatIndex = len(data)
        self._addDatarefWithIndexMember(data,
                                        "laminar/B738/ice/wing_heat_pos",
                                        TYPE_FLOAT)
        self._eng1HeatIndex = len(data)
        self._addDatarefWithIndexMember(data,
                                        "laminar/B738/ice/eng1_heat_pos",
                                        TYPE_FLOAT)
        self._eng2HeatIndex = len(data)
        self._addDatarefWithIndexMember(data,
                                        "laminar/B738/ice/eng2_heat_pos",
                                        TYPE_FLOAT)
        self._spoilersArmedIndex = len(data)
        self._addDatarefWithIndexMember(data,
                                        "laminar/B738/annunciator/speedbrake_armed",
                                        TYPE_FLOAT)


    def getAircraftState(self, aircraft, timestamp, data):
        """Get the aircraft state."""
        state = super(ZiboB737NGModel, self).getAircraftState(aircraft,
                                                              timestamp,
                                                              data)
        state.cog = data[self._cgIndex]/100.0

        flapsRatios = self._flapsRatios
        flapsRatio = data[self._monidx_flapsLeft]
        index = len(flapsRatios)
        for i in range(1, len(flapsRatios)):
            if flapsRatio<flapsRatios[i]:
                index = i-1
                break
        if index<len(flapsRatios):
            flapsRatio0 = flapsRatios[index]
            flapsNotch0 = self._flapsNotches[index]
            state.flaps = flapsNotch0 + \
                (self._flapsNotches[index+1] - flapsNotch0) * \
                (flapsRatio - flapsRatio0) / \
                (flapsRatios[index+1] - flapsRatio0)
        else:
            state.flaps = self._flapsNotches[-1]

        # 0 -> -1
        # 15 -> 0.790881
        state.elevatorTrim = \
            15.0 * (data[self._monidx_elevatorTrim] + 1) / 1.790881

        state.spoilersExtension = \
            sum(data[self._speedBrakeIndex] + data[self._speedBrakeIndex+1])/4

        state.antiIceOn = data[self._wingHeatIndex]!=0 or \
                          data[self._eng1HeatIndex]!=0 or \
                          data[self._eng2HeatIndex]!=0

        state.spoilersArmed = data[self._spoilersArmedIndex]!=0

        return state

#------------------------------------------------------------------------------

class ZiboB738Model(ZiboB737NGModel):
    """Model for the Zibo Boeing 737-800 model."""
    @staticmethod
    def doesHandle(aircraft, data):
        """Determine if this model handler handles the aircraft with the given
        name."""
        (tailnum, author, description, notes, icao, liveryPath) = data
        return author=="Alex Unruh" and \
            description=="Boeing 737-800X" and \
            notes.startswith("ZIBOmod") and \
            icao=="B738"

    def __init__(self):
        """Construct the model."""
        super(ZiboB738Model, self).__init__(
            flapsRatios = [0.0, 0.081633, 0.142857, 0.224490, 0.285714, 0.346939,
                           0.551020, 0.673469, 1.0])

    @property
    def name(self):
        """Get the name for this aircraft model."""
        return "Zibo Boeing 737-800"

#------------------------------------------------------------------------------

class LevelUpB736Model(ZiboB737NGModel):
    """Model for the LevelUp Boeing 737-600 model."""

    @staticmethod
    def doesHandle(aircraft, data):
        """Determine if this model handler handles the aircraft with the given
        name."""
        (tailnum, author, description, notes, icao, liveryPath) = data
        return author=="Alex Unruh" and \
            description=="Boeing 737-600NG" and \
            icao=="B736"

    @property
    def name(self):
        """Get the name for this aircraft model."""
        return "LevelUp Boeing 737-600"

#------------------------------------------------------------------------------

class LevelUpB737Model(ZiboB737NGModel):
    """Model for the LevelUp Boeing 737-700 model."""

    @staticmethod
    def doesHandle(aircraft, data):
        """Determine if this model handler handles the aircraft with the given
        name."""
        (tailnum, author, description, notes, icao, liveryPath) = data
        return author=="Alex Unruh" and \
            description=="Boeing 737-700NG" and \
            icao=="B737"

    @property
    def name(self):
        """Get the name for this aircraft model."""
        return "LevelUp Boeing 737-700"

#------------------------------------------------------------------------------

class LevelUpB738Model(ZiboB737NGModel):
    """Model for the LevelUp Boeing 737-800 model."""

    @staticmethod
    def doesHandle(aircraft, data):
        """Determine if this model handler handles the aircraft with the given
        name."""
        (tailnum, author, description, notes, icao, liveryPath) = data
        return author=="Alex Unruh" and \
            description=="Boeing 737-800NG" and \
            icao=="B738"

    @property
    def name(self):
        """Get the name for this aircraft model."""
        return "LevelUp Boeing 737-800"

#------------------------------------------------------------------------------

class B767Model(GenericAircraftModel):
    """Generic model for the Boeing 767 aircraft."""
    fuelTanks = [const.FUELTANK_LEFT, const.FUELTANK_CENTRE, const.FUELTANK_RIGHT]

    def __init__(self):
        """Construct the model."""
        super(B767Model, self). \
            __init__(flapsNotches = [0, 1, 5, 15, 20, 25, 30],
                     fuelTanks = B767Model.fuelTanks,
                     numEngines = 2)

    @property
    def name(self):
        """Get the name for this aircraft model."""
        return "X-Plane/Generic Boeing 767"

#------------------------------------------------------------------------------

class DH8DModel(GenericAircraftModel):
    """Generic model for the Bombardier  Dash 8-Q400 aircraft."""
    fuelTanks = [const.FUELTANK_LEFT, const.FUELTANK_RIGHT]

    def __init__(self):
        """Construct the model."""
        super(DH8DModel, self). \
            __init__(flapsNotches = [0, 5, 10, 15, 35],
                     fuelTanks = DH8DModel.fuelTanks,
                     numEngines = 2)

    @property
    def name(self):
        """Get the name for this aircraft model."""
        return "X-Plane/Generic Bombardier Dash 8-Q400"

#------------------------------------------------------------------------------

class FJSDH8DModel(DH8DModel):
    """Model handler for the FlyJSim Dash 8-Q400."""
    @staticmethod
    def doesHandle(aircraft, data):
        """Determine if this model handler handles the aircraft with the given
        name."""
        (tailnum, author, description, notes, icao, liveryPath) = data
        return aircraft.type==const.AIRCRAFT_DH8D and \
          description.find("Dash 8 Q400")!=-1 and \
          ((author in ["2012", "2013"] and tailnum=="N62890") or \
           author.find("Jack Skieczius")!=-1)

    @property
    def name(self):
        """Get the name for this aircraft model."""
        return "X-Plane/FlyJSim Bombardier Dash 8-Q400"

    def addMonitoringData(self, data, fsType):
        """Add the model-specific monitoring data to the given array."""
        super(FJSDH8DModel, self).addMonitoringData(data, fsType)

        self._speedBrakeIndex = len(data)
        self._addDatarefWithIndexMember(data,
                                        "sim/flightmodel2/wing/speedbrake1_deg",
                                        (TYPE_FLOAT_ARRAY, 2))
        self._addDatarefWithIndexMember(data,
                                        "sim/flightmodel2/wing/speedbrake2_deg",
                                        (TYPE_FLOAT_ARRAY, 2))


    def getAircraftState(self, aircraft, timestamp, data):
        """Get the aircraft state.

        Get it from the parent, and then invert the pitot heat state."""
        state = super(FJSDH8DModel, self).getAircraftState(aircraft,
                                                           timestamp,
                                                           data)
        state.antiCollisionLightsOn = \
          state.antiCollisionLightsOn or state.strobeLightsOn
        state.cog = (state.cog / 0.0254 + 21.504) / 94.512

        # It seems that N1 does not always go down to 0 properly
        # (maybe due to winds?)
        state.n1 = [0 if n1<2.0 else n1 for n1 in state.n1]

        state.spoilersExtension = \
            sum(data[self._speedBrakeIndex] + data[self._speedBrakeIndex+1])/4

        return state

#------------------------------------------------------------------------------

class CRJ2Model(GenericAircraftModel):
    """Generic model for the Bombardier CRJ-200 aircraft."""
    fuelTanks = [const.FUELTANK_LEFT, const.FUELTANK_CENTRE, const.FUELTANK_RIGHT]

    def __init__(self):
        """Construct the model."""
        super(CRJ2Model, self). \
            __init__(flapsNotches = [0, 8, 20, 30, 45],
                     fuelTanks = CRJ2Model.fuelTanks,
                     numEngines = 2)

    @property
    def name(self):
        """Get the name for this aircraft model."""
        return "X-Plane/Generic Bombardier CRJ-200"

#------------------------------------------------------------------------------

class F70Model(GenericAircraftModel):
    """Generic model for the Fokker F70 aircraft."""
    fuelTanks = [const.FUELTANK_LEFT, const.FUELTANK_CENTRE, const.FUELTANK_RIGHT]

    def __init__(self):
        """Construct the model."""
        super(F70Model, self). \
            __init__(flapsNotches = [0, 8, 15, 25, 42],
                     fuelTanks = F70Model.fuelTanks,
                     numEngines = 2)

    @property
    def name(self):
        """Get the name for this aircraft model."""
        return "X-Plane/Generic Fokker 70"

#------------------------------------------------------------------------------

class DC3Model(GenericAircraftModel):
    """Generic model for the Lisunov Li-2 (DC-3) aircraft."""
    fuelTanks = [const.FUELTANK_LEFT, const.FUELTANK_CENTRE,
                 const.FUELTANK_RIGHT]
    # fuelTanks = [const.FUELTANK_LEFT_AUX, const.FUELTANK_LEFT,
    #              const.FUELTANK_RIGHT, const.FUELTANK_RIGHT_AUX]

    def __init__(self):
        """Construct the model."""
        super(DC3Model, self). \
            __init__(flapsNotches = [0, 15, 30, 45],
                     fuelTanks = DC3Model.fuelTanks,
                     numEngines = 2, isN1 = False)
        self._leftLevel = 0.0
        self._rightLevel = 0.0

    @property
    def name(self):
        """Get the name for this aircraft model."""
        return "X-Plane/Generic Lisunov Li-2 (DC-3)"

#------------------------------------------------------------------------------

class T134Model(GenericAircraftModel):
    """Generic model for the Tupolev Tu-134 aircraft."""
    fuelTanks = [const.FUELTANK_LEFT_TIP, const.FUELTANK_EXTERNAL1,
                 const.FUELTANK_LEFT_AUX,
                 const.FUELTANK_CENTRE,
                 const.FUELTANK_RIGHT_AUX,
                 const.FUELTANK_EXTERNAL2, const.FUELTANK_RIGHT_TIP]

    def __init__(self):
        """Construct the model."""
        super(T134Model, self). \
            __init__(flapsNotches = [0, 10, 20, 30],
                     fuelTanks = T134Model.fuelTanks,
                     numEngines = 2)

    @property
    def name(self):
        """Get the name for this aircraft model."""
        return "X-Plane/Generic Tupolev Tu-134"

#------------------------------------------------------------------------------

class T154Model(GenericAircraftModel):
    """Generic model for the Tupolev Tu-154 aircraft."""
    fuelTanks = [const.FUELTANK_CENTRE, const.FUELTANK_CENTRE2,
                 const.FUELTANK_RIGHT, const.FUELTANK_LEFT,
                 const.FUELTANK_RIGHT_AUX, const.FUELTANK_LEFT_AUX]

    def __init__(self):
        """Construct the model."""
        super(T154Model, self). \
            __init__(flapsNotches = [0, 15, 28, 45],
                     fuelTanks = T154Model.fuelTanks,
                     numEngines = 3)

    @property
    def name(self):
        """Get the name for this aircraft model."""
        return "X-Plane/Generic Tupolev Tu-154"

    def getAircraftState(self, aircraft, timestamp, data):
        """Get an aircraft state object for the given monitoring data.

        This removes the reverser value for the middle engine."""
        state = super(T154Model, self).getAircraftState(aircraft, timestamp, data)
        del state.reverser[1]
        return state

#------------------------------------------------------------------------------

class FelisT154Model(T154Model):
    """Model for Felis' Tupolev Tu-154-M aircraft."""
    @staticmethod
    def doesHandle(aircraft, data):
        """Determine if this model handler handles the aircraft with the given
        name."""
        (tailnum, author, description, notes, icao, liveryPath) = data
        return aircraft.type==const.AIRCRAFT_T154 and \
          author.find("Felis")!=-1 and \
          description.find("Tu154M")!=-1

    def __init__(self):
        """Construct the model."""
        super(T154Model, self). \
            __init__(flapsNotches = [0, 15, 28, 36, 45],
                     fuelTanks = T154Model.fuelTanks,
                     numEngines = 3)

    @property
    def name(self):
        """Get the name for this aircraft model."""
        return "X-Plane/Felis Tupolev Tu-154-M"

#------------------------------------------------------------------------------

class YK40Model(GenericAircraftModel):
    """Generic model for the Yakovlev Yak-40 aircraft."""
    fuelTanks = [const.FUELTANK_LEFT, const.FUELTANK_RIGHT]

    def __init__(self):
        """Construct the model."""
        super(YK40Model, self). \
            __init__(flapsNotches = [0, 20, 35],
                     fuelTanks = YK40Model.fuelTanks,
                     numEngines = 2)

    @property
    def name(self):
        """Get the name for this aircraft model."""
        return "X-Plane/Generic Yakovlev Yak-40"

#------------------------------------------------------------------------------

_genericModels = { const.AIRCRAFT_B736  : B737Model,
                   const.AIRCRAFT_B737  : B737Model,
                   const.AIRCRAFT_B738  : B737Model,
                   const.AIRCRAFT_B738C : B737Model,
                   const.AIRCRAFT_B732  : B737Model,
                   const.AIRCRAFT_B733  : B737Model,
                   const.AIRCRAFT_B734  : B737Model,
                   const.AIRCRAFT_B735  : B737Model,
                   const.AIRCRAFT_DH8D  : DH8DModel,
                   const.AIRCRAFT_B762  : B767Model,
                   const.AIRCRAFT_B763  : B767Model,
                   const.AIRCRAFT_CRJ2  : CRJ2Model,
                   const.AIRCRAFT_F70   : F70Model,
                   const.AIRCRAFT_DC3   : DC3Model,
                   const.AIRCRAFT_T134  : T134Model,
                   const.AIRCRAFT_T154  : T154Model,
                   const.AIRCRAFT_YK40  : YK40Model }

#------------------------------------------------------------------------------

AircraftModel.registerSpecial(ZiboB738Model)
AircraftModel.registerSpecial(LevelUpB736Model)
AircraftModel.registerSpecial(LevelUpB737Model)
AircraftModel.registerSpecial(LevelUpB738Model)
AircraftModel.registerSpecial(FJSDH8DModel)
AircraftModel.registerSpecial(FelisT154Model)

#------------------------------------------------------------------------------

# if __name__ == "__main__":
#     class ConnectionListener:
#         def connected(self, fsType, descriptor):
#             """Called when a connection has been established to the flight
#             simulator of the given type."""
#             print "fs.ConnectionListener.connected, fsType:", fsType, ", descriptor:", descriptor

#         def connectionFailed(self):
#             """Called when the connection could not be established."""
#             print "fs.ConnectionListener.connectionFailed"

#         def disconnected(self):
#             """Called when a connection to the flight simulator has been broken."""
#             print "fs.ConnectionListener.disconnected"

#     class Config:
#         def __init__(self):
#             self.onlineACARS = False
#             self.realIASSmoothingLength = 2
#             self.realVSSmoothingLength = 2
#             self.enableSounds = False
#             self.usingFS2Crew = False

#         def isMessageTypeFS(self, type):
#             return True



#     class GUI:
#         def __init__(self):
#             self.config = Config()
#             self.entranceExam = False
#             self.zfw = 30000.0

#         def resetFlightStatus(self):
#             pass

#         def setRating(self, value):
#             pass

#         def insertFlightLogLine(self, index, ts, text, isFault):
#             pass

#         def setStage(self, stage):
#             pass


#     from i18n import setLanguage

#     setLanguage("/home/vi/munka/repules/mlx", "en")

#     from logger import Logger
#     from flight import Flight
#     from acft import DH8D

#     gui = GUI()

#     logger = Logger(gui)

#     flight = Flight(logger, gui)
#     acft = DH8D(flight)

#     Watchdog()

#     connectionListener = ConnectionListener()
#     simulator = Simulator(connectionListener, connectAttempts = 3)

#     simulator.connect(acft)

#     time.sleep(2)

#     simulator.startMonitoring()

#     simulator.sendMessage("[MLX] Flight stage: Taxi", duration = 3)

#     time.sleep(4)

#     simulator.sendMessage("[MLX] Free gates: 1, 2, 3, 4, 5, 6, 25, 26, 27, 32, 33, 34, 35, 36, 37, 38, 39, 42, 43, 45, 107, 108, 109, R113, R114, R115, R116, R117, R210, R211, R212, R212A, R220, R221, R222, R223, R224, R225, R226, R227, R270, R271, R272, R274, R275, R276, R277, R278, R278A, R279", duration = 20)
#     #simulator.sendMessage("[MLX] Free gates: 1, 2, 3, 4, 5, 6, 25, 26, 27, 32, 33, 34, 35, 36, 37, 38, 39, 42, 43, 45, 107, 108, 109, R113, R114, R115, R116", duration = 20)
#     #simulator.sendMessage("[MLX] Free gates: 1, 2, 3, 4, 5, 6, 25, 26, 27, 32, 33, 34, 35, 36, 37, 38, 39, 42, 43, 45, 107, 108, 109, R113, R114, R115", duration = 20)

#     time.sleep(30)

#     simulator.sendMessage("[MLX] Hello", duration = 3)

#     time.sleep(10)
