# Module to handle sound playback

#------------------------------------------------------------------------------

import os

#------------------------------------------------------------------------------

if os.name=="nt":
    import time
    import threading
    from ctypes import windll, c_buffer

    class MCIException(Exception):
        """MCI exception."""
        def __init__(self, mci, command, errorCode):
            """Construct an MCI exception for the given error code."""
            message = "MCI error: %s: %s" % (command, mci.getErrorString(errorCode))
            super(MCIException, self).__init__(message)

    class MCI:
        """Interface for the Media Control Interface."""
        def __init__(self):
            """Construct the interface."""
            self.w32mci = windll.winmm.mciSendStringA
            self.w32mcierror = windll.winmm.mciGetErrorStringA

        def send(self, command):
            """Send the given command to the MCI."""
            buffer = c_buffer(255)
            errorCode = self.w32mci(str(command), buffer, 254, 0)
            if errorCode:
                raise MCIException(self, command, errorCode)
            else:
                return buffer.value

        def getErrorString(self, errorCode):
            """Get the string representation of the given error code."""
            buffer = c_buffer(255)
            self.w32mcierror(int(errorCode), buffer, 254)
            return buffer.value

    class SoundThread(threading.Thread):
        """The thread controlling the playback of sounds."""
        def __init__(self, soundsDirectory):
            threading.Thread.__init__(self)

            self._soundsDirectory = soundsDirectory
            self._mci = MCI()

            self._requestCondition = threading.Condition()
            self._requestedPaths = []
            self._pendingAliases = []
            self._count = 0

            self.daemon = True

        def requestSound(self, name):
            """Request the playback of the sound with the given name."""
            path = os.path.join(self._soundsDirectory, name)
            with self._requestCondition:
                self._requestedPaths.append(path)
                self._requestCondition.notify()

        def run(self):
            """Perform the operation of the thread.

            It waits for a request or a timeout. If a request is received, that
            is started to be played back. If a timeout occurs, the file is
            closed."""

            while True:
                with self._requestCondition:
                    if not self._requestedPaths:
                        if self._pendingAliases:
                            timeout = max(time.time() -
                                          self._pendingAliases[0][0], 0.0)
                        else:
                            timeout = 10.0
                            
                        self._requestCondition.wait(timeout)

                    requestedPaths = []
                    for path in self._requestedPaths:
                        requestedPaths.append((path, self._count))
                        self._count += 1
                    self._requestedPaths = []

                    now = time.time()
                    aliasesToClose = []
                    while self._pendingAliases and \
                          self._pendingAliases[0][0]<=now:
                        aliasesToClose.append(self._pendingAliases[0][1])
                        del self._pendingAliases[0]

                for alias in aliasesToClose:
                    try:
                        print "Closing", alias
                        self._mci.send("close " + alias)
                        print "Closed", alias
                    except Exception, e:
                        print "Failed closing " + alias + ":", str(e)

                for (path, counter) in requestedPaths:
                    try:
                        alias = "mlxsound%d" % (counter,)
                        print "Starting to play", path, "as", alias
                        self._mci.send("open \"%s\" alias %s" % \
                                       (path, alias))
                        self._mci.send("set %s time format milliseconds" % \
                                       (alias,))
                        lengthBuffer = self._mci.send("status %s length" % \
                                                      (alias,))
                        self._mci.send("play %s from 0 to %s" % \
                                       (alias, lengthBuffer))
                        length = int(lengthBuffer)
                        timeout = time.time() + length / 1000.0
                        with self._requestCondition:
                            self._pendingAliases.append((timeout, alias))
                            self._pendingAliases.sort()
                        print "Started to play", path
                    except Exception, e:
                        print "Failed to start playing " + path + ":", str(e)

    _thread = None

    def initializeSound(soundsDirectory):
        """Initialize the sound handling with the given directory containing
        the sound files."""
        global _thread
        _thread = SoundThread(soundsDirectory)
        _thread.start()

    def startSound(name):
        """Start playing back the given sound.
        
        name should be the name of a sound file relative to the sound directory
        given in initializeSound."""
        _thread.requestSound(name)
        
#------------------------------------------------------------------------------

else: # os.name!="nt"
    def initializeSound(soundsDirectory):
        """Initialize the sound handling with the given directory containing
        the sound files."""
        pass

    def startSound(name):
        """Start playing back the given sound.

        FIXME: it does not do anything currently, but it should."""
        pass

#------------------------------------------------------------------------------
#------------------------------------------------------------------------------

if __name__ == "__main__":
    initializeSound("e:\\home\\vi\\tmp")
    startSound("malev.mp3")
    time.sleep(5)
    startSound("ding.wav")
    time.sleep(5)
    startSound("ding.wav")
    time.sleep(5)
    startSound("ding.wav")
    time.sleep(50)

#------------------------------------------------------------------------------
