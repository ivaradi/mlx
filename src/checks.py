# The various checks that may be performed during flight

#---------------------------------------------------------------------------------------

import const

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
            elif state.radioAltitude>200:
                aircraft.cancelFlare()
            elif state.radioAltitude<150 and not state.onTheGround:
                aircraft.flare()
        elif stage==const.STAGE_TAXIAFTERLAND:
            if state.parking:
                aircraft.setStage(state, const.STAGE_PARKING)
        elif stage==const.STAGE_PARKING:
            if aircraft.checkFlightEnd(state):
                aircraft.setStage(state, const.STAGE_END)

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
        - _getMessage(self, state): return a strings containing the message to log
        with the new value
        """
        self._logInitial = logInitial    

    def check(self, flight, aircraft, logger, oldState, state):
        """Check if the state has changed, and if so, log the new state."""
        shouldLog = False
        if oldState is None:
            shouldLog = self._logInitial
        else:
            shouldLog = self._changed(oldState, state)
        
        if shouldLog:
            logger.message(state.timestamp, self._getMessage(state))
        
#---------------------------------------------------------------------------------------

class SimpleChangeMixin(object):
    """A mixin that defines a _changed() function which simply calls a function
    to retrieve the value two monitor for both states and compares them.

    Child classes should define the following function:
    - _getValue(state): get the value we are interested in."""
    def _changed(self, oldState, state):
        """Determine if the value has changed."""
        return self._getValue(oldState)!=self._getValue(state)

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
    def __init__(self, delay = 10.0):
        """Construct the mixin with the given delay in seconds."""
        self._delay = delay
        self._oldValue = None
        self._firstChange = None

    def _changed(self, oldState, state):
        """Determine if the value has changed."""
        if self._oldValue is None:
            self._oldValue = self._getValue(oldState)
            
        newValue = self._getValue(state)
        if newValue!=self._oldValue:
            if self._firstChange is None:
                self._firstChange = state.timestamp
            if state.timestamp >= (self._firstChange + self._delay):
                self._oldValue = newValue
                self._firstChange = None
                return True
        else:
            self._firstChange = None

        return False

#---------------------------------------------------------------------------------------

class TemplateMessageMixin(object):
    """Mixin to generate a message based on a template.

    Child classes should define the following function:
    - _getValue(state): get the value we are interested in."""
    def __init__(self, template):
        """Construct the mixin."""
        self._template = template

    def _getMessage(self, state):
        """Get the message."""
        return self._template % (self._getValue(state),)

#---------------------------------------------------------------------------------------

class GenericStateChangeLogger(StateChangeLogger, SingleValueMixin,
                               DelayedChangeMixin, TemplateMessageMixin):
    """Base for generic state change loggers that monitor a single value in the
    state possibly with a delay and the logged message comes from a template"""
    def __init__(self, attrName, template, logInitial = True, delay = 0.0):
        """Construct the object."""
        StateChangeLogger.__init__(self, logInitial = logInitial)
        SingleValueMixin.__init__(self, attrName)
        DelayedChangeMixin.__init__(self, delay = delay)
        TemplateMessageMixin.__init__(self, template)

#---------------------------------------------------------------------------------------

class AltimeterLogger(StateChangeLogger, SingleValueMixin,
                      DelayedChangeMixin):
    """Logger for the altimeter setting."""
    def __init__(self):
        """Construct the logger."""
        StateChangeLogger.__init__(self, logInitial = True)
        SingleValueMixin.__init__(self, "altimeter")
        DelayedChangeMixin.__init__(self)

    def _getMessage(self, state):
        """Get the message to log on a change."""
        return "Altimeter: %.0f hPa at %.0f feet" % (state.altimeter, state.altitude)

#---------------------------------------------------------------------------------------

class NAV1Logger(GenericStateChangeLogger):
    """Logger for the NAV1 radio setting."""
    def __init__(self):
        """Construct the logger."""
        super(NAV1Logger, self).__init__("nav1", "NAV1 frequency: %s MHz")

#---------------------------------------------------------------------------------------

class NAV2Logger(GenericStateChangeLogger):
    """Logger for the NAV2 radio setting."""
    def __init__(self):
        """Construct the logger."""
        super(NAV2Logger, self).__init__("nav2", "NAV2 frequency: %s MHz")

#---------------------------------------------------------------------------------------

class SquawkLogger(GenericStateChangeLogger):
    """Logger for the squawk setting."""
    def __init__(self):
        """Construct the logger."""
        super(SquawkLogger, self).__init__("squawk", "Squawk code: %s",
                                           delay = 10.0)

#---------------------------------------------------------------------------------------

class LightsLogger(StateChangeLogger, SingleValueMixin, SimpleChangeMixin):
    """Base class for the loggers of the various lights."""
    def __init__(self, attrName, template):
        """Construct the logger."""
        StateChangeLogger.__init__(self)
        SingleValueMixin.__init__(self, attrName)
        
        self._template = template

    def _getMessage(self, state):
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

    def _getMessage(self, state):
        """Get the message to log on a change."""
        speed = state.groundSpeed if state.groundSpeed<80.0 else state.ias
        return "Flaps set to %.0f at %.0f knots" % (state.flapsSet, speed)

#---------------------------------------------------------------------------------------

class GearsLogger(StateChangeLogger, SingleValueMixin, SimpleChangeMixin):
    """Logger for the gears state."""
    def __init__(self):
        """Construct the logger."""
        StateChangeLogger.__init__(self, logInitial = True)
        SingleValueMixin.__init__(self, "gearsDown")

    def _getMessage(self, state):
        """Get the message to log on a change."""
        return "Gears %s at %.0f knots, %f feet" % \
            ("DOWN" if state.gearsDown else "UP", state.ias, state.altitude)

#---------------------------------------------------------------------------------------
