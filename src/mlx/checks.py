
import fs
import const
import util
from acars import ACARS
from sound import startSound

import time

#---------------------------------------------------------------------------------------

## @package mlx.checks
#
# The classes that check the state of the aircraft.
#
# During the flight the program periodically queries various data from the
# simulator. This data is returned in instances of the \ref
# mlx.fs.AircraftState class and passed to the various "checkers",
# i.e. instances of subclasses of the \ref StateChecker class. These checkers
# perform various checks to see if the aircraft's parameters are within the
# expected limits, or some of them just logs something.
#
# There are a few special ones, such as \ref StageChecker which computes the
# transitions from one stage of the flight to the next one. Or \ref ACARSSender
# which sends the ACARS periodically

#---------------------------------------------------------------------------------------

class StateChecker(object):
    """Base class for classes the instances of which check the aircraft's state
    from some aspect.

    As a result of the check they may log something, or notify of some fault, etc."""
    def check(self, flight, aircraft, logger, oldState, state):
        """Perform the check and do whatever is needed.

        This default implementation raises a NotImplementedError."""
        raise NotImplementedError()
    
#---------------------------------------------------------------------------------------

class StageChecker(StateChecker):
    """Check the flight stage transitions."""
    def __init__(self):
        """Construct the stage checker."""
        self._flareStarted = False

    def check(self, flight, aircraft, logger, oldState, state):
        """Check the stage of the aircraft."""
        stage = flight.stage
        if stage==None:
            aircraft.setStage(state, const.STAGE_BOARDING)
        elif stage==const.STAGE_BOARDING:
            if not state.parking or \
               (not state.trickMode and state.groundSpeed>5.0):
                aircraft.setStage(state, const.STAGE_PUSHANDTAXI)
        elif stage==const.STAGE_PUSHANDTAXI or stage==const.STAGE_RTO:
            if state.landingLightsOn or state.strobeLightsOn or \
               state.groundSpeed>80.0:
                aircraft.setStage(state, const.STAGE_TAKEOFF)
        elif stage==const.STAGE_TAKEOFF:
            if not state.gearsDown or \
               (state.radioAltitude>3000.0 and state.vs>0):
                aircraft.setStage(state, const.STAGE_CLIMB)
            elif not state.landingLightsOn and \
                 not state.strobeLightsOn and \
                 state.onTheGround and \
                 state.groundSpeed<50.0:
                aircraft.setStage(state, const.STAGE_RTO)
        elif stage==const.STAGE_CLIMB:
            if (state.altitude+2000) > flight.cruiseAltitude:
                aircraft.setStage(state, const.STAGE_CRUISE)
            elif state.radioAltitude<2000.0 and \
                 state.vs < 0.0 and state.gearsDown:
                aircraft.setStage(state, const.STAGE_LANDING)
        elif stage==const.STAGE_CRUISE:
            if (state.altitude+2000) < flight.cruiseAltitude:
                aircraft.setStage(state, const.STAGE_DESCENT)
        elif stage==const.STAGE_DESCENT or stage==const.STAGE_GOAROUND:
            if state.gearsDown and state.radioAltitude<2000.0:
                aircraft.setStage(state, const.STAGE_LANDING)
            elif (state.altitude+2000) > flight.cruiseAltitude:
                aircraft.setStage(state, const.STAGE_CRUISE)
        elif stage==const.STAGE_LANDING:
            if state.onTheGround and state.groundSpeed<50.0:
                aircraft.setStage(state, const.STAGE_TAXIAFTERLAND)
            elif not state.gearsDown:
                aircraft.setStage(state, const.STAGE_GOAROUND)
            elif state.radioAltitude>200 and self._flareStarted:
                aircraft.cancelFlare()
                self._flareStarted = False
            elif state.radioAltitude<150 and not state.onTheGround and \
                 not self._flareStarted:
                self._flareStarted = True
                aircraft.prepareFlare()
        elif stage==const.STAGE_TAXIAFTERLAND:
            if state.parking:
                aircraft.setStage(state, const.STAGE_PARKING)
        elif stage==const.STAGE_PARKING:
            if aircraft.checkFlightEnd(state):
                aircraft.setStage(state, const.STAGE_END)

#---------------------------------------------------------------------------------------

class ACARSSender(StateChecker):
    """Sender of online ACARS.

    It sends the ACARS every 3 minutes to the MAVA website."""

    ## The interval at which the ACARS are sent
    INTERVAL = 3*60.0
    
    def __init__(self, gui):
        """Construct the ACARS sender."""
        self._gui = gui
        self._lastSent = None

    def check(self, flight, aircraft, logger, oldState, state):
        """If the time has come to send the ACARS, send it."""
        now = time.time()
        
        if self._lastSent is not None and \
           (self._lastSent + ACARSSender.INTERVAL)>now:
            return 

        acars = ACARS(self._gui, state)
        self._gui.webHandler.sendACARS(self._acarsCallback, acars)

    def _acarsCallback(self, returned, result):
        """Callback for ACARS sending."""
        if returned:
            print "Sent online ACARS"
            self._lastSent = time.time() if self._lastSent is None \
                             else self._lastSent + ACARSSender.INTERVAL
        else:
            print "Failed to send the ACARS"
        
#---------------------------------------------------------------------------------------

class TakeOffLogger(StateChecker):
    """Logger for the cruise speed."""
    def __init__(self):
        """Construct the logger."""
        self._onTheGround = True
    
    def check(self, flight, aircraft, logger, oldState, state):
        """Log the cruise speed if necessary."""
        if flight.stage==const.STAGE_TAKEOFF and \
           self._onTheGround and not state.onTheGround:
            logger.message(state.timestamp,
                           "Takeoff speed: %.0f %s" % \
                           (flight.speedFromKnots(state.ias),
                            flight.getEnglishSpeedUnit()))
            logger.message(state.timestamp,
                           "Takeoff heading: %03.0f degrees" % (state.heading,))
            logger.message(state.timestamp,
                           "Takeoff pitch: %.1f degrees" % (state.pitch,))
            logger.message(state.timestamp, 
                           "Centre of gravity:  %.1f%%" % (state.cog*100.0,))
            self._onTheGround = False

