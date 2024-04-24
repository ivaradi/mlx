#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Script that generates the delay code data files from a common data base
#
# It generates the following files:
# - src/mlx/gui/dcdata.py: a Python module that contains the data structures
#   describing the delay code information for each aircraft type.
# - locale/en/mlx_delay.po, local/hu/mlx_delay.po: PO files containing the
#   delay code texts. Those texts are referred to from dcdata.py

#----------------------------------------------------------------------------

import os

#----------------------------------------------------------------------------

# The list of language codes. The strings should be arrays of at least this
# length
languageCodes = ["en", "hu"]

#----------------------------------------------------------------------------

# Row type: a caption
CAPTION = 1

# Row type: an actual delay code
DELAYCODE = 2

# Row type: an actual delay code requiring a textual explanation
DELAYCODE_EXPLANATION_REQUIRED = 3

#----------------------------------------------------------------------------

# Prefixes for the generated tables
tablePrefixes = [ "common" ]

# Type groups
typeGroups = [ ["B736", "B737", "B738", "B738C", "B733", "B734", "B735",
                "DH8D", "B762", "B763", "CRJ2", "F70", "B462",
                "DC3", "T134", "T154", "YK40"] ]

#----------------------------------------------------------------------------

# The associated row or column is for the common case
FOR_COMMON = 1

#----------------------------------------------------------------------------

