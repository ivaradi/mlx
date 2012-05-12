# Module to schedule the sounds to be played

#------------------------------------------------------------------------------

from sound import startSound
import const

import threading

#------------------------------------------------------------------------------

class Sound(object):
    """A sound (file) that should be played in certain circumstances."""

    # Common lock for sounds
    _lock = threading.Lock()

    def __init__(self, name):
        """Construct the sound object for the sound file with the given
        name."""
        self._name = name
        
        self._playing = 0

    @property
    def playing(self):
        """Determine if sound is playing or not."""
        return self._playing>0

    def check(self, flight, state, pilotHotkeyPressed):
        """Check if the file should be played, and if it should be, play it."""
        if self.shouldPlay(flight, state, pilotHotkeyPressed):
            with Sound._lock:
                self._playing += 1
            startSound(self._name, finishCallback = self._playbackDone)

    def shouldPlay(self, flight, state, pilotHotkeyPressed):
        """Determine if the sound should be played.

        This default implementation returns False."""
        return False

    def _playbackDone(self, success, extra):
        """Called when the playback of thee sound has finished (or failed)."""
        if success is None:
            print "Failed to start sound", self._name
        elif not success:
            print "Failed to finish sound", self._name
        with Sound._lock:            
            self._playing -= 1

#------------------------------------------------------------------------------

class ScreamSound(Sound):
    """A screaming sound that is played under certain circumstance."""
    def __init__(self):
        """Construct the screaming sound."""
        super(ScreamSound, self).__init__(const.SOUND_SCREAM)

    def shouldPlay(self, flight, state, pilotHotkeyPressed):
        """Determine if the sound should be played.

        It should be played if it is not being played and the absolute value of
        the vertical speed is greater than 6000 fpm."""
        return not self.playing and abs(state.vs)>6000        

#------------------------------------------------------------------------------

class SimpleSound(Sound):
    """A simple sound that should be played only once, in a certain flight
    stage when the hotkey has been pressed or it is not the pilot who controls
    the sounds.

    If it is not the pilot who controls the sounds, it may be delayed relative
    to the first detection of a certain flight stage."""
    def __init__(self, name, stage, delay = 0.0, extraCondition = None,
                 considerHotkey = True, previousSound = None):
        """Construct the simple sound."""
        super(SimpleSound, self).__init__(name)
        
        self._stage = stage
        self._delay = delay
        self._extraCondition = extraCondition
        self._considerHotkey = considerHotkey
        self._previousSound = previousSound

        self._played = False
        self._stageDetectionTime = None

    def shouldPlay(self, flight, state, pilotHotkeyPressed):
        """Determine if the sound should be played."""
        if flight.stage!=self._stage or self._played or \
           (self._previousSound is not None and
            self._previousSound.playing):
            return False

        toPlay = False
        if flight.config.pilotControlsSounds and self._considerHotkey:
            toPlay = pilotHotkeyPressed
        else:
            if self._stageDetectionTime is None:
                self._stageDetectionTime = state.timestamp
            toPlay = state.timestamp>=(self._stageDetectionTime + self._delay)
            if toPlay and self._extraCondition is not None:
                toPlay = self._extraCondition(flight, state)

        if toPlay:
            self._played = True

        return toPlay

#------------------------------------------------------------------------------

class TaxiSound(SimpleSound):
    """The taxi sound.

    It first plays the Malev theme song, then an aircraft-specific taxi
    sound. The playback is started only, if the boarding sound is not being
    played."""

    _sounds = { const.AIRCRAFT_B736 : const.SOUND_TAXI_BOEING737NG,
                const.AIRCRAFT_B737 : const.SOUND_TAXI_BOEING737NG,
                const.AIRCRAFT_B738 : const.SOUND_TAXI_BOEING737NG,
                const.AIRCRAFT_B762 : const.SOUND_TAXI_BOEING767,
                const.AIRCRAFT_B763 : const.SOUND_TAXI_BOEING767,
                const.AIRCRAFT_F70  : const.SOUND_TAXI_F70 }
                    
    def __init__(self, flight, boardingSound = None):
        """Construct the taxi sound."""
        super(TaxiSound, self).__init__(const.SOUND_MALEV,
                                        const.STAGE_PUSHANDTAXI,
                                        previousSound = boardingSound,
                                        extraCondition = lambda _flight, state:
                                        state.groundSpeed>5)

        self._flight = flight

    def _playbackDone(self, success, extra):
        """Called when the playback is done.

        It starts playing the aircraft type-specific taxi sound, if any."""
        super(TaxiSound, self)._playbackDone(success, extra)
        aircraftType = self._flight.aircraftType
        sounds = TaxiSound._sounds
        if aircraftType in sounds:
            startSound(sounds[aircraftType])

#------------------------------------------------------------------------------

class TouchdownApplause(Sound):
    """An applause sound that is played after a gentle touchdown."""
    def __init__(self):
        super(TouchdownApplause, self).__init__(const.SOUND_APPLAUSE)

        self._touchdownTime = None
        self._played = False
        
    def shouldPlay(self, flight, state, pilotHotkeyPressed):
        """Determine if the sound should be played.

        It should be played if we are 2 seconds after a gentle touchdown."""
        if self._played or flight.tdRate is None:
            return False

        if self._touchdownTime is None:
            self._touchdownTime = state.timestamp

        if state.timestamp>=(self._touchdownTime + 2) and \
           flight.tdRate<150:
            self._played = True
            return True
        else:
            return False
        
#------------------------------------------------------------------------------

class SoundScheduler(object):
    """A scheduler for the sounds."""
    def __init__(self, flight):
        """Construct the sound scheduler for the given flight."""
        self._flight = flight
        self._sounds = []

        self._sounds.append(ScreamSound())

        boardingSound = SimpleSound(const.SOUND_BOARDING,
                                    const.STAGE_BOARDING,
                                    delay = 10.0)
        self._sounds.append(boardingSound)
        self._sounds.append(TaxiSound(flight, boardingSound))
        self._sounds.append(SimpleSound(const.SOUND_CAPTAIN_TAKEOFF,
                                        const.STAGE_TAKEOFF,
                                        extraCondition = lambda flight, state:
                                        state.landingLightsOn or state.gs>80,
                                        considerHotkey = False))
        self._sounds.append(SimpleSound(const.SOUND_CRUISE, const.STAGE_CRUISE))
        self._sounds.append(SimpleSound(const.SOUND_DESCENT, const.STAGE_DESCENT,
                                        extraCondition = lambda flight, state:
                                        state.altitude<15000))
        self._sounds.append(TouchdownApplause())
        self._sounds.append(SimpleSound(const.SOUND_TAXIAFTERLAND,
                                        const.STAGE_TAXIAFTERLAND,
                                        delay = 10.0))

    def schedule(self, state, pilotHotkeyPressed):
        """Schedule any sound, if needed."""
        flight = self._flight
        if flight.config.enableSounds:
            for sound in self._sounds:
                sound.check(flight, state, pilotHotkeyPressed)

#------------------------------------------------------------------------------
