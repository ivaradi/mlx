
 Notes:

 * In case of values that are toggles (on/off, etc.), use only the bit that changes for sure, because other bits may be related to different things.    

## General

 * 0x7b91: transponder mode C/standby (bit 0: 1/0)

## PMDG 737 NG

 * 0x6202: bit 0 is the STD button state: 1 means the button is pressed
 * 0x6216: the values of the transponder settings: 1: standby, 2: XPDR, 3: TA, 4: TA/RA
 * 0x6227: autopilot on (2)/off (0)
 * 0x6228: heading mode: 2: HDG SEL
 * 0x622a: pitch mode: 4: alt hold, 3: VNAV
 * 0x622c (U16): AP heading
 * 0x622e (U16): AP altitude

More information is here: http://forum.pl-vacc.org/viewtopic.php?f=68&t=20948

## Dash 8-Q400
 
 * The N1 values at 0x0898, etc. are incorrect, use the values starting at 0x2000. Perhaps use it for all aircraft with turbines?