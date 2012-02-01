# Module for the simulator-independent aircraft classes

#---------------------------------------------------------------------------------------

import time

import const

#---------------------------------------------------------------------------------------

class Aircraft(object):
    """Base class for aircraft."""
    def __init__(self, type):
        """Construct the aircraft for the given type."""
        self._type = type
        self._aircraftState = None

    @property
    def type(self):
        """Get the type of the aircraft."""
        return self._type

    def modelChanged(self, aircraftName, modelName):
        """Called when the simulator's aircraft changes."""
        print "Aircraft.modelChanged: aircraftName='%s', modelName='%s'" % \
            (aircraftName, modelName)

    def handleState(self, aircraftState):
        """Called when the state of the aircraft changes."""
        timeStr = time.ctime(aircraftState.timestamp)

        if self._aircraftState is None or \
           self._aircraftState.paused != aircraftState.paused:
            print "Aircraft.handleState: %s: paused=%d" % \
                (timeStr, aircraftState.paused)

        if self._aircraftState is None or \
           self._aircraftState.trickMode != aircraftState.trickMode:
            print "Aircraft.handleState: %s: trickMode=%d" % \
                (timeStr, aircraftState.trickMode)

        if self._aircraftState is None or \
           self._aircraftState.overspeed != aircraftState.overspeed:
            print "Aircraft.handleState: %s: overspeed=%d" % \
                (timeStr, aircraftState.overspeed)

        if self._aircraftState is None or \
           self._aircraftState.stalled != aircraftState.stalled:
            print "Aircraft.handleState: %s: stalled=%d" % \
                (timeStr, aircraftState.stalled)

        if self._aircraftState is None or \
           self._aircraftState.onTheGround != aircraftState.onTheGround:
            print "Aircraft.handleState: %s: onTheGround=%d" % \
                (timeStr, aircraftState.onTheGround)

        if self._aircraftState is None or \
           self._aircraftState.grossWeight != aircraftState.grossWeight:
            print "Aircraft.handleState: %s: grossWeight=%f" % \
                (timeStr, aircraftState.grossWeight)

        if self._aircraftState is None or \
           self._aircraftState.heading != aircraftState.heading:
            print "Aircraft.handleState: %s: heading=%f" % \
                (timeStr, aircraftState.heading)

        if self._aircraftState is None or \
           self._aircraftState.pitch != aircraftState.pitch:
            print "Aircraft.handleState: %s: pitch=%f" % \
                (timeStr, aircraftState.pitch)

        if self._aircraftState is None or \
           self._aircraftState.bank != aircraftState.bank:
            print "Aircraft.handleState: %s: bank=%f" % \
                (timeStr, aircraftState.bank)

        if self._aircraftState is None or \
           self._aircraftState.ias != aircraftState.ias:
            print "Aircraft.handleState: %s: ias=%f" % \
                (timeStr, aircraftState.ias)

        if self._aircraftState is None or \
           self._aircraftState.groundSpeed != aircraftState.groundSpeed:
            print "Aircraft.handleState: %s: groundSpeed=%f" % \
                (timeStr, aircraftState.groundSpeed)

        if self._aircraftState is None or \
           self._aircraftState.vs != aircraftState.vs:
            print "Aircraft.handleState: %s: vs=%f" % \
                (timeStr, aircraftState.vs)

        if self._aircraftState is None or \
           self._aircraftState.altitude != aircraftState.altitude:
            print "Aircraft.handleState: %s: altitude=%f" % \
                (timeStr, aircraftState.altitude)

        if self._aircraftState is None or \
           self._aircraftState.gLoad != aircraftState.gLoad:
            print "Aircraft.handleState: %s: gLoad=%f" % \
                (timeStr, aircraftState.gLoad)

        if self._aircraftState is None or \
           self._aircraftState.flapsSet != aircraftState.flapsSet:
            print "Aircraft.handleState: %s: flapsSet=%f" % \
                (timeStr, aircraftState.flapsSet)

        if self._aircraftState is None or \
           self._aircraftState.flaps != aircraftState.flaps:
            print "Aircraft.handleState: %s: flaps=%f" % \
                (timeStr, aircraftState.flaps)

        if self._aircraftState is None or \
           self._aircraftState.navLightsOn != aircraftState.navLightsOn:
            print "Aircraft.handleState: %s: navLightsOn=%d" % \
                (timeStr, aircraftState.navLightsOn)

        if self._aircraftState is None or \
           self._aircraftState.antiCollisionLightsOn != aircraftState.antiCollisionLightsOn:
            print "Aircraft.handleState: %s: antiCollisionLightsOn=%d" % \
                (timeStr, aircraftState.antiCollisionLightsOn)

        if self._aircraftState is None or \
           self._aircraftState.strobeLightsOn != aircraftState.strobeLightsOn:
            print "Aircraft.handleState: %s: strobeLightsOn=%d" % \
                (timeStr, aircraftState.strobeLightsOn)

        if self._aircraftState is None or \
           self._aircraftState.landingLightsOn != aircraftState.landingLightsOn:
            print "Aircraft.handleState: %s: landingLightsOn=%d" % \
                (timeStr, aircraftState.landingLightsOn)

        if self._aircraftState is None or \
           self._aircraftState.pitotHeatOn != aircraftState.pitotHeatOn:
            print "Aircraft.handleState: %s: pitotHeatOn=%d" % \
                (timeStr, aircraftState.pitotHeatOn)

        if self._aircraftState is None or \
           self._aircraftState.gearsDown != aircraftState.gearsDown:
            print "Aircraft.handleState: %s: gearsDown=%f" % \
                (timeStr, aircraftState.gearsDown)

        if self._aircraftState is None or \
           self._aircraftState.spoilersArmed != aircraftState.spoilersArmed:
            print "Aircraft.handleState: %s: spoilersArmed=%f" % \
                (timeStr, aircraftState.spoilersArmed)

        if self._aircraftState is None or \
           self._aircraftState.spoilersExtension != aircraftState.spoilersExtension:
            print "Aircraft.handleState: %s: spoilersExtension=%f" % \
                (timeStr, aircraftState.spoilersExtension)

        if self._aircraftState is None or \
           self._aircraftState.altimeter != aircraftState.altimeter:
            print "Aircraft.handleState: %s: altimeter=%f" % \
                (timeStr, aircraftState.altimeter)

        if self._aircraftState is None or \
           self._aircraftState.nav1 != aircraftState.nav1:
            print "Aircraft.handleState: %s: nav1=%s" % \
                (timeStr, aircraftState.nav1)

        if self._aircraftState is None or \
           self._aircraftState.nav2 != aircraftState.nav2:
            print "Aircraft.handleState: %s: nav2=%s" % \
                (timeStr, aircraftState.nav2)

        if self._aircraftState is None or \
           self._aircraftState.fuel != aircraftState.fuel:
            print "Aircraft.handleState: %s: fuel=%s" % \
                (timeStr, aircraftState.fuel)

        if self._aircraftState is None or \
           self._aircraftState.n1 != aircraftState.n1:
            print "Aircraft.handleState: %s: n1=%s" % \
                (timeStr, aircraftState.n1)

        if self._aircraftState is None or \
           self._aircraftState.reverser != aircraftState.reverser:
            print "Aircraft.handleState: %s: reverser=%s" % \
                (timeStr, aircraftState.reverser)

        self._aircraftState = aircraftState
            
