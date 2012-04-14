# Various constants used in the logger

#-------------------------------------------------------------------------------

# The version of the program
VERSION="0.005"

#-------------------------------------------------------------------------------

# The ratio between lbs and kg
LBSTOKG=0.4536

# The ratio between kgs and lbs
KGSTOLB=1/LBSTOKG

# The ratio between feet and metre
FEETTOMETRES=0.3048

#-------------------------------------------------------------------------------

# Flight simulator type: MS Flight Simulator 2004
SIM_MSFS9 = 1

# Flight simulator type: MS Flight Simulator X
SIM_MSFSX = 2

# Flight simulator type: X-Plane 9
SIM_XPLANE9 = 3

# Flight simulator type: X-Plane 10
SIM_XPLANE10 = 4

#-------------------------------------------------------------------------------

# Aircraft type: Boeing 737-600
AIRCRAFT_B736 = 1

# Aircraft type: Boeing 737-700
AIRCRAFT_B737 = 2

# Aircraft type: Boeing 737-800
AIRCRAFT_B738 = 3

# Aircraft type: Boeing 737-300
AIRCRAFT_B733 = 4

# Aircraft type: Boeing 737-400
AIRCRAFT_B734 = 5

# Aircraft type: Boeing 737-500
AIRCRAFT_B735 = 6

# Aircraft type: Dash-8 Q400
AIRCRAFT_DH8D = 7

# Aircraft type: Boeing 767-200
AIRCRAFT_B762 = 8

# Aircraft type: Boeing 767-300
AIRCRAFT_B763 = 9

# Aircraft type: Canadair CRJ-200
AIRCRAFT_CRJ2 = 10

# Aircraft type: Fokker F-70
AIRCRAFT_F70 = 11

# Aircraft type: Lisunov Li-2
AIRCRAFT_DC3 = 12

# Aircraft type: Tupolev Tu-134
AIRCRAFT_T134 = 13

# Aircraft type: Tupolev Tu-154
AIRCRAFT_T154 = 14

# Aircraft type: Yakovlev Yak-40
AIRCRAFT_YK40 = 15

#-------------------------------------------------------------------------------

# Flight stage: boarding
STAGE_BOARDING = 1

# Flight stage: pushback, startup and taxi
STAGE_PUSHANDTAXI = 2

# Flight stage: takeoff
STAGE_TAKEOFF = 3

# Flight stage: RTO
STAGE_RTO = 4

# Flight stage: climb
STAGE_CLIMB = 5

# Flight stage: cruise
STAGE_CRUISE = 6

# Flight stage: descent
STAGE_DESCENT = 7

# Flight stage: landing
STAGE_LANDING = 8

# Flight stage: taxi after landing
STAGE_TAXIAFTERLAND = 9

# Flight stage: parking
STAGE_PARKING = 10

# Flight stage: go-around
STAGE_GOAROUND = 11

# Flight stage: end
STAGE_END = 12

#-------------------------------------------------------------------------------

# Plane status: unknown
PLANE_UNKNOWN = 0

# Plane status: at home, i.e. LHBP
PLANE_HOME = 1

# Plane status: away
PLANE_AWAY = 2

# Plane status: parking
PLANE_PARKING = 3

#-------------------------------------------------------------------------------

# The available gates at LHBP
lhbpGateNumbers = []

for i in range(1, 7):
    lhbpGateNumbers.append(str(i))

for i in range(10, 19):
    lhbpGateNumbers.append(str(i))

for i in range(24, 28):
    lhbpGateNumbers.append(str(i))

for i in range(31, 39):
    lhbpGateNumbers.append(str(i))

for i in range(42, 47):
    lhbpGateNumbers.append(str(i))

for i in range(60, 84):
    if i!=70 and i!=80:
        lhbpGateNumbers.append(str(i))

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
        
    
