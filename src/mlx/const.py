
import sys

#-------------------------------------------------------------------------------

## @package mlx.const
#
# The constants used by the program.

#-------------------------------------------------------------------------------

## The version of the program
VERSION="0.33"

#-------------------------------------------------------------------------------

## The ratio between lbs and kg
LBSTOKG=0.4536

## The ratio between kgs and lbs
KGSTOLB=1/LBSTOKG

## The ratio between feet and metre
FEETTOMETRES=0.3048

#-------------------------------------------------------------------------------

## The ratio between knots and km/h
KNOTSTOKMPH=1.852

## The ratio between km/h and knots
KMPHTOKNOTS=1/1.852

#-------------------------------------------------------------------------------

## Flight simulator type: MS Flight Simulator 2004
SIM_MSFS9 = 1

## Flight simulator type: MS Flight Simulator X
SIM_MSFSX = 2

## Flight simulator type: X-Plane 9
SIM_XPLANE9 = 3

## Flight simulator type: X-Plane 10
SIM_XPLANE10 = 4

#-------------------------------------------------------------------------------

## Aircraft type: Boeing 737-600
AIRCRAFT_B736 = 1

## Aircraft type: Boeing 737-700
AIRCRAFT_B737 = 2

## Aircraft type: Boeing 737-800
AIRCRAFT_B738 = 3

## Aircraft type: Boeing 737-800 (charter configuration)
AIRCRAFT_B738C = 16

## Aircraft type: Boeing 737-300
AIRCRAFT_B733 = 4

## Aircraft type: Boeing 737-400
AIRCRAFT_B734 = 5

## Aircraft type: Boeing 737-500
AIRCRAFT_B735 = 6

## Aircraft type: Dash-8 Q400
AIRCRAFT_DH8D = 7

## Aircraft type: Boeing 767-200
AIRCRAFT_B762 = 8

## Aircraft type: Boeing 767-300
AIRCRAFT_B763 = 9

## Aircraft type: Canadair CRJ-200
AIRCRAFT_CRJ2 = 10

## Aircraft type: Fokker F-70
AIRCRAFT_F70 = 11

## Aircraft type: Lisunov Li-2
AIRCRAFT_DC3 = 12

## Aircraft type: Tupolev Tu-134
AIRCRAFT_T134 = 13

## Aircraft type: Tupolev Tu-154
AIRCRAFT_T154 = 14

## Aircraft type: Yakovlev Yak-40
AIRCRAFT_YK40 = 15

## Aircraft type: British Aerospace BAe-146
AIRCRAFT_B462 = 17

#-------------------------------------------------------------------------------

## The list of aircraft types that we know of
# The order is mostly from most recent to oldest considering
# Malev's history
aircraftTypes = [AIRCRAFT_B736, AIRCRAFT_B737,
                 AIRCRAFT_B738, AIRCRAFT_B738C,
                 AIRCRAFT_DH8D,
                 AIRCRAFT_F70, AIRCRAFT_CRJ2,
                 AIRCRAFT_B762, AIRCRAFT_B763,
                 AIRCRAFT_B733, AIRCRAFT_B734, AIRCRAFT_B735,
                 AIRCRAFT_T154, AIRCRAFT_T134,
                 AIRCRAFT_YK40, AIRCRAFT_DC3,
                 AIRCRAFT_B462]

#-------------------------------------------------------------------------------

## A mapping of aircraft types to their 'internal' ICAO codes (which are
# the same as the real ICAO codes, except in a few cases)
icaoCodes = { AIRCRAFT_B736  : "B736",
              AIRCRAFT_B737  : "B737",
              AIRCRAFT_B738  : "B738",
              AIRCRAFT_B738C : "B738C",
              AIRCRAFT_B733  : "B733",
              AIRCRAFT_B734  : "B734",
              AIRCRAFT_B735  : "B735",
              AIRCRAFT_DH8D  : "DH8D",
              AIRCRAFT_B762  : "B762",
              AIRCRAFT_B763  : "B763",
              AIRCRAFT_CRJ2  : "CRJ2",
              AIRCRAFT_F70   : "F70",
              AIRCRAFT_DC3   : "DC3",
              AIRCRAFT_T134  : "T134",
              AIRCRAFT_T154  : "T154",
              AIRCRAFT_YK40  : "YK40",
              AIRCRAFT_B462  : "B462" }

#-------------------------------------------------------------------------------

## Flight stage: boarding
STAGE_BOARDING = 1

## Flight stage: pushback, startup and taxi
STAGE_PUSHANDTAXI = 2

## Flight stage: takeoff
STAGE_TAKEOFF = 3

## Flight stage: RTO
STAGE_RTO = 4

## Flight stage: climb
STAGE_CLIMB = 5

## Flight stage: cruise
STAGE_CRUISE = 6

## Flight stage: descent
STAGE_DESCENT = 7

## Flight stage: landing
STAGE_LANDING = 8

## Flight stage: taxi after landing
STAGE_TAXIAFTERLAND = 9

## Flight stage: parking
STAGE_PARKING = 10

