
import const
from sound import startSound

import fsuipc
import threading
import time

#-------------------------------------------------------------------------------

## @package mlx.fs
#
# The main interface to the flight simulator.
#
# The \ref createSimulator function can be used to create an instance of
# the class that can be used to access the simulator. It expects an instance of
# the \ref ConnectionListener class, the member functions of which will be
# called when something happens with the connection to the simulator.
#
# The simulator interface is most often used to retrieve the state of the
# simulated aircraft. Instances of class \ref AircraftState are used for this
# purpose.
#
# This module also contains some definitions for message sending and implements
# the timing logic itself.

#-------------------------------------------------------------------------------

class ConnectionListener(object):
    """Base class for listeners on connections to the flight simulator."""
    def connected(self, fsType, descriptor):
        """Called when a connection has been established to the flight
        simulator of the given type."""
        print "fs.ConnectionListener.connected, fsType:", fsType, ", descriptor:", descriptor

    def connectionFailed(self):
        """Called when the connection could not be established."""
        print "fs.ConnectionListener.connectionFailed"        

    def disconnected(self):
        """Called when a connection to the flight simulator has been broken."""
        print "fs.ConnectionListener.disconnected"

#-------------------------------------------------------------------------------

class SimulatorException(Exception):
    """Exception thrown by the simulator interface for communication failure."""

#-------------------------------------------------------------------------------

def createSimulator(type, connectionListener):
    """Create a simulator instance for the given simulator type with the given
    connection listener.

    The returned object should provide the following members:
    FIXME: add info
    """
    assert type in [const.SIM_MSFS9, const.SIM_MSFSX], \
           "Only MS Flight Simulator 2004 and X are supported"
    return fsuipc.Simulator(connectionListener, connectAttempts = 3)

#-------------------------------------------------------------------------------

class MessageThread(threading.Thread):
    """Thread to handle messages."""
    def __init__(self, config, simulator):
        """Initialize the message thread with the given configuration and
        simulator."""
        super(MessageThread, self).__init__()

        self._config = config
        self._simulator = simulator

        self._requestCondition = threading.Condition()
        self._messages = []
        self._nextMessageTime = None
        self._toQuit = False

        self.daemon = True

    def add(self, messageType, text, duration, disconnect):
        """Add the given message to the requested messages."""
        with self._requestCondition:
            self._messages.append((messageType, text, duration,
                                   disconnect))
            self._requestCondition.notify()

    def quit(self):
        """Quit the thread."""
        with self._requestCondition:
            self._toQuit = True
            self._requestCondition.notifty()
        self.join()

    def run(self):
        """Perform the thread's operation."""
        while True:
            (messageType, text, duration, disconnect) = (None, None, None, None)
            with self._requestCondition:
                now = time.time()
                while not self._toQuit and \
                      ((self._nextMessageTime is not None and \
                        self._nextMessageTime>now) or \
                       not self._messages):
                    self._requestCondition.wait(1)
                    now = time.time()

                if self._toQuit: return
                if self._nextMessageTime is None or \
                   self._nextMessageTime<=now:
                    self._nextMessageTime = None

                    if self._messages:
                        (messageType, text,
                         duration, disconnect) = self._messages[0]
                        del self._messages[0]

            if text is not None:        
                self._sendMessage(messageType, text, duration, disconnect)

    def _sendMessage(self, messageType, text, duration, disconnect):
        """Send the message and setup the next message time."""        
        messageLevel = self._config.getMessageTypeLevel(messageType)
        if messageLevel==const.MESSAGELEVEL_SOUND or \
           messageLevel==const.MESSAGELEVEL_BOTH:
            startSound(const.SOUND_NOTIFY
                       if messageType==const.MESSAGETYPE_VISIBILITY
                       else const.SOUND_DING)
        if (messageLevel==const.MESSAGELEVEL_FS or \
            messageLevel==const.MESSAGELEVEL_BOTH):
            if disconnect:
                self._simulator.disconnect("[MLX] " + text,
                                           duration = duration)
            else:
                self._simulator.sendMessage("[MLX] " + text,
                                            duration = duration)
        elif disconnect:
            self._simulator.disconnect()
        self._nextMessageTime = time.time() + duration

#-------------------------------------------------------------------------------

_messageThread = None

#-------------------------------------------------------------------------------

def setupMessageSending(config, simulator):
    """Setup message sending with the given config and simulator."""
    global _messageThread
    if _messageThread is not None:
        _messageThread.quit()
    _messageThread = MessageThread(config, simulator)
    _messageThread.start()

#-------------------------------------------------------------------------------

def sendMessage(messageType, text, duration = 3, disconnect = False):
    """Send the given message of the given type into the simulator and/or play
    a corresponding sound."""
    global _messageThread
    if _messageThread is not None:
        _messageThread.add(messageType, text, duration, disconnect)