#---------------------------------------------------------------------------------------

class CruiseSpeedLogger(StateChecker):
    """Logger for the cruise speed."""
    def __init__(self):
        """Construct the logger."""
        self._lastTime = None
    
    def check(self, flight, aircraft, logger, oldState, state):
        """Log the cruise speed if necessary."""
        if flight.stage==const.STAGE_CRUISE and \
           (self._lastTime is None or \
            (self._lastTime+800)<=state.timestamp):
                if state.altitude>24500.0:
                    logger.message(state.timestamp,
                                   "Cruise speed: %.3f mach" % (state.mach,))
                else:
                    logger.message(state.timestamp,
                                   "Cruise speed: %.0f %s" %
                                   (flight.speedFromKnots(state.ias),
                                    flight.getEnglishSpeedUnit()))
                self._lastTime = state.timestamp

#---------------------------------------------------------------------------------------

class SpoilerLogger(StateChecker):
    """Logger for the cruise speed."""
    def __init__(self):
        """Construct the logger."""
        self._logged = False
        self._spoilersExtension = None
    
    def check(self, flight, aircraft, logger, oldState, state):
        """Log the cruise speed if necessary."""
        if flight.stage==const.STAGE_LANDING and not self._logged:
            if state.onTheGround:
                if state.spoilersExtension!=self._spoilersExtension:
                    logger.message(state.timestamp, "Spoilers deployed")
                    self._logged = True
                    config = flight.config
                    if config.enableSounds and config.speedbrakeAtTD:
                        startSound(const.SOUND_SPEEDBRAKE)
            else:
                self._spoilersExtension = state.spoilersExtension

#---------------------------------------------------------------------------------------

class VisibilityChecker(StateChecker):
    """Inform the pilot of the visibility once when descending below 2000 ft,
    then when descending below 1000 ft."""
    def __init__(self):
        """Construct the visibility checker."""
        self._informedBelow2000 = False
        self._informedBelow1000 = False

    def check(self, flight, aircraft, logger, oldState, state):
        """Check if we need to inform the pilot of the visibility."""
        if flight.stage==const.STAGE_DESCENT or \
           flight.stage==const.STAGE_LANDING:
            if (state.radioAltitude<2000 and not self._informedBelow2000) or \
               (state.radioAltitude<1000 and not self._informedBelow1000):
                visibilityString = util.visibility2String(state.visibility)
                fs.sendMessage(const.MESSAGETYPE_VISIBILITY,
                               "Current visibility: " + visibilityString,
                               5)
                logger.message(state.timestamp,
                               "Pilot was informed about the visibility: " +
                               visibilityString)
                self._informedBelow2000 = True
                self._informedBelow1000 = state.radioAltitude<1000

#---------------------------------------------------------------------------------------

class ApproachCalloutsPlayer(StateChecker):
    """A state checker that plays a sequence of approach callouts.

    It tracks the altitude during the descent and landing phases and
    if the altitude crosses one that has a callout associated with and
    the vertical speed is negative, that callout will be played."""    
    def __init__(self, approachCallouts):
        """Construct the approach callouts player."""
        self._approachCallouts = approachCallouts
        self._altitudes = approachCallouts.getAltitudes(descending = False)

    def check(self, flight, aircraft, logger, oldState, state):
        """Check if we need to play a callout."""
        if (flight.stage==const.STAGE_DESCENT or \
            flight.stage==const.STAGE_LANDING) and state.vs<0:
            oldRadioAltitude = oldState.radioAltitude
            radioAltitude = state.radioAltitude
            for altitude in self._altitudes:
                if radioAltitude<=altitude and \
                   oldRadioAltitude>altitude:
                    startSound(self._approachCallouts[altitude])
                    break

#---------------------------------------------------------------------------------------

class StateChangeLogger(StateChecker):
    """Base class for classes the instances of which check if a specific change has
    occured in the aircraft's state, and log such change."""
    def __init__(self, logInitial = True):
        """Construct the logger.

        If logInitial is True, the initial value will be logged, not just the
        changes later.

        Child classes should define the following functions:
        - _changed(self, oldState, state): returns a boolean indicating if the
        value has changed or not
        - _getMessage(self, flight, state, forced): return a strings containing
        the message to log with the new value
        """
        self._logInitial = logInitial    

    def _getLogTimestamp(self, state):
        """Get the log timestamp."""
        return state.timestamp

    def check(self, flight, aircraft, logger, oldState, state):
        """Check if the state has changed, and if so, log the new state."""
        shouldLog = False
        if oldState is None:
            shouldLog = self._logInitial
        else:
            shouldLog = self._changed(oldState, state)
        
        if shouldLog:
            self.logState(flight, logger, state)

    def logState(self, flight, logger, state, forced = False):
        """Log the state."""
        message = self._getMessage(flight, state, forced)
        if message is not None:
            logger.message(self._getLogTimestamp(state), message)
        
#-------------------------------------------------------------------------------

class SimpleChangeMixin(object):
    """A mixin that defines a _changed() function which simply calls a function
    to retrieve the value two monitor for both states and compares them.

    Child classes should define the following function:
    - _getValue(state): get the value we are interested in."""
    def _changed(self, oldState, state):
        """Determine if the value has changed."""
        currentValue = self._getValue(state)
        return currentValue is not None and self._getValue(oldState)!=currentValue

