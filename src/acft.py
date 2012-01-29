# Module for the simulator-independent aircraft classes

#---------------------------------------------------------------------------------------

import time

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
           self._aircraftState.vs != aircraftState.vs:
            print "Aircraft.handleState: %s: vs=%f" % \
                (timeStr, aircraftState.vs)

        if self._aircraftState is None or \
           self._aircraftState.altitude != aircraftState.altitude:
            print "Aircraft.handleState: %s: altitude=%f" % \
                (timeStr, aircraftState.altitude)

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

        self._aircraftState = aircraftState
            
#---------------------------------------------------------------------------------------
            
