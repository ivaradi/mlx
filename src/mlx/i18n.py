# Internationalization support
# -*- coding: utf-8 -*-

#------------------------------------------------------------------------------

_strings = None
_fallback = None

#------------------------------------------------------------------------------

def setLanguage(language):
    """Setup the internationalization support for the given language."""
    print "i18n.setLanguage", language
    _Strings.set(language)
    
#------------------------------------------------------------------------------

def xstr(key):
    """Get the string for the given key in the current language.

    If not found, the fallback language is searched. If that is not found
    either, the key itself is returned within curly braces."""
    s = _Strings.current()[key]
    if s is None:
        s = _Strings.fallback()[key]
    return "{" + key + "}" if s is None else s
    
#------------------------------------------------------------------------------

class _Strings(object):
    """A collection of strings belonging to a certain language."""
    # The registry of the string collections. This is a mapping from
    # language codes to the actual collection objects
    _instances = {}

    # The fallback instance
    _fallback = None

    # The currently used instance.
    _current = None

    @staticmethod
    def _find(language):
        """Find an instance for the given language.

        First the language is searched for as is. If not found, it is truncated
        from the end until the last underscore and that is searched for. And so
        on, until no underscore remains.

        If nothing is found this way, the 
        """
        while language:
            if language in _Strings._instances:
                return _Strings._instances[language]
            underscoreIndex = language.rfind("_")
            language = language[:underscoreIndex] if underscoreIndex>0 else ""
        return _Strings._fallback

    @staticmethod
    def set(language):
        """Set the string for the given language.

        A String instance is searched for the given language (see
        _Strings._find()). Otherwise the fallback language is used."""
        strings = _Strings._find(language)
        assert strings is not None
        if _Strings._current is not None and \
           _Strings._current is not _Strings._fallback:
            _Strings._current.finalize()
        if strings is not _Strings._fallback:
            strings.initialize()
        _Strings._current = strings

    @staticmethod
    def fallback():
        """Get the fallback."""
        return _Strings._fallback

    @staticmethod
    def current():
        """Get the current."""
        return _Strings._current

    def __init__(self, languages, fallback = False):
        """Construct an empty strings object."""
        self._strings = {}
        for language in languages:
            _Strings._instances[language] = self
        if fallback:
            _Strings._fallback = self
            self.initialize()

    def initialize(self):
        """Initialize the strings.

        This should be overridden in children to setup the strings."""
        pass

    def finalize(self):
        """Finalize the object.

        This releases the string dictionary to free space."""
        self._strings = {}

    def add(self, id, s):
        """Add the given text as the string with the given ID.

        If the ID is already in the object, that is an assertion failure!"""
        assert id not in self._strings
        self._strings[id] = s

    def __getitem__(self, key):
        """Get the string  with the given key."""
        return self._strings[key] if key in self._strings else None

#------------------------------------------------------------------------------