#---------------------------------------------------------------------------------------

class SingleValueMixin(object):
    """A mixin that provides a _getValue() function to query a value from the
    state using the name of the attribute."""
    def __init__(self, attrName):
        """Construct the mixin with the given attribute name."""
        self._attrName = attrName

    def _getValue(self, state):
        """Get the value of the attribute from the state."""
        return getattr(state, self._attrName)
    
#---------------------------------------------------------------------------------------

class DelayedChangeMixin(object):
    """A mixin to a StateChangeLogger that stores the old value and reports a
    change only if the change has been there for a certain amount of time.

    Child classes should define the following function:
    - _getValue(state): get the value we are interested in."""
    def __init__(self, minDelay = 3.0, maxDelay = 10.0):
        """Construct the mixin with the given delay in seconds."""
        self._minDelay = minDelay
        self._maxDelay = maxDelay
        self._oldValue = None
        self._firstChange = None
        self._lastChangeState = None
        
    def _changed(self, oldState, state):
        """Determine if the value has changed."""
        if self._oldValue is None:
            self._oldValue = self._getValue(oldState)
            
        newValue = self._getValue(state)
        if self._isDifferent(self._oldValue, newValue):
            if self._firstChange is None:
                self._firstChange = state.timestamp
            self._lastChangeState = state
            self._oldValue = newValue

        if self._firstChange is not None:
            if state.timestamp >= min(self._lastChangeState.timestamp + self._minDelay,
                                      self._firstChange + self._maxDelay):
                self._firstChange = None
                return True
            
        return False

    def _getLogTimestamp(self, state):
        """Get the log timestamp."""
        return self._lastChangeState.timestamp if \
               self._lastChangeState is not None else state.timestamp

    def _isDifferent(self, oldValue, newValue):
        """Determine if the given values are different.

        This default implementation checks for simple equality."""
        return oldValue!=newValue

#---------------------------------------------------------------------------------------

class TemplateMessageMixin(object):
    """Mixin to generate a message based on a template.

    Child classes should define the following function:
    - _getValue(state): get the value we are interested in."""
    def __init__(self, template):
        """Construct the mixin."""
        self._template = template

    def _getMessage(self, flight, state, forced):
        """Get the message."""
        value = self._getValue(state)        
        return None if value is None else self._template % (value,)

#---------------------------------------------------------------------------------------

class GenericStateChangeLogger(StateChangeLogger, SingleValueMixin,
                               DelayedChangeMixin, TemplateMessageMixin):
    """Base for generic state change loggers that monitor a single value in the
    state possibly with a delay and the logged message comes from a template"""
    def __init__(self, attrName, template, logInitial = True,
                 minDelay = 0.0, maxDelay = 0.0):
        """Construct the object."""
        StateChangeLogger.__init__(self, logInitial = logInitial)
        SingleValueMixin.__init__(self, attrName)
        DelayedChangeMixin.__init__(self, minDelay = minDelay, maxDelay = maxDelay)
        TemplateMessageMixin.__init__(self, template)
        self._getLogTimestamp = lambda state: \
                                DelayedChangeMixin._getLogTimestamp(self, state)

#---------------------------------------------------------------------------------------

class ForceableLoggerMixin(object):
    """A mixin for loggers that can be forced to log a certain state.

    The last logged state is always maintained, and when checking for a change,
    that state is compared to the current one (which may actually be the same,
    if a forced logging was performed for that state).

    Children should implement the following functions:
    - _hasChanged(oldState, state): the real check for a change
    - _logState(flight, logger, state, forced): the real logging function
    """
    def __init__(self):
        """Construct the mixin."""
        self._lastLoggedState = None

    def forceLog(self, flight, logger, state):
        """Force logging the given state."""
        self.logState(flight, logger, state, forced = True)

    def logState(self, flight, logger, state, forced = False):
        """Log the state.

        It calls _logState to perform the real logging, and saves the given
        state as the last logged one."""
        self._logState(flight, logger, state, forced)
        self._lastLoggedState = state
    
    def _changed(self, oldState, state):
        """Check if the state has changed.

        This function calls _hasChanged for the real check, and replaces
        oldState with the stored last logged state, if any."""
        if self._lastLoggedState is not None:
            oldState = self._lastLoggedState
        return self._hasChanged(oldState, state)

#---------------------------------------------------------------------------------------

class AltimeterLogger(StateChangeLogger, SingleValueMixin,
                      DelayedChangeMixin):
    """Logger for the altimeter setting."""
    def __init__(self):
        """Construct the logger."""
        StateChangeLogger.__init__(self, logInitial = True)
        SingleValueMixin.__init__(self, "altimeter")
        DelayedChangeMixin.__init__(self)
        self._getLogTimestamp = lambda state: \
                                DelayedChangeMixin._getLogTimestamp(self, state)

    def _getMessage(self, flight, state, forced):
        """Get the message to log on a change."""
        logState = self._lastChangeState if \
                   self._lastChangeState is not None else state
        return "Altimeter: %.0f hPa at %.0f feet" % \
               (logState.altimeter, logState.altitude)

#---------------------------------------------------------------------------------------

