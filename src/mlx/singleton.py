# Module to allow for a single instance of an application to run

import os
import time

#----------------------------------------------------------------------------

if os.name=="nt":
    import win32event
    import win32file
    import win32pipe
    import win32api
    import winerror

    import threading

    class _PipeServer(threading.Thread):
        """A server that creates a named pipe, and waits for messages on
        that."""
        
        BUFFER_SIZE = 4096
        
        def __init__(self, pipeName, raiseCallback):
            """Construct the server thread."""
            super(_PipeServer, self).__init__()
            
            self._pipeName = pipeName
            self._raiseCallback = raiseCallback
            self.daemon = True

        def run(self):
            """Perform the operation of the thread."""
            try:
                while True:
                    handle = self._createPipe()

                    if handle is None:
                        break

                    print "singleton._PipeServer.run: created the pipe"
                    try:
                        if win32pipe.ConnectNamedPipe(handle)==0:
                            print "singleton._PipeServer.run: client connection received"
                            (code, message) = \
                                win32file.ReadFile(handle,
                                                   _PipeServer.BUFFER_SIZE,
                                                   None)

                            if code==0:
                                print "singleton._PipeServer.run: message received from client"
                                self._raiseCallback()
                            else:
                                print "singleton._PipeServer.run: failed to read from the pipe"
                    except Exception, e:
                        print "singleton._PipeServer.run: exception:", str(e)
                    finally:
                        win32pipe.DisconnectNamedPipe(handle)
                        win32file.CloseHandle(handle)
            except Exception, e:
                print "singleton._PipeServer.run: fatal exception:", str(e)
                            
        def _createPipe(self):
            """Create the pipe."""
            handle = win32pipe.CreateNamedPipe(self._pipeName,
                                               win32pipe.PIPE_ACCESS_INBOUND,
                                               win32pipe.PIPE_TYPE_BYTE |
                                               win32pipe.PIPE_READMODE_BYTE |
                                               win32pipe.PIPE_WAIT,
                                               win32pipe.PIPE_UNLIMITED_INSTANCES,
                                               _PipeServer.BUFFER_SIZE,
                                               _PipeServer.BUFFER_SIZE,
                                               1000,
                                               None)
            if handle==win32file.INVALID_HANDLE_VALUE:
                print "singleton._PipeServer.run: could not create the handle"
                return None
            else:
                return handle            

    class SingleInstance(object):
        """Creating an instance of this object checks if only one instance of
        the process runs."""
        def __init__(self, baseName, raiseCallback):
            """Construct the single instance object.

            raiseCallback is a function that will be called, if another
            instance of the program is started."""
            self._name = baseName + "_" + win32api.GetUserName()
            self._mutex = win32event.CreateMutex(None, False, self._name)
            self._isSingle = win32api.GetLastError() != \
                             winerror.ERROR_ALREADY_EXISTS
            if self._isSingle:
                self._startPipeServer(raiseCallback)
            else:
                self._notifySingleton()

        def close(self):
            """Close the instance by closing the mutex."""
            if self._mutex:
                win32api.CloseHandle(self._mutex)
                self._mutex = None

        def _getPipeName(self):
            """Get the name of the pipe to be used for communication."""
            return r'\\.\pipe\\' + self._name

        def _startPipeServer(self, raiseCallback):
            """Start the pipe server"""
            pipeServer = _PipeServer(self._getPipeName(),
                                     raiseCallback)
            pipeServer.start()

        def _notifySingleton(self):
            """Notify the already running instance of the program of our
            presence."""
            pipeName = self._getPipeName()
            for i in range(0, 3):
                try:
                    f = open(pipeName, "wb")
                    f.write("hello")
                    f.close()
                    return
                except Exception, e:
                    print "SingleInstance._notifySingleton: failed:", str(e)
                    time.sleep(0.5)
        
        def __nonzero__(self):
            """Return a boolean representation of the object.

            It is True, if this is the single instance of the program."""
            return self._isSingle            
                
        def __del__(self):
            """Destroy the object."""
            self.close()
                
#----------------------------------------------------------------------------

else:     # os.name=="nt"
    import fcntl
    import socket
    import tempfile
    import threading
    
    class _SocketServer(threading.Thread):
        """Server thread to handle the Unix socket through which we are
        notified of other instances starting."""
        def __init__(self, socketName, raiseCallback):
            """Construct the server."""
            super(_SocketServer, self).__init__()

            self._socketName = socketName
            self._raiseCallback = raiseCallback

            self.daemon = True
            

        def run(self):
            """Perform the thread's operation."""
            try:
                try:
                    os.remove(self._socketName)
                except:
                    pass
                
                s = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
                s.bind(self._socketName)

                while True:
                    s.recv(64)
                    self._raiseCallback()
            except Exception, e:
                print "singleton._SocketServer.run: fatal exception:", str(e)            
    
    class SingleInstance(object):
        """Creating an instance of this object checks if only one instance of
        the process runs."""
        def __init__(self, baseName, raiseCallback):
            """Construct the single instance object.

            raiseCallback is a function that will be called, if another
            instance of the program is started."""
            baseName = baseName + "_" + os.environ["LOGNAME"]

            tempDir = tempfile.gettempdir()
            self._lockName = os.path.join(tempDir, baseName + ".lock")
            self._socketName = os.path.join(tempDir, baseName + ".sock")
            
            self._lockFile = open(self._lockName, "w")

            self._isSingle = False
            try:
                fcntl.lockf(self._lockFile, fcntl.LOCK_EX | fcntl.LOCK_NB)
                self._isSingle = True
            except Exception, e:
                self._lockFile.close()
                self._lockFile = None
                pass

            if self._isSingle:
                self._startSocketServer(raiseCallback)
            else:
                self._notifySingleton()

        def close(self):
            """Close the instance by closing the mutex."""
            if self._isSingle:
                if self._lockFile:
                    self._lockFile.close()
                    self._lockFile = None
                    try:
                        os.remove(self._lockName)
                    except:
                        pass
                    try:
                        os.remove(self._socketName)
                    except:
                        pass
                

        def _startSocketServer(self, raiseCallback):
            """Start the pipe server"""
            pipeServer = _SocketServer(self._socketName, raiseCallback)
            pipeServer.start()

        def _notifySingleton(self):
            """Notify the already running instance of the program of our
            presence."""
            s = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            for i in range(0, 3):
                try:
                    s.connect(self._socketName)
                    s.send("hello")
                    s.close()
                    return
                except Exception, e:
                    print "singleton.SingleInstance._notifySingleton: failed:", str(e)
                    time.sleep(0.5)

        def __nonzero__(self):
            """Return a boolean representation of the object.

            It is True, if this is the single instance of the program."""
            return self._isSingle            

        def __del__(self):
            """Destroy the object."""
            self.close()
                
#----------------------------------------------------------------------------
#----------------------------------------------------------------------------

# MAVA Logger X-specific stuff

#----------------------------------------------------------------------------

# The callback to use
raiseCallback = None

#----------------------------------------------------------------------------

def raiseCallbackWrapper():
    """The actual function to be used as the callback.

    It checks if raiseCallback is None, and if not, it calls that."""
    callback = raiseCallback
    if callback is not None:
        callback()

#----------------------------------------------------------------------------
#----------------------------------------------------------------------------

if __name__=="__main__":
    def raiseCallback():
        print "Raise the window!"

    instance = SingleInstance("mlx", raiseCallback)
    if instance:
        print "The first instance"
        time.sleep(10)
    else:
        print "The program is already running."