## Flight stage: go-around
STAGE_GOAROUND = 11

## Flight stage: end
STAGE_END = 12

#-------------------------------------------------------------------------------

_stageStrings = { STAGE_BOARDING : "boarding",
                  STAGE_PUSHANDTAXI : "pushback and taxi",
                  STAGE_TAKEOFF : "takeoff",
                  STAGE_RTO : "RTO",
                  STAGE_CLIMB : "climb",
                  STAGE_CRUISE : "cruise",
                  STAGE_DESCENT : "descent",
                  STAGE_LANDING : "landing",
                  STAGE_TAXIAFTERLAND : "taxi",
                  STAGE_PARKING : "parking",
                  STAGE_GOAROUND : "go-around",
                  STAGE_END : "end" }

def stage2string(stage):
    """Convert the given stage to a lower-case string."""
    return _stageStrings[stage] if stage in _stageStrings else None

#-------------------------------------------------------------------------------

## Plane status: unknown
PLANE_UNKNOWN = 0

## Plane status: at home, i.e. LHBP
PLANE_HOME = 1

## Plane status: away
PLANE_AWAY = 2

## Plane status: parking
PLANE_PARKING = 3

#-------------------------------------------------------------------------------

## Flight type: scheduled
FLIGHTTYPE_SCHEDULED = 0

## Flight type: old-timer
FLIGHTTYPE_OLDTIMER = 1

## Flight type: VIP
FLIGHTTYPE_VIP = 2

## Flight type: charter
FLIGHTTYPE_CHARTER = 3

#-------------------------------------------------------------------------------

flightTypes = [ FLIGHTTYPE_SCHEDULED,
                FLIGHTTYPE_OLDTIMER,
                FLIGHTTYPE_VIP,
                FLIGHTTYPE_CHARTER ]

#-------------------------------------------------------------------------------

_flightTypeStrings = { FLIGHTTYPE_SCHEDULED : "scheduled",
                       FLIGHTTYPE_OLDTIMER : "ot",
                       FLIGHTTYPE_VIP : "vip",
                       FLIGHTTYPE_CHARTER : "charter" }

def flightType2string(flightType):
    """Get the string equivalent of the given flight type."""
    return _flightTypeStrings[flightType] \
           if flightType in _flightTypeStrings else None

#-------------------------------------------------------------------------------

## Message type: logger error
# FIXME: cannot set the hotkey
MESSAGETYPE_LOGGER_ERROR = 1

## Message type: information
MESSAGETYPE_INFORMATION = 2

## Message type: in-flight information
MESSAGETYPE_INFLIGHT = 3

## Message type: fault messages
MESSAGETYPE_FAULT = 4

## Message type: NO-GO fault messages
MESSAGETYPE_NOGO = 5

## Message type: gate system messages
MESSAGETYPE_GATE_SYSTEM = 6

## Message type: environment messages
# FIXME: flight plan closed (5 sec)
MESSAGETYPE_ENVIRONMENT = 7

## Message type: help messages
MESSAGETYPE_HELP = 8

## Message type: visibility messages
MESSAGETYPE_VISIBILITY = 9

#-------------------------------------------------------------------------------

messageTypes = [ MESSAGETYPE_LOGGER_ERROR,
                 MESSAGETYPE_INFORMATION,
                 MESSAGETYPE_INFLIGHT,
                 MESSAGETYPE_FAULT,
                 MESSAGETYPE_NOGO,
                 MESSAGETYPE_GATE_SYSTEM,
                 MESSAGETYPE_ENVIRONMENT,
                 MESSAGETYPE_HELP,
                 MESSAGETYPE_VISIBILITY ]

#-------------------------------------------------------------------------------

_messageTypeStrings = { MESSAGETYPE_LOGGER_ERROR : "loggerError",
                        MESSAGETYPE_INFORMATION : "information",
                        MESSAGETYPE_INFLIGHT : "inflight",
                        MESSAGETYPE_FAULT : "fault",
                        MESSAGETYPE_NOGO : "nogo",
                        MESSAGETYPE_GATE_SYSTEM : "gateSystem",
                        MESSAGETYPE_ENVIRONMENT : "environment",
                        MESSAGETYPE_HELP : "help",
                        MESSAGETYPE_VISIBILITY : "visibility" }

def messageType2string(messageType):
    """Get the string equivalent of the given message type."""
    return _messageTypeStrings[messageType] \
           if messageType in _messageTypeStrings else None

#-------------------------------------------------------------------------------

## Message display level: none
MESSAGELEVEL_NONE = 0

## Message display level: only message in the simulator
MESSAGELEVEL_FS = 1

## Message display level: only sound
MESSAGELEVEL_SOUND = 2

## Message display level: both
MESSAGELEVEL_BOTH = 3

#-------------------------------------------------------------------------------

messageLevels = [ MESSAGELEVEL_NONE,
                  MESSAGELEVEL_FS,
                  MESSAGELEVEL_SOUND,
                  MESSAGELEVEL_BOTH ]

#-------------------------------------------------------------------------------