class NAVLogger(StateChangeLogger, DelayedChangeMixin, ForceableLoggerMixin):
    """Logger for NAV radios.

    It also logs the OBS frequency set."""
    @staticmethod
    def getMessage(logName, frequency, obs):
        """Get the message for the given NAV radio setting."""
        message = u"%s frequency: %s MHz" % (logName, frequency)
        if obs is not None: message += u" [%d\u00b0]" % (obs,)
        return message
    
    def __init__(self, attrName, logName):
        """Construct the NAV logger."""
        StateChangeLogger.__init__(self, logInitial = True)
        DelayedChangeMixin.__init__(self)
        ForceableLoggerMixin.__init__(self)

        self.logState = lambda flight, logger, state, forced = False: \
            ForceableLoggerMixin.logState(self, flight, logger, state,
                                          forced = forced)
        self._getLogTimestamp = \
            lambda state: DelayedChangeMixin._getLogTimestamp(self, state)
        self._changed = lambda oldState, state: \
            ForceableLoggerMixin._changed(self, oldState, state)
        self._hasChanged = lambda oldState, state: \
            DelayedChangeMixin._changed(self, oldState, state)
        self._logState = lambda flight, logger, state, forced: \
             StateChangeLogger.logState(self, flight, logger, state,
                                        forced = forced)

        self._attrName = attrName
        self._logName = logName

    def _getValue(self, state):
        """Get the value.

        If both the frequency and the obs settings are available, a tuple
        containing them is returned, otherwise None."""
        frequency = getattr(state, self._attrName)
        obs = getattr(state, self._attrName + "_obs")
        manual = getattr(state, self._attrName + "_manual")
        return (frequency, obs, manual)

    def _getMessage(self, flight, state, forced):
        """Get the message."""
        (frequency, obs, manual) = self._getValue(state)
        return None if frequency is None or obs is None or \
               (not manual and not forced) else \
               self.getMessage(self._logName, frequency, obs)

    def _isDifferent(self, oldValue, newValue):
        """Determine if the valie has changed between the given states."""
        (oldFrequency, oldOBS, _oldManual) = oldValue
        (newFrequency, newOBS, _newManual) = newValue
        return oldFrequency!=newFrequency or oldOBS!=newOBS

#---------------------------------------------------------------------------------------

class NAV1Logger(NAVLogger):
    """Logger for the NAV1 radio setting."""
    def __init__(self):
        """Construct the logger."""
        super(NAV1Logger, self).__init__("nav1", "NAV1")

#---------------------------------------------------------------------------------------

class NAV2Logger(NAVLogger):
    """Logger for the NAV2 radio setting."""
    def __init__(self):
        """Construct the logger."""
        super(NAV2Logger, self).__init__("nav2", "NAV2")

#---------------------------------------------------------------------------------------

class ADFLogger(GenericStateChangeLogger, ForceableLoggerMixin):
    """Base class for the ADF loggers."""
    def __init__(self, attr, logName):
        """Construct the ADF logger."""
        GenericStateChangeLogger.__init__(self, attr,
                                          "%s frequency: %%s kHz" % (logName,),
                                          minDelay = 3.0, maxDelay = 10.0)
        ForceableLoggerMixin.__init__(self)

        self.logState = lambda flight, logger, state, forced = False: \
            ForceableLoggerMixin.logState(self, flight, logger, state,
                                          forced = forced)
        self._changed = lambda oldState, state: \
            ForceableLoggerMixin._changed(self, oldState, state)
        self._hasChanged = lambda oldState, state: \
            DelayedChangeMixin._changed(self, oldState, state)
        self._logState = lambda flight, logger, state, forced: \
             StateChangeLogger.logState(self, flight, logger, state, forced)

#---------------------------------------------------------------------------------------

class ADF1Logger(ADFLogger):
    """Logger for the ADF1 radio setting."""
    def __init__(self):
        """Construct the logger."""
        super(ADF1Logger, self).__init__("adf1", "ADF1")

#---------------------------------------------------------------------------------------

class ADF2Logger(ADFLogger):
    """Logger for the ADF2 radio setting."""
    def __init__(self):
        """Construct the logger."""
        super(ADF2Logger, self).__init__("adf2", "ADF2")

#---------------------------------------------------------------------------------------

class SquawkLogger(GenericStateChangeLogger):
    """Logger for the squawk setting."""
    def __init__(self):
        """Construct the logger."""
        super(SquawkLogger, self).__init__("squawk", "Squawk code: %s",
                                           minDelay = 3.0, maxDelay = 10.0)

#---------------------------------------------------------------------------------------

class LightsLogger(StateChangeLogger, SingleValueMixin, SimpleChangeMixin):
    """Base class for the loggers of the various lights."""
    def __init__(self, attrName, template):
        """Construct the logger."""
        StateChangeLogger.__init__(self)
        SingleValueMixin.__init__(self, attrName)
        
        self._template = template

    def _getMessage(self, flight, state, forced):
        """Get the message from the given state."""
        return self._template % ("ON" if self._getValue(state) else "OFF")
        
#---------------------------------------------------------------------------------------

class AnticollisionLightsLogger(LightsLogger):
    """Logger for the anti-collision lights."""
    def __init__(self):
        LightsLogger.__init__(self, "antiCollisionLightsOn",
                              "Anti-collision lights: %s")

#---------------------------------------------------------------------------------------

class LandingLightsLogger(LightsLogger):
    """Logger for the landing lights."""
    def __init__(self):
        LightsLogger.__init__(self, "landingLightsOn",
                              "Landing lights: %s")

#---------------------------------------------------------------------------------------

class StrobeLightsLogger(LightsLogger):
    """Logger for the strobe lights."""
    def __init__(self):
        LightsLogger.__init__(self, "strobeLightsOn",
                              "Strobe lights: %s")

#---------------------------------------------------------------------------------------

class NavLightsLogger(LightsLogger):
    """Logger for the navigational lights."""
    def __init__(self):
        LightsLogger.__init__(self, "navLightsOn",
                              "Navigational lights: %s")

#---------------------------------------------------------------------------------------

