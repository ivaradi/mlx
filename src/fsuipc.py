# Module handling the connection to FSUIPC

import threading
import os
import fs
import time

if os.name == "nt":
    import pyuipc
else:
    import pyuipc_emu as pyuipc

class Handler(threading.Thread):
    """The thread to handle the FSUIPC requests."""
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
                self._callback(self._extra)
            else:
                values = pyuipc.read(self._data)
                self._callback(values, self._extra)            

            return True

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

            self._callback(values, self._extra)

            while self._nextFire <= time:
                self._nextFire += self._period
            
            return True

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
        - the values retrieved
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

        callback is a function that receives the extra data when writing was
        succesful. It will called in the handler's thread!
        """
        with self._requestCondition:
            self._requests.append(Handler.Request(True, data, callback, extra))
            self._requestCondition.notify()

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
                self._connectionListener.connected(fs.TYPE_FS2K4, description)
                return True
            except Exception, e:
                print "fsuipc.Handler._connect: connection failed: " + str(e)

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
        self._connectionListener.disconnected()

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