_messageLevelStrings = { MESSAGELEVEL_NONE : "none",
                         MESSAGELEVEL_FS : "fs",
                         MESSAGELEVEL_SOUND : "sound",
                         MESSAGELEVEL_BOTH : "both" }

def messageLevel2string(messageLevel):
    """Get the string equivalent of the given message level."""
    return _messageLevelStrings[messageLevel] \
           if messageLevel in _messageLevelStrings else None

def string2messageLevel(str):
    """Get the message level for the given string."""
    for (value, s) in _messageLevelStrings.iteritems():
        if str==s:
            return value
    return MESSAGELEVEL_NONE

#-------------------------------------------------------------------------------

## Sound: ding
SOUND_DING = "ding.wav"

## Sound: notify
SOUND_NOTIFY = "notify.wav"

## Sound: NOTAM
SOUND_NOTAM = "notam.mp3"

## Sound: scream
SOUND_SCREAM = "sikoly.mp3"

## Sound: boarding
SOUND_BOARDING = "board.mp3"

## Sound: Malev theme
SOUND_MALEV = "malev.mp3"

## Sound: taxi: Boeing 737 NG
SOUND_TAXI_BOEING737NG = "737taxi.mp3"

## Sound: taxi: Boeing 767
SOUND_TAXI_BOEING767 = "767taxi.mp3"

## Sound: taxi: Fokker F70
SOUND_TAXI_F70 = "F70taxi.mp3"

## Sound: takeoff preparation request from the captain
SOUND_CAPTAIN_TAKEOFF = "cpt_takeoff.mp3"

## Sound: cruise
SOUND_CRUISE = "TOC.mp3"

## Sound: descent
SOUND_DESCENT = "TOD.mp3"

## Sound: applause
SOUND_APPLAUSE = "taps.mp3"

## Sound: speedbrake
SOUND_SPEEDBRAKE = "speed.mp3"

## Sound: taxi after landing
SOUND_TAXIAFTERLAND = "TaxiAfterLand.mp3"


#-------------------------------------------------------------------------------

## Fuel tank: centre
FUELTANK_CENTRE = 1

## Fuel tank: left
FUELTANK_LEFT = 2

## Fuel tank: right
FUELTANK_RIGHT = 3

## Fuel tank: left aux
FUELTANK_LEFT_AUX = 4

## Fuel tank: right aux
FUELTANK_RIGHT_AUX = 5

## Fuel tank: left tip
FUELTANK_LEFT_TIP = 6

## Fuel tank: right tip
FUELTANK_RIGHT_TIP = 7

## Fuel tank: external 1
FUELTANK_EXTERNAL1 = 8

## Fuel tank: external 2
FUELTANK_EXTERNAL2 = 9

## Fuel tank: centre2
FUELTANK_CENTRE2 = 10

#-------------------------------------------------------------------------------

fuelTanks = [ FUELTANK_CENTRE,
              FUELTANK_LEFT,
              FUELTANK_RIGHT,
              FUELTANK_LEFT_AUX,
              FUELTANK_RIGHT_AUX,
              FUELTANK_LEFT_TIP,
              FUELTANK_RIGHT_TIP,
              FUELTANK_EXTERNAL1,
              FUELTANK_EXTERNAL2,
              FUELTANK_CENTRE2 ]

#-------------------------------------------------------------------------------

_fuelTankStrings = { FUELTANK_CENTRE : "centre",
                     FUELTANK_LEFT : "left",
                     FUELTANK_RIGHT : "right",
                     FUELTANK_LEFT_AUX : "left_aux",
                     FUELTANK_RIGHT_AUX : "right_aux",
                     FUELTANK_LEFT_TIP : "left_tip",
                     FUELTANK_RIGHT_TIP : "right_tip",
                     FUELTANK_EXTERNAL1 : "external1",
                     FUELTANK_EXTERNAL2 : "external2",
                     FUELTANK_CENTRE2 : "centre2" }

def fuelTank2string(fuelTank):
    """Get the string equivalent of the given fuelTank."""
    return _fuelTankStrings[fuelTank] \
           if fuelTank in _fuelTankStrings else None

#-------------------------------------------------------------------------------

_fuelTankLogStrings = { FUELTANK_CENTRE : "centre",
                        FUELTANK_LEFT : "left",
                        FUELTANK_RIGHT : "right",
                        FUELTANK_LEFT_AUX : "left aux",
                        FUELTANK_RIGHT_AUX : "right aux",
                        FUELTANK_LEFT_TIP : "left tip",
                        FUELTANK_RIGHT_TIP : "right tip",
                        FUELTANK_EXTERNAL1 : "external 1",
                        FUELTANK_EXTERNAL2 : "external 2",
                        FUELTANK_CENTRE2 : "centre 2" }

def fuelTank2logString(fuelTank):
    """Get the log string equivalent of the given fuelTank."""
    return _fuelTankLogStrings[fuelTank] \
        if fuelTank in _fuelTankLogStrings else "unknown"

#-------------------------------------------------------------------------------

languages = ["$system", "en_GB", "hu_HU"]

#-------------------------------------------------------------------------------