class FlapsLogger(StateChangeLogger, SingleValueMixin, SimpleChangeMixin):
    """Logger for the flaps setting."""
    def __init__(self):
        """Construct the logger."""
        StateChangeLogger.__init__(self, logInitial = True)
        SingleValueMixin.__init__(self, "flapsSet")

    def _getMessage(self, flight, state, forced):
        """Get the message to log on a change."""
        speed = state.groundSpeed if state.groundSpeed<80.0 else state.ias
        return "Flaps set to %.0f at %.0f %s" % \
               (state.flapsSet, flight.speedFromKnots(speed),
                flight.getEnglishSpeedUnit())

#---------------------------------------------------------------------------------------

class GearsLogger(StateChangeLogger, SingleValueMixin, SimpleChangeMixin):
    """Logger for the gears state."""
    def __init__(self):
        """Construct the logger."""
        StateChangeLogger.__init__(self, logInitial = True)
        SingleValueMixin.__init__(self, "gearControlDown")

    def _getMessage(self, flight, state, forced):
        """Get the message to log on a change."""
        return "Gears SET to %s at %.0f %s, %.0f feet" % \
            ("DOWN" if state.gearControlDown else "UP",
             flight.speedFromKnots(state.ias),
             flight.getEnglishSpeedUnit(), state.altitude)

#---------------------------------------------------------------------------------------

class FaultChecker(StateChecker):
    """Base class for checkers that look for faults."""
    @staticmethod
    def _appendDuring(flight, message):
        """Append a 'during XXX' test to the given message, depending on the
        flight stage."""
        stageStr = const.stage2string(flight.stage)
        return message if stageStr is None \
               else (message + " during " + stageStr.upper())

    @staticmethod
    def _getLinearScore(minFaultValue, maxFaultValue, minScore, maxScore,
                        value):
        """Get the score for a faulty value where the score is calculated
        linearly within a certain range."""
        if value<minFaultValue:
            return 0
        elif value>maxFaultValue:
            return maxScore
        else:
            return minScore + (maxScore-minScore) * (value-minFaultValue) / \
                   (maxFaultValue - minFaultValue)

#---------------------------------------------------------------------------------------

class SimpleFaultChecker(FaultChecker):
    """Base class for fault checkers that check for a single occurence of a
    faulty condition.

    Child classes should implement the following functions:
    - isCondition(self, flight, aircraft, oldState, state): should return whether the
    condition holds
    - logFault(self, flight, aircraft, logger, oldState, state): log the fault
    via the logger."""
    def check(self, flight, aircraft, logger, oldState, state):
        """Perform the check."""
        if self.isCondition(flight, aircraft, oldState, state):
            self.logFault(flight, aircraft, logger, oldState, state)

#---------------------------------------------------------------------------------------

class PatientFaultChecker(FaultChecker):
    """A fault checker that does not decides on a fault when the condition
    arises immediately, but can wait some time.

    Child classes should implement the following functions:
    - isCondition(self, flight, aircraft, oldState, state): should return whether the
    condition holds
    - logFault(self, flight, aircraft, logger, oldState, state): log the fault
    via the logger
    """
    def __init__(self, timeout = 2.0):
        """Construct the fault checker with the given timeout."""
        self._timeout = timeout
        self._faultStarted = None

    def getTimeout(self, flight, aircraft, oldState, state):
        """Get the timeout.

        This default implementation returns the timeout given in the
        constructor, but child classes might want to enforce a different
        policy."""
        return self._timeout

    def check(self, flight, aircraft, logger, oldState, state):
        """Perform the check."""
        if self.isCondition(flight, aircraft, oldState, state):
            if self._faultStarted is None:
                self._faultStarted = state.timestamp
            timeout = self.getTimeout(flight, aircraft, oldState, state)
            if state.timestamp>=(self._faultStarted + timeout):
                self.logFault(flight, aircraft, logger, oldState, state)
                self._faultStarted = state.timestamp
        else:
            self._faultStarted = None
                
#---------------------------------------------------------------------------------------

class AntiCollisionLightsChecker(PatientFaultChecker):
    """Check for the anti-collision light being off at high N1 values."""
    def isCondition(self, flight, aircraft, oldState, state):
        """Check if the fault condition holds."""
        return (flight.stage!=const.STAGE_PARKING or \
                not flight.config.usingFS2Crew) and \
                not state.antiCollisionLightsOn and \
                self.isEngineCondition(state)

    def logFault(self, flight, aircraft, logger, oldState, state):
        """Log the fault."""
        flight.handleFault(AntiCollisionLightsChecker, state.timestamp,
                           FaultChecker._appendDuring(flight,
                                                      "Anti-collision lights were off"),
                           1)

    def isEngineCondition(self, state):
        """Determine if the engines are in such a state that the lights should
        be on."""
        if state.n1 is not None:
            return max(state.n1)>5
        elif state.rpm is not None:
            return max(state.rpm)>0
        else:
            return False

#---------------------------------------------------------------------------------------

class TupolevAntiCollisionLightsChecker(AntiCollisionLightsChecker):
    """Check for the anti-collision light for Tuplev planes."""
    def isCondition(self, flight, aircraft, oldState, state):
        """Check if the fault condition holds."""        
        numEnginesRunning = 0
        for n1 in state.n1:
            if n1>5: numEnginesRunning += 1
            
        if flight.stage==const.STAGE_PARKING:
            return numEnginesRunning<len(state.n1) \
                   and state.antiCollisionLightsOn
        else:
            return numEnginesRunning>1 and not state.antiCollisionLightsOn or \
                   numEnginesRunning<1 and state.antiCollisionLightsOn

#---------------------------------------------------------------------------------------

