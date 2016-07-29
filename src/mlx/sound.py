
from util import utf2unicode

import os
import traceback

#------------------------------------------------------------------------------

## @package mlx.sound
#
# Sound playback handling.
#
# This is the low level sound playback handling. The \ref initializeSound
# function should be called to initialize the sound handling with the directory
# containing the sound files. Then the \ref startSound function should be
# called to start the playback of a certain sound file. A callback may be
# called when the playback of a certain file has finished.
#
# See also the \ref mlx.soundsched module.

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
            self._requests = []
            self._pending = []
            self._count = 0

            self.daemon = True

        def requestSound(self, name, finishCallback = None, extra = None):
            """Request the playback of the sound with the given name."""
            path = name if os.path.isabs(name) \
                   else os.path.join(self._soundsDirectory, name)
            with self._requestCondition:
                self._requests.append((path, (finishCallback, extra)))
                self._requestCondition.notify()

        def run(self):
            """Perform the operation of the thread.

            It waits for a request or a timeout. If a request is received, that
            is started to be played back. If a timeout occurs, the file is
            closed."""

            while True:
                with self._requestCondition:
                    if not self._requests:
                        if self._pending:
                            timeout = max(self._pending[0][0] - time.time(),
                                          0.0)
                        else:
                            timeout = 10.0

                        #print "Waiting", timeout
                        self._requestCondition.wait(timeout)

                    requests = []
                    for (path, finishData) in self._requests:
                        requests.append((path, finishData, self._count))
                        self._count += 1
                    self._requests = []

                    now = time.time()
                    toClose = []
                    while self._pending and \
                          self._pending[0][0]<=now:
                        toClose.append(self._pending[0][1])
                        del self._pending[0]

                for (alias, (finishCallback, extra)) in toClose:
                    success = True
                    try:
                        print "Closing", alias
                        self._mci.send("close " + alias)
                        print "Closed", alias
                    except Exception, e:
                        print "Failed closing " + alias + ":",
                        print utf2unicode(str(e))
                        success = False

                    if finishCallback is not None:
                        try:
                            finishCallback(success, extra)
                        except:
                            traceback.print_exc()

                for (path, finishData, counter) in requests:
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
                            self._pending.append((timeout, (alias, finishData)))
                            self._pending.sort()
                        print "Started to play", path
                    except Exception, e:
                        print "Failed to start playing " + path + ":",
                        print utf2unicode(str(e))
                        (finishCallback, extra) = finishData
                        if finishCallback is not None:
                            try:
                                finishCallback(None, extra)
                            except:
                                traceback.print_exc()

    _thread = None

    def preInitializeSound():
        """Perform any-pre initialization.

        This does nothing on Windows."""

    def initializeSound(soundsDirectory):
        """Initialize the sound handling with the given directory containing
        the sound files."""
        global _thread
        _thread = SoundThread(soundsDirectory)
        _thread.start()

    def startSound(name, finishCallback = None, extra = None):
        """Start playing back the given sound.

        name should be the name of a sound file relative to the sound directory
        given in initializeSound."""
        _thread.requestSound(name, finishCallback = finishCallback,
                             extra = extra)

    def finalizeSound():
        """Finalize the sound handling."""
        pass

#------------------------------------------------------------------------------