# The complete delay code table
table = (("info_delay_",
          "lambda row: row[0].strip()"),
         [ ["MA", "MA"], ["IATA", "IATA"],
           ["Name", "Név"],["Description", "Leírás" ] ],
         [ FOR_COMMON, FOR_COMMON, FOR_COMMON, FOR_COMMON ],
         [ (CAPTION, FOR_COMMON,
            ["Others", "Egyebek"] ),
           (DELAYCODE, FOR_COMMON,
            ["061", ("06", "OA"),
             ["NO GATES/STAND AVAILABLE", "NINCS SZABAD KAPU/ÁLLÓHELY"],
             ["Due to own airline activity",
              "Saját tevékenység miatt"]]),
           (DELAYCODE, FOR_COMMON,
            ["091", ("09", "SG"),
             ["SCHEDULED GROUND TIME", "ÜTEMEZETT FORDULÓ IDŐ"],
             ["Planned turnaround time less than declared minimum",
              "A tervezett forduló idő rövidebb a minimálisnál"]]),

           (CAPTION, FOR_COMMON,
            ["Passenger and baggage",
             "Utas és poggyászkezelés"] ),
           (DELAYCODE, FOR_COMMON,
            ["111", ("11", "PD"),
             ["LATE CHECK-IN", "KÉSEI JEGYKEZELÉS"],
             ["Check-in reopened for late passengers",
              "Check-in járatzárás után"]]),
           (DELAYCODE, FOR_COMMON,
            ["121", ("12", "PL"),
             ["LATE CHECK-IN", "KÉSEI JEGYKEZELÉS"],
             ["Check-in not completed by flight closure time",
              "Torlódás az indulási csarnokban"]]),
           (DELAYCODE, FOR_COMMON,
            ["132", ("13", "PE"),
             ["CHECK-IN ERROR", "JEGYKEZELÉSI HIBA"],
             ["Error with passenger or baggage details",
              "Téves utas és poggyászfelvétel"]]),
           (DELAYCODE, FOR_COMMON,
            ["142", ("14", "PO"),
             ["OVERSALES", "TÚLKÖNYVELÉS"],
             ["Booking errors – not resolved at check-in",
              "Téves könyvelés, a jegykezelés során nem megoldott"]]),
           (DELAYCODE, FOR_COMMON,
            ["151", ("15", "PH"),
             ["BOARDING", "BESZÁLLÍTÁS"],
             ["Boarding discrepancies due to the passenger's fault",
              "Beszállítási rendellenesség utas hibájából"]]),
           (DELAYCODE, FOR_COMMON,
            ["152", ("15", "PH"),
             ["BOARDING", "BESZÁLLÍTÁS"],
             ["Boarding discrepancies due to the tranzit's fault",
              "Beszállítási rendellenesség tranzit hibájából"]]),
           (DELAYCODE, FOR_COMMON,
            ["161", ("16", "PS"),
             ["COMMERCIAL PUBLICITY/\nPASSENGER CONVENIENCE",
              "NYILVÁNOS FOGADÁS/\nUTASKÉNYELMI SZEMPONTOK"],
             ["Local decision to delay for VIP or press; \ndelay due to offload of passengers following family bereavement",
              "Késleltetés helyi döntés alapján reptérzár,\nbetegség/halál, VIP, sajtó, TV miatt"]]),
           (DELAYCODE, FOR_COMMON,
            ["171", ("17", "PC"),
             ["CATERING ORDER", "CATERING MEGRENDELÉS"],
             ["Late or incorrect order given to supplier",
              "Kései vagy téves megrendelés leadása a szállítónak"]]),
           (DELAYCODE, FOR_COMMON,
            ["172", ("17", "PC"),
             ["CATERING ORDER", "CATERING MEGRENDELÉS"],
             ["Late catering order due to negligence",
              "Kései catering megrendelés gondatlanságból"]]),
           (DELAYCODE, FOR_COMMON,
            ["181", ("18", "PD"),
             ["BAGGAGE PROCESSING", "POGGYÁSZKEZELÉS"],
             ["Late or incorrectly sorted baggage",
              "Késő vagy tévesen szortírozott poggyász"]]),

           (CAPTION, FOR_COMMON,
            ["Cargo and mail",
             "Áru és postakezelés"] ),
           (DELAYCODE, FOR_COMMON,
            ["212", ("21", "CD"),
             ["DOCUMENTATION", "DOKUMENTÁCIÓ"],
             ["Late or incorrect documentation for booked cargo",
              "Hibás vagy kései áruokmányolás"]]),
           (DELAYCODE, FOR_COMMON,
            ["221", ("22", "CP"),
             ["LATE POSITIONING", "KÉSEI SZÁLLÍTÁS"],
             ["Late delivery of booked cargo to airport/aircraft",
              "Szállítmány kései érkezése a repülőtérre"]]),
           (DELAYCODE, FOR_COMMON,
            ["232", ("23", "CC"),
             ["LATE ACCEPTANCE", "KÉSEI ÁTVÉTEL"],
             ["Acceptance of cargo after deadline",
              "Kereskedelmi döntés, áru és posta járatzárás utáni elfogadása"]]),
           (DELAYCODE, FOR_COMMON,
            ["242", ("24", "CI"),
             ["INADEQUATE PACKING", "NEM MEGFELELŐ CSOMAGOLÁS"],
             ["Repackaging and/or re-labelling of booked cargo",
              "Az áru újracsomagolása és/vagy -címkézése"]]),
           (DELAYCODE, FOR_COMMON,
            ["252", ("25", "CO"),
             ["OVERSALES", "ÁRUTÚLKÖNYVELÉS"],
             ["Booked load in excess of saleable load capacity\n"
              "(weight or volume), resulting in reloading or off-load",
              "A könyvelt terhelés meghaladja az eladható (tömeg\n"
              "vagy térfogat) kapacitást."]]),
           (DELAYCODE, FOR_COMMON,
            ["261", ("26", "CU"),
             ["LATE PREPARATION", "KÉESI ELŐKÉSZÍTÉS"],
             ["Late preparation in warehouse.",
              "Szállítmány kései előkészítése a raktárban"]]),

           (CAPTION, FOR_COMMON,
            ["Mail only",
             "Postakezelés"] ),
           (DELAYCODE, FOR_COMMON,
            ["271", ("27", "CE"),
             ["DOCUMENTATION, PACKING", "DOKUMENTÁCIÓ, CSOMAGOLÁS"],
             ["Incomplete and/or inaccurate documentation",
              "Hiányos és/vagy pontatlan dokumentáció"]]),
           (DELAYCODE, FOR_COMMON,
            ["281", ("28", "CL"),
             ["LATE POSITIONING", "KÉSEI SZÁLLÍTÁS"],
             ["Late delivery of mail to airport / aircraft",
              "Posta kései érkezése a repülőtérre"]]),
           (DELAYCODE, FOR_COMMON,
            ["291", ("29", "CA"),
             ["LATE ACCEPTANCE", "KÉSEI ÁTVÉTEL"],
             ["Acceptance of mail after deadline",
              "Posta járatázárás utáni átvétele"]]),

           (CAPTION, FOR_COMMON,
            ["Aircraft and Ramp Handling",
             "Repülőgép-kiszolgálás"] ),
           (DELAYCODE, FOR_COMMON,
            ["312", ("31", "GD"),
             ["LATE/INACCURATE\nAIRCRAFT DOCUMENTATION",
              "KÉSEI/PONTATLAN\nFEDÉLZETI OKMÁNYOK"],
             ["Late or inaccurate mass and balance documentation, \n"
              "general declaration, passenger manifest",
              "Fedélzeti okmányok elégtelensége, kései kiállítása"]]),
           (DELAYCODE, FOR_COMMON,
            ["322", ("32", "GL"),
             ["LOADING/UNLOADING", "BE- ÉS KIRAKODÁS"],
             ["Bulky items, special load, lack of loading staff",
              "Különleges, súlyos vagy nagy terjedelmű áru,\n"
              "rakodószemélyzet hiánya miatt"]]),
           (DELAYCODE, FOR_COMMON,
            ["324", ("32", "GL"),
             ["LOADING/UNLOADING", "BE- ÉS KIRAKODÁS"],
             ["Lack of loading staff",
              "Rakodószemélyzet hiánya miatt"]]),
           (DELAYCODE, FOR_COMMON,
            ["332", ("33", "GE"),
             ["LOADING EQUIPMENT", "RAKODÓBERENDEZÉSEK"],
             ["Lack of and/or breakdown; lack of operating staff",
              "Hiányuk vagy üzemképtelenségük, működtető személyzet hiánya"]]),
           (DELAYCODE, FOR_COMMON,
            ["342", ("34", "GS"),
             ["SERVICING EQUIPMENT", "KISZOLGÁLÓ ESZKÖZÖK"],
             ["Lack of and/or breakdown; lack of operating staff",
              "Hiányuk vagy üzemképtelenségük, működtető személyzet hiánya"]]),
           (DELAYCODE, FOR_COMMON,
            ["352", ("35", "GC"),
             ["AIRCRAFT CLEANING", "REPÜLŐGÉP TAKARÍTÁS"],
             ["Late completion of aircraft cleaning",
              "Késedelme vagy elhúzódása"]]),
           (DELAYCODE, FOR_COMMON,
            ["362", ("36", "GF"),
             ["FUELLING/DEFUELLING", "ÜZEMANYAG TÖLTÉS/LESZÍVÁS"],
             ["Late delivery of fuel; excludes late request",
              "Üzemanyag kései szállítása, kivéva, ha az igénylés késett"]]),
           (DELAYCODE, FOR_COMMON,
            ["372", ("37", "GB"),
             ["CATERING", "CATERING"],
             ["Late and/or incomplete delivery; late loading",
              "Catering kései szállítása, berakása"]]),
           (DELAYCODE, FOR_COMMON,
            ["381", ("38", "GU"),
             ["ULD", "ULD"],
             ["Lack of and/or unserviceable ULD's or pallets",
              "Üzemképes konténerek és raklapok hiánya"]]),
           (DELAYCODE, FOR_COMMON,
            ["391", ("39", "GT"),
             ["TECHNICAL EQUIPMENT", "BERENDEZÉSEK"],
             ["Lack and/or breakdown; lack of operating staff;\n"
              "includes GPU, air start, pushback tug, de-icing",
              "Hiánya és/vagy elromlása, működtető személyzet hiánya\n"
              "ide tartozik a földi áramellátó, a hajtómű indító,\n"
              "a repülőgép-vontató és a jégtelenítő"]]),

           (CAPTION, FOR_COMMON,
            ["Technical and Aircraft Equipment",
             "Műszaki előkészítés"] ),
           (DELAYCODE, FOR_COMMON,
            ["411", ("41", "TD"),
             ["TECHNICAL DEFECTS", "REPÜLŐGÉP HIBÁK"],
             ["Aircraft arrived with defects from abroad",
              "Külföldről hibával érkezett repülőgép"]]),
           (DELAYCODE, FOR_COMMON,
            ["412", ("41", "TD"),
             ["TECHNICAL DEFECTS", "REPÜLŐGÉP HIBÁK"],
             ["Departing aircraft with defects",
              "Hibásan kiállított induló repülőgép"]]),
           (DELAYCODE, FOR_COMMON,
            ["421", ("42", "TM"),
             ["SCHEDULED MAINTENANCE", "TERVEZETT KARBANTARTÁS"],
             ["Late release from maintenance due to lack of parts",
              "Betervezett karbantartás kései befejezése alkatrészhiány miatt"]]),
           (DELAYCODE, FOR_COMMON,
            ["422", ("42", "TM"),
             ["SCHEDULED MAINTENANCE", "TERVEZETT KARBANTARTÁS"],
             ["Late release from maintenance due to bad management\n"
              "or other internal deficiencies",
              "Betervezett karbantartás kései befejezése rossz\n"
              "szervezés vagy egyéb belső hiányosság miatt"]]),
           (DELAYCODE, FOR_COMMON,
            ["431", ("43", "TN"),
             ["NON-SCHEDULED\nMAINTENANCE", "RENDKÍVÜLI KARBANTARTÁS"],
             ["Special checks in an ad-hoc manner",
              "Különleges ellenőrzések ad hoc jelleggel"]]),
           (DELAYCODE, FOR_COMMON,
            ["432", ("43", "TN"),
             ["NON-SCHEDULED\nMAINTENANCE", "RENDKÍVÜLI KARBANTARTÁS"],
             ["Lack of earlier scheduled checks",
              "Korábbi tervezett ellenőrzések elmaradása"]]),
           (DELAYCODE, FOR_COMMON,
            ["441", ("44", "TS"),
             ["SPARES AND MAINTENANCE", "PÓTALKATRÉSZEK ÉS\nKARBANTARTÁS"],
             ["Lack of spares and equipment due to external factors",
              "Repülőgép berendezések és alkatrészek hiánya külső okokból"]]),
           (DELAYCODE, FOR_COMMON,
            ["442", ("44", "TS"),
             ["SPARES AND MAINTENANCE", "PÓTALKATRÉSZEK ÉS\nKARBANTARTÁS"],
             ["Lack of spares and equipment due to failing to order",
              "Repülőgép berendezések és alkatrészek hiánya\n"
              "megrendelés hiányából"]]),
           (DELAYCODE, FOR_COMMON,
            ["451", ("45", "TA"),
             ["AOG SPARES", "AOG PÓTALKATRÉSZEK"],
             ["Awaiting AOG spare(s) to be carried to another station",
              "Alkatrész szállítás más állomásokra, külföldi meghibásodás\n"
              "(külföldön leragadt saját gép) esetén"]]),
           (DELAYCODE, FOR_COMMON,
            ["461", ("46", "TC"),
             ["AIRCRAFT CHANGE", "REPÜLŐGÉPCSERE"],
             ["If the reason is: 411",
              "Ha az ok: 411"]]),
           (DELAYCODE, FOR_COMMON,
            ["462", ("46", "TC"),
             ["AIRCRAFT CHANGE", "REPÜLŐGÉPCSERE"],
             ["If the reason is: 412",
              "Ha az ok: 412"]]),
           (DELAYCODE, FOR_COMMON,
            ["471", ("47", "TL"),
             ["STANDBY AIRCRAFT", "TARTALÉK REPÜLŐGÉP"],
             ["Standby aircraft unavailable for technical reasons",
              "Csere repülőgép nem áll rendelkezésre, ha az ok: 411 / 461"]]),
           (DELAYCODE, FOR_COMMON,
            ["472", ("47", "TL"),
             ["STANDBY AIRCRAFT", "TARTALÉK REPÜLŐGÉP"],
             ["Standby aircraft unavailable for technical reasons",
              "Csere repülőgép nem áll rendelkezésre, ha az ok: 412 / 462"]]),
           (DELAYCODE, FOR_COMMON,
            ["481", ("47", "TV"),
             ["CABIN CONFIGURATION", "UTASTÉR KONFIGURÁCIÓ"],
             ["Scheduled cabin configuration and version adjustments",
              "Tervezett átszékezés"]]),

           (CAPTION, FOR_COMMON,
            ["Damage to Aircraft &amp; EDP Automated Equipment Failure",
             "Repülőgép sérülése és számítógépes rendszerek hibái"] ),
           (DELAYCODE, FOR_COMMON,
            ["511", ("51", "DF"),
             ["DAMAGE DURING\nFLIGHT OPERATIONS", "REPÜLÉS KÖZBENI SÉRÜLÉS"],
             ["Bird or lightning strike, turbulence",
              "Madár, villámcsapás, turbulencia"]]),
           (DELAYCODE, FOR_COMMON,
            ["512", ("51", "DF"),
             ["DAMAGE DURING\nFLIGHT OPERATIONS", "REPÜLÉS KÖZBENI SÉRÜLÉS"],
             ["Overweight landing, collisions during taxiing",
              "Leszállási túlsúly, gurulás közbeni ütközés"]]),
           (DELAYCODE, FOR_COMMON,
            ["521", ("52", "DG"),
             ["DAMAGE DURING\nGROUND OPERATIONS", "SÉRÜLÉS A FÖLDÖN"],
             ["Not during taxiing, extreme weather conditions",
              "Nem gurulás közben, időjárás következtében"]]),
           (DELAYCODE, FOR_COMMON,
            ["522", ("52", "DG"),
             ["DAMAGE DURING\nGROUND OPERATIONS", "SÉRÜLÉS A FÖLDÖN"],
             ["Loading/offloading damage, towing other collisions",
              "Ki- vagy berakodásnál, vontatásnál vagy egyéb ütközések miatt"]]),

           (DELAYCODE, FOR_COMMON,
            ["551", ("55", "ED"),
             ["DEPARTURE CONTROL", "INDULÁS-IRÁNYÍTÁS"],
             ["System failure due to transmission errors",
              "Rendszerleállás vonalhiba, átviteli hiba miatt"]]),
           (DELAYCODE, FOR_COMMON,
            ["552", ("55", "ED"),
             ["DEPARTURE CONTROL", "INDULÁS-IRÁNYÍTÁS"],
             ["System failure due to operator error",
              "Rendszerleállás kezelői hiba miatt"]]),
           (DELAYCODE, FOR_COMMON,
            ["561", ("56", "EC"),
             ["CARGO PREPARATION\nDOCUMENTATION", "ÁRUDOKUMENTÁCIÓ"],
             ["System failure due to transmission errors",
              "Rendszerleállás vonalhiba, átviteli hiba miatt"]]),
           (DELAYCODE, FOR_COMMON,
            ["562", ("56", "EC"),
             ["CARGO PREPARATION\nDOCUMENTATION", "ÁRUDOKUMENTÁCIÓ"],
             ["System failure due to operator error",
              "Rendszerleállás kezelői hiba miatt"]]),
           (DELAYCODE, FOR_COMMON,
            ["571", ("57", "EF"),
             ["FLIGHT PLANS", "REPÜLÉSI TERVEK"],
             ["Failure of automated flight plan systems",
              "A repülési terveket kezelő rendszerek meghibásodása"]]),
           (DELAYCODE, FOR_COMMON,
            ["581", ("58", "EO"),
             ["OTHER AUTOMATED SYSTEM", "EGYÉB AUTOMATA RENDSZER"],
             ["",
              "Egyéb automata rendszer meghibásodása / leállása"]]),

           (CAPTION, FOR_COMMON,
            ["Flight Operations and Crewing",
             "Repülés üzemeltetés, személyzet"] ),
           (DELAYCODE, FOR_COMMON,
            ["612", ("61", "FP"),
             ["FLIGHT PLAN", "REPÜLÉSI TERV"],
             ["Late completion of or change to flight plan",
              "Repülési terv kései benyújtása vagy módosítása"]]),
           (DELAYCODE, FOR_COMMON,
            ["622", ("62", "FF"),
             ["OPERATIONAL REQUIREMENT", "ÜZEMELTETÉSI IGÉNYEK"],
             ["Late alteration to fuel or payload",
              "Üzemanyag mennyiség vagy hasznos teher\n"
              "kései módosítása"]]),
           (DELAYCODE, FOR_COMMON,
            ["632", ("63", "FT"),
             ["LATE CREW BOARDING\nOR DEPARTURE PROCEDURES",
              "SZEMÉLYZET KÉSEI MEGJELENÉSE\nVAGY ELHÚZÓDÓ INDULÁS"],
             ["Late flight deck, or entire crew, other than standby;\n"
              "late completion of flight deck crew checks",
              "A repülő- vagy a teljes, nem készenléti személyzet\n"
              "késése, az ellenőrzések elhúzódása"]]),
           (DELAYCODE, FOR_COMMON,
            ["642", ("64", "FS"),
             ["FLIGHT DECK\nCREW SHORTAGE", "REPÜLŐSZEMÉLYZET\nLÉTSZÁMHIÁNYA"],
             ["Sickness, awaiting standby, flight time limitations,\n"
              "valid visa, health documents, etc.",
              "Betegség, készenlét, a repülési idő korlátozásai,\n"
              "érvényes vízum, egészségügyi papírok hiánya, stb."]]),
           (DELAYCODE, FOR_COMMON,
            ["652", ("65", "FR"),
             ["FLIGHT DECK CREW\nSPECIAL REQUEST",
              "SZEMÉLYZET KÜLÖNLEGES IGÉNYE"],
             ["Requests not within operational requirements",
              "Az üzemeltetési feltételeken kívül eső igények"]]),
           (DELAYCODE, FOR_COMMON,
            ["661", ("66", "FL"),
             ["LATE CABIN CREW BOARDING\nOR DEPARTURE PROCEDURES",
              "UTASKÍSÉRŐK KÉSEI MEGJELENÉSE\nVAGY ELHÚZÓDÓ INDULÁS"],
             ["Late cabin crew other than standby; late completion\n"
              "of cabin crew checks",
              "Utaskísérők késése, kivéve csatlakozást vagy tartalék\n"
              "behívást; utaskísérői ellenőrzések késése"]]),
           (DELAYCODE, FOR_COMMON,
            ["662", ("66", "FL"),
             ["LATE CABIN CREW BOARDING\nOR DEPARTURE PROCEDURES",
              "UTASKÍSÉRŐK KÉSEI MEGJELENÉSE\nVAGY ELHÚZÓDÓ INDULÁS"],
             ["Late cabin crew other than standby; late completion\n"
              "of cabin crew checks",
              "Forgalmi (földi) döntés, útvonal módosítás, járatösszevonás,\n"
              "járattörlés kereskedelmi okból"]]),
           (DELAYCODE, FOR_COMMON,
            ["672", ("67", "FC"),
             ["CABIN CREW SHORTAGE", "UTASKÍSÉRŐK HIÁNYA"],
             ["Sickness, awaiting standby, flight time limitations,\n"
              "valid visa, health documents",
              "Utaskísérők hiánya hibás tervezés miatt"]]),
           (DELAYCODE, FOR_COMMON,
            ["682", ("68", "FA"),
             ["CABIN CREW ERROR OR\nSPECIAL REQUEST",
              "UTASKÍSÉRŐK HIBÁJA\nVAGY KÜLÖNLEGES IGÉNYE"],
             ["Requests not within operational requirements",
              "Az üzemeltetési feltételeken kívül eső igények"]]),
           (DELAYCODE, FOR_COMMON,
            ["692", ("69", "FB"),
             ["CAPTAIN REQUEST FOR\nSECURITY CHECK",
              "KAPITÁNY KÉRÉSÉRE\nBIZTONSÁGI ELLENŐRZÉS"],
             ["Extraordinary requests outside mandatory requirements",
              "Kapitány kérésére biztonsági ellenőrzés (gép alatt)"]]),


           (CAPTION, FOR_COMMON,
            ["Weather", "Időjárás"] ),
           (DELAYCODE, FOR_COMMON,
            ["711", ("71", "WO"),
             ["DEPARTURE STATION", "INDULÓ ÁLLOMÁS"],
             ["Below operating limits",
              "Kedvezőtlen/minimum alatti időjárás"]]),
           (DELAYCODE, FOR_COMMON,
            ["721", ("72", "WT"),
             ["DESTINATION STATION", "CÉLÁLLOMÁS"],
             ["Below operating limits",
              "Kedvezőtlen/minimum alatti időjárás"]]),
           (DELAYCODE, FOR_COMMON,
            ["731", ("73", "WR"),
             ["EN-ROUTE OR ALTERNATE", "ÚTVONAL VAGY\nKITÉRŐ REPÜLŐTÉR"],
             ["Below operating limits",
              "Kedvezőtlen/minimum alatti időjárás"]]),
           (DELAYCODE, FOR_COMMON,
            ["751", ("75", "WI"),
             ["DE-ICING OF AIRCRAFT", "JÉGTELENÍTÉS"],
             ["Removal of ice and/or snow; excludes\n"
              "equipment – lack of or breakdown",
              "Jég és hó eltakarítás, ha az nem a berendezések\n"
              "hiánya vagy meghibásodása miatt késik"]]),
           (DELAYCODE, FOR_COMMON,
            ["752", ("75", "WI"),
             ["DE-ICING OF AIRCRAFT", "JÉGTELENÍTÉS"],
             ["Bad management, technology or the lack of\n"
              "de-icing liquid",
              "Rossz munkaszervezés, rossz technológia vagy a\n"
              "jégtelenító folyadék hiánya miatt"]]),
           (DELAYCODE, FOR_COMMON,
            ["761", ("76", "WS"),
             ["REMOVAL OF SNOW, ICE,\nWATER, AND SAND FROM\nAIRPORT",
              "HÓ, JÉG, VÍZ ÉS\nHOMOK ELTAKARÍTÁSA\nA REPÜLŐTÉREN"],
             ["Runway, taxiway conditions",
              "A futópályák, gurulóutak állapota"]]),
           (DELAYCODE, FOR_COMMON,
            ["771", ("77", "WG"),
             ["GROUND HANDLING\nIMPAIRED BY ADVERSE\nWEATHER CONDITIONS",
              "AZ IDŐJÁRÁS AKADÁLYOZTA\nFÖLDI KISZOLGÁLÁST"],
             ["High winds, heavy rain, blizzards, monsoons etc.",
              "Erős szél, heves esőzés, hóvihar, monszun, stb."]]),

           (CAPTION, FOR_COMMON,
            ["Air Traffic Flow Management Restrictions",
             "Légiforgalom áramlásszervezési korlátozások"] ),
           (DELAYCODE, FOR_COMMON,
            ["811", ("81", "AT"),
             ["ATFM DUE TO ATC\nENROUTE DEMAND/CAPACITY",
              "ÚTVONAL TERHELTSÉG/KAPACITÁS"],
             ["Standard demand/capacity problems",
              "A szokványos terheltségi és kapacitás problémák"]]),
           (DELAYCODE, FOR_COMMON,
            ["821", ("82", "AX"),
             ["ATFM DUE TO ATC STAFF/\nEQUIPMENT ENROUTE",
              "ÚTVONAL ÁTERESZTŐKÉPESSÉG\nELÉGTELENSÉGE"],
             ["Reduced capacity caused by industrial\n"
              "action or staff shortage, equipment failure,\n"
              "military exercise or extraordinary demand\n"
              "due to capacity reduction in neighbouring area",
              "Csökkent kapacitás sztrájk vagy munkaerőhiány,\n"
              "berendezések meghibásodása, hadgyakorlat vagy\n"
              "egy szomszédos terület kapacitáscsökkenési miatti\n"
              "megnövekedett leterheltség"]]),
           (DELAYCODE, FOR_COMMON,
            ["835", ("83", "AE"),
             ["ATFM DUE TO\nRESTRICTION AT\nDESTINATION AIRPORT",
              "KORLÁTOZÁSOK A\nCÉLÁLLOMÁSON"],
             ["Airport and/or runway closed due to obstruction,\n"
              "industrial action, staff shortage, political unrest,\n"
              "noise abatement, night curfew, special flights",
              "A repülőtér és/vagy a futopálya bezárt akadály,\n"
              "sztrájk, munkaerőhiány, politikai megmozdulások\n"
              "zajcsökkentés, kijárási tilalom, kölönleges járatok miatt"]]),
           (DELAYCODE, FOR_COMMON,
            ["841", ("84", "AW"),
             ["ATFM DUE TO WEATHER\n AT DESTINATION",
              "ÁRAMLÁSSZERVESÉS A\nCÉLÁLLOMÁS IDŐJÁRÁSA MIATT"],
             ["", ""]]),

           (CAPTION, FOR_COMMON,
            ["Airport and state authorities",
             "Repülőtéri és állami hatóságok"] ),
           (DELAYCODE, FOR_COMMON,
            ["851", ("85", "AS"),
             ["MANDATORY SECURITY", "BIZTONSÁGI ELLENŐRZÉS" ],
             ["Passengers, baggage, crew, etc.",
              "Utasok, poggyász, személyzet, stb."]]),
           (DELAYCODE, FOR_COMMON,
            ["852", ("85", "AS"),
             ["MANDATORY SECURITY", "BOMBARIADÓ" ],
             ["Passengers, baggage, crew, etc.",
              "Bombariadó."]]),
           (DELAYCODE, FOR_COMMON,
            ["861", ("86", "AG"),
             ["IMMIGRATION, CUSTOMS,\nHEALTH",
              "VÁMHATÓSÁGI ELLENŐRZÉSEK" ],
             ["Passengers, crew",
              "Vámhatósági ellenőrzések"]]),
           (DELAYCODE, FOR_COMMON,
            ["862", ("86", "AG"),
             ["IMMIGRATION, CUSTOMS,\nHEALTH",
              "HATÁRRENDÉSZETI ELLENŐRZÉSEK" ],
             ["Passengers, crew",
              "Határrendészeti ellenőrzések"]]),
           (DELAYCODE, FOR_COMMON,
            ["863", ("86", "AG"),
             ["IMMIGRATION, CUSTOMS,\nHEALTH",
              "EGÉSZSÉGÜGYI ELLENŐRZÉSEK" ],
             ["Passengers, crew",
              "Egészségügyi ellenőrzések"]]),
           (DELAYCODE, FOR_COMMON,
            ["871", ("87", "AF"),
             ["AIRPORT FACILITIES", "REPÜLŐTÉRI LÉTESÍTMÉNYEK" ],
             ["Parking stands, ramp congestion, lighting,\n"
              "buildings, gate limitations etc.",
              "Repülőtéri befogadó és áteresztőképességének\n"
              "elégtelensége, állóhely (lépcső stb.) hiánya,\n"
              "torlódás az előtéren, kijáratok zsúfoltsága."]]),
           (DELAYCODE, FOR_COMMON,
            ["881", ("88", "AD"),
             ["RESTRICTIONS AT\nDESTINATION AIRPORT",
              "KORLÁTOZÁSOK A\nCÉLÁLLOMÁSON" ],
             ["Airport and/or runway closed due to obstruction,\n"
              "industrial action, staff shortage, political unrest,\n"
              "noise abatement, night curfew, special flights",
              "Korlátozások a repülőtéren, leszállópályazárlat,\n"
              "sztrájk, politikai esemény vagy zajvédelem miatt"]]),
           (DELAYCODE, FOR_COMMON,
            ["891", ("89", "AM"),
             ["RESTRICTIONS AT\nAIRPORT OF DEPARTURE\n"
              "WITH OR WITHOUT ATFM RESTRICTIONS",
              "KORLÁTOZÁSOK AZ INDULÓ\n"
              "ÁLLOMÁSON ÁRAMLÁS-SZERVEZÉSI\n"
              "KORLÁTOZÁSOKKALVAGY\nAZOK NÉLKÜL"],
             ["Including air traffic services, start-up and pushback,\n"
              "airport and/or runway closed due to obstruction or weather\n"
              "(restriction due to weather in case of ATFM only) industrial\n"
              "action, staff shortage, political unrest, noise abatement,\n"
              "night curfew, special flights",
              "Repülőtéri befogadó és áteresztőképességének elégtelensége,\n",
              "állóhely (lépcső stb.) hiánya, torlódás az előtéren,\n"
              "kijáratok zsúfoltsága, leszállópályazárlat, sztrájk,\n"
              "politikai esemény vagy zajvédelem miatt"]]),

           (CAPTION, FOR_COMMON,
            ["Reactionary", "Visszahatások"] ),

           (DELAYCODE, FOR_COMMON,
            ["911", ("91", "RL"),
             ["LOAD CONNECTION", "HASZNOS TEHER\nCSATLAKOZÁSA"],
             ["Awaiting load from another flight",
              "Csatlakozásra várás más járatról, utas és áru"]]),
           (DELAYCODE, FOR_COMMON,
            ["921", ("91", "RT"),
             ["THROUGH CHECK-IN ERROR", "JEGYKEZELÉSI HIBA"],
             ["Passenger or baggage check-in error at originating station",
              "Utas- vagy csomagkezelési hiba az induló állomáson"]]),
           (DELAYCODE, FOR_COMMON,
            ["931", ("93", "RA"),
             ["AIRCRAFT ROTATION", "REPÜLŐGÉP ROTÁCIÓ"],
             ["Late arrival of aircraft from another flight or previous sector",
              "Repülőgép kései érkezése előző járatról\n"
              "(nem vállalati okok miatt)"]]),
           (DELAYCODE, FOR_COMMON,
            ["932", ("93", "RA"),
             ["AIRCRAFT ROTATION", "REPÜLŐGÉP ROTÁCIÓ"],
             ["Late arrival of aircraft from another flight or previous sector",
              "Repülőgép kései érkezése előző járatról\n"
              "(vállalati okok miatt)"]]),
           (DELAYCODE, FOR_COMMON,
            ["941", ("94", "RS"),
             ["CABIN CREW ROTATION", "UTASKÍSÉRŐ ROTÁCIÓ"],
             ["Awaiting cabin crew from another flight",
              "Utaskísérők kései érkezése előző járatról"]]),
           (DELAYCODE, FOR_COMMON,
            ["951", ("95", "RC"),
             ["CREW ROTATION", "SZEMÉLYZET ROTÁCIÓ"],
             ["Awaiting flight deck, or entire crew, from another flight",
              "Teljes személyzet kései érkezése előző járatról"]]),
           (DELAYCODE, FOR_COMMON,
            ["961", ("96", "RO"),
             ["OPERATIONS CONTROL", "ÜZEMELTETÉS"],
             ["Re-routing, diversion, consolidation, aircraft change\n"
              "for reasons other than technical",
              "Útvonalváltoztatás, repülőgép cseréje nem műszaki okokból"]]),

           (CAPTION, FOR_COMMON,
            ["Miscellaneous", "Egyéb"] ),
           (DELAYCODE, FOR_COMMON,
            ["971", ("97", "MI"),
             ["INDUSTRIAL ACTION\nWITHIN OWN AIRLINE",
              "MUNKAÜGYI AKCIÓ SAJÁT\nLÉGITÁRSASÁGON BELÜL"],
             ["",
              "Sztrájk, lassító sztrájk vállalaton belül"]]),
           (DELAYCODE, FOR_COMMON,
            ["981", ("98", "MO"),
             ["INDUSTRIAL ACTION\nOUTSIDE OWN AIRLINE",
              "MUNKAÜGYI AKCIÓ SAJÁT\nLÉGITÁRSASÁGON KÍVÜL"],
             ["Industrial action (except Air Traffic Control Services)",
              "Sztrájk, lassító sztrájk vállalaton kívül"]]),
           (DELAYCODE, FOR_COMMON,
            ["991", ("99", "MX"),
             ["MISCELLANEOUS", "EGYÉB"],
             ["No suitable code; explain reason(s) in plain text",
              "A táblázatban nem szereplő egyéb ok (szöveges indoklást igényel)"]])
           ])