#-------------------------------------------------------------------------------

class AircraftState(object):
    """Base class for the aircraft state produced by the aircraft model based
    on readings from the simulator.

    The following data members should be provided at least:
    - timestamp: the simulator time of the measurement in seconds since the
    epoch (float)
    - latitude (in degrees, North is positive)
    - longitude (in degrees, East is positive)
    - paused: a boolean indicating if the flight simulator is paused for
    whatever reason (it could be a pause mode, or a menu, a dialog, or a
    replay, etc.)
    - trickMode: a boolean indicating if some "trick" mode (e.g. "SLEW" in
    MSFS) is activated
    - overspeed: a boolean indicating if the aircraft is in overspeed
    - stalled: a boolean indicating if the aircraft is stalled
    - onTheGround: a boolean indicating if the aircraft is on the ground    
    - zfw: the zero-fuel weight in kilograms (float)
    - grossWeight: the gross weight in kilograms (float)
    - heading: the heading of the aircraft in degrees (float)
    - pitch: the pitch of the aircraft in degrees. Positive means pitch down,
    negative means pitch up (float)
    - bank: the bank of the aircraft in degrees. Positive means bank left,
    negative means bank right (float)
    - ias: the indicated airspeed in knots (float)
    - smoothedIAS: the smoothed IAS in knots (float)
    - mach: the airspeed in mach (float)    
    - groundSpeed: the ground speed (float)
    - vs: the vertical speed in feet/minutes (float)
    - smoothedVS: the smoothed VS in feet/minutes (float)
    - radioAltitude: the radio altitude of the aircraft in feet (float)
    - altitude: the altitude of the aircraft in feet (float)
    - gLoad: G-load (float)
    - flapsSet: the selected degrees of the flaps (float)
    - flaps: the actual degrees of the flaps (float)
    - fuel[]: the fuel information. It is a list of tuples with items:
    the fuel tank identifier and the amount of fuel in that tank in
    kgs
    - totalFuel: the total amount of fuel in kg
    - n1[]: the N1 values of the turbine engines (array of floats
    of as many items as the number of engines, present only for aircraft with
    turbines, for other aircraft it is None)
    - rpm[]: the RPM values of the piston engines (array of floats
    of as many items as the number of engines, present only for aircraft with
    pistons, for other aircraft it is None)
    - reverser[]: an array of booleans indicating if the thrust reversers are
    activated on any of the engines. The number of items equals to the number
    of engines with a reverser.
    - navLightsOn: a boolean indicating if the navigation lights are on
    - antiCollisionLightsOn: a boolean indicating if the anti-collision lights are on
    - strobeLightsOn: a boolean indicating if the strobe lights are on
    - landingLightsOn: a boolean indicating if the landing lights are on. If
    the detection of the state of the landing lights is unreliable, and should
    not be considered, this is set to None.
    - pitotHeatOn: a boolean indicating if the pitot heat is on
    - parking: a boolean indicating if the parking brake is set
    - gearControlDown: a boolean indicating if the gear control is set to down
    - gearsDown: a boolean indicating if the gears are down
    - spoilersArmed: a boolean indicating if the spoilers have been armed for
    automatic deployment
    - spoilersExtension: the percentage of how much the spoiler is extended
    (float) 
    - altimeter: the altimeter setting in hPa (float)
    - nav1: the frequency of the NAV1 radio in MHz (string). Can be None, if
    the frequency is unreliable or meaningless.
    - nav1_obs: the OBS setting of the NAV1 radio in degrees (int). Can be None, if
    the value is unreliable or meaningless.
    - nav1_manual: a boolean indicating if the NAV1 radio is on manual control
    - nav2: the frequency of the NAV1 radio in MHz (string). Can be None, if
    the frequency is unreliable or meaningless.
    - nav2_obs: the OBS setting of the NAV2 radio in degrees (int). Can be None, if
    the value is unreliable or meaningless.
    - nav2_manual: a boolean indicating if the NAV2 radio is on manual control
    - adf1: the frequency of the ADF1 radio in kHz (string). Can be None, if
    the frequency is unreliable or meaningless.
    - adf2: the frequency of the ADF2 radio in kHz (string). Can be None, if
    the frequency is unreliable or meaningless.
    - squawk: the transponder code (string)
    - windSpeed: the speed of the wind at the aircraft in knots (float)
    - windDirection: the direction of the wind at the aircraft in degrees (float)
    - visibility: the visibility in metres (float)
    - cog: the centre of gravity 

    FIXME: needed when taxiing only:
    - payload weight

    FIXME: needed rarely:
    - latitude, longitude
    - transporter
    - visibility 
    """
    