#---------------------------------------------------------------------------------------

class Boeing737(Aircraft):
    """Base class for the various aircraft in the Boeing 737 family.

    The aircraft type-specific values in the aircraft state have the following
    structure:
    - fuel: centre, left, right
    - n1: left, right
    - reverser: left, right"""
    pass

#---------------------------------------------------------------------------------------

class B736(Boeing737):
    """Boeing 737-600 aircraft."""
    def __init__(self):
        super(B736, self).__init__(const.AIRCRAFT_B736)

#---------------------------------------------------------------------------------------

class B737(Boeing737):
    """Boeing 737-700 aircraft."""
    def __init__(self):
        super(B737, self).__init__(const.AIRCRAFT_B737)

#---------------------------------------------------------------------------------------

class B738(Boeing737):
    """Boeing 737-800 aircraft."""
    def __init__(self):
        super(B738, self).__init__(const.AIRCRAFT_B738)

#---------------------------------------------------------------------------------------

class B733(Boeing737):
    """Boeing 737-300 aircraft."""
    def __init__(self):
        super(B733, self).__init__(const.AIRCRAFT_B733)

#---------------------------------------------------------------------------------------

class B734(Boeing737):
    """Boeing 737-400 aircraft."""
    def __init__(self):
        super(B734, self).__init__(const.AIRCRAFT_B734)

