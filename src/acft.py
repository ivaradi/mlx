# Module for the simulator-independent aircraft classes

#---------------------------------------------------------------------------------------

import const
import checks

import time

#---------------------------------------------------------------------------------------

class Aircraft(object):
    """Base class for aircraft."""
    @staticmethod
    def create(flight):
        """Create an aircraft instance for the type in the given flight."""
        return _classes[flight.aircraftType](flight)

    def __init__(self, flight):
        """Construct the aircraft for the given type."""
        self._flight = flight
        self._aircraftState = None

        self._checkers = []

        self._checkers.append(checks.StageChecker())

        self._checkers.append(checks.AltimeterLogger())
        
        self._checkers.append(checks.NAV1Logger())
        self._checkers.append(checks.NAV2Logger())
        self._checkers.append(checks.SquawkLogger())

        self._checkers.append(checks.AnticollisionLightsLogger())
        self._checkers.append(checks.LandingLightsLogger())
        self._checkers.append(checks.StrobeLightsLogger())
        self._checkers.append(checks.NavLightsLogger())

        self._checkers.append(checks.FlapsLogger())

        self._checkers.append(checks.GearsLogger())

    @property
    def type(self):
        """Get the type of the aircraft."""
        return self._flight.aircraftType

    @property
    def flight(self):
        """Get the flight the aircraft belongs to."""
        return self._flight

    @property
    def logger(self):
        """Get the logger to use for the aircraft."""
        return self._flight.logger

    def modelChanged(self, timestamp, aircraftName, modelName):
        """Called when the simulator's aircraft changes."""
        self._flight.logger.message(timestamp,
                                    "Aircraft: name='%s', model='%s'" % \
                                    (aircraftName, modelName))

    def handleState(self, aircraftState):
        """Called when the state of the aircraft changes."""
        for checker in self._checkers:
            checker.check(self._flight, self, self._flight.logger,
                          self._aircraftState, aircraftState)

        self._aircraftState = aircraftState
    
    def setStage(self, aircraftState, newStage):
        """Set the given stage as the new one and do whatever should be
        done."""
        self._flight.setStage(aircraftState.timestamp, newStage)

    def flare(self):
        """Called when it is detected that we are during flare.

        On the first call, it should start monitoring some parameters more
        closely to determine flare time."""
        pass

    def cancelFlare(self):
        """Cancel flare, if it has started."""
        pass

    def checkFlightEnd(self, aircraftState):
        """Check if the end of the flight has arrived.

        This default implementation checks the N1 values, but for
        piston-powered aircraft you need to check the RPMs."""
        for n1 in aircraftState.n1:
            if n1>=0.5: return False
        return True

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
    def __init__(self, flight):
        super(B736, self).__init__(flight)

#---------------------------------------------------------------------------------------

class B737(Boeing737):
    """Boeing 737-700 aircraft."""
    def __init__(self, flight):
        super(B737, self).__init__(flight)

#---------------------------------------------------------------------------------------

class B738(Boeing737):
    """Boeing 737-800 aircraft."""
    def __init__(self, flight):
        super(B738, self).__init__(flight)

#---------------------------------------------------------------------------------------

class B733(Boeing737):
    """Boeing 737-300 aircraft."""
    def __init__(self, flight):
        super(B733, self).__init__(flight)

#---------------------------------------------------------------------------------------

class B734(Boeing737):
    """Boeing 737-400 aircraft."""
    def __init__(self, flight):
        super(B734, self).__init__(flight)

#---------------------------------------------------------------------------------------

class B735(Boeing737):
    """Boeing 737-500 aircraft."""
    def __init__(self, flight):
        super(B735, self).__init__(flight)

#---------------------------------------------------------------------------------------

class DH8D(Aircraft):
    """Bombardier Dash-8 Q400 aircraft.

    The aircraft type-specific values in the aircraft state have the following
    structure:
    - fuel: centre, left, right
    - n1: left, right
    - reverser: left, right."""
    def __init__(self, flight):
        super(DH8D, self).__init__(flight)

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
    def __init__(self, flight):
        super(B762, self).__init__(flight)

#---------------------------------------------------------------------------------------

class B763(Boeing767):
    """Boeing 767-300 aircraft."""
    def __init__(self, flight):
        super(B763, self).__init__(cflight)

#---------------------------------------------------------------------------------------

class CRJ2(Aircraft):
    """Bombardier CRJ-200 aircraft.

    The aircraft type-specific values in the aircraft state have the following
    structure:
    - fuel: centre, left, right
    - n1: left, right
    - reverser: left, right."""
    def __init__(self, flight):
        super(CRJ2, self).__init__(flight)

#---------------------------------------------------------------------------------------

class F70(Aircraft):
    """Fokker 70 aircraft.

    The aircraft type-specific values in the aircraft state have the following
    structure:
    - fuel: centre, left, right
    - n1: left, right
    - reverser: left, right."""
    def __init__(self, flight):
        super(F70, self).__init__(flight)

#---------------------------------------------------------------------------------------

class DC3(Aircraft):
    """Lisunov Li-2 (DC-3) aircraft.

    The aircraft type-specific values in the aircraft state have the following
    structure:
    - fuel: left, right, left aux, right aix
    - rpm: left, right
    - reverser: left, right."""
    def __init__(self, flight):
        super(DC3, self).__init__(flight)

    def _checkFlightEnd(self, aircraftState):
        """Check if the end of the flight has arrived.

        This implementation checks the RPM values to be 0."""
        for rpm in aircraftState.rpm:
            if rpm>0: return
        self._setStage(aircraftState, const.STAGE_END)

#---------------------------------------------------------------------------------------

class T134(Aircraft):
    """Tupolev Tu-134 aircraft.

    The aircraft type-specific values in the aircraft state have the following
    structure:
    - fuel: centre, left tip, left aux, right tip, right aux, external 1,
    external 2
    - n1: left, right
    - reverser: left, right."""
    def __init__(self, flight):
        super(T134, self).__init__(flight)

#---------------------------------------------------------------------------------------

class T154(Aircraft):
    """Tupolev Tu-154 aircraft.

    The aircraft type-specific values in the aircraft state have the following
    structure:
    - fuel: centre, left, right, centre 2, left aux, right aux
    - n1: left, centre, right
    - reverser: left, right"""
    def __init__(self, flight):
        super(T154, self).__init__(flight)

#---------------------------------------------------------------------------------------

class YK40(Aircraft):
    """Yakovlev Yak-40 aircraft.

    The aircraft type-specific values in the aircraft state have the following
    structure:
    - fuel: left, right
    - n1: left, right
    - reverser: left, right"""
    def __init__(self, flight):
        super(YK40, self).__init__(flight)

#---------------------------------------------------------------------------------------

_classes = { const.AIRCRAFT_B736 : B736,
             const.AIRCRAFT_B737 : B737,
             const.AIRCRAFT_B738 : B738,
             const.AIRCRAFT_B733 : B733,
             const.AIRCRAFT_B734 : B734,
             const.AIRCRAFT_B735 : B735,
             const.AIRCRAFT_DH8D : DH8D,
             const.AIRCRAFT_B762 : B762,
             const.AIRCRAFT_B763 : B763,
             const.AIRCRAFT_CRJ2 : CRJ2,
             const.AIRCRAFT_F70 : F70,
             const.AIRCRAFT_DC3 : DC3,
             const.AIRCRAFT_T134 : T134,
             const.AIRCRAFT_T154 : T154,
             const.AIRCRAFT_YK40 : YK40 }

#---------------------------------------------------------------------------------------