class _English(_Strings):
    """The strings for the English language."""
    def __init__(self):
        """Construct the object."""
        super(_English, self).__init__(["en_GB", "en"], fallback = True)

    def initialize(self):
        """Initialize the strings."""
        self.add("tab_flight", "_Flight")
        self.add("tab_flight_tooltip", "Flight wizard")
        self.add("tab_flight_info", "Flight _info")
        self.add("tab_flight_info_tooltip", "Further information regarding the flight")
        self.add("tab_log", "_Log")
        self.add("tab_log_tooltip",
                 "The log of your flight that will be sent to the MAVA website")
        self.add("tab_debug_log", "_Debug log")
        self.add("tab_help", "_Help")
        self.add("tab_gates", "_Gates")

        self.add("conn_failed", "Cannot connect to the simulator.")
        self.add("conn_failed_sec",
                 "Rectify the situation, and press <b>Try again</b> "
                 "to try the connection again, " 
                 "or <b>Cancel</b> to cancel the flight.")
        self.add("conn_broken",
                 "The connection to the simulator failed unexpectedly.")
        self.add("conn_broken_sec",
                 "If the simulator has crashed, restart it "
                 "and restore your flight as much as possible "
                 "to the state it was in before the crash. "
                 "Then press <b>Reconnect</b> to reconnect.\n\n"
                 "If you want to cancel the flight, press <b>Cancel</b>.")
        self.add("button_cancel", "_Cancel")
        self.add("button_tryagain", "_Try again")
        self.add("button_reconnect", "_Reconnect")
        
        self.add("login", "Login")
        self.add("loginHelp",
                 "Enter your MAVA pilot's ID and password to\n" \
                 "log in to the MAVA website and download\n" \
                 "your booked flights.")
        self.add("label_pilotID", "Pil_ot ID:")
        self.add("login_pilotID_tooltip",
                 "Enter your MAVA pilot's ID. This usually starts with a "
                 "'P' followed by 3 digits.")
        self.add("label_password", "_Password:")
        self.add("login_password_tooltip",
                 "Enter the password for your pilot's ID")
        self.add("remember_password", "_Remember password")
        self.add("login_remember_tooltip",
                 "If checked, your password will be stored, so that you should "
                 "not have to enter it every time. Note, however, that the password "
                 "is stored as text, and anybody who can access your files will "
                 "be able to read it.")
        self.add("button_login", "Logi_n")
        self.add("login_button_tooltip", "Click to log in.")
        self.add("login_busy", "Logging in...")
        self.add("login_invalid", "Invalid pilot's ID or password.")
        self.add("login_invalid_sec",
                 "Check the ID and try to reenter the password.")
        self.add("login_failconn",
                 "Failed to connect to the MAVA website.")
        self.add("login_failconn_sec", "Try again in a few minutes.")

        self.add("button_next", "_Next")
        self.add("button_next_tooltip", "Click to go to the next page.")
        self.add("button_previous", "_Previous")
        self.add("button_previous_tooltip", "Click to go to the previous page.")

        self.add("flightsel_title", "Flight selection")
        self.add("flightsel_help", "Select the flight you want to perform.")
        self.add("flightsel_chelp", "You have selected the flight highlighted below.")
        self.add("flightsel_no", "Flight no.")
        self.add("flightsel_deptime", "Departure time [UTC]")
        self.add("flightsel_from", "From")
        self.add("flightsel_to", "To")

        self.add("fleet_busy", "Retrieving fleet...")
        self.add("fleet_failed",
                 "Failed to retrieve the information on the fleet.")
        self.add("fleet_update_busy", "Updating plane status...")
        self.add("fleet_update_failed",
                 "Failed to update the status of the airplane.")
        
        self.add("gatesel_title", "LHBP gate selection")
        self.add("gatesel_help",
                 "The airplane's gate position is invalid.\n\n" \
                 "Select the gate from which you\n" \
                 "would like to begin the flight.")
        self.add("gatesel_conflict", "Gate conflict detected again.")
        self.add("gatesel_conflict_sec",
                 "Try to select a different gate.")

        self.add("connect_title", "Connect to the simulator")
        self.add("connect_help",
                 "Load the aircraft below into the simulator and park it\n" \
                 "at the given airport, at the gate below, if present.\n\n" \
                 "Then press the Connect button to connect to the simulator.")
        self.add("connect_chelp",
                 "The basic data of your flight can be read below.")
        self.add("connect_flightno", "Flight number:")
        self.add("connect_acft", "Aircraft:")
        self.add("connect_tailno", "Tail number:")
        self.add("connect_airport", "Airport:")
        self.add("connect_gate", "Gate:")
        self.add("button_connect", "_Connect")
        self.add("button_connect_tooltip", "Click to connect to the simulator.")
        self.add("connect_busy", "Connecting to the simulator...")

        self.add("payload_title", "Payload")
        self.add("payload_help",
                 "The briefing contains the weights below.\n" \
                 "Setup the cargo weight here and the payload weight "
                 "in the simulator.\n\n" \
                 "You can also check here what the simulator reports as ZFW.")
        self.add("payload_chelp",
                 "You can see the weights in the briefing\n" \
                 "and the cargo weight you have selected below.\n\n" \
                 "You can also query the ZFW reported by the simulator.")
        self.add("payload_crew", "Crew:")
        self.add("payload_pax", "Passengers:")
        self.add("payload_bag", "Baggage:")
        self.add("payload_cargo", "_Cargo:")
        self.add("payload_cargo_tooltip",
                 "The weight of the cargo for your flight.")
        self.add("payload_mail", "Mail:")
        self.add("payload_zfw", "Calculated ZFW:")
        self.add("payload_fszfw", "_ZFW from FS:")
        self.add("payload_fszfw_tooltip",
                 "Click here to refresh the ZFW value from the simulator.")
        self.add("payload_zfw_busy", "Querying ZFW...")

        self.add("time_title", "Time")
        self.add("time_help",
                 "The departure and arrival times are displayed below in UTC.\n\n" \
                 "You can also query the current UTC time from the simulator.\n" \
                 "Ensure that you have enough time to properly prepare for the flight.")
        self.add("time_chelp",
                 "The departure and arrival times are displayed below in UTC.\n\n" \
                 "You can also query the current UTC time from the simulator.\n")
        self.add("time_departure", "Departure:")
        self.add("time_arrival", "Arrival:")
        self.add("time_fs", "_Time from FS:")
        self.add("time_fs_tooltip",
                 "Click here to query the current UTC time from the simulator.")
        self.add("time_busy", "Querying time...")

        self.add("route_title", "Route")
        self.add("route_help",
                 "Set your cruise flight level below, and\n" \
                 "if necessary, edit the flight plan.")
        self.add("route_chelp",
                 "If necessary, you can modify the cruise level and\n" \
                 "the flight plan below during flight.\n" \
                 "If so, please, add a comment on why " \
                 "the modification became necessary.")
        self.add("route_level", "_Cruise level:")
        self.add("route_level_tooltip",
                 "The cruise flight level. Click on the arrows to increment "
                 "or decrement by 10, or enter the number on the keyboard.")
        self.add("route_route", "_Route")
        self.add("route_route_tooltip",
                 "The planned flight route in the standard format.")
        self.add("route_down_notams", "Downloading NOTAMs...")
        self.add("route_down_metars", "Downloading METARs...")

        self.add("briefing_title", "Briefing (%d/2): %s")
        self.add("briefing_departure", "departure")
        self.add("briefing_arrival", "arrival")
        self.add("briefing_help",
                 "Read carefully the NOTAMs and METAR below.\n\n" \
                 "You can edit the METAR if your simulator or network\n" \
                 "provides different weather.")
        self.add("briefing_chelp",
                 "If your simulator or network provides a different\n" \
                 "weather, you can edit the METAR below.")
        self.add("briefing_notams_init", "LHBP NOTAMs")
        self.add("briefing_metar_init", "LHBP METAR")
        self.add("briefing_button",
                 "I have read the briefing and am _ready to fly!")
        self.add("briefing_notams_template", "%s NOTAMs")
        self.add("briefing_metar_template", "%s _METAR")
        self.add("briefing_notams_failed", "Could not download NOTAMs")
        self.add("briefing_notams_missing",
                 "Could not download NOTAM for this airport")
        self.add("briefing_metar_failed", "Could not download METAR")

        self.add("takeoff_title", "Takeoff")
        self.add("takeoff_help",
                 "Enter the runway and SID used, as well as the speeds.")
        self.add("takeoff_chelp",
                 "The runway, SID and takeoff speeds logged can be seen below.")
        self.add("takeoff_runway", "Run_way:")
        self.add("takeoff_runway_tooltip",
                 "The runway the takeoff is performed from.")
        self.add("takeoff_sid", "_SID:")
        self.add("takeoff_sid_tooltip",
                 "The name of the Standard Instrument Deparature procedure followed.")
        self.add("takeoff_v1", "V<sub>_1</sub>:")
        self.add("takeoff_v1_tooltip", "The takeoff decision speed in knots.")
        self.add("label_knots", "knots")
        self.add("takeoff_vr", "V<sub>_R</sub>:")
        self.add("takeoff_vr_tooltip", "The takeoff rotation speed in knots.")
        self.add("takeoff_v2", "V<sub>_2</sub>:")
        self.add("takeoff_v2_tooltip", "The takeoff safety speed in knots.")

        self.add("landing_title", "Landing")
        self.add("landing_help",
                 "Enter the STAR and/or transition, runway,\n" \
                 "approach type and V<sub>Ref</sub> used.")
        self.add("landing_chelp",
                 "The STAR and/or transition, runway, approach\n" \
                 "type and V<sub>Ref</sub> logged can be seen below.")
        self.add("landing_star", "_STAR:")
        self.add("landing_star_tooltip",
                 "The name of Standard Terminal Arrival Route followed.")
        self.add("landing_transition", "_Transition:")
        self.add("landing_transition_tooltip",
                 "The name of transition executed or VECTORS if vectored by ATC.")
        self.add("landing_runway", "Run_way:")
        self.add("landing_runway_tooltip",
                 "The runway the landing is performed on.")
        self.add("landing_approach", "_Approach type:")
        self.add("landing_approach_tooltip",
                 "The type of the approach, e.g. ILS or VISUAL.")
        self.add("landing_vref", "V<sub>_Ref</sub>:")
        self.add("landing_vref_tooltip",
                 "The landing reference speed in knots.")

        self.add("flighttype_scheduled", "scheduled")
        self.add("flighttype_ot", "old-timer")
        self.add("flighttype_vip", "VIP")
        self.add("flighttype_charter", "charter")

        self.add("finish_title", "Finish")
        self.add("finish_help",
                 "There are some statistics about your flight below.\n\n" \
                 "Review the data, also on earlier pages, and if you are\n" \
                 "satisfied, you can save or send your PIREP.")
        self.add("finish_rating", "Flight rating:")
        self.add("finish_flight_time", "Flight time:")
        self.add("finish_block_time", "Block time:")
        self.add("finish_distance", "Distance flown:")
        self.add("finish_fuel", "Fuel used:")
        self.add("finish_type", "_Type:")
        self.add("finish_type_tooltip", "Select the type of the flight.")
        self.add("finish_online", "_Online flight")
        self.add("finish_online_tooltip",
                 "Check if your flight was online, uncheck otherwise.")
        self.add("finish_save", "S_ave PIREP...")
        self.add("finish_save_tooltip",
                 "Click to save the PIREP into a file on your computer. " \
                 "The PIREP can be loaded and sent later.")
        self.add("finish_send", "_Send PIREP...")
        self.add("finish_send_tooltip",
                 "Click to send the PIREP to the MAVA website for further review.")
        self.add("finish_send_busy", "Sending PIREP...")
        self.add("finish_send_success",
                 "The PIREP was sent successfully.")
        self.add("finish_send_success_sec",
                 "Await the thorough scrutiny by our fearless PIREP reviewers! :)")
        self.add("finish_send_already",
                 "The PIREP for this flight has already been sent!")
        self.add("finish_send_already_sec",
                 "You may clear the old PIREP on the MAVA website.")
        self.add("finish_send_notavail",
                 "This flight is not available anymore!")
        self.add("finish_send_unknown",
                 "The MAVA website returned with an unknown error.")
        self.add("finish_send_unknown_sec",
                 "See the debug log for more information.")
        self.add("finish_send_failed",
                 "Could not send the PIREP to the MAVA website.")
        self.add("finish_send_failed_sec",
                 "This can be a network problem, in which case\n" \
                 "you may try again later. Or it can be a bug;\n" \
                 "see the debug log for more information.")
                 