#---------------------------------------------------------------------------------------

class B735(Boeing737):
    """Boeing 737-500 aircraft."""
    def __init__(self):
        super(B735, self).__init__(const.AIRCRAFT_B735)

#---------------------------------------------------------------------------------------

class DH8D(Aircraft):
    """Bombardier Dash-8 Q400 aircraft.

    The aircraft type-specific values in the aircraft state have the following
    structure:
    - fuel: centre, left, right
    - n1: left, right
    - reverser: left, right."""
    def __init__(self):
        super(DH8D, self).__init__(const.AIRCRAFT_DH8D)

#---------------------------------------------------------------------------------------

class Boeing767(Aircraft):
    """Base class for the various aircraft in the Boeing 767 family.

    The aircraft type-specific values in the aircraft state have the following
    structure:
    - fuel: centre, left, right
    - n1: left, right
    - reverser: left, right"""

#---------------------------------------------------------------------------------------

class B762(Boeing767):
    """Boeing 767-200 aircraft."""
    def __init__(self):
        super(B762, self).__init__(const.AIRCRAFT_B762)

#---------------------------------------------------------------------------------------

class B763(Boeing767):
    """Boeing 767-300 aircraft."""
    def __init__(self):
        super(B763, self).__init__(const.AIRCRAFT_B763)

#---------------------------------------------------------------------------------------

class CRJ2(Aircraft):
    """Bombardier CRJ-200 aircraft.

    The aircraft type-specific values in the aircraft state have the following
    structure:
    - fuel: centre, left, right
    - n1: left, right
    - reverser: left, right."""
    def __init__(self):
        super(CRJ2, self).__init__(const.AIRCRAFT_CRJ2)

#---------------------------------------------------------------------------------------

class F70(Aircraft):
    """Fokker 70 aircraft.

    The aircraft type-specific values in the aircraft state have the following
    structure:
    - fuel: centre, left, right
    - n1: left, right
    - reverser: left, right."""
    def __init__(self):
        super(F70, self).__init__(const.AIRCRAFT_F70)

#---------------------------------------------------------------------------------------

class DC3(Aircraft):
    """Lisunov Li-2 (DC-3) aircraft.

    The aircraft type-specific values in the aircraft state have the following
    structure:
    - fuel: left, right, left aux, right aix
    - rpm: left, right
    - reverser: left, right."""
    def __init__(self):
        super(DC3, self).__init__(const.AIRCRAFT_DC3)

#---------------------------------------------------------------------------------------

class T134(Aircraft):
    """Tupolev Tu-134 aircraft.

    The aircraft type-specific values in the aircraft state have the following
    structure:
    - fuel: centre, left tip, left aux, right tip, right aux, external 1,
    external 2
    - n1: left, right
    - reverser: left, right."""
    def __init__(self):
        super(T134, self).__init__(const.AIRCRAFT_T134)

#---------------------------------------------------------------------------------------

class T154(Aircraft):
    """Tupolev Tu-154 aircraft.

    The aircraft type-specific values in the aircraft state have the following
    structure:
    - fuel: centre, left, right, centre 2, left aux, right aux
    - n1: left, centre, right
    - reverser: left, right"""
    def __init__(self):
        super(T154, self).__init__(const.AIRCRAFT_T154)

#---------------------------------------------------------------------------------------

class YK40(Aircraft):
    """Yakovlev Yak-40 aircraft.

    The aircraft type-specific values in the aircraft state have the following
    structure:
    - fuel: left, right
    - n1: left, right
    - reverser: left, right"""
    def __init__(self):
        super(YK40, self).__init__(const.AIRCRAFT_YK40)

#---------------------------------------------------------------------------------------

