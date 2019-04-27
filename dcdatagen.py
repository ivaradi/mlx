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

#----------------------------------------------------------------------------

# Prefixes for the generated tables
tablePrefixes = [ "modern", "ot" ]

# Type groups
typeGroups = [ ["B736", "B737", "B738", "B738C", "B733", "B734", "B735",
                "DH8D", "B762", "B763", "CRJ2", "F70", "B462" ],
               ["DC3", "T134", "T154", "YK40"] ]

#----------------------------------------------------------------------------

# The associated row or column is for the modern fleet
FOR_MODERN = 1

# The associated row or column is for the old-timer fleet
FOR_OT = 2

#----------------------------------------------------------------------------

# The complete delay code table
table = (("info_delay_",
          "lambda row: row[0].strip()"),
         [ ["MA", "MA"], ["IATA", "IATA"], ["Code", "Kód"],
           ["Name", "Név"],["Description", "Leírás" ] ],
         [ FOR_OT, FOR_MODERN | FOR_OT, FOR_MODERN,
           FOR_OT | FOR_MODERN, FOR_OT | FOR_MODERN ],
         [ (CAPTION, FOR_MODERN | FOR_OT,
            ["Others", "Egyebek"] ),
           (DELAYCODE, FOR_OT,
            ["012      ", "01      ", None,
             ["LATE PARTS OR MATERIALS", "KÉSEI ALKATRÉSZ VAGY ANYAG"],
             ["Parts and/or materials shipped late from the warehouse",
              "Kései alkatrész és/vagy anyagkiszállítás a raktárból"]]),
           (DELAYCODE, FOR_MODERN,
            [None, "06    ", "OA     ",
             ["NO GATES/STAND AVAILABLE", "NINCS SZABAD KAPU/ÁLLÓHELY"],
             ["Due to own airline activity",
              "Saját tevékenység miatt"]]),
           (DELAYCODE, FOR_MODERN,
            [None, "09", "SG",
             ["SCHEDULED GROUND TIME", "ÜTEMEZETT FORDULÓ IDŐ"],
             ["Planned turnaround time less than declared minimum",
              "A tervezett forduló idő rövidebb a minimálisnál"]]),

           (CAPTION, FOR_MODERN | FOR_OT,
            ["Passenger and baggage",
             "Utas és poggyászkezelés"] ),
           (DELAYCODE, FOR_MODERN | FOR_OT,
            ["111", "11", "PD",
             ["LATE CHECK-IN", "KÉSEI JEGYKEZELÉS"],
             ["Check-in reopened for late passengers",
              "Check-in járatzárás után"]]),
           (DELAYCODE, FOR_MODERN | FOR_OT,
            ["121", "12", "PL",
             ["LATE CHECK-IN", "KÉSEI JEGYKEZELÉS"],
             ["Check-in not completed by flight closure time",
              "Torlódás az indulási csarnokban"]]),
           (DELAYCODE, FOR_MODERN | FOR_OT,
            ["132", "13", "PE",
             ["CHECK-IN ERROR", "JEGYKEZELÉSI HIBA"],
             ["Error with passenger or baggage details",
              "Téves utas és poggyászfelvétel"]]),
           (DELAYCODE, FOR_MODERN | FOR_OT,
            ["142", "14", "PO",
             ["OVERSALES", "TÚLKÖNYVELÉS"],
             ["Booking errors – not resolved at check-in",
              "Téves könyvelés, a jegykezelés során nem megoldott"]]),
           (DELAYCODE, FOR_MODERN,
            [None, "15", "PH",
             ["BOARDING", "BESZÁLLÍTÁS"],
             ["Discrepancies and paging, missing checked in passengers",
              "Beszállítási rendellenesség, hiányzó utasok"]]),
           (DELAYCODE, FOR_OT,
            ["151", "15", None,
             ["BOARDING", "BESZÁLLÍTÁS"],
             ["Boarding discrepancies due to the passenger's fault",
              "Beszállítási rendellenesség utas hibájából"]]),
           (DELAYCODE, FOR_OT,
            ["152", "", None,
             ["BOARDING", "BESZÁLLÍTÁS"],
             ["Boarding discrepancies due to the tranzit's fault",
              "Beszállítási rendellenesség tranzit hibájából"]]),
           (DELAYCODE, FOR_MODERN | FOR_OT,
            ["161", "16", "PS",
             ["COMMERCIAL PUBLICITY/\nPASSENGER CONVENIENCE",
              "NYILVÁNOS FOGADÁS/\nUTASKÉNYELMI SZEMPONTOK"],
             ["Local decision to delay for VIP or press; \ndelay due to offload of passengers following family bereavement",
              "Késleltetés helyi döntés alapján reptérzár,\nbetegség/halál, VIP, sajtó, TV miatt"]]),
           (DELAYCODE, FOR_MODERN,
            [None, "17", "PC",
             ["CATERING ORDER", "CATERING MEGRENDELÉS"],
             ["Late or incorrect order given to supplier",
              "Kései vagy téves megrendelés leadása a szállítónak"]]),
           (DELAYCODE, FOR_OT,
            ["171", "17", None,
             ["CATERING ORDER", "CATERING MEGRENDELÉS"],
             ["Late catering order in case of an additional group of people",
              "Kései catering megrendelés, extra csoport jelentkezése esetén"]]),
           (DELAYCODE, FOR_OT,
            ["172", "", None,
             ["CATERING ORDER", "CATERING MEGRENDELÉS"],
             ["Late catering order due to negligence",
              "Kései catering megrendelés gondatlanságból"]]),
           (DELAYCODE, FOR_MODERN | FOR_OT,
            ["182", "18", "PD",
             ["BAGGAGE PROCESSING", "POGGYÁSZKEZELÉS"],
             ["Late or incorrectly sorted baggage",
              "Késő vagy tévesen szortírozott poggyász"]]),

           (CAPTION, FOR_MODERN | FOR_OT,
            ["Cargo and mail",
             "Áru és postakezelés"] ),
           (DELAYCODE, FOR_MODERN | FOR_OT,
            ["212", "21", "CD",
             ["DOCUMENTATION", "DOKUMENTÁCIÓ"],
             ["Late or incorrect documentation for booked cargo",
              "Hibás vagy kései áruokmányolás"]]),
           (DELAYCODE, FOR_MODERN | FOR_OT,
            ["221", "22", "CP",
             ["LATE POSITIONING", "KÉSEI SZÁLLÍTÁS"],
             ["Late delivery of booked cargo to airport/aircraft",
              "Szállítmány kései érkezése a repülőtérre"]]),
           (DELAYCODE, FOR_MODERN | FOR_OT,
            ["232", "23", "CC",
             ["LATE ACCEPTANCE", "KÉSEI ÁTVÉTEL"],
             ["Acceptance of cargo after deadline",
              "Kereskedelmi döntés, áru és posta járatzárás utáni elfogadása"]]),
           (DELAYCODE, FOR_MODERN | FOR_OT,
            ["242", "24", "CI",
             ["INADEQUATE PACKING", "NEM MEGFELELŐ CSOMAGOLÁS"],
             ["Repackaging and/or re-labelling of booked cargo",
              "Az áru újracsomagolása és/vagy -címkézése"]]),
           (DELAYCODE, FOR_MODERN | FOR_OT,
            ["252", "25", "CO",
             ["OVERSALES", "ÁRUTÚLKÖNYVELÉS"],
             ["Booked load in excess of saleable load capacity\n"
              "(weight or volume), resulting in reloading or off-load",
              "A könyvelt terhelés meghaladja az eladható (tömeg\n"
              "vagy térfogat) kapacitást."]]),

           (CAPTION, FOR_MODERN,
            ["Mail only",
             "Postakezelés"] ),
           (DELAYCODE, FOR_MODERN,
            [None, "27", "CE",
             ["DOCUMENTATION, PACKING", "DOKUMENTÁCIÓ, CSOMAGOLÁS"],
             ["Incomplete and/or inaccurate documentation",
              "Hiányos és/vagy pontatlan dokumentáció"]]),
           (DELAYCODE, FOR_MODERN,
            [None, "28", "CL",
             ["LATE POSITIONING", "KÉSEI SZÁLLÍTÁS"],
             ["Late delivery of mail to airport / aircraft",
              "Posta kései érkezése a repülőtérre"]]),
           (DELAYCODE, FOR_MODERN,
            [None, 29, "CA",
             ["LATE ACCEPTANCE", "KÉSEI ÁTVÉTEL"],
             ["Acceptance of mail after deadline",
              "Posta járatázárás utáni átvétele"]]),

           (CAPTION, FOR_MODERN | FOR_OT,
            ["Aircraft and Ramp Handling",
             "Repülőgép-kiszolgálás"] ),
           (DELAYCODE, FOR_MODERN | FOR_OT,
            ["312", "31", "GD",
             ["LATE/INACCURATE\nAIRCRAFT DOCUMENTATION",
              "KÉSEI/PONTATLAN\nFEDÉLZETI OKMÁNYOK"],
             ["Late or inaccurate mass and balance documentation, \n"
              "general declaration, passenger manifest",
              "Fedélzeti okmányok elégtelensége, kései kiállítása"]]),
           (DELAYCODE, FOR_MODERN,
            [None, "32", "GL",
             ["LOADING/UNLOADING", "BE- ÉS KIRAKODÁS"],
             ["Bulky items, special load, lack of loading staff",
              "Különleges, súlyos vagy nagy terjedelmű áru,\n"
              "rakodószemélyzet hiánya miatt"]]),
           (DELAYCODE, FOR_OT,
            ["322", "32", None,
             ["LOADING/UNLOADING", "BE- ÉS KIRAKODÁS"],
             ["Bulky items, special load",
              "Különleges, súlyos vagy nagy terjedelmű áru miatt"]]),
           (DELAYCODE, FOR_OT,
            ["324", "", None,
             ["LOADING/UNLOADING", "BE- ÉS KIRAKODÁS"],
             ["Lack of loading staff",
              "Rakodószemélyzet hiánya miatt"]]),
           (DELAYCODE, FOR_MODERN | FOR_OT,
            ["332", "33", "GE",
             ["LOADING EQUIPMENT", "RAKODÓBERENDEZÉSEK"],
             ["Lack of and/or breakdown; lack of operating staff",
              "Hiányuk vagy üzemképtelenségük, működtető személyzet hiánya"]]),
           (DELAYCODE, FOR_MODERN | FOR_OT,
            ["342", "34", "GS",
             ["SERVICING EQUIPMENT", "KISZOLGÁLÓ ESZKÖZÖK"],
             ["Lack of and/or breakdown; lack of operating staff",
              "Hiányuk vagy üzemképtelenségük, működtető személyzet hiánya"]]),
           (DELAYCODE, FOR_MODERN | FOR_OT,
            ["352", "34", "GC",
             ["AIRCRAFT CLEANING", "REPÜLŐGÉP TAKARÍTÁS"],
             ["Late completion of aircraft cleaning",
              "Késedelme vagy elhúzódása"]]),
           (DELAYCODE, FOR_MODERN | FOR_OT,
            ["362", "36", "GF",
             ["FUELLING/DEFUELLING", "ÜZEMANYAG TÖLTÉS/LESZÍVÁS"],
             ["Late delivery of fuel; excludes late request",
              "Üzemanyag kései szállítása, kivéva, ha az igénylés késett"]]),
           (DELAYCODE, FOR_MODERN | FOR_OT,
            ["372", "37", "GB",
             ["CATERING", "CATERING"],
             ["Late and/or incomplete delivery; late loading",
              "Catering kései szállítása, berakása"]]),
           (DELAYCODE, FOR_MODERN,
            [None, "38", "GU",
             ["ULD", "KONTÉNER"],
             ["Lack of and/or unserviceable ULD's or pallets",
              "Üzemképes konténerek és raklapok hiánya"]]),
           (DELAYCODE, FOR_MODERN,
            [None, "39", "GT",
             ["TECHNICAL EQUIPMENT", "BERENDEZÉSEK"],
             ["Lack and/or breakdown; lack of operating staff;\n"
              "includes GPU, air start, pushback tug, de-icing",
              "Hiánya és/vagy elromlása, működtető személyzet hiánya\n"
              "ide tartozik a földi áramellátó, a hajtómű indító,\n"
              "a repülőgép-vontató és a jégtelenítő"]]),

           (CAPTION, FOR_MODERN | FOR_OT,
            ["Technical and Aircraft Equipment",
             "Műszaki előkészítés"] ),
           (DELAYCODE, FOR_MODERN,
            [None, "41", "TD",
             ["TECHNICAL DEFECTS", "REPÜLŐGÉP HIBÁK"],
             ["Aircraft defects including items covered by MEL",
              "Repülőgép hibák, idértve a MEL alá tartozó berendezéseket"]]),
           (DELAYCODE, FOR_OT,
            ["411", "41", None,
             ["TECHNICAL DEFECTS", "REPÜLŐGÉP HIBÁK"],
             ["Aircraft arrived with defects from abroad",
              "Külföldről hibával érkezett repülőgép"]]),
           (DELAYCODE, FOR_OT,
            ["412", "41", None,
             ["TECHNICAL DEFECTS", "REPÜLŐGÉP HIBÁK"],
             ["Departing aircraft with defects",
              "Hibásan kiállított induló repülőgép"]]),
           (DELAYCODE, FOR_MODERN,
            [None, "42", "TM",
             ["SCHEDULED MAINTENANCE", "TERVEZETT KARBANTARTÁS"],
             ["Late release from maintenance",
              "Karbantartás kései befejezése"]]),
           (DELAYCODE, FOR_OT,
            ["421", "42", None,
             ["SCHEDULED MAINTENANCE", "TERVEZETT KARBANTARTÁS"],
             ["Late release from maintenance due to lack of parts",
              "Betervezett karbantartás kései befejezése alkatrészhiány miatt"]]),
           (DELAYCODE, FOR_OT,
            ["422", "", None,
             ["SCHEDULED MAINTENANCE", "TERVEZETT KARBANTARTÁS"],
             ["Late release from maintenance due to bad management\n"
              "or other internal deficiencies",
              "Betervezett karbantartás kései befejezése rossz\n"
              "szervezés vagy egyéb belső hiányosság miatt"]]),
           (DELAYCODE, FOR_MODERN,
            [None, "43", "TN",
             ["NON-SCHEDULED\nMAINTENANCE", "RENDKÍVÜLI KARBANTARTÁS"],
             ["Special checks and/or additional works\n"
              "beyond normal maintenance schedule",
              "A normál karbantartási ütemterven felül elvégzett\n"
              "speciális ellenőrzések és/vagy egyéb munkák"]]),
           (DELAYCODE, FOR_OT,
            ["431", "43", None,
             ["NON-SCHEDULED\nMAINTENANCE", "RENDKÍVÜLI KARBANTARTÁS"],
             ["Special checks in an ad-hoc manner",
              "Különleges ellenőrzések ad hoc jelleggel"]]),
           (DELAYCODE, FOR_OT,
            ["432", "", None,
             ["NON-SCHEDULED\nMAINTENANCE", "RENDKÍVÜLI KARBANTARTÁS"],
             ["Lack of earlier scheduled checks",
              "Korábbi tervezett ellenőrzések elmaradása"]]),
           (DELAYCODE, FOR_MODERN,
            [None, "44", "TS",
             ["SPARES AND MAINTENANCE", "PÓTALKATRÉSZEK ÉS\nKARBANTARTÁS"],
             ["Lack of spares, lack of and/or breakdown of\n"
              "specialist equipment required for defect rectification\n",
              "Pótalkatrészek hiánya, a meghibásodások kijavításához\n"
              "szükséges felszerelés hiánya és/vagy üzemképtelensége"]]),
           (DELAYCODE, FOR_OT,
            ["441", "44", None,
             ["SPARES AND MAINTENANCE", "PÓTALKATRÉSZEK ÉS\nKARBANTARTÁS"],
             ["Lack of spares and equipment due to external factors",
              "Repülőgép berendezések és alkatrészek hiánya külső okokból"]]),
           (DELAYCODE, FOR_OT,
            ["442", "", None,
             ["SPARES AND MAINTENANCE", "PÓTALKATRÉSZEK ÉS\nKARBANTARTÁS"],
             ["Lack of spares and equipment due to failing to order",
              "Repülőgép berendezések és alkatrészek hiánya\n"
              "megrendelés hiányából"]]),
           (DELAYCODE, FOR_MODERN | FOR_OT,
            ["451", "45", "TA",
             ["AOG SPARES", "AOG PÓTALKATRÉSZEK"],
             ["Awaiting AOG spare(s) to be carried to another station",
              "Alkatrész szállítás más állomásokra, külföldi meghibásodás\n"
              "(külföldön leragadt saját gép) esetén"]]),
           (DELAYCODE, FOR_MODERN,
            [None, "46", "TC",
             ["AIRCRAFT CHANGE", "REPÜLŐGÉPCSERE"],
             ["For technical reasons, e.g. a prolonged technical delay",
              "Műszaki okok, pl. elhúzódó javítás miatt"]]),
           (DELAYCODE, FOR_OT,
            ["461", "46", None,
             ["AIRCRAFT CHANGE", "REPÜLŐGÉPCSERE"],
             ["If the reason is: 411",
              "Ha az ok: 411"]]),
           (DELAYCODE, FOR_OT,
            ["462", "", None,
             ["AIRCRAFT CHANGE", "REPÜLŐGÉPCSERE"],
             ["If the reason is: 412",
              "Ha az ok: 412"]]),

           (CAPTION, FOR_MODERN | FOR_OT,
            ["Damage to Aircraft",
             "Repülőgép sérülése"] ),
           (DELAYCODE, FOR_MODERN,
            [None, "51", "DF",
             ["DAMAGE DURING\nFLIGHT OPERATIONS", "REPÜLÉS KÖZBENI SÉRÜLÉS"],
             ["Bird or lightning strike, turbulence, heavy or\n"
              "overweight landing, collisions during taxiing",
              "Madár, villámcsapás, légörvény, túl erős vagy\n"
              "túlsúlyos leszállás, ütközés gurulás közben"]]),
           (DELAYCODE, FOR_OT,
            ["511", "51", None,
             ["DAMAGE DURING\nFLIGHT OPERATIONS", "REPÜLÉS KÖZBENI SÉRÜLÉS"],
             ["Bird or lightning strike, turbulence",
              "Madár, villámcsapás, turbulencia"]]),
           (DELAYCODE, FOR_OT,
            ["512", "", None,
             ["DAMAGE DURING\nFLIGHT OPERATIONS", "REPÜLÉS KÖZBENI SÉRÜLÉS"],
             ["Overweight landing, collisions during taxiing",
              "Leszállási túlsúly, gurulás közbeni ütközés"]]),
           (DELAYCODE, FOR_MODERN,
            [None, "52", "DG",
             ["DAMAGE DURING\nGROUND OPERATIONS", "SÉRÜLÉS A FÖLDÖN"],
             ["Collisions (other than taxiing), loading/offloading\n"
              "damage, towing, contamination, extreme weather conditions",
              "Ütközés (nem gurulás közben), rakodásnál, vontatásnál\n"
              "szennyeződés vagy szélsőséges időjárás miatt"]]),
           (DELAYCODE, FOR_OT,
            ["521", "52", None,
             ["DAMAGE DURING\nGROUND OPERATIONS", "SÉRÜLÉS A FÖLDÖN"],
             ["Not during taxiing, extreme weather conditions",
              "Nem gurulás közben, időjárás következtében"]]),
           (DELAYCODE, FOR_OT,
            ["522", "52", None,
             ["DAMAGE DURING\nGROUND OPERATIONS", "SÉRÜLÉS A FÖLDÖN"],
             ["Loading/offloading damage, towing other collisions",
              "Ki- vagy berakodásnál, vontatásnál vagy egyéb ütközések miatt"]]),

           (CAPTION, FOR_MODERN | FOR_OT,
            ["EDP/Automated Equipment Failure",
             "Számítógépes rendszerek hibái"] ),
           (DELAYCODE, FOR_MODERN,
            [None, "55", "ED",
             ["DEPARTURE CONTROL", "INDULÁS-IRÁNYÍTÁS"],
             ["Failure of automated systems, including check-in;\n"
              "load control systems producing mass and balance",
              "Az automatizált rendszerek meghibásodása, beleértve a\n",
              "check-int és a tömeg- és egyensúlyszámítást végző rendszereket"]]),
           (DELAYCODE, FOR_OT,
            ["551", "55", None,
             ["DEPARTURE CONTROL", "INDULÁS-IRÁNYÍTÁS"],
             ["System failure due to transmission errors",
              "Rendszerleállás vonalhiba, átviteli hiba miatt"]]),
           (DELAYCODE, FOR_OT,
            ["552", "", None,
             ["DEPARTURE CONTROL", "INDULÁS-IRÁNYÍTÁS"],
             ["System failure due to operator error",
              "Rendszerleállás kezelői hiba miatt"]]),
           (DELAYCODE, FOR_MODERN,
            [None, "56", "EC",
             ["CARGO PREPARATION\nDOCUMENTATION", "ÁRUDOKUMENTÁCIÓ"],
             ["Failure of documentation and/or load control\n"
              "systems covering cargo"
              "A dokumentációs és/vagy terhelés irányító rendszerek\n",
              "árukezeléssel kapcsolatos részének hibája"]]),
           (DELAYCODE, FOR_OT,
            ["561", "56", None,
             ["CARGO PREPARATION\nDOCUMENTATION", "ÁRUDOKUMENTÁCIÓ"],
             ["System failure due to transmission errors",
              "Rendszerleállás vonalhiba, átviteli hiba miatt"]]),
           (DELAYCODE, FOR_OT,
            ["562", "", None,
             ["CARGO PREPARATION\nDOCUMENTATION", "ÁRUDOKUMENTÁCIÓ"],
             ["System failure due to operator error",
              "Rendszerleállás kezelői hiba miatt"]]),
           (DELAYCODE, FOR_MODERN | FOR_OT,
            ["571", "57", "EF",
             ["FLIGHT PLANS", "REPÜLÉSI TERVEK"],
             ["Failure of automated flight plan systems",
              "A repülési terveket kezelő rendszerek meghibásodása"]]),
           (DELAYCODE, FOR_OT,
            ["581", "58", "EF",
             ["", ""],
             ["",
              ""]]),

           (CAPTION, FOR_MODERN | FOR_OT,
            ["Flight Operations and Crewing",
             "Üzemeltetés"] ),
           (DELAYCODE, FOR_MODERN | FOR_OT,
            ["612", "61", "FP",
             ["FLIGHT PLAN", "REPÜLÉSI TERV"],
             ["Late completion of or change to flight plan",
              "Repülési terv kései benyújtása vagy módosítása"]]),
           (DELAYCODE, FOR_MODERN | FOR_OT,
            ["622", "62", "FF",
             ["OPERATIONAL REQUIREMENT", "ÜZEMELTETÉSI IGÉNYEK"],
             ["Late alteration to fuel or payload",
              "Üzemanyag mennyiség vagy hasznos teher\n"
              "kései módosítása"]]),
           (DELAYCODE, FOR_MODERN | FOR_OT,
            ["632", "63", "FT",
             ["LATE CREW BOARDING\nOR DEPARTURE PROCEDURES",
              "SZEMÉLYZET KÉSEI MEGJELENÉSE\nVAGY ELHÚZÓDÓ INDULÁS"],
             ["Late flight deck, or entire crew, other than standby;\n"
              "late completion of flight deck crew checks",
              "A repülő- vagy a teljes, nem készenléti személyzet\n"
              "késése, az ellenőrzések elhúzódása"]]),
           (DELAYCODE, FOR_MODERN | FOR_OT,
            ["642", "64", "FS",
             ["FLIGHT DECK\nCREW SHORTAGE", "REPÜLŐSZEMÉLYZET\nLÉTSZÁMHIÁNYA"],
             ["Sickness, awaiting standby, flight time limitations,\n"
              "valid visa, health documents, etc.",
              "Betegség, készenlét, a repülési idő korlátozásai,\n"
              "érvényes vízum, egészségügyi papírok hiánya, stb."]]),
           (DELAYCODE, FOR_MODERN | FOR_OT,
            ["652", "65", "FR",
             ["FLIGHT DECK CREW\nSPECIAL REQUEST",
              "SZEMÉLYZET KÜLÖNLEGES IGÉNYE"],
             ["Requests not within operational requirements",
              "Az üzemeltetési feltételeken kívül eső igények"]]),
           (DELAYCODE, FOR_MODERN,
            [None, "66", "FL",
             ["LATE CABIN CREW BOARDING\nOR DEPARTURE PROCEDURES",
              "UTASKÍSÉRŐK KÉSEI MEGJELENÉSE\nVAGY ELHÚZÓDÓ INDULÁS"],
             ["Late cabin crew other than standby; late completion\n"
              "of cabin crew checks",
              "A nem készenléti utaskisérők késése,\n"
              "az ellenőrzések elhúzódása"]]),
           (DELAYCODE, FOR_OT,
            ["662", "66", None,
             ["OPERATIONAL (GROUND)\nDECISION",
              "FORGALMI (FÖLDI) DÖNTÉS"],
             ["Modification of route, merging or cancelling flights\n"
              "due to business reasons",
              "Útvonal módosítás, járatösszevonás, járattörlés\n"
              "kereskedelmi okból"]]),
           (DELAYCODE, FOR_MODERN | FOR_OT,
            ["672", "67", "FC",
             ["CABIN CREW SHORTAGE", "UTASKÍSÉRŐK HIÁNYA"],
             ["Sickness, awaiting standby, flight time limitations,\n"
              "valid visa, health documents",
              "Betegség, készenlét, a repülési idő korlátozásai,\n"
              "érvényes vízum, egészségügyi papírok hiánya."]]),
           (DELAYCODE, FOR_MODERN | FOR_OT,
            ["682", "68", "FA",
             ["CABIN CREW ERROR OR\nSPECIAL REQUEST",
              "UTASKÍSÉRŐK HIBÁJA\nVAGY KÜLÖNLEGES IGÉNYE"],
             ["Requests not within operational requirements",
              "Az üzemeltetési feltételeken kívül eső igények"]]),
           (DELAYCODE, FOR_MODERN | FOR_OT,
            ["692", "69", "FB",
             ["CAPTAIN REQUEST FOR\nSECURITY CHECK",
              "KAPITÁNY KÉRÉSÉRE\nBIZTONSÁGI ELLENŐRZÉS"],
             ["Extraordinary requests outside mandatory requirements",
              "A kötelező elvárásokon felüli kérés"]]),


           (CAPTION, FOR_MODERN | FOR_OT,
            ["Weather", "Időjárás"] ),
           (DELAYCODE, FOR_MODERN | FOR_OT,
            ["711", "71", "WO",
             ["DEPARTURE STATION", "INDULÓ ÁLLOMÁS"],
             ["Below operating limits",
              "Kedvezőtlen/minimum alatti időjárás"]]),
           (DELAYCODE, FOR_MODERN | FOR_OT,
            ["721", "72", "WT",
             ["DESTINATION STATION", "CÉLÁLLOMÁS"],
             ["Below operating limits",
              "Kedvezőtlen/minimum alatti időjárás"]]),
           (DELAYCODE, FOR_MODERN | FOR_OT,
            ["731", "73", "WR",
             ["EN-ROUTE OR ALTERNATE", "ÚTVONAL VAGY\nKITÉRŐ REPÜLŐTÉR"],
             ["Below operating limits",
              "Kedvezőtlen/minimum alatti időjárás"]]),
           (DELAYCODE, FOR_MODERN | FOR_OT,
            ["751", "75", "WS",
             ["DE-ICING OF AIRCRAFT", "JÉGTELENÍTÉS"],
             ["Removal of ice and/or snow; excludes\n"
              "equipment – lack of or breakdown",
              "Jég és hó eltakarítás, ha az nem a berendezések\n"
              "hiánya vagy meghibásodása miatt késik"]]),
           (DELAYCODE, FOR_OT,
            ["752", "", None,
             ["DE-ICING OF AIRCRAFT", "JÉGTELENÍTÉS"],
             ["Bad management, technology or the lack of\n"
              "de-icing liquid",
              "Rossz munkaszervezés, rossz technológia vagy a\n"
              "jégtelenító folyadék hiánya miatt"]]),
           (DELAYCODE, FOR_MODERN | FOR_OT,
            ["761", "76", "WS",
             ["REMOVAL OF SNOW, ICE,\nWATER, AND SAND FROM\nAIRPORT",
              "HÓ, JÉG, VÍZ ÉS\nHOMOK ELTAKARÍTÁSA\nA REPÜLŐTÉREN"],
             ["Runway, taxiway conditions",
              "A futópályák, gurulóutak állapota"]]),
           (DELAYCODE, FOR_MODERN | FOR_OT,
            ["771", "77", "WG",
             ["GROUND HANDLING\nIMPAIRED BY ADVERSE\nWEATHER CONDITIONS",
              "AZ IDŐJÁRÁS AKADÁLYOZTA\nFÖLDI KISZOLGÁLÁST"],
             ["High winds, heavy rain, blizzards, monsoons etc.",
              "Erős szél, heves esőzés, hóvihar, monszun, stb."]]),

           (CAPTION, FOR_MODERN,
            ["Air Traffic Flow Management Restrictions",
             "A forgalomáramlás-irányítás követelményei"] ),
           (DELAYCODE, FOR_MODERN,
            [None, "81", "AT",
             ["ATFM DUE TO ATC\nENROUTE DEMAND/CAPACITY",
              "ÚTVONAL TERHELTSÉG/KAPACITÁS"],
             ["Standard demand/capacity problems",
              "A szokványos terheltségi és kapacitás problémák"]]),
           (DELAYCODE, FOR_MODERN,
            [None, "82", "AX",
             ["ATFM DUE TO ATC STAFF/\nEQUIPMENT ENROUTE",
              "ÚTVONALI IRÁNYÍTÓ\nSZEMÉLYZET/NBERENDEZÉSEK"],
             ["Reduced capacity caused by industrial\n"
              "action or staff shortage, equipment failure,\n"
              "military exercise or extraordinary demand\n"
              "due to capacity reduction in neighbouring area",
              "Csökkent kapacitás sztrájk vagy munkaerőhiány,\n"
              "berendezések meghibásodása, hadgyakorlat vagy\n"
              "egy szomszédos terület kapacitáscsökkenési miatti\n"
              "megnövekedett leterheltség"]]),
           (DELAYCODE, FOR_MODERN,
            [None, "83", "AE",
             ["ATFM DUE TO\nRESTRICTION AT\nDESTINATION AIRPORT",
              "KORLÁTOZÁSOK A\nCÉLREPÜLŐTÉREN"],
             ["Airport and/or runway closed due to obstruction,\n"
              "industrial action, staff shortage, political unrest,\n"
              "noise abatement, night curfew, special flights",
              "A repülőtér és/vagy a futopálya bezárt akadály,\n"
              "sztrájk, munkaerőhiány, politikai megmozdulások\n"
              "zajcsökkentés, kijárási tilalom, kölönleges járatok miatt"]]),
           (DELAYCODE, FOR_MODERN,
            [None, "84", "AW",
             ["ATFM DUE TO WEATHER\n AT DESTINATION",
              "CÉLREPÜLŐTÉR IDŐJÁRÁSA"],
             ["", ""]]),

           (CAPTION, FOR_MODERN | FOR_OT,
            ["Airport and state authorities",
             "Repülőtéri és állami hatóságok"] ),
           (DELAYCODE, FOR_MODERN,
            [None, "85", "AS",
             ["MANDATORY SECURITY", "BIZTONSÁGI ELLENŐRZÉS" ],
             ["Passengers, baggage, crew, etc.",
              "Utasok, poggyász, személyzet, stb."]]),
           (DELAYCODE, FOR_MODERN,
            [None, "86", "AG",
             ["IMMIGRATION, CUSTOMS,\nHEALTH",
              "HATÁRRENDÉSZET, VÁM,\nEGÉSZSÉGÜGY" ],
             ["Passengers, crew",
              "Utasok, személyzet"]]),
           (DELAYCODE, FOR_MODERN,
            [None, "87", "AF",
             ["AIRPORT FACILITIES", "REPÜLŐTÉRI LÉTESÍTMÉNYEK" ],
             ["Parking stands, ramp congestion, lighting,\n"
              "buildings, gate limitations etc.",
              "Állóhelyek, torlódás az előtéren, világítás\n"
              "épületek, kapuk, stb."]]),
           (DELAYCODE, FOR_MODERN,
            [None, "88", "AD",
             ["RESTRICTIONS AT\nDESTINATION AIRPORT",
              "KORLÁTOZÁSOK A\nCÉLREPÜLŐTÉREN" ],
             ["Airport and/or runway closed due to obstruction,\n"
              "industrial action, staff shortage, political unrest,\n"
              "noise abatement, night curfew, special flights",
              "A repülőtér és/vagy a futopálya bezárt akadály,\n"
              "sztrájk, munkaerőhiány, politikai megmozdulások\n"
              "zajcsökkentés, kijárási tilalom, kölönleges járatok miatt"]]),
           (DELAYCODE, FOR_MODERN,
            [None, "89", "AM",
             ["RESTRICTIONS AT\nAIRPORT OF DEPARTURE",
              "KORLÁTOZÁSOK AZ\nINDULÓ REPÜLŐTÉREN" ],
             ["Including air traffic services, start-up and pushback,\n"
              "airport and/or runway closed due to obstruction or weather\n"
              "(restriction due to weather in case of ATFM only) industrial\n"
              "action, staff shortage, political unrest, noise abatement,\n"
              "night curfew, special flights",
              "Beleértve a légiirányítás, a hajtóműindítás és hátratolás\n"
              "szüneteltetését, a repülőtér és/vagy a futopálya bezárását\n"
              "akadály vagy időjárás (csak forgalom-áramlási okokból),\n"
              "sztrájk, munkaerőhiány, politikai megmozdulások\n"
              "zajcsökkentés, kijárási tilalom, kölönleges járatok miatt"]]),

           (DELAYCODE, FOR_OT,
            ["811", "81", None,
             ["ATC", "IRÁNYÍTÁS"],
             ["E.g. lack of clearances",
              "Pl. engedélyek hiánya"]]),
           (DELAYCODE, FOR_OT,
            ["821", "82", None,
             ["SECURITY CHECK", "BIZTONSÁGI ELLENŐRZÉS"],
             ["Passenger, baggage, cargo",
              "Utas, poggyász, áru"]]),
           (DELAYCODE, FOR_OT,
            ["823", "", None,
             ["BOMB SCARE", "BOMBARIADÓ"],
             ["", ""]]),
           (DELAYCODE, FOR_OT,
            ["831", "83", None,
             ["CUSTOMS CHECKS", "VÁMHATÓSÁGI ELLENŐRZÉSEK"],
             ["", ""]]),
           (DELAYCODE, FOR_OT,
            ["833", "", None,
             ["IMMIGRATION CHECKS", "HATÁRRENDÉSZETI\nELLENŐRZÉSEK"],
             ["",  ""]]),
           (DELAYCODE, FOR_OT,
            ["835", "", None,
             ["HEALTHCARE CHECKS", "EGÉSZSÉGÜGYI ELLENŐRZÉSEK"],
             ["",  ""]]),
           (DELAYCODE, FOR_OT,
            ["841", "84", None,
             ["AIRPORT CAPACITY", "REPÜLŐTÉR KAPACITÁS"],
             ["Inadequate capacity and throughput of the airport,\n"
              "lack of stands (stairs, etc.), congestion in the\n"
              "apron and at the exists",
              "Repülőtér befogadó és áteresztő képességének elégtelensége,\n"
              "állóhely (lépcső stb.) hiánya, torlódás az előtéren,\n"
              "kijáratok zsúfoltsága"]]),
           (DELAYCODE, FOR_OT,
            ["851", "85", None,
             ["AIRPORT RESTRICTIONS", "KORLÁTOZÁSOK A REPÜLŐTÉREN"],
             ["Closed runway, industrial action, political unrest\n"
              "or noise abatement",
              "Leszállópályazárlat, sztrájk, politikai esemény\n"
              "vagy zajvédelem miatt"]]),
           (DELAYCODE, FOR_OT,
            ["861", "86", None,
             ["AIRPORT CLOSED", "TELJES REPTÉRZÁR"],
             ["E.g. due to security reasons, including all flights",
              "Pl. biztonsági okok miatt, minden járatot beleértve"]]),

           (CAPTION, FOR_MODERN | FOR_OT,
            ["Reactionary", "Visszahatások"] ),

           (DELAYCODE, FOR_MODERN | FOR_OT,
            ["911", "91", "RL",
             ["LOAD CONNECTION", "CSATLAKOZÁS"],
             ["Awaiting load from another flight",
              "Csatlakozásra várás más járatról, utas és áru"]]),
           (DELAYCODE, FOR_MODERN,
            [None, "91", "RT",
             ["THROUGH CHECK-IN ERROR", "JEGYKEZELÉSI HIBA"],
             ["Passenger or baggage check-in error at originating station",
              "Utas- vagy a csomagkezelési hiba az induló repülőtéren"]]),
           (DELAYCODE, FOR_OT,
            ["921", "91", None,
             ["CREW LATE ARRIVAL", "SZEMÉLYZET KÉSEI ÉRKEZÉSE"],
             ["Deck crew arrived later from preceding flight",
              "Személyzet kései érkezése előző járatról (deck crew)"]]),
           (DELAYCODE, FOR_MODERN,
            [None, "93", "RA",
             ["AIRCRAFT ROTATION", "REPÜLŐGÉP ROTÁCIÓ"],
             ["Late arrival of aircraft from another flight or previous sector",
              "Repülőgép kései érkezése előző járatról vagy szektorból"]]),
           (DELAYCODE, FOR_OT,
            ["931", "93", None,
             ["AIRCRAFT LATE", "REPÜLŐGÉP KÉSIK"],
             ["Late arrival of aircraft from another flight\n"
              "(not due to company reasons)",
              "Repülőgép kései érkezése előző járatról\n"
              "(nem vállalati okok miatt)"]]),
           (DELAYCODE, FOR_OT,
            ["932", "", None,
             ["AIRCRAFT LATE", "REPÜLŐGÉP KÉSIK"],
             ["Late arrival of aircraft from another flight\n"
              "(due to company reasons)",
              "Repülőgép kései érkezése előző járatról\n"
              "(vállalati okok miatt)"]]),
           (DELAYCODE, FOR_MODERN | FOR_OT,
            ["941", "94", "RS",
             ["CABIN CREW ROTATION", "UTASKÍSÉRŐK KÉSEI ÉRKEZÉSE"],
             ["Awaiting cabin crew from another flight",
              "Utaskísérők kései érkezése előző járatról"]]),
           (DELAYCODE, FOR_MODERN | FOR_OT,
            ["951", "95", "RC",
             ["CREW ROTATION", "SZEMÉLYZET KÉSEI ÉRKEZÉSE"],
             ["Awaiting flight deck, or entire crew, from another flight",
              "Teljes személyzet kései érkezése előző járatról"]]),
           (DELAYCODE, FOR_MODERN,
            [None, "96", "RO",
             ["OPERATIONS CONTROL", "ÜZEMELTETÉS"],
             ["Re-routing, diversion, consolidation, aircraft change\n"
              "for reasons other than technical",
              "Útvonalváltoztatás, repülőgép cseréje nem műszaki okokból"]]),

           (CAPTION, FOR_MODERN | FOR_OT,
            ["Miscellaneous", "Egyéb"] ),
           (DELAYCODE, FOR_OT,
            ["961", "96", None,
             ["INDUSTRIAL ACTION\nWITHIN OWN AIRLINE",
              "SZTRÁJK VÁLLALATON BELÜL"],
             ["", ""]]),
           (DELAYCODE, FOR_MODERN,
            [None, "97", "MI",
             ["INDUSTRIAL ACTION\n WITHIN OWN AIRLINE",
              "SZTRÁJK VÁLLALATON BELÜL"],
             ["", ""]]),
           (DELAYCODE, FOR_MODERN | FOR_OT,
            ["981", "98", "MO",
             ["INDUSTRIAL ACTION\nOUTSIDE OWN AIRLINE",
              "SZTRÁJK VÁLLALTON KÍVÜL"],
             ["Industrial action (except Air Traffic Control Services)",
              "Sztrájk (kivéve a légiirányítást)"]]),
           (DELAYCODE, FOR_MODERN | FOR_OT,
            ["991", "99", "MX",
             ["MISCELLANEOUS", "EGYÉB"],
             ["No suitable code; explain reason(s) in plain text",
              "A táblázatban nem szereplő egyéb ok"]])
           ])