class BankChecker(SimpleFaultChecker):
    """Check for the bank is within limits."""
    def isCondition(self, flight, aircraft, oldState, state):
        """Check if the fault condition holds."""
        if flight.stage==const.STAGE_CRUISE:
            bankLimit = 30
        elif flight.stage in [const.STAGE_TAKEOFF, const.STAGE_CLIMB,
                              const.STAGE_DESCENT, const.STAGE_LANDING]:
            bankLimit = 35
        else:
            return False

        return state.bank>bankLimit or state.bank<-bankLimit

    def logFault(self, flight, aircraft, logger, oldState, state):
        """Log the fault."""
        flight.handleFault(BankChecker, state.timestamp,
                           FaultChecker._appendDuring(flight, "Bank too steep"),
                           2)

#---------------------------------------------------------------------------------------

class FlapsRetractChecker(SimpleFaultChecker):
    """Check if the flaps are not retracted too early."""
    def __init__(self):
        """Construct the flaps checker."""
        self._timeStart = None
    
    def isCondition(self, flight, aircraft, oldState, state):
        """Check if the fault condition holds.

        FIXME: check if this really is the intention (FlapsRetractedMistake.java)"""
        if (flight.stage==const.STAGE_TAKEOFF and not state.onTheGround) or \
           (flight.stage==const.STAGE_LANDING and state.onTheGround):
            if self._timeStart is None:
                self._timeStart = state.timestamp

            if state.flapsSet==0 and state.timestamp<=(self._timeStart+2.0):
                return True
        else:
            self._timeStart = None
        return False

    def logFault(self, flight, aircraft, logger, oldState, state):
        """Log the fault."""
        flight.handleFault(FlapsRetractChecker, state.timestamp,
                           FaultChecker._appendDuring(flight, "Flaps retracted"),
                           20)

#---------------------------------------------------------------------------------------

class FlapsSpeedLimitChecker(SimpleFaultChecker):
    """Check if the flaps are extended only at the right speeds."""
    def isCondition(self, flight, aircraft, oldState, state):
        """Check if the fault condition holds."""
        speedLimit = aircraft.getFlapsSpeedLimit(state.flapsSet)
        return speedLimit is not None and state.smoothedIAS>speedLimit

    def logFault(self, flight, aircraft, logger, oldState, state):
        """Log the fault."""
        flight.handleFault(FlapsSpeedLimitChecker, state.timestamp,
                           FaultChecker._appendDuring(flight, "Flap speed limit fault"),
                           5)

#---------------------------------------------------------------------------------------

class GearsDownChecker(SimpleFaultChecker):
    """Check if the gears are down at low altitudes."""
    def isCondition(self, flight, aircraft, oldState, state):
        """Check if the fault condition holds."""
        return state.radioAltitude<10 and not state.gearsDown and \
               flight.stage!=const.STAGE_TAKEOFF

    def logFault(self, flight, aircraft, logger, oldState, state):
        """Log the fault."""
        flight.handleNoGo(GearsDownChecker, state.timestamp,
                          "Gears not down at %.0f feet radio altitude" % \
                          (state.radioAltitude,),
                          "GEAR DOWN NO GO")

#---------------------------------------------------------------------------------------

class GearSpeedLimitChecker(PatientFaultChecker):
    """Check if the gears not down at too high a speed."""
    def isCondition(self, flight, aircraft, oldState, state):
        """Check if the fault condition holds."""
        return state.gearsDown and state.smoothedIAS>aircraft.gearSpeedLimit

    def logFault(self, flight, aircraft, logger, oldState, state):
        """Log the fault."""
        flight.handleFault(GearSpeedLimitChecker, state.timestamp,
                           FaultChecker._appendDuring(flight, "Gear speed limit fault"),
                           5)

#---------------------------------------------------------------------------------------

class GLoadChecker(SimpleFaultChecker):
    """Check if the G-load does not exceed 2 except during flare."""
    def isCondition(self, flight, aircraft, oldState, state):
        """Check if the fault condition holds."""
        return state.gLoad>2.0 and (flight.stage!=const.STAGE_LANDING or \
                                    state.radioAltitude>=50)
               
    def logFault(self, flight, aircraft, logger, oldState, state):
        """Log the fault."""
        flight.handleFault(GLoadChecker, state.timestamp,
                           "G-load was %.2f" % (state.gLoad,),
                           10)

#---------------------------------------------------------------------------------------

class LandingLightsChecker(PatientFaultChecker):
    """Check if the landing lights are used properly."""
    def getTimeout(self, flight, aircraft, oldState, state):
        """Get the timeout.

        It is the default timeout except for landing and takeoff."""
        return 0.0 if flight.stage in [const.STAGE_TAKEOFF,
                                       const.STAGE_LANDING] else self._timeout

    def isCondition(self, flight, aircraft, oldState, state):
        """Check if the fault condition holds."""
        return state.landingLightsOn is not None and \
               ((flight.stage==const.STAGE_BOARDING and \
                 state.landingLightsOn and state.onTheGround) or \
                (flight.stage==const.STAGE_TAKEOFF and \
                 not state.landingLightsOn and not state.onTheGround) or \
                (flight.stage in [const.STAGE_CLIMB, const.STAGE_CRUISE,
                                  const.STAGE_DESCENT] and \
                 state.landingLightsOn and state.altitude>12500) or \
                (flight.stage==const.STAGE_LANDING and \
                 not state.landingLightsOn and state.onTheGround) or \
                (flight.stage==const.STAGE_PARKING and \
                 state.landingLightsOn and state.onTheGround))
               
    def logFault(self, flight, aircraft, logger, oldState, state):
        """Log the fault."""
        score = 0 if flight.stage==const.STAGE_LANDING else 1
        message = "Landing lights were %s" % (("on" if state.landingLightsOn else "off"),)
        flight.handleFault(LandingLightsChecker, state.timestamp,
                           FaultChecker._appendDuring(flight, message),
                           score)   

#---------------------------------------------------------------------------------------

