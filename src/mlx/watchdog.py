# Watchdog

#-----------------------------------------------------------------------------

from threading import Thread, Lock

import time

#-----------------------------------------------------------------------------

## @package mlx.watchdog
#
# Watchdog module. It implements a thread which wakes up regularly and checks
# that none of its clients is left in a state for too long a time. If so, that
# fact is logged.

#-----------------------------------------------------------------------------

class _ClientState(object):
    """A client state.

    It can be set or cleared. If set, there is a timeout associated with it. If
    the timeout is over, the client state is logged. If it becomes clear later,
    that fact is logged too."""
    def __init__(self, timeout, name):
        """Construct the client state with the given timeout and log text."""

        self._lock = Lock()

        self._timeout = timeout
        self._name = name
        self._nextTimeout = None
        self._timedout = False

    def set(self):
        """Put the client into the set state."""
        with self._lock:
            if self._nextTimeout is None:
                self._nextTimeout = time.time() + self._timeout

    def clear(self):
        """Put the client into the cleared state."""
        with self._lock:
            self._nextTimeout = None

    def _check(self, t):
        """Check the client state.

        If it has timed out, and it has not been logged yet, it is logged. If
        it is cleared, but had a timeout earlier, that fact is also logged."""
        logTimeout = False
        logCleared = False
        with self._lock:
            if self._nextTimeout is None:
                logCleared = self._timedout
                self._timedout = False
            elif t>=self._nextTimeout:
                logTimeout = not self._timedout
                self._timedout = True

        if logTimeout:
            print("Watchdog client %s has timed out!" % (self._name))
        elif logCleared:
            print("Watchdog client %s has been cleared." % (self._name))

#-----------------------------------------------------------------------------

class Watchdog(Thread):
    """The watchdog thread."""
    _instance = None

    WAKEUP_INTERVAL = 1.0

    LOG_INTERVAL = 60.0

    @staticmethod
    def get():
        """Get the only instance of the watchdog."""
        return Watchdog._instance

    def __init__(self):
        """Construct the watchdog."""
        assert self._instance is None

        super(Watchdog, self).__init__()
        self.daemon = True

        self._lock = Lock()
        self._clients = []

        Watchdog._instance = self

    def addClient(self, timeout, name):
        """Add a client with the given timeout and name.

        The new client is returned."""
        client = _ClientState(timeout, name)
        with self._lock:
            self._clients.append(client)
        return client

    def run(self):
        """Perform the client checks, then wait for WAKEUP_INTERVAL.

        If LOG_INTERVAL elapses, put an entry in the debug log to confirm that
        the watchdog still works."""

        nextLogTime = time.time()
        nextWakeupTime = nextLogTime + self.WAKEUP_INTERVAL

        while True:
            t = time.time()
            while t>=nextWakeupTime:
                nextWakeupTime += self.WAKEUP_INTERVAL

            if t>=nextLogTime:
                print("Watchdog.run: running")
                while t>=nextLogTime:
                    nextLogTime += self.LOG_INTERVAL

            self._checkClients(t)

            t = time.time()
            if t<nextWakeupTime:
                time.sleep(nextWakeupTime - t)

    def _checkClients(self, t):
        """Check the clients."""
        with self._lock:
            clients = self._clients[:]

        for client in clients:
            client._check(t)

#-----------------------------------------------------------------------------
#-----------------------------------------------------------------------------