#-------------------------------------------------------------------------------

def generateMsgStr(file, text):
    """Generate an 'msgstr' entry for the given text."""
    lines = text.splitlines()
    numLines = len(lines)
    if numLines==0:
        print("msgstr \"\"", file=file)
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
            elif type==DELAYCODE:
                columnIndex = 0
                for column in columns:
                    if isinstance(column, list):
                        for i in range(0, numLanguages):
                            if column[i]:
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

                if type==DELAYCODE:
                    print("    \"%s\": \"%s\"," % \
                      (str(columns[codeIndex]).strip(), columns[meaningIndex][0].replace("\n", "")), file=dcdata)

            print("}", file=dcdata)
            print(file=dcdata)

            tableMask <<= 1

        print("def _extract(table, row):", file=dcdata)
        print("    code = row[0].strip()", file=dcdata)
        print("    meaning = table[code] if code in table else None", file=dcdata)
        print("    return code + ((\" (\" + meaning + \")\") if meaning else \"\")", file=dcdata)
        print(file=dcdata)

        tableMask = 1
        for i in range(0, len(tablePrefixes)):

            print("_%s_data = (" % (tablePrefixes[i],), file=dcdata)
            print("    lambda row: _extract(_%s_code2meaning, row)," % \
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
                elif type==DELAYCODE:
                    print("        (DELAYCODE, [", file=dcdata)
                    for j in columnIndexes:
                        column = columns[j]
                        if j!=columnIndexes[0]:
                            print(",", file=dcdata)
                        if isinstance(column, list):
                            if column[0]:
                                print("            xstr(\"%srow%d_col%d\")"  % \
                                (poPrefix, rowIndex, j), end=' ', file=dcdata)
                            else:
                                print("            \"\"", end=' ', file=dcdata)
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