#-------------------------------------------------------------------------------

def generateMsgStr(file, text):
    """Generate an 'msgstr' entry for the given text."""
    lines = text.splitlines()
    numLines = len(lines)
    if numLines==0:
        print("msgstr \" \"", file=file)
    elif numLines==1:
        print("msgstr \"%s\"" % (lines[0]), file=file)
    else:
        print("msgstr \"\"", file=file)
        for i in range(0, numLines):
            print("\"%s%s\"" % (lines[i], "" if i==(numLines-1) else "\\n"), file=file)
    print(file=file)

#-------------------------------------------------------------------------------

def generateFiles(baseDir):
    """Generate the various files."""
    dcdata = None
    poFiles = []

    try:
        dcdataPath = os.path.join(baseDir, "src", "mlx", "gui", "dcdata.py")
        dcdata = open(dcdataPath, "wt")

        numLanguages = len(languageCodes)
        for language in languageCodes:
            poPath = os.path.join(baseDir, "locale", language, "mlx_delay.po")
            poFile = open(poPath, "wt")
            poFiles.append(poFile)
            print("msgid \"\"", file=poFile)
            print("msgstr \"\"", file=poFile)
            print("\"Content-Type: text/plain; charset=utf-8\\n\"", file=poFile)
            print("\"Content-Transfer-Encoding: 8bit\\n\"", file=poFile)

        (baseData, headings, headingFlags, rows) = table
        (poPrefix, extractor) = baseData

        for i in range(0, len(headings)):
            heading = headings[i]
            for j in range(0, numLanguages):
                poFile = poFiles[j]
                print("msgid \"%sheading%d\"" % (poPrefix, i), file=poFile)
                generateMsgStr(poFile, heading[j])


        rowIndex = 0
        for (type, _tableMask, columns) in rows:
            if type==CAPTION:
                for i in range(0, numLanguages):
                    poFile = poFiles[i]
                    print("msgid \"%srow%d\"" % (poPrefix, rowIndex), file=poFile)
                    generateMsgStr(poFile, columns[i])
            elif type in [DELAYCODE, DELAYCODE_EXPLANATION_REQUIRED]:
                columnIndex = 0
                for column in columns:
                    if isinstance(column, list):
                        for i in range(0, numLanguages):
                            if any(column):
                                poFile = poFiles[i]
                                print("msgid \"%srow%d_col%d\"" % \
                                  (poPrefix, rowIndex, columnIndex), file=poFile)
                                generateMsgStr(poFile, column[i])
                    columnIndex += 1
            rowIndex += 1

        print("import mlx.const as const", file=dcdata)
        print("from mlx.i18n import xstr", file=dcdata)
        print(file=dcdata)
        print("CAPTION = 1", file=dcdata)
        print("DELAYCODE = 2", file=dcdata)
        print(file=dcdata)

        tableMask = 1
        for i in range(0, len(tablePrefixes)):
            print("_%s_code2meaning = {" % (tablePrefixes[i],), file=dcdata)

            columnIndexes = []
            for j in range(0, len(headings)):
                if ( (headingFlags[j]&tableMask)==tableMask ):
                    columnIndexes.append(j)

            codeIndex = columnIndexes[0]
            meaningIndex = columnIndexes[2]

            rowIndex = 0
            for (type, mask, columns) in rows:
                if (mask&tableMask)!=tableMask:
                    continue

                if type in [DELAYCODE, DELAYCODE_EXPLANATION_REQUIRED]:
                    print("    \"%s\": \"%s\"," % \
                      (str(columns[codeIndex]).strip(), columns[meaningIndex][0].replace("\n", "")), file=dcdata)

            print("}", file=dcdata)
            print(file=dcdata)

            tableMask <<= 1

        print("def _extract(table, row):", file=dcdata)
        print("    code = row[0].strip()", file=dcdata)
        print("    meaning = table[code] if code in table else None", file=dcdata)
        print("    return code", file=dcdata)
        print(file=dcdata)

        tableMask = 1
        for i in range(0, len(tablePrefixes)):
            print("_%s_code2explanationRequired = {" % (tablePrefixes[i],), file=dcdata)

            columnIndexes = []
            for j in range(0, len(headings)):
                if ( (headingFlags[j]&tableMask)==tableMask ):
                    columnIndexes.append(j)

            codeIndex = columnIndexes[0]
            meaningIndex = columnIndexes[2]

            rowIndex = 0
            for (type, mask, columns) in rows:
                if (mask&tableMask)!=tableMask:
                    continue

                if type in [DELAYCODE, DELAYCODE_EXPLANATION_REQUIRED]:
                    print("    \"%s\": %s," % \
                          (str(columns[codeIndex]).strip(),
                           "True" if type==DELAYCODE_EXPLANATION_REQUIRED else
                           "False"),
                          file = dcdata)

            print("}", file=dcdata)
            print(file=dcdata)

            tableMask <<= 1

        print("def _isExplanationRequired(table, row):", file=dcdata)
        print("    code = row[0].strip()", file=dcdata)
        print("    return table[code] if code in table else false", file=dcdata)
        print(file=dcdata)

        tableMask = 1
        for i in range(0, len(tablePrefixes)):

            print("_%s_data = (" % (tablePrefixes[i],), file=dcdata)
            print("    (lambda row: row[0].strip(),", file=dcdata)
            print("     lambda row: _extract(_%s_code2meaning, row)," % \
              (tablePrefixes[i],), file=dcdata)
            print("     lambda row: _isExplanationRequired(_%s_code2explanationRequired, row))," % \
              (tablePrefixes[i],), file=dcdata)
            print("    [", end=' ', file=dcdata)

            columnIndexes = []
            for j in range(0, len(headings)):
                if ( (headingFlags[j]&tableMask)==tableMask ):
                    if columnIndexes:
                        print(",", end=' ', file=dcdata)
                    print("xstr(\"%sheading%d\")" % (poPrefix, j), end=' ', file=dcdata)
                    columnIndexes.append(j)

            print("],", file=dcdata)

            print("    [", file=dcdata)

            rowIndex = 0
            for (type, mask, columns) in rows:
                if (mask&tableMask)!=tableMask:
                    rowIndex += 1
                    continue

                if type==CAPTION:
                    print("        (CAPTION, xstr(\"%srow%d\"))," % \
                      (poPrefix, rowIndex), file=dcdata)
                elif type in [DELAYCODE, DELAYCODE_EXPLANATION_REQUIRED]:
                    print("        (DELAYCODE, [", file=dcdata)
                    for j in columnIndexes:
                        column = columns[j]
                        if j!=columnIndexes[0]:
                            print(",", file=dcdata)
                        if isinstance(column, list):
                            if any(column):
                                print("            xstr(\"%srow%d_col%d\")"  % \
                                (poPrefix, rowIndex, j), end=' ', file=dcdata)
                            else:
                                print("            \"\"", end=' ', file=dcdata)
                        elif isinstance(column, tuple) and len(column)==2:
                            print("            \"%s (%s)\""  % \
                                  (column[0], column[1]), end = ' ', file = dcdata)
                        else:
                            print("            \"%s\""  % \
                              (column,), end=' ', file=dcdata)
                    print("] ),", file=dcdata)
                rowIndex += 1

            print("    ]", file=dcdata)

            print(")", file=dcdata)
            print(file=dcdata)

            tableMask <<= 1

        print("def getTable(aircraftType):", file=dcdata)
        first = True
        for i in range(0, len(tablePrefixes)):
            tablePrefix = tablePrefixes[i]
            for typeSuffix in typeGroups[i]:
                print("    %s aircraftType==const.AIRCRAFT_%s:" % \
                  ("if" if first else "elif", typeSuffix), file=dcdata)
                print("        return _%s_data" % (tablePrefix,), file=dcdata)
                first = False

        print("    else:", file=dcdata)
        print("        return None", file=dcdata)
    finally:
        for poFile in poFiles:
            poFile.close()
        if dcdata is not None:
            dcdata.close()

#-------------------------------------------------------------------------------

if __name__ == "__main__":
    generateFiles(os.path.dirname(__file__))