else: # os.name!="nt"
    from multiprocessing import Process, Queue
    from threading import Thread, Lock

    COMMAND_STARTSOUND = 1
    COMMAND_QUIT = 2

    REPLY_FINISHED = 101
    REPLY_FAILED = 102
    REPLY_QUIT = 103

    _initialized = False
    _process = None
    _thread = None
    _inQueue = None
    _outQueue = None
    _nextReference = 1
    _ref2Data = {}
    _lock = Lock()

    def _processFn(inQueue, outQueue):
        """The function running in the helper process created.

        It tries to load the Gst module. If successful, True is sent back,
        otherwise False followed by the exception caught and the function
        quits.

        In case of successful initialization, the directory of the sound files
        is read, the command reader thread is created and the gobject main loop
        is executed."""
        try:
            import gi.repository
            gi.require_version("Gst", "1.0")
            from gi.repository import Gst
            from gi.repository import GObject as gobject

            Gst.init(None)
        except Exception, e:
            outQueue.put(False)
            outQueue.put(e)
            return

        outQueue.put(True)

        soundsDirectory = inQueue.get()

        _bins = set()

        mainLoop = None

        def _handlePlayBinMessage(bus, message, bin, reference):
            """Handle messages related to a playback."""
            if bin in _bins:
                if message.type==Gst.MessageType.EOS:
                    _bins.remove(bin)
                    if reference is not None:
                        outQueue.put((REPLY_FINISHED, (reference,)))
                elif message.type==Gst.MessageType.ERROR:
                    _bins.remove(bin)
                    if reference is not None:
                        outQueue.put((REPLY_FAILED, (reference,)))

        def _handleCommand(command, args):
            """Handle commands sent to the server."""
            if command==COMMAND_STARTSOUND:
                (name, reference) = args
                try:
                    playBin = Gst.ElementFactory.make("playbin", "player")

                    bus = playBin.get_bus()
                    bus.add_signal_watch()
                    bus.connect("message", _handlePlayBinMessage,
                                playBin, reference)

                    path = os.path.join(soundsDirectory, name)
                    playBin.set_property( "uri", "file://%s" % (path,))

                    playBin.set_state(Gst.State.PLAYING)
                    _bins.add(playBin)
                except Exception as e:
                    if reference is not None:
                        outQueue.put((REPLY_FAILED, (reference,)))
            elif command==COMMAND_QUIT:
                outQueue.put((REPLY_QUIT, None))
                mainLoop.quit()

        def _processCommands():
            """Process incoming commands.

            It is to be executed in a separate thread and it reads the incoming
            queue for commands. The commands with their arguments are added to the
            idle queue of gobject so that _handleCommand will be called by them.

            If COMMAND_QUIT is received, the thread exits."""

            while True:
                (command, args) = inQueue.get()

                gobject.idle_add(_handleCommand, command, args)
                if command==COMMAND_QUIT:
                    break

        commandThread = Thread(target = _processCommands)
        commandThread.daemon = True
        commandThread.start()


        mainLoop = gobject.MainLoop()
        mainLoop.run()

        commandThread.join()

    def _handleInQueue():
        """Handle the incoming queue in the main program.

        It reads the replies sent by the helper process. In case of
        REPLY_FINISHED and REPLY_FAILED the appropriate callback is called. In
        case of REPLY_QUIT, the thread quits as well."""
        while True:
            (reply, args) = _inQueue.get()
            if reply==REPLY_FINISHED or reply==REPLY_FAILED:
                (reference,) = args
                callback = None
                extra = None
                with _lock:
                    (callback, extra) = _ref2Data.get(reference, (None, None))
                    if callback is not None:
                        del _ref2Data[reference]
                if callback is not None:
                    callback(reply==REPLY_FINISHED, extra)
            elif reply==REPLY_QUIT:
                break

    def preInitializeSound():
        """Start the sound handling process and create the thread handling the
        incoming queue."""
        global _thread
        global _process
        global _inQueue
        global _outQueue

        _inQueue = Queue()
        _outQueue = Queue()

        _process = Process(target = _processFn, args = (_outQueue, _inQueue))
        _process.start()

        _thread = Thread(target = _handleInQueue)
        _thread.daemon = True

    def initializeSound(soundsDirectory):
        """Initialize the sound handling. It reads a boolean from the incoming
        queue indicating if the libraries could be loaded by the process.

        If the boolean is True, the thread handling the incoming replies is
        started and the directory containing the sounds file is written to the
        output queue.

        Otherwise the exception is read from the queue, and printed with an
        error message."""
        global _initialized
        _initialized = _inQueue.get()

        if _initialized:
            _thread.start()
            _outQueue.put(soundsDirectory)
        else:
            exception = _inQueue.get()
            print "The Gst library is missing from your system. It is needed for sound playback on Linux:"
            print exception

    def startSound(name, finishCallback = None, extra = None):
        """Start playing back the given sound.

        If a callback is given, a new reference is acquired and the callback is
        registered with it. Then a COMMAND_STARTSOUND command is written to the
        output queue"""
        if _initialized:
            reference = None
            if finishCallback is not None:
                with _lock:
                    global _nextReference
                    reference = _nextReference
                    _nextReference += 1
                    _ref2Data[reference] = (finishCallback, extra)

            _outQueue.put((COMMAND_STARTSOUND, (name, reference)))

    def finalizeSound():
        """Finalize the sound handling.

        COMMAND_QUIT is sent to the helper process, and then it is joined."""
        if _initialized:
            _outQueue.put((COMMAND_QUIT, None))
            _process.join()
            _thread.join()

#------------------------------------------------------------------------------
#------------------------------------------------------------------------------

if __name__ == "__main__":
    import time

    def callback(result, extra):
        print "callback", result, extra

    preInitializeSound()

    soundsPath = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                              "..", "..", "sounds"))
    print "soundsPath:", soundsPath
    initializeSound(soundsPath)
    startSound("notam.mp3", finishCallback = callback, extra= "notam.mp3")
    time.sleep(5)
    startSound("malev.mp3", finishCallback = callback, extra="malev.mp3")
    time.sleep(5)
    startSound("ding.wav", finishCallback = callback, extra="ding1.wav")
    time.sleep(5)
    startSound("ding.wav", finishCallback = callback, extra="ding2.wav")
    time.sleep(5)
    startSound("ding.wav", finishCallback = callback, extra="ding3.wav")
    time.sleep(5)
    startSound("dong.wav", finishCallback = callback, extra="dong3.wav")
    time.sleep(50)

    finalizeSound()

#------------------------------------------------------------------------------