class WeightChecker(PatientFaultChecker):
    """Base class for checkers that check that some limit is not exceeded."""
    def __init__(self, name):
        """Construct the checker."""
        super(WeightChecker, self).__init__(timeout = 5.0)
        self._name = name

    def isCondition(self, flight, aircraft, oldState, state):
        """Check if the fault condition holds."""
        if flight.entranceExam:
            return False

        limit = self.getLimit(flight, aircraft, state)
        if limit is not None:
            #if flight.options.compensation is not None:
            #    limit += flight.options.compensation
            return self.getWeight(state)>limit

        return False

    def logFault(self, flight, aircraft, logger, oldState, state):
        """Log the fault."""
        mname = "M" + self._name
        flight.handleNoGo(self.__class__, state.timestamp,
                          "%s exceeded: %s is %.0f kg" % \
                                    (mname, self._name, self.getWeight(state)),
                          "%s NO GO" % (mname,))

    def getWeight(self, state):
        """Get the weight that is interesting for us."""
        return state.grossWeight

#---------------------------------------------------------------------------------------

class MLWChecker(WeightChecker):
    """Checks if the MLW is not exceeded on landing."""
    def __init__(self):
        """Construct the checker."""
        super(MLWChecker, self).__init__("LW")

    def getLimit(self, flight, aircraft, state):
        """Get the limit if we are in the right state."""
        return aircraft.mlw if flight.stage==const.STAGE_LANDING and \
                               state.onTheGround and \
                               not flight.entranceExam else None

#---------------------------------------------------------------------------------------

class MTOWChecker(WeightChecker):
    """Checks if the MTOW is not exceeded on landing."""
    def __init__(self):
        """Construct the checker."""
        super(MTOWChecker, self).__init__("TOW")

    def getLimit(self, flight, aircraft, state):
        """Get the limit if we are in the right state."""
        return aircraft.mtow if flight.stage==const.STAGE_TAKEOFF and \
                             not flight.entranceExam else None

#---------------------------------------------------------------------------------------

class MZFWChecker(WeightChecker):
    """Checks if the MZFW is not exceeded on landing."""
    def __init__(self):
        """Construct the checker."""
        super(MZFWChecker, self).__init__("ZFW")

    def getLimit(self, flight, aircraft, state):
        """Get the limit if we are in the right state."""
        return aircraft.mzfw if not flight.entranceExam else None

    def getWeight(self, state):
        """Get the weight that is interesting for us."""
        return state.zfw

#---------------------------------------------------------------------------------------

class NavLightsChecker(PatientFaultChecker):
    """Check if the navigational lights are used properly."""
    def isCondition(self, flight, aircraft, oldState, state):
        """Check if the fault condition holds."""
        return flight.stage!=const.STAGE_BOARDING and \
               flight.stage!=const.STAGE_PARKING and \
               not state.navLightsOn
               
    def logFault(self, flight, aircraft, logger, oldState, state):
        """Log the fault."""
        flight.handleFault(NavLightsChecker, state.timestamp,
                           FaultChecker._appendDuring(flight,
                                                      "Navigation lights were off"),
                           1)

#---------------------------------------------------------------------------------------

class OverspeedChecker(PatientFaultChecker):
    """Check if Vne has been exceeded."""
    def __init__(self, timeout = 5.0):
        """Construct the checker."""
        super(OverspeedChecker, self).__init__(timeout = timeout)

    def isCondition(self, flight, aircraft, oldState, state):
        """Check if the fault condition holds."""
        return state.overspeed
               
    def logFault(self, flight, aircraft, logger, oldState, state):
        """Log the fault."""
        flight.handleFault(OverspeedChecker, state.timestamp,
                           FaultChecker._appendDuring(flight, "Overspeed"),
                           20)        

#---------------------------------------------------------------------------------------

class PayloadChecker(SimpleFaultChecker):
    """Check if the payload matches the specification."""
    TOLERANCE=550

    @staticmethod
    def isZFWFaulty(aircraftZFW, flightZFW):
        """Check if the given aircraft's ZFW is outside of the limits."""
        return aircraftZFW < (flightZFW - PayloadChecker.TOLERANCE) or \
               aircraftZFW > (flightZFW + PayloadChecker.TOLERANCE)        
    
    def isCondition(self, flight, aircraft, oldState, state):
        """Check if the fault condition holds."""
        return not flight.entranceExam and \
               flight.stage==const.STAGE_PUSHANDTAXI and \
               PayloadChecker.isZFWFaulty(state.zfw, flight.zfw)
               
    def logFault(self, flight, aircraft, logger, oldState, state):
        """Log the fault."""
        flight.handleNoGo(PayloadChecker, state.timestamp,
                          "ZFW difference is more than %d kgs" % \
                          (PayloadChecker.TOLERANCE,),
                          "ZFW NO GO")

#---------------------------------------------------------------------------------------

class PitotChecker(PatientFaultChecker):
    """Check if pitot heat is on."""
    def __init__(self):
        """Construct the checker."""
        super(PitotChecker, self).__init__(timeout = 3.0)

    def isCondition(self, flight, aircraft, oldState, state):
        """Check if the fault condition holds."""
        return state.groundSpeed>80 and not state.pitotHeatOn
               
    def logFault(self, flight, aircraft, logger, oldState, state):
        """Log the fault."""
        score = 2 if flight.stage in [const.STAGE_TAKEOFF, const.STAGE_CLIMB,
                                      const.STAGE_CRUISE, const.STAGE_DESCENT,
                                      const.STAGE_LANDING] else 0
        flight.handleFault(PitotChecker, state.timestamp,
                           FaultChecker._appendDuring(flight, "Pitot heat was off"),
                           score)   

#---------------------------------------------------------------------------------------