#------------------------------------------------------------------------------

class _Hungarian(_Strings):
    """The strings for the Hungarian language."""
    def __init__(self):
        """Construct the object."""
        super(_Hungarian, self).__init__(["hu_HU", "hu"])

    def initialize(self):
        """Initialize the strings."""
        self.add("tab_flight", "_Járat")
        self.add("tab_flight_tooltip", "Járat varázsló")
        self.add("tab_flight_info", "Járat _info")
        self.add("tab_flight_info_tooltip", "Egyéb információk a járat teljesítésével kapcsolatban")
        self.add("tab_log", "_Napló")
        self.add("tab_log_tooltip",
                 "A járat naplója, amit majd el lehet küldeni a MAVA szerverére")
        self.add("tab_debug_log", "_Debug napló")
        self.add("tab_help", "_Segítség")
        self.add("tab_gates", "_Kapuk")        

        self.add("conn_failed", "Nem tudtam kapcsolódni a szimulátorhoz.")
        self.add("conn_failed_sec",
                 "Korrigáld a problémát, majd nyomd meg az "
                 "<b>Próbáld újra</b> gombot a újrakapcsolódáshoz, "
                 "vagy a <b>Mégse</b> gombot a járat megszakításához.")
        self.add("conn_broken",
                 "A szimulátorral való kapcsolat váratlanul megszakadt.")
        self.add("conn_broken_sec",
                 "Ha a szimulátor elszállt, indítsd újra "
                 "és állítsd vissza a repülésed elszállás előtti "
                 "állapotát amennyire csak lehet. "
                 "Ezután nyomd meg az <b>Újrakapcsolódás</b> gombot "
                 "a kapcsolat ismételt felvételéhez.\n\n"
                 "Ha meg akarod szakítani a repülést, nyomd meg a "
                 "<b>Mégse</b> gombot.")
        self.add("button_cancel", "_Mégse")
        self.add("button_tryagain", "_Próbáld újra")
        self.add("button_reconnect", "Újra_kapcsolódás")
        
        self.add("login", "Bejelentkezés")
        self.add("loginHelp",
                 "Írd be a MAVA pilóta azonosítódat és a\n" \
                 "bejelentkezéshez használt jelszavadat,\n" \
                 "hogy választhass a foglalt járataid közül.")
        self.add("label_pilotID", "_Azonosító:")
        self.add("login_pilotID_tooltip",
                 "Írd be a MAVA pilóta azonosítódat. Ez általában egy 'P' "
                 "betűvel kezdődik, melyet 3 számjegy követ.")
        self.add("label_password", "Je_lszó:")
        self.add("login_password_tooltip",
                 "Írd be a pilóta azonosítódhoz tartozó jelszavadat.")
        self.add("remember_password", "_Emlékezz a jelszóra")
        self.add("login_remember_tooltip",
                 "Ha ezt kiválasztod, a jelszavadat eltárolja a program, így "
                 "nem kell mindig újból beírnod. Vedd azonban figyelembe, "
                 "hogy a jelszót szövegként tároljuk, így bárki elolvashatja, "
                 "aki hozzáfér a fájljaidhoz.")
        self.add("button_login", "_Bejelentkezés")
        self.add("login_button_tooltip", "Kattints ide a bejelentkezéshez.")
        self.add("login_busy", "Bejelentkezés...")
        self.add("login_invalid", "Érvénytelen azonosító vagy jelszó.")
        self.add("login_invalid_sec",
                 "Ellenőrízd az azonosítót, és próbáld meg újra beírni a jelszót.")
        self.add("login_failconn",
                 "Nem sikerült kapcsolódni a MAVA honlaphoz.")
        self.add("login_failconn_sec", "Próbáld meg pár perc múlva.")
        
        self.add("button_next", "_Előre")
        self.add("button_next_tooltip",
                 "Kattints ide, hogy a következő lapra ugorj.")
        self.add("button_previous", "_Vissza")
        self.add("button_previous_tooltip",
                 "Kattints ide, hogy az előző lapra ugorj.")

        self.add("flightsel_title", "Járatválasztás")
        self.add("flightsel_help", "Válaszd ki a járatot, amelyet le szeretnél repülni.")
        self.add("flightsel_chelp", "A lent kiemelt járatot választottad.")
        self.add("flightsel_no", "Járatszám")
        self.add("flightsel_deptime", "Indulás ideje [UTC]")
        self.add("flightsel_from", "Honnan")
        self.add("flightsel_to", "Hová")

        self.add("fleet_busy", "Flottaadatok letöltése...")
        self.add("fleet_failed",
                 "Nem sikerült letöltenem a flotta adatait.")
        self.add("fleet_update_busy", "Repülőgép pozíció frissítése...")
        self.add("fleet_update_failed",
                 "Nem sikerült frissítenem a repülőgép pozícióját.")

        self.add("gatesel_title", "LHBP kapuválasztás")
        self.add("gatesel_help",
                 "A repülőgép kapu pozíciója érvénytelen.\n\n" \
                 "Válaszd ki azt a kaput, ahonnan\n" \
                 "el szeretnéd kezdeni a járatot.")
        self.add("gatesel_conflict", "Ismét kapuütközés történt.")
        self.add("gatesel_conflict_sec",
                 "Próbálj egy másik kaput választani.")

        self.add("connect_title", "Kapcsolódás a szimulátorhoz")
        self.add("connect_help",
                 "Tölsd be a lent látható repülőgépet a szimulátorba\n" \
                 "az alább megadott reptérre és kapuhoz.\n\n" \
                 "Ezután nyomd meg a Kapcsolódás gombot a kapcsolódáshoz.")
        self.add("connect_chelp",
                 "A járat alapadatai lent olvashatók.")
        self.add("connect_flightno", "Járatszám:")
        self.add("connect_acft", "Típus:")
        self.add("connect_tailno", "Lajstromjel:")
        self.add("connect_airport", "Repülőtér:")
        self.add("connect_gate", "Kapu:")
        self.add("button_connect", "K_apcsolódás")
        self.add("button_connect_tooltip",
                 "Kattints ide a szimulátorhoz való kapcsolódáshoz.")
        self.add("connect_busy", "Kapcsolódás a szimulátorhoz...")

        self.add("payload_title", "Terhelés")
        self.add("payload_help",
                 "Az eligazítás az alábbi tömegeket tartalmazza.\n" \
                 "Allítsd be a teherszállítmány tömegét itt, a hasznos "
                 "terhet pedig a szimulátorban.\n\n" \
                 "Azt is ellenőrízheted, hogy a szimulátor milyen ZFW-t jelent.")
        self.add("payload_chelp",
                 "Lent láthatók az eligazításban szereplő tömegek, valamint\n" \
                 "a teherszállítmány általad megadott tömege.\n\n" \
                 "Azt is ellenőrízheted, hogy a szimulátor milyen ZFW-t jelent.")
        self.add("payload_crew", "Legénység:")
        self.add("payload_pax", "Utasok:")
        self.add("payload_bag", "Poggyász:")
        self.add("payload_cargo", "_Teher:")
        self.add("payload_cargo_tooltip",
                 "A teherszállítmány tömege.")
        self.add("payload_mail", "Posta:")
        self.add("payload_zfw", "Kiszámolt ZFW:")
        self.add("payload_fszfw", "_ZFW a szimulátorból:")
        self.add("payload_fszfw_tooltip",
                 "Kattints ide, hogy frissítsd a ZFW értékét a szimulátorból.")
        self.add("payload_zfw_busy", "ZFW lekérdezése...")
        
        self.add("time_title", "Menetrend")
        self.add("time_help",
                 "Az indulás és az érkezés ideje lent látható UTC szerint.\n\n" \
                 "A szimulátor aktuális UTC szerinti idejét is lekérdezheted.\n" \
                 "Győzödj meg arról, hogy elég időd van a repülés előkészítéséhez.")
        self.add("time_chelp",
                 "Az indulás és az érkezés ideje lent látható UTC szerint.\n\n" \
                 "A szimulátor aktuális UTC szerinti idejét is lekérdezheted.")
        self.add("time_departure", "Indulás:")
        self.add("time_arrival", "Érkezés:")
        self.add("time_fs", "Idő a s_zimulátorból:")
        self.add("time_fs_tooltip",
                 "Kattings ide, hogy frissítsd a szimulátor aktuális UTC szerint idejét.")
        self.add("time_busy", "Idő lekérdezése...")

        self.add("route_title", "Útvonal")
        self.add("route_help",
                 "Állítsd be az utazószintet lent, és ha szükséges,\n" \
                 "módosítsd az útvonaltervet.")
        self.add("route_chelp",
                 "Ha szükséges, lent módosíthatod az utazószintet és\n" \
                 "az útvonaltervet repülés közben is.\n" \
                 "Ha így teszel, légy szíves a megjegyzés mezőben " \
                 "ismertesd ennek okát.")
        self.add("route_level", "_Utazószint:")
        self.add("route_level_tooltip", "Az utazószint.")
        self.add("route_route", "Út_vonal")
        self.add("route_route_tooltip", "Az útvonal a szokásos formátumban.")
        self.add("route_down_notams", "NOTAM-ok letöltése...")
        self.add("route_down_metars", "METAR-ok letöltése...")
        
        self.add("briefing_title", "Eligazítás (%d/2): %s")
        self.add("briefing_departure", "indulás")
        self.add("briefing_arrival", "érkezés")
        self.add("briefing_help",
                 "Olvasd el figyelmesen a lenti NOTAM-okat és METAR-t.\n\n" \
                 "Ha a szimulátor vagy hálózat más időjárást ad,\n" \
                 "a METAR-t módosíthatod.")
        self.add("briefing_chelp",
                 "Ha a szimulátor vagy hálózat más időjárást ad,\n" \
                 "a METAR-t módosíthatod.")
        self.add("briefing_notams_init", "LHBP NOTAM-ok")
        self.add("briefing_metar_init", "LHBP METAR")
        self.add("briefing_button",
                 "Elolvastam az eligazítást, és készen állok a _repülésre!")
        self.add("briefing_notams_template", "%s NOTAM-ok")
        self.add("briefing_metar_template", "%s _METAR")
        self.add("briefing_notams_failed", "Nem tudtam letölteni a NOTAM-okat.")
        self.add("briefing_notams_missing",
                 "Ehhez a repülőtérhez nem találtam NOTAM-ot.")
        self.add("briefing_metar_failed", "Nem tudtam letölteni a METAR-t.")
        
        self.add("takeoff_title", "Felszállás")
        self.add("takeoff_help",
                 "Írd be a felszállásra használt futópálya és SID nevét, valamint a sebességeket.")
        self.add("takeoff_chelp",
                 "A naplózott futópálya, SID és a sebességek lent olvashatók.")
        self.add("takeoff_runway", "_Futópálya:")
        self.add("takeoff_runway_tooltip",
                 "A felszállásra használt futópálya.")
        self.add("takeoff_sid", "_SID:")
        self.add("takeoff_sid_tooltip",
                 "Az alkalmazott szabványos műszeres indulási eljárás neve.")
        self.add("takeoff_v1", "V<sub>_1</sub>:")
        self.add("takeoff_v1_tooltip", "Az elhatározási sebesség csomóban.")
        self.add("label_knots", "csomó")
        self.add("takeoff_vr", "V<sub>_R</sub>:")
        self.add("takeoff_vr_tooltip", "Az elemelkedési sebesség csomóban.")
        self.add("takeoff_v2", "V<sub>_2</sub>:")
        self.add("takeoff_v2_tooltip", "A biztonságos emelkedési sebesség csomóban.")
        
        self.add("landing_title", "Leszállás")
        self.add("landing_help",
                 "Írd be az alkalmazott STAR és/vagy bevezetési eljárás nevét,\n"
                 "a használt futópályát, a megközelítés módját, és a V<sub>Ref</sub>-et.")
        self.add("landing_chelp",
                 "Az alkalmazott STAR és/vagy bevezetési eljárás neve, a használt\n"
                 "futópálya, a megközelítés módja és a V<sub>Ref</sub> lent olvasható.")
        self.add("landing_star", "_STAR:")
        self.add("landing_star_tooltip",
                 "A követett szabványos érkezési eljárás neve.")
        self.add("landing_transition", "_Bevezetés:")
        self.add("landing_transition_tooltip",
                 "Az alkalmazott bevezetési eljárás neve, vagy VECTORS, "
                 "ha az irányítás vezetett be.")
        self.add("landing_runway", "_Futópálya:")
        self.add("landing_runway_tooltip",
                 "A leszállásra használt futópálya.")
        self.add("landing_approach", "_Megközelítés típusa:")
        self.add("landing_approach_tooltip",
                 "A megközelítgés típusa, pl. ILS vagy VISUAL.")
        self.add("landing_vref", "V<sub>_Ref</sub>:")
        self.add("landing_vref_tooltip",
                 "A leszállási sebesség csomóban.")
        
        self.add("flighttype_scheduled", "menetrendszerinti")
        self.add("flighttype_ot", "old-timer")
        self.add("flighttype_vip", "VIP")
        self.add("flighttype_charter", "charter")

        self.add("finish_title", "Lezárás")
        self.add("finish_help",
                 "Lent olvasható némi statisztika a járat teljesítéséről.\n\n" \
                 "Ellenőrízd az adatokat, az előző oldalakon is, és ha\n" \
                 "megfelelnek, elmentheted vagy elküldheted a PIREP-et.")
        self.add("finish_rating", "Pontszám:")
        self.add("finish_flight_time", "Repülési idő:")
        self.add("finish_block_time", "Blokk idő:")
        self.add("finish_distance", "Repült táv:")
        self.add("finish_fuel", "Elhasznált üzemanyag:")
        self.add("finish_type", "_Típus:")
        self.add("finish_type_tooltip", "Válaszd ki a repülés típusát.")
        self.add("finish_online", "_Online repülés")
        self.add("finish_online_tooltip",
                 "Jelöld be, ha a repülésed a hálózaton történt, egyébként " \
                 "szűntesd meg a kijelölést.")
        self.add("finish_save", "PIREP _mentése...")
        self.add("finish_save_tooltip",
                 "Kattints ide, hogy elmenthesd a PIREP-et egy fájlba a számítógépeden. " \
                 "A PIREP-et később be lehet tölteni és el lehet küldeni.")
        self.add("finish_send", "PIREP _elküldése...")
        self.add("finish_send_tooltip",
                 "Kattints ide, hogy elküldd a PIREP-et a MAVA szerverére javításra.")
        self.add("finish_send_busy", "PIREP küldése...")
        self.add("finish_send_success",
                 "A PIREP elküldése sikeres volt.")
        self.add("finish_send_success_sec",
                 "Várhatod félelmet nem ismerő PIREP javítóink alapos észrevételeit! :)")
        self.add("finish_send_already",
                 "Ehhez a járathoz már küldtél be PIREP-et!")
        self.add("finish_send_already_sec",
                 "A korábban beküldött PIREP-et törölheted a MAVA honlapján.")
        self.add("finish_send_notavail",
                 "Ez a járat már nem elérhető!")
        self.add("finish_send_unknown",
                 "A MAVA szervere ismeretlen hibaüzenettel tért vissza.")
        self.add("finish_send_unknown_sec",
                 "A debug naplóban részletesebb információt találsz.")
        self.add("finish_send_failed",
                 "Nem tudtam elküldeni a PIREP-et a MAVA szerverére.")
        self.add("finish_send_failed_sec",
                 "Lehet, hogy hálózati probléma áll fenn, amely esetben később\n" \
                 "újra próbálkozhatsz. Lehet azonban hiba is a loggerben:\n" \
                 "részletesebb információt találhatsz a debug naplóban.")
                 
#------------------------------------------------------------------------------

# The fallback language is English
_English()

# We also support Hungarian
_Hungarian()

#------------------------------------------------------------------------------
