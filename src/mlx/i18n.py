# Internationalization support
# -*- coding: utf-8 -*-

#------------------------------------------------------------------------------

import locale

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

    def __iter__(self):
        """Return an iterator over the keys in the string set."""
        return iter(self._strings)

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
        self.add("aircraft_b736", "Boeing 737-600")
        self.add("aircraft_b737", "Boeing 737-700")
        self.add("aircraft_b738", "Boeing 737-800")
        self.add("aircraft_b733", "Boeing 737-300")
        self.add("aircraft_b734", "Boeing 737-400")
        self.add("aircraft_b735", "Boeing 737-500")
        self.add("aircraft_dh8d", "Bombardier Dash 8 Q400")
        self.add("aircraft_b762", "Boeing 767-200")
        self.add("aircraft_b763", "Boeing 767-300")
        self.add("aircraft_crj2", "Canadair Regional Jet CRJ-200")
        self.add("aircraft_f70",  "Fokker F70")
        self.add("aircraft_dc3",  "Lisunov Li-2")
        self.add("aircraft_t134", "Tupolev Tu-134")
        self.add("aircraft_t154", "Tupolev Tu-154")
        self.add("aircraft_yk40", "Yakovlev Yak-40")

        self.add("button_ok", "_OK")
        self.add("button_cancel", "_Cancel")
        self.add("button_yes", "_Yes")
        self.add("button_no", "_No")
        self.add("button_browse", "Browse...")
        
        self.add("menu_file", "File")
        self.add("menu_file_loadPIREP", "_Load PIREP...")
        self.add("menu_file_loadPIREP_key", "l")
        self.add("menu_file_quit", "_Quit")
        self.add("menu_file_quit_key", "q")
        self.add("quit_question", "Are you sure to quit the logger?")

        self.add("menu_tools", "Tools")
        self.add("menu_tools_chklst", "_Checklist Editor")
        self.add("menu_tools_chklst_key", "c")
        self.add("menu_tools_prefs", "_Preferences")
        self.add("menu_tools_prefs_key", "p")

        self.add("menu_view", "View")
        self.add("menu_view_monitor", "Show _monitor window")
        self.add("menu_view_monitor_key", "m")
        self.add("menu_view_debug", "Show _debug log")
        self.add("menu_view_debug_key", "d")
        
        self.add("tab_flight", "_Flight")
        self.add("tab_flight_tooltip", "Flight wizard")
        self.add("tab_flight_info", "Flight _info")
        self.add("tab_flight_info_tooltip", "Further information regarding the flight")
        self.add("tab_weight_help", "_Help")
        self.add("tab_weight_help_tooltip", "Help to calculate the weights")
        self.add("tab_log", "_Log")
        self.add("tab_log_tooltip",
                 "The log of your flight that will be sent to the MAVA website")
        self.add("tab_gates", "_Gates")        
        self.add("tab_gates_tooltip", "The status of the MAVA fleet and the gates at LHBP")        
        self.add("tab_debug_log", "_Debug log")
        self.add("tab_debug_log_tooltip", "Log with debugging information.")

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

        self.add("fuel_title", "Fuel")
        self.add("fuel_help",
                 "Enter the amount of fuel in kilograms that need to be "
                 "present in each tank below.\n\n"
                 "When you press <b>Next</b>, the necessary amount of fuel\n"
                 "will be pumped into or out of the tanks.")
        self.add("fuel_chelp",
                 "The amount of fuel tanked into your aircraft at the\n"
                 "beginning of the flight can be seen below.")

        self.add("fuel_tank_centre", "_Centre\n")
        self.add("fuel_tank_left", "L_eft\n")
        self.add("fuel_tank_right", "_Right\n")
        self.add("fuel_tank_left_aux", "Left\nA_ux")
        self.add("fuel_tank_right_aux", "Right\nAu_x")
        self.add("fuel_tank_left_tip", "Left\n_Tip")
        self.add("fuel_tank_right_tip", "Right\nTip")
        self.add("fuel_tank_external1", "External\n_1")
        self.add("fuel_tank_external2", "External\n_2")
        self.add("fuel_tank_centre2", "Ce_ntre\n2")
        self.add("fuel_get_busy", "Querying fuel information...")
        self.add("fuel_pump_busy", "Pumping fuel...")
        self.add("fuel_tank_tooltip",
                 "This part displays the current level of the fuel in the "
                 "compared to its capacity. The "
                 '<span color="turquoise">turquoise</span> '
                 "slider shows the level that should be loaded into the tank "
                 "for the flight. You can click anywhere in the widget to "
                 "move the slider there. Or you can grab it by holding down "
                 "the left button of your mouse, and move the pointer up or "
                 "down. The scroll wheel on your mouse also increments or "
                 "decrements the amount of fuel by 10. If you hold down "
                 "the <b>Shift</b> key while scrolling, the steps will be "
                 "100, or with the <b>Control</b> key, 1.")

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
        self.add("finish_gate", "_Arrival gate:")
        self.add("finish_gate_tooltip",
                 "Select the gate or stand at which you have arrived to LHBP.")
        self.add("finish_save", "Sa_ve PIREP...")
        self.add("finish_save_tooltip",
                 "Click to save the PIREP into a file on your computer. " \
                 "The PIREP can be loaded and sent later.")
        self.add("finish_save_title", "Save PIREP into")
        self.add("finish_save_done", "The PIREP was saved successfully")
        self.add("finish_save_failed", "Failed to save the PIREP")
        self.add("finish_save_failed_sec", "See the debug log for the details.")

        # C D
        
        self.add("info_comments", "_Comments")
        self.add("info_defects", "Flight _defects")
        self.add("info_delay", "Delay codes")

        # O V N E Y T R A W P
        
        self.add("info_delay_loading", "L_oading problems")
        self.add("info_delay_vatsim", "_VATSIM problem")
        self.add("info_delay_net", "_Net problems")
        self.add("info_delay_atc", "Controll_er's fault")
        self.add("info_delay_system", "S_ystem crash/freeze")
        self.add("info_delay_nav", "Naviga_tion problem")
        self.add("info_delay_traffic", "T_raffic problems")
        self.add("info_delay_apron", "_Apron navigation problem")
        self.add("info_delay_weather", "_Weather problems")
        self.add("info_delay_personal", "_Personal reasons")

        self.add("statusbar_conn_tooltip",
                 'The state of the connection.\n'
                 '<span foreground="grey">Grey</span> means idle.\n'
                 '<span foreground="red">Red</span> means trying to connect.\n'
                 '<span foreground="green">Green</span> means connected.')
        self.add("statusbar_stage_tooltip", "The flight stage")
        self.add("statusbar_time_tooltip", "The simulator time in UTC")
        self.add("statusbar_rating_tooltip", "The flight rating")
        self.add("statusbar_busy_tooltip", "The status of the background tasks.")

        self.add("flight_stage_boarding", "boarding")
        self.add("flight_stage_pushback and taxi", "pushback and taxi")
        self.add("flight_stage_takeoff", "takeoff")
        self.add("flight_stage_RTO", "RTO")
        self.add("flight_stage_climb", "climb")
        self.add("flight_stage_cruise", "cruise")
        self.add("flight_stage_descent", "descent")
        self.add("flight_stage_landing", "landing")
        self.add("flight_stage_taxi", "taxi")
        self.add("flight_stage_parking", "parking")
        self.add("flight_stage_go-around", "go-around")
        self.add("flight_stage_end", "end")

        self.add("statusicon_showmain", "Show main window")
        self.add("statusicon_showmonitor", "Show monitor window")
        self.add("statusicon_quit", "Quit")
        self.add("statusicon_stage", "Stage")
        self.add("statusicon_rating", "Rating")

        self.add("update_title", "Update")
        self.add("update_needsudo",
                 "There is an update available, but the program cannot write\n"
                 "its directory due to insufficient privileges.\n\n"
                 "Click OK, if you want to run a helper program\n"
                 "with administrator privileges "
                 "to complete the update,\n"
                 "Cancel otherwise.")
        self.add("update_manifest_progress", "Downloading manifest...")
        self.add("update_manifest_done", "Downloaded manifest...")
        self.add("update_files_progress", "Downloading files...")
        self.add("update_files_bytes", "Downloaded %d of %d bytes")
        self.add("update_renaming", "Renaming downloaded files...")
        self.add("update_renamed", "Renamed %s")
        self.add("update_removing", "Removing files...")
        self.add("update_removed", "Removed %s")
        self.add("update_writing_manifest", "Writing the new manifest")
        self.add("update_finished",
                 "Finished updating. Press OK to restart the program.")
        self.add("update_nothing", "There was nothing to update")
        self.add("update_failed", "Failed, see the debug log for details.")

        self.add("weighthelp_usinghelp", "_Using help")
        self.add("weighthelp_usinghelp_tooltip",
                 "If you check this, some help will be displayed on how "
                 "to calculate the payload weight for your flight. "
                 "Note, that the usage of this facility will be logged.")
        self.add("weighthelp_header_calculated", "Requested/\ncalculated")
        self.add("weighthelp_header_simulator", "Simulator\ndata")
        self.add("weighthelp_header_simulator_tooltip",
                 "Click this button to retrieve the weight values from the "
                 "simulator, which will be displayed below. If a value is "
                 "within 10% of the tolerance, it is displayed in "
                 '<b><span foreground="darkgreen">green</span></b>, '
                 "if it is out of the tolerance, it is displayed in "
                 '<b><span foreground="red">red</span></b>, '
                 "otherwise in"
                 '<b><span foreground="orange">yellow</span></b>.')
        self.add("weighthelp_crew", "Crew (%s):")
        self.add("weighthelp_pax", "Passengers (%s):")
        self.add("weighthelp_baggage", "Baggage:")
        self.add("weighthelp_cargo", "Cargo:")
        self.add("weighthelp_mail", "Mail:")
        self.add("weighthelp_payload", "Payload:")
        self.add("weighthelp_dow", "DOW:")
        self.add("weighthelp_zfw", "ZFW:")
        self.add("weighthelp_gross", "Gross weight:")
        self.add("weighthelp_mzfw", "MZFW:")
        self.add("weighthelp_mtow", "MTOW:")
        self.add("weighthelp_mlw", "MLW:")
        self.add("weighthelp_busy", "Querying weight data...")

        self.add("gates_fleet_title", "Fl_eet")
        self.add("gates_gates_title", "LHBP gates")
        self.add("gates_tailno", "Tail nr.")
        self.add("gates_planestatus", "Status")
        self.add("gates_refresh", "_Refresh data")
        self.add("gates_refresh_tooltip",
                 "Click this button to refresh the status data above")
        self.add("gates_planes_tooltip",
                 "This table lists all the planes in the MAVA fleet and their "
                 "last known location. If a plane is conflicting with another "
                 "because of occupying the same gate its data is displayed in "
                 "<b><span foreground=\"red\">red</span></b>.")
        self.add("gates_gates_tooltip",
                 "The numbers of the gates occupied by MAVA planes are "
                 "displayed in "
                 '<b><span foreground="orange">yellow</span></b>, '
                 "while available gates in black.")
        self.add("gates_plane_away", "AWAY")
        self.add("gates_plane_parking", "PARKING")
        self.add("gates_plane_unknown", "UNKNOWN")

        self.add("prefs_title", "Preferences")
        self.add("prefs_tab_general", "_General")
        self.add("prefs_tab_general_tooltip", "General preferences")
        self.add("prefs_tab_messages", "_Messages")
        self.add("prefs_tab_message_tooltip",
                 "Enable/disable message notifications in FS and/or by sound")
        self.add("prefs_tab_sounds", "_Sounds")
        self.add("prefs_tab_sounds_tooltip",
                 "Preferences regarding what sounds should be played during the various flight stages")
        self.add("prefs_tab_advanced", "_Advanced")
        self.add("prefs_tab_advanced_tooltip",
                 "Advanced preferences, edit with care!")
        self.add("prefs_language", "_Language:")
        self.add("prefs_language_tooltip",
                 "The language of the program")
        self.add("prefs_restart",
                 "Restart needed")
        self.add("prefs_language_restart_sec",
                 "If you change the language, the program should be restarted "
                 "so that the change has an effect.")
        self.add("prefs_lang_$system", "system default")
        self.add("prefs_lang_en_GB", "English")
        self.add("prefs_lang_hu_HU", "Hungarian")
        self.add("prefs_hideMinimizedWindow",
                 "_Hide the main window when minimized")
        self.add("prefs_hideMinimizedWindow_tooltip",
                 "If checked, the main window will be hidden completely "
                 "when minimized. You can still make it appear by "
                 "clicking on the status icon or using its popup menu.")
        self.add("prefs_onlineGateSystem",
                 "_Use the Online Gate System")
        self.add("prefs_onlineGateSystem_tooltip",
                 "If this is checked, the logger will query and update the "
                 "LHBP Online Gate System.")
        self.add("prefs_onlineACARS",
                 "Use the Online ACA_RS System")
        self.add("prefs_onlineACARS_tooltip",
                 "If this is checked, the logger will continuously update "
                 "the MAVA Online ACARS System with your flight's data.")
        self.add("prefs_flaretimeFromFS",
                 "Take flare _time from the simulator")
        self.add("prefs_flaretimeFromFS_tooltip",
                 "If this is checked, the time of the flare will be calculated "
                 "from timestamps returned by the simulator.")
        self.add("prefs_syncFSTime",
                 "S_ynchronize the time in FS with the computer's clock")
        self.add("prefs_syncFSTime_tooltip",
                 "If this is checked the flight simulator's internal clock "
                 "will always be synchronized to the computer's clock.")
        self.add("prefs_pirepDirectory",
                 "_PIREP directory:")
        self.add("prefs_pirepDirectory_tooltip",
                 "The directory that will be offered by default when "
                 "saving a PIREP.")
        self.add("prefs_pirepDirectory_browser_title",
                 "Select PIREP directory")

        self.add("chklst_title", "Checklist Editor")
        self.add("chklst_aircraftType", "Aircraft _type:")
        self.add("chklst_aircraftType_tooltip",
                 "The type of the aircraft for which the checklist "
                 "is being edited.")
        self.add("chklst_add", "_Add to checklist")
        self.add("chklst_add_tooltip",
                 "Append the files selected on the left to the "
                 "checklist on the right.")
        self.add("chklst_remove", "_Remove")
        self.add("chklst_remove_tooltip",
                 "Remove the selected items from the checklist.")
        self.add("chklst_moveUp", "Move _up")
        self.add("chklst_moveUp_tooltip",
                 "Move up the selected file(s) in the checklist.")
        self.add("chklst_moveDown", "Move _down")
        self.add("chklst_moveDown_tooltip",
                 "Move down the selected file(s) in the checklist.")
        self.add("chklst_filter_audio", "Audio files")
        self.add("chklst_filter_all", "All files")
        self.add("chklst_header", "Checklist files")

        self.add("prefs_sounds_frame_bg", "Background")
        self.add("prefs_sounds_enable",
                 "_Enable background sounds")
        self.add("prefs_sounds_enable_tooltip",
                 "If the background sounds are enabled, the logger "
                 "can play different pre-recorded sounds during the "
                 "various stages of the flight.")
        self.add("prefs_sounds_pilotControls",
                 "_Pilot controls the sounds")
        self.add("prefs_sounds_pilotControls_tooltip",
                 "If checked, the background sounds can be started by the "
                 "pilot by pressing the hotkey specified below. Otherwise "
                 "the sounds will start automatically when certain "
                 "conditions hold.")
        self.add("prefs_sounds_pilotHotkey",
                 "_Hotkey:")
        self.add("prefs_sounds_pilotHotkey_tooltip",
                 "The key to press possibly together with modifiers to play "
                 "the sound relevant to the current flight status.")
        self.add("prefs_sounds_pilotHotkeyCtrl_tooltip",
                 "If checked, the Ctrl key should be pressed together with the "
                 "main key.")
        self.add("prefs_sounds_pilotHotkeyShift_tooltip",
                 "If checked, the Shift key should be pressed together with the "
                 "main key.")
        self.add("prefs_sounds_approachCallOuts",
                 "Enable approach callouts")
        self.add("prefs_sounds_approachCallOuts_tooltip",
                 "If checked, the approach callouts will be played at "
                 "certain altitudes.")
        self.add("prefs_sounds_speedbrakeAtTD",
                 "Enable speed_brake sound at touchdown")
        self.add("prefs_sounds_speedbrakeAtTD_tooltip",
                 "If checked, a speedbrake sound will be played after "
                 "touchdown, when the speedbrakes deploy.")
        self.add("prefs_sounds_frame_checklists", "Checklists")
        self.add("prefs_sounds_enableChecklists",
                 "E_nable aircraft-specific checklists")
        self.add("prefs_sounds_enableChecklists_tooltip",
                 "If checked, the program will play back pre-recorded "
                 "aircraft-specific checklists at the pilot's discretion.")
        self.add("prefs_sounds_checklistHotkey",
                 "Checklist hot_key:")
        self.add("prefs_sounds_checklistHotkey_tooltip",
                 "The key to press possibly together with modifiers to play the next "
                 "checklist item.")
        self.add("prefs_sounds_checklistHotkeyCtrl_tooltip",
                 "If checked, the Ctrl key should be pressed together with the "
                 "main key.")
        self.add("prefs_sounds_checklistHotkeyShift_tooltip",
                 "If checked, the Shift key should be pressed together with the "
                 "main key.")
        
        self.add("prefs_update_auto", "Update the program auto_matically")
        self.add("prefs_update_auto_tooltip",
                 "If checked the program will look for updates when "
                 "it is starting, and if new updates are found, they "
                 "will be downloaded and installed. This ensures that "
                 "the PIREP you send will always conform to the latest "
                 "expectations of the airline.")
        self.add("prefs_update_auto_warning",
                 "Disabling automatic updates may result in "
                 "your version of the program becoming out of date "
                 "and your PIREPs not being accepted.")
        self.add("prefs_update_url", "Update _URL:")
        self.add("prefs_update_url_tooltip",
                 "The URL from which to download the updates. Change this "
                 "only if you know what you are doing!")

        # A C G M O S
        
        self.add("prefs_msgs_fs", "Displayed in FS")
        self.add("prefs_msgs_sound", "Sound alert")
        self.add("prefs_msgs_type_loggerError", "Logger _Error Messages")
        self.add("prefs_msgs_type_information",
                 "_Information Messages\n(e.g. flight status)")
        self.add("prefs_msgs_type_fault",
                 "_Fault Messages\n(e.g. strobe light fault)")
        self.add("prefs_msgs_type_nogo",
                 "_NOGO Fault messages\n(e.g. MTOW NOGO)")
        self.add("prefs_msgs_type_gateSystem",
                 "Ga_te System Messages\n(e.g. available gates)")
        self.add("prefs_msgs_type_environment",
                 "Envi_ronment Messages\n(e.g. \"welcome to XY aiport\")")
        self.add("prefs_msgs_type_help",
                 "_Help Messages\n(e.g. \"don't forget to set VREF\")")
        self.add("prefs_msgs_type_visibility",
                 "_Visibility Messages")

        self.add("loadPIREP_browser_title", "Select the PIREP to load")
        self.add("loadPIREP_filter_pireps", "PIREP files")
        self.add("loadPIREP_filter_all", "All files")
        self.add("loadPIREP_failed", "Failed to load the PIREP")
        self.add("loadPIREP_failed_sec", "See the debug log for the details.")
        self.add("loadPIREP_send_title", "PIREP")
        self.add("loadPIREP_send_help",
                 "The main data of the PIREP loaded:")
        self.add("loadPIREP_send_flightno", "Flight number:")
        self.add("loadPIREP_send_date", "Date:")
        self.add("loadPIREP_send_from", "From:")
        self.add("loadPIREP_send_to", "To:")
        self.add("loadPIREP_send_rating", "Rating:")
        
        self.add("sendPIREP", "_Send PIREP...")
        self.add("sendPIREP_tooltip",
                 "Click to send the PIREP to the MAVA website for further review.")
        self.add("sendPIREP_busy", "Sending PIREP...")
        self.add("sendPIREP_success",
                 "The PIREP was sent successfully.")
        self.add("sendPIREP_success_sec",
                 "Await the thorough scrutiny by our fearless PIREP reviewers! :)")
        self.add("sendPIREP_already",
                 "The PIREP for this flight has already been sent!")
        self.add("sendPIREP_already_sec",
                 "You may clear the old PIREP on the MAVA website.")
        self.add("sendPIREP_notavail",
                 "This flight is not available anymore!")
        self.add("sendPIREP_unknown",
                 "The MAVA website returned with an unknown error.")
        self.add("sendPIREP_unknown_sec",
                 "See the debug log for more information.")
        self.add("sendPIREP_failed",
                 "Could not send the PIREP to the MAVA website.")
        self.add("sendPIREP_failed_sec",
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
        self.add("aircraft_b736", "Boeing 737-600")
        self.add("aircraft_b737", "Boeing 737-700")
        self.add("aircraft_b738", "Boeing 737-800")
        self.add("aircraft_b733", "Boeing 737-300")
        self.add("aircraft_b734", "Boeing 737-400")
        self.add("aircraft_b735", "Boeing 737-500")
        self.add("aircraft_dh8d", "Bombardier Dash 8 Q400")
        self.add("aircraft_b762", "Boeing 767-200")
        self.add("aircraft_b763", "Boeing 767-300")
        self.add("aircraft_crj2", "Canadair Regional Jet CRJ-200")
        self.add("aircraft_f70",  "Fokker F70")
        self.add("aircraft_dc3",  "Liszunov Li-2")
        self.add("aircraft_t134", "Tupoljev Tu-134")
        self.add("aircraft_t154", "Tupoljev Tu-154")
        self.add("aircraft_yk40", "Jakovlev Jak-40")

        self.add("button_ok", "_OK")
        self.add("button_cancel", "_Mégse")
        self.add("button_yes", "_Igen")
        self.add("button_no", "_Nem")
        self.add("button_browse", "Keresés...")
        
        self.add("menu_file", "Fájl")
        self.add("menu_file_loadPIREP", "PIREP be_töltése...")
        self.add("menu_file_loadPIREP_key", "t")
        self.add("menu_file_quit", "_Kilépés")
        self.add("menu_file_quit_key", "k")
        self.add("quit_question", "Biztosan ki akarsz lépni?")

        self.add("menu_tools", "Eszközök")
        self.add("menu_tools_chklst", "_Ellenörzőlista szerkesztő")
        self.add("menu_tools_chklst_key", "e")
        self.add("menu_tools_prefs", "_Beállítások")
        self.add("menu_tools_prefs_key", "b")

        self.add("menu_view", "Nézet")
        self.add("menu_view_monitor", "Mutasd a _monitor ablakot")
        self.add("menu_view_monitor_key", "m")
        self.add("menu_view_debug", "Mutasd a _debug naplót")
        self.add("menu_view_debug_key", "d")
        
        self.add("tab_flight", "_Járat")
        self.add("tab_flight_tooltip", "Járat varázsló")
        self.add("tab_flight_info", "Járat _info")
        self.add("tab_flight_info_tooltip", "Egyéb információk a járat teljesítésével kapcsolatban")
        self.add("tab_weight_help", "_Segítség")
        self.add("tab_weight_help_tooltip", "Segítség a súlyszámításhoz")
        self.add("tab_log", "_Napló")
        self.add("tab_log_tooltip",
                 "A járat naplója, amit majd el lehet küldeni a MAVA szerverére")
        self.add("tab_gates", "_Kapuk")        
        self.add("tab_gates_tooltip", "A MAVA flotta és LHBP kapuinak állapota")        
        self.add("tab_debug_log", "_Debug napló")
        self.add("tab_debug_log_tooltip",
                 "Hibakereséshez használható információkat tartalmazó napló.")

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

        self.add("fuel_title", "Üzemanyag")
        self.add("fuel_help",
                 "Írd be az egyes tartályokba szükséges üzemanyag "
                 "mennyiségét kilogrammban.\n\n"
                 "Ha megnyomod az <b>Előre</b> gombot, a megadott mennyiségű\n"
                 "üzemanyag bekerül a tartályokba.")
        self.add("fuel_chelp",
                 "A repülés elején az egyes tartályokba tankolt\n"
                 "üzemanyag mennyisége lent látható.")

        # A B D E I G J K N O P S T V Y Z
        
        self.add("fuel_tank_centre", "Kö_zépső\n")
        self.add("fuel_tank_left", "_Bal\n")
        self.add("fuel_tank_right", "J_obb\n")
        self.add("fuel_tank_left_aux", "Bal\nkie_gészítő")
        self.add("fuel_tank_right_aux", "Jobb\nkiegészí_tő")
        self.add("fuel_tank_left_tip", "B_al\nszárnyvég")
        self.add("fuel_tank_right_tip", "Jobb\nszárn_yvég")
        self.add("fuel_tank_external1", "Külső\n_1")
        self.add("fuel_tank_external2", "Külső\n_2")
        self.add("fuel_tank_centre2", "Közé_pső\n2")
        self.add("fuel_get_busy", "Az üzemanyag lekérdezése...")
        self.add("fuel_pump_busy", "Az üzemanyag pumpálása...")
        self.add("fuel_tank_tooltip",
                 "Ez mutatja az üzemanyag szintjét a tartályban annak "
                 "kapacitásához mérve. A "
                 '<span color="turquoise">türkizkék</span> '
                 "csúszka mutatja a repüléshez kívánt szintet. "
                 "Ha a bal gombbal bárhová kattintasz az ábrán, a csúszka "
                 "odaugrik. Ha a gombot lenyomva tartod, és az egérmutatót "
                 "föl-le mozgatod, a csúszka követi azt. Az egered görgőjével "
                 "is kezelheted a csúszkát. Alaphelyzetben az üzemanyag "
                 "mennyisége 10-zel nő, illetve csökken a görgetés irányától "
                 "függően. Ha a <b>Shift</b> billentyűt lenyomva tartod, "
                 "növekmény 100, a <b>Control</b> billentyűvel pedig 1 lesz.")

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
        self.add("finish_gate", "_Érkezési kapu:")
        self.add("finish_gate_tooltip",
                 "Válaszd ki azt a kaput vagy állóhelyet, ahová érkeztél LHBP-n.")
        self.add("finish_save", "PIREP _mentése...")
        self.add("finish_save_tooltip",
                 "Kattints ide, hogy elmenthesd a PIREP-et egy fájlba a számítógépeden. " \
                 "A PIREP-et később be lehet tölteni és el lehet küldeni.")
        self.add("finish_save_title", "PIREP mentése")
        self.add("finish_save_done", "A PIREP mentése sikerült")
        self.add("finish_save_failed", "A PIREP mentése nem sikerült")
        self.add("finish_save_failed_sec", "A részleteket lásd a debug naplóban.")

        # M A 

        self.add("info_comments", "_Megjegyzések")
        self.add("info_defects", "Hib_ajelenségek")
        self.add("info_delay", "Késés kódok")

        # B V H Y R G F E P Z
                 
        self.add("info_delay_loading", "_Betöltési problémák")
        self.add("info_delay_vatsim", "_VATSIM probléma")
        self.add("info_delay_net", "_Hálózati problémák")
        self.add("info_delay_atc", "Irán_yító hibája")
        self.add("info_delay_system", "_Rendszer elszállás/fagyás")
        self.add("info_delay_nav", "Navi_gációs probléma")
        self.add("info_delay_traffic", "_Forgalmi problémák")
        self.add("info_delay_apron", "_Előtér navigációs probléma")
        self.add("info_delay_weather", "Időjárási _problémák")
        self.add("info_delay_personal", "S_zemélyes okok")
                 
        self.add("statusbar_conn_tooltip",
                 'A kapcsolat állapota.\n'
                 '<span foreground="grey">Szürke</span>: nincs kapcsolat.\n'
                 '<span foreground="red">Piros</span>: kapcsolódás folyamatban.\n'
                 '<span foreground="green">Zöld</span>: a kapcsolat él.')
        self.add("statusbar_stage_tooltip", "A repülés fázisa")
        self.add("statusbar_time_tooltip", "A szimulátor ideje UTC-ben")
        self.add("statusbar_rating_tooltip", "A repülés pontszáma")
        self.add("statusbar_busy_tooltip", "A háttérfolyamatok állapota.")

        self.add("flight_stage_boarding", u"beszállás")
        self.add("flight_stage_pushback and taxi", u"hátratolás és kigurulás")
        self.add("flight_stage_takeoff", u"felszállás")
        self.add("flight_stage_RTO", u"megszakított felszállás")
        self.add("flight_stage_climb", u"emelkedés")
        self.add("flight_stage_cruise", u"utazó")
        self.add("flight_stage_descent", u"süllyedés")
        self.add("flight_stage_landing", u"leszállás")
        self.add("flight_stage_taxi", u"begurulás")
        self.add("flight_stage_parking", u"parkolás")
        self.add("flight_stage_go-around", u"átstartolás")
        self.add("flight_stage_end", u"kész")

        self.add("statusicon_showmain", "Mutasd a főablakot")
        self.add("statusicon_showmonitor", "Mutasd a monitor ablakot")
        self.add("statusicon_quit", "Kilépés")
        self.add("statusicon_stage", u"Fázis")
        self.add("statusicon_rating", u"Pontszám")

        self.add("update_title", "Frissítés")
        self.add("update_needsudo",
                 "Lenne mit frissíteni, de a program hozzáférési jogok\n"
                 "hiányában nem tud írni a saját könyvtárába.\n\n"
                 "Kattints az OK gombra, ha el szeretnél indítani egy\n"
                 "segédprogramot adminisztrátori jogokkal, amely\n"
                 "befejezné a frissítést, egyébként a Mégse gombra.")
        self.add("update_manifest_progress", "A manifesztum letöltése...")
        self.add("update_manifest_done", "A manifesztum letöltve...")
        self.add("update_files_progress", "Fájlok letöltése...")
        self.add("update_files_bytes", "%d bájtot töltöttem le %d bájtból")
        self.add("update_renaming", "A letöltött fájlok átnevezése...")
        self.add("update_renamed", "Átneveztem a(z) %s fájlt")
        self.add("update_removing", "Fájlok törlése...")
        self.add("update_removed", "Letöröltem a(z) %s fájlt")
        self.add("update_writing_manifest", "Az új manifesztum írása")
        self.add("update_finished",
                 "A frissítés sikerült. Kattints az OK-ra a program újraindításához.")
        self.add("update_nothing", "Nem volt mit frissíteni")
        self.add("update_failed", "Nem sikerült, a részleteket lásd a debug naplóban.")

        self.add("weighthelp_usinghelp", "_Használom a segítséget")
        self.add("weighthelp_usinghelp_tooltip",
                 "Ha bejelölöd, az alábbiakban kapsz egy kis segítséget "
                 "a járathoz szükséges hasznos teher megállapításához. "
                 "Ha igénybe veszed ezt a szolgáltatást, ez a tény "
                 "a naplóba bekerül.")
        self.add("weighthelp_header_calculated", "Elvárt/\nszámított")
        self.add("weighthelp_header_simulator", "Szimulátor\nadatok")
        self.add("weighthelp_header_simulator_tooltip",
                 "Kattints erre a gombra a súlyadatoknak a szimulátortól "
                 "való lekérdezéséhez. Az értékek lent jelennek meg. Ha "
                 "egy érték a tűrés 10%-án belül van, akkor az "
                 '<b><span foreground="darkgreen">zöld</span></b> '
                 "színnel jelenik meg. Ha nem fér bele a tűrésbe, akkor "
                 '<b><span foreground="red">piros</span></b>, '
                 "egyébként "
                 '<b><span foreground="orange">sárga</span></b> '
                 "színben olvasható.")
        self.add("weighthelp_crew", "Legénység (%s):")
        self.add("weighthelp_pax", "Utasok (%s):")
        self.add("weighthelp_baggage", "Poggyász:")
        self.add("weighthelp_cargo", "Teher:")
        self.add("weighthelp_mail", "Posta:")
        self.add("weighthelp_payload", "Hasznos teher:")
        self.add("weighthelp_dow", "DOW:")
        self.add("weighthelp_zfw", "ZFW:")
        self.add("weighthelp_gross", "Teljes tömeg:")
        self.add("weighthelp_mzfw", "MZFW:")
        self.add("weighthelp_mtow", "MTOW:")
        self.add("weighthelp_mlw", "MLW:")
        self.add("weighthelp_busy", "A tömegadatok lekérdezése...")

        self.add("gates_fleet_title", "_Flotta")
        self.add("gates_gates_title", "LHBP kapuk")
        self.add("gates_tailno", "Lajstromjel")
        self.add("gates_planestatus", "Állapot")
        self.add("gates_refresh", "_Adatok frissítése")
        self.add("gates_refresh_tooltip",
                 "Kattints erre a gombra a fenti adatok frissítéséhez")
        self.add("gates_planes_tooltip",
                 "Ez a táblázat tartalmazza a MAVA flottája összes "
                 "repülőgépének lajstromjelét és utolsó ismert helyét. "
                 "Ha egy repülőgép olyan kapun áll, amelyet másik gép is "
                 "elfoglal, akkor annak a repülőgépnek az adatai "
                 "<b><span foreground=\"red\">piros</span></b> "
                 "színnel jelennek meg.")
        self.add("gates_gates_tooltip",
                 "A MAVA repülőgépei által elfoglalt kapuk száma "
                 '<b><span foreground="orange">sárga</span></b> színnel,'
                 "a többié feketén jelenik meg.")
        self.add("gates_plane_away", "TÁVOL")
        self.add("gates_plane_parking", "PARKOL")
        self.add("gates_plane_unknown", "ISMERETLEN")
                 
        self.add("chklst_title", "Ellenörzőlista szerkesztő")

        self.add("prefs_title", "Beállítások")
        self.add("prefs_tab_general", "_Általános")
        self.add("prefs_tab_general_tooltip", "Általános beállítások")
        self.add("prefs_tab_messages", "_Üzenetek")
        self.add("prefs_tab_message_tooltip",
                 "A szimulátorba és/vagy hangjelzés általi üzenetküldés be- "
                 "és kikapcsolása")
        self.add("prefs_tab_sounds", "_Hangok")
        self.add("prefs_tab_sounds_tooltip",
                 "A repülés különféle fázisai alatt lejátszandó hangokkal "
                 "kapcsolatos beállítások.")
        self.add("prefs_tab_advanced", "H_aladó")
        self.add("prefs_tab_advanced_tooltip",
                 "Haladó beállítások: óvatosan módosítsd őket!")
        self.add("prefs_language", "_Nyelv:")
        self.add("prefs_language_tooltip",
                 "A program által használt nyelv")
        self.add("prefs_restart",
                 "Újraindítás szükséges")
        self.add("prefs_language_restart_sec",
                 "A program nyelvének megváltoztatása csak egy újraindítást "
                 "követően jut érvényre.")
        self.add("prefs_lang_$system", "alapértelmezett")
        self.add("prefs_lang_en_GB", "angol")
        self.add("prefs_lang_hu_HU", "magyar")
        self.add("prefs_hideMinimizedWindow",
                 "A főablak _eltüntetése minimalizáláskor")
        self.add("prefs_hideMinimizedWindow_tooltip",
                 "Ha ezt kijelölöd, a főablak teljesen eltűnik, "
                 "ha minimalizálod. A státuszikonra kattintással vagy annak "
                 "menüje segítségével újra meg tudod jeleníteni.")
        self.add("prefs_onlineGateSystem",
                 "Az Online _Gate System használata")
        self.add("prefs_onlineGateSystem_tooltip",
                 "Ha ezt bejelölöd, a logger lekérdezi és frissíti az "
                 "LHBP Online Gate System adatait.")
        self.add("prefs_onlineACARS",
                 "Az Online ACA_RS rendszer használata")
        self.add("prefs_onlineACARS_tooltip",
                 "Ha ezt bejölöd, a logger folyamatosan közli a repülésed "
                 "adatait a MAVA Online ACARS rendszerrel.")
        self.add("prefs_flaretimeFromFS",
                 "A ki_lebegtetés idejét vedd a szimulátorból")
        self.add("prefs_flaretimeFromFS_tooltip",
                 "Ha ezt bejelölöd, a kilebegtetés idejét a szimulátor "
                 "által visszaadott időbélyegek alapján számolja a program.")
        self.add("prefs_syncFSTime",
                 "_Szinkronizáld a szimulátor idéjét a számítógépével")
        self.add("prefs_syncFSTime_tooltip",
                 "Ha ez bejelölöd, a szimulátor belső óráját a program "
                 "szinkronban tartja a számítógép órájával.")
        self.add("prefs_pirepDirectory",
                 "_PIREP-ek könyvtára:")
        self.add("prefs_pirepDirectory_tooltip",
                 "Az itt megadott könyvtárt ajánlja majd fel a program "
                 "a PIREP-ek mentésekor.")
        self.add("prefs_pirepDirectory_browser_title",
                 "Válaszd ki a PIREP-ek könyvtárát")

        self.add("prefs_sounds_frame_bg", "Háttérhangok")
        self.add("prefs_sounds_enable",
                 "Háttérhangok _engedélyezése")
        self.add("prefs_sounds_enable_tooltip",
                 "Ha a háttérhangokat engedélyezed, a logger a repülés "
                 "egyes fázisai alatt különféle hangállományokat játszik le.")
        self.add("prefs_sounds_pilotControls",
                 "_Pilóta vezérli a hangokat")
        self.add("prefs_sounds_pilotControls_tooltip",
                 "Ha azt kijelölöd, a legtöbb háttérhang csak akkor hallható, "
                 "ha a pilóta a lent megadott gyorsbillentyűt leüti. Egyébként "
                 "a hangok maguktól, bizonyos feltételek teljesülése esetén "
                 "szólalnak meg.")
        self.add("prefs_sounds_pilotHotkey",
                 "_Gyorsbillentyű:")
        self.add("prefs_sounds_pilotHotkey_tooltip",
                 "A billentyű, amit az esetlegesen megadott módosítókkal "
                 "együtt le kell ütni, hogy a repülés aktuális fázisához "
                 "tartozó hang megszólaljon.")
        self.add("prefs_sounds_pilotHotkeyCtrl_tooltip",
                 "Ha kijelölöd, a Ctrl billentyűt is le kell nyomni a "
                 "főbillentyűvel együtt.")
        self.add("prefs_sounds_pilotHotkeyShift_tooltip",
                 "Ha kijelölöd, a Shift billentyűt is le kell nyomni a "
                 "főbillentyűvel együtt.")
        self.add("prefs_sounds_approachCallOuts",
                 "Megközelítési figyelmeztetések engedélyezés")
        self.add("prefs_sounds_approachCallOuts_tooltip",
                 "Ha kijelölöd, megközelítés közben egyes magasságokat "
                 "bemond a program.")
        self.add("prefs_sounds_speedbrakeAtTD",
                 "_Spoiler hang bekapcsolása leszálláskor")
        self.add("prefs_sounds_speedbrakeAtTD_tooltip",
                 "Ha kijelölöd, egy, a spoilerek kibocsájtását imitáló "
                 "hang hallatszik földetérés után, ha a spoilerek "
                 "automatikusan kinyílnak.")
        self.add("prefs_sounds_frame_checklists", "Ellenörzőlisták")
        self.add("prefs_sounds_enableChecklists",
                 "_Repülőgép-specifikus ellenörzőlisták engedélyezése")
        self.add("prefs_sounds_enableChecklists_tooltip",
                 "Ha kijelölöd, a program a lenti gyorsbillentyű "
                 "megnyomásokor a használt repülőgép típushoz tartozó "
                 "ellenörzőlista következő elemét játssza le.")
        self.add("prefs_sounds_checklistHotkey",
                 "E_llenörzőlista gyorsbillentyű:")
        self.add("prefs_sounds_checklistHotkey_tooltip",
                 "A billentyű, amit az esetlegesen megadott módosítókkal "
                 "együtt le kell ütni, hogy az ellenörzőlista következő "
                 "eleme elhangozzék.")
        self.add("prefs_sounds_checklistHotkeyCtrl_tooltip",
                 "Ha kijelölöd, a Ctrl billentyűt is le kell nyomni a "
                 "főbillentyűvel együtt.")
        self.add("prefs_sounds_checklistHotkeyShift_tooltip",
                 "Ha kijelölöd, a Shift billentyűt is le kell nyomni a "
                 "főbillentyűvel együtt.")

        self.add("prefs_update_auto",
                 "Frissítsd a programot _automatikusan")
        self.add("prefs_update_auto_tooltip",
                 "Ha ez be van jelölve, a program induláskor frissítést "
                 "keres, és ha talál, azokat letölti és telepíti. Ez "
                 "biztosítja, hogy az elküldött PIREP minden megfelel "
                 "a legújabb elvárásoknak.")
        self.add("prefs_update_auto_warning",
                 "Az automatikus frissítés kikapcsolása azt okozhatja, "
                 "hogy a program Nálad lévő verziója elavulttá válik, "
                 "és a PIREP-jeidet így nem fogadják el.")
        self.add("prefs_update_url", "Frissítés _URL-je:")
        self.add("prefs_update_url_tooltip",
                 "Az URL, ahol a frissítéseket keresi a program. Csak akkor "
                 "változtasd meg, ha biztos vagy a dolgodban!")

        # A Á H M O Ü

        self.add("prefs_msgs_fs", "Szimulátorban\nmegjelenítés")
        self.add("prefs_msgs_sound", "Hangjelzés")
        self.add("prefs_msgs_type_loggerError", "_Logger hibaüzenetek")
        self.add("prefs_msgs_type_information",
                 "_Információs üzenetek\n(pl. a repülés fázisa)")
        self.add("prefs_msgs_type_fault",
                 "Hi_baüzenetek\n(pl. a villogó fény hiba)")
        self.add("prefs_msgs_type_nogo",
                 "_NOGO hibaüzenetek\n(pl. MTOW NOGO)")
        self.add("prefs_msgs_type_gateSystem",
                 "_Kapukezelő rendszer üzenetei\n(pl. a szabad kapuk listája)")
        self.add("prefs_msgs_type_environment",
                 "Kö_rnyezeti üzenetek\n(pl. \"welcome to XY aiport\")")
        self.add("prefs_msgs_type_help",
                 "_Segítő üzenetek\n(pl. \"don't forget to set VREF\")")
        self.add("prefs_msgs_type_visibility",
                 "Lá_tótávolság üzenetek")

        self.add("loadPIREP_browser_title", "Válaszd ki a betöltendő PIREP-et")
        self.add("loadPIREP_filter_pireps", "PIREP fájlok")
        self.add("loadPIREP_filter_all", "Összes fájl")
        self.add("loadPIREP_failed", "Nem tudtam betölteni a PIREP-et")
        self.add("loadPIREP_failed_sec",
                 "A részleteket lásd a debug naplóban.")
        self.add("loadPIREP_send_title", "PIREP")
        self.add("loadPIREP_send_help",
                 "A betöltött PIREP főbb adatai:")
        self.add("loadPIREP_send_flightno", "Járatszám:")
        self.add("loadPIREP_send_date", "Dátum:")
        self.add("loadPIREP_send_from", "Honnan:")
        self.add("loadPIREP_send_to", "Hová:")
        self.add("loadPIREP_send_rating", "Pontszám:")

        self.add("sendPIREP", "PIREP _elküldése...")
        self.add("sendPIREP_tooltip",
                 "Kattints ide, hogy elküldd a PIREP-et a MAVA szerverére javításra.")
        self.add("sendPIREP_busy", "PIREP küldése...")
        self.add("sendPIREP_success",
                 "A PIREP elküldése sikeres volt.")
        self.add("sendPIREP_success_sec",
                 "Várhatod félelmet nem ismerő PIREP javítóink alapos észrevételeit! :)")
        self.add("sendPIREP_already",
                 "Ehhez a járathoz már küldtél be PIREP-et!")
        self.add("sendPIREP_already_sec",
                 "A korábban beküldött PIREP-et törölheted a MAVA honlapján.")
        self.add("sendPIREP_notavail",
                 "Ez a járat már nem elérhető!")
        self.add("sendPIREP_unknown",
                 "A MAVA szervere ismeretlen hibaüzenettel tért vissza.")
        self.add("sendPIREP_unknown_sec",
                 "A debug naplóban részletesebb információt találsz.")
        self.add("sendPIREP_failed",
                 "Nem tudtam elküldeni a PIREP-et a MAVA szerverére.")
        self.add("sendPIREP_failed_sec",
                 "Lehet, hogy hálózati probléma áll fenn, amely esetben később\n" \
                 "újra próbálkozhatsz. Lehet azonban hiba is a loggerben:\n" \
                 "részletesebb információt találhatsz a debug naplóban.")

#------------------------------------------------------------------------------

# The fallback language is English
_english = _English()

# We also support Hungarian
_hungarian = _Hungarian()

#------------------------------------------------------------------------------

if __name__ == "__main__":
    _hungarian.initialize()
    for key in _english:
        if _hungarian[key] is None:
            print key

#------------------------------------------------------------------------------