class ReverserChecker(SimpleFaultChecker):
    """Check if the reverser is not used below 60 knots."""
    def isCondition(self, flight, aircraft, oldState, state):
        """Check if the fault condition holds."""
        return flight.stage in [const.STAGE_DESCENT, const.STAGE_LANDING,
                                const.STAGE_TAXIAFTERLAND] and \
            state.groundSpeed<60 and max(state.reverser)
                           
    def logFault(self, flight, aircraft, logger, oldState, state):
        """Log the fault."""
        message = "Reverser used below %.0f %s" % \
                  (flight.speedFromKnots(60), flight.getEnglishSpeedUnit())
        flight.handleFault(ReverserChecker, state.timestamp,
                           FaultChecker._appendDuring(flight, message),
                           15)

#---------------------------------------------------------------------------------------

class SpeedChecker(SimpleFaultChecker):
    """Check if the speed is in the prescribed limits."""
    def isCondition(self, flight, aircraft, oldState, state):
        """Check if the fault condition holds."""
        return flight.stage in [const.STAGE_PUSHANDTAXI,
                                const.STAGE_TAXIAFTERLAND] and \
            state.groundSpeed>50
                           
    def logFault(self, flight, aircraft, logger, oldState, state):
        """Log the fault."""
        message = "Taxi speed over %.0f %s" % \
                  (flight.speedFromKnots(50), flight.getEnglishSpeedUnit())
        flight.handleFault(SpeedChecker, state.timestamp,
                           FaultChecker._appendDuring(flight, message),
                           FaultChecker._getLinearScore(50, 80, 10, 15,
                                                        state.groundSpeed))

#---------------------------------------------------------------------------------------

class StallChecker(PatientFaultChecker):
    """Check if stall occured."""
    def isCondition(self, flight, aircraft, oldState, state):
        """Check if the fault condition holds."""
        return flight.stage in [const.STAGE_TAKEOFF, const.STAGE_CLIMB,
                                const.STAGE_CRUISE, const.STAGE_DESCENT,
                                const.STAGE_LANDING] and state.stalled
               
    def logFault(self, flight, aircraft, logger, oldState, state):
        """Log the fault."""
        score = 40 if flight.stage in [const.STAGE_TAKEOFF,
                                       const.STAGE_LANDING] else 30
        flight.handleFault(StallChecker, state.timestamp,
                           FaultChecker._appendDuring(flight, "Stalled"),
                           score)   

#---------------------------------------------------------------------------------------

class StrobeLightsChecker(PatientFaultChecker):
    """Check if the strobe lights are used properly."""
    def isCondition(self, flight, aircraft, oldState, state):
        """Check if the fault condition holds."""
        return (flight.stage==const.STAGE_BOARDING and \
                state.strobeLightsOn and state.onTheGround) or \
                (flight.stage==const.STAGE_TAKEOFF and \
                 not state.strobeLightsOn and not state.gearsDown) or \
                 (flight.stage in [const.STAGE_CLIMB, const.STAGE_CRUISE,
                                   const.STAGE_DESCENT] and \
                  not state.strobeLightsOn and not state.onTheGround) or \
                  (flight.stage==const.STAGE_PARKING and \
                   state.strobeLightsOn and state.onTheGround)
               
    def logFault(self, flight, aircraft, logger, oldState, state):
        """Log the fault."""
        message = "Strobe lights were %s" % (("on" if state.strobeLightsOn else "off"),)
        flight.handleFault(StrobeLightsChecker, state.timestamp,
                           FaultChecker._appendDuring(flight, message),
                           1)

#---------------------------------------------------------------------------------------

class ThrustChecker(SimpleFaultChecker):
    """Check if the thrust setting is not too high during takeoff.

    FIXME: is this really so general, for all aircraft?"""
    def isCondition(self, flight, aircraft, oldState, state):
        """Check if the fault condition holds."""
        return flight.stage==const.STAGE_TAKEOFF and \
               state.n1 is not None and max(state.n1)>97
               
    def logFault(self, flight, aircraft, logger, oldState, state):
        """Log the fault."""
        flight.handleFault(ThrustChecker, state.timestamp,
                           FaultChecker._appendDuring(flight,
                                                      "Thrust setting was too high (>97%)"),
                           FaultChecker._getLinearScore(97, 110, 0, 10, max(state.n1)))

#---------------------------------------------------------------------------------------

class VSChecker(SimpleFaultChecker):
    """Check if the vertical speed is not too low at certain altitudes"""
    BELOW10000 = -5000
    BELOW5000 = -2500
    BELOW2500 = -1500
    BELOW500 = -1000
    TOLERANCE = 1.2

    def isCondition(self, flight, aircraft, oldState, state):
        """Check if the fault condition holds."""
        vs = state.smoothedVS
        altitude = state.altitude
        return vs < -8000 or vs > 8000 or \
               (altitude<500 and vs < (VSChecker.BELOW500 *
                                       VSChecker.TOLERANCE)) or \
               (altitude<2500 and vs < (VSChecker.BELOW2500 *
                                        VSChecker.TOLERANCE)) or \
               (altitude<5000 and vs < (VSChecker.BELOW5000 *
                                        VSChecker.TOLERANCE)) or \
               (altitude<10000 and vs < (VSChecker.BELOW10000 *
                                         VSChecker.TOLERANCE))
               
    def logFault(self, flight, aircraft, logger, oldState, state):
        """Log the fault."""
        vs = state.smoothedVS

        message = "Vertical speed was %.0f feet/min" % (vs,)
        if vs>-8000 and vs<8000:
            message += " at %.0f feet (exceeds company limit)" % (state.altitude,)

        score = 10 if vs<-8000 or vs>8000 else 0

        flight.handleFault(VSChecker, state.timestamp,
                           FaultChecker._appendDuring(flight, message),
                           score)

#---------------------------------------------------------------------------------------
