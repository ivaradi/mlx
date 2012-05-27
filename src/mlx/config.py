# Configuration and related stuff
# -*- encoding: utf-8 -*-

#-------------------------------------------------------------------------------

import const

import os
import sys
import ConfigParser

#-------------------------------------------------------------------------------

configPath = os.path.join(os.path.expanduser("~"),
                          "mlx.config" if os.name=="nt" else ".mlxrc")

#-------------------------------------------------------------------------------

if os.name=="nt":
    _languageMap = { "en_GB" : "eng",
                     "hu_HU" : "hun" }

#-------------------------------------------------------------------------------

class Hotkey(object):
    """A hotkey."""
    def __init__(self, ctrl = False, shift = False, key = "0"):
        """Construct the hotkey."""
        self.ctrl = ctrl
        self.shift = shift
        self.key = key

    def set(self, s):
        """Set the hotkey from the given string."""
        self.ctrl = "C" in s[:-1]
        self.shift = "S" in s[:-1]
        self.key = s[-1]

    def __eq__(self, other):
        """Check if the given hotkey is equal to the other one."""
        return self.ctrl == other.ctrl and self.shift == other.shift and \
               self.key == other.key

    def __str__(self):
        """Construct the hotkey to a string."""
        s = ""
        if self.ctrl: s += "C"
        if self.shift: s += "S"
        s += self.key
        return s

#-------------------------------------------------------------------------------

class Checklist(object):
    """A checklist for a certain aircraft type."""
    # The name of the section of the checklists
    SECTION="checklists"
    
    @staticmethod
    def fromConfig(config, aircraftType):
        """Create a checklist for the given aircraft type from the given
        config."""
        baseName = "checklist." + const.icaoCodes[aircraftType] + "."
        fileList = []
        while True:
            option = baseName + str(len(fileList))
            if config.has_option(Checklist.SECTION, option):
                fileList.append(config.get(Checklist.SECTION, option))
            else:
                break

        return Checklist(fileList)

    def __init__(self, fileList = None):
        """Construct the check list with the given file list."""
        self._fileList = [] if fileList is None else fileList[:]

    def clone(self):
        """Clone the checklist."""
        return Checklist(self._fileList)

    def toConfig(self, config, aircraftType):
        """Add this checklist to the given config."""
        baseName = "checklist." + const.icaoCodes[aircraftType] + "."
        for index in range(0, len(self._fileList)):
            option = baseName + str(index)
            config.set(Checklist.SECTION, option,
                       self._fileList[index])

    def __eq__(self, other):
        """Determine if the checklist is equal to the given other one."""
        return self._fileList == other._fileList

    def __len__(self):
        """Get the length of the file list."""
        return len(self._fileList)

    def __getitem__(self, index):
        """Get the file with the given index."""
        return self._fileList[index]

    def __iter__(self):
        """Iterate over the files."""
        return iter(self._fileList)

#-------------------------------------------------------------------------------

class Config(object):
    """Our configuration."""
    DEFAULT_UPDATE_URL = "http://mlx.varadiistvan.hu/update"

    _messageTypesSection = "messageTypes"
    
    def __init__(self):
        """Construct the configuration with default values."""

        self._pilotID = ""
        self._password = ""
        self._rememberPassword = False

        self._language = ""
        self._hideMinimizedWindow = True
        self._onlineGateSystem = True
        self._onlineACARS = True
        self._flareTimeFromFS = False
        self._syncFSTime = False
        self._usingFS2Crew = False
        self._iasSmoothingLength = -2
        self._vsSmoothingLength = -2

        self._pirepDirectory = None

        self._enableSounds = True

        self._pilotControlsSounds = True
        self._pilotHotkey = Hotkey(ctrl = True, shift = False, key = "0")

        #self._approachCallOuts = False
        self._speedbrakeAtTD = True

        self._enableChecklists = False
        self._checklistHotkey = Hotkey(ctrl = True, shift = True, key = "0")
                
        self._autoUpdate = True        
        self._updateURL = Config.DEFAULT_UPDATE_URL

        self._messageTypeLevels = {}

        self._checklists = {}
        for aircraftType in const.aircraftTypes:
            self._checklists[aircraftType] = Checklist()
        
        self._modified = False

    @property
    def pilotID(self):
        """Get the pilot ID."""
        return self._pilotID

    @pilotID.setter
    def pilotID(self, pilotID):
        """Set the pilot ID."""
        if pilotID!=self._pilotID:
            self._pilotID = pilotID
            self._modified = True

    @property
    def password(self):
        """Get the password."""
        return self._password

    @password.setter
    def password(self, password):
        """Set the password."""
        if password!=self._password:
            self._password = password
            self._modified = True

    @property
    def rememberPassword(self):
        """Get if we should remember the password."""
        return self._rememberPassword

    @rememberPassword.setter
    def rememberPassword(self, rememberPassword):
        """Set if we should remember the password."""
        if rememberPassword!=self._rememberPassword:
            self._rememberPassword = rememberPassword
            self._modified = True

    @property
    def language(self):
        """Get the language to use."""
        return self._language

    @language.setter
    def language(self, language):
        """Set the language to use."""
        if language!=self._language:
            self._language = language
            self._modified = True

    @property
    def hideMinimizedWindow(self):
        """Get whether a minimized window should be hidden."""
        return self._hideMinimizedWindow

    @hideMinimizedWindow.setter
    def hideMinimizedWindow(self, hideMinimizedWindow):
        """Set whether a minimized window should be hidden."""
        if hideMinimizedWindow!=self._hideMinimizedWindow:
            self._hideMinimizedWindow = hideMinimizedWindow
            self._modified = True
    
    @property
    def onlineGateSystem(self):
        """Get whether the online gate system should be used."""
        return self._onlineGateSystem

    @onlineGateSystem.setter
    def onlineGateSystem(self, onlineGateSystem):
        """Set whether the online gate system should be used."""
        if onlineGateSystem!=self._onlineGateSystem:
            self._onlineGateSystem = onlineGateSystem
            self._modified = True

    @property
    def onlineACARS(self):
        """Get whether the online ACARS system should be used."""
        return self._onlineACARS

    @onlineACARS.setter
    def onlineACARS(self, onlineACARS):
        """Set whether the online ACARS system should be used."""
        if onlineACARS!=self._onlineACARS:
            self._onlineACARS = onlineACARS
            self._modified = True

    @property
    def flareTimeFromFS(self):
        """Get whether the flare time should be calculated from the time values
        returned by the simulator."""
        return self._flareTimeFromFS

    @flareTimeFromFS.setter
    def flareTimeFromFS(self, flareTimeFromFS):
        """Set whether the flare time should be calculated from the time values
        returned by the simulator."""
        if flareTimeFromFS!=self._flareTimeFromFS:
            self._flareTimeFromFS = flareTimeFromFS
            self._modified = True

    @property
    def syncFSTime(self):
        """Get whether the simulator's time should be synchronized with the
        machine's clock."""
        return self._syncFSTime

    @syncFSTime.setter
    def syncFSTime(self, syncFSTime):
        """Set whether the simulator's time should be synchronized with the
        machine's clock."""
        if syncFSTime!=self._syncFSTime:
            self._syncFSTime = syncFSTime
            self._modified = True

    @property
    def usingFS2Crew(self):
        """Get whether the FS2Crew addon is being used."""
        return self._usingFS2Crew

    @usingFS2Crew.setter
    def usingFS2Crew(self, usingFS2Crew):
        """Set whether the FS2Crew addon is being used."""
        if usingFS2Crew!=self._usingFS2Crew:
            self._usingFS2Crew = usingFS2Crew
            self._modified = True

    @property
    def iasSmoothingLength(self):
        """Get the number of samples over which the IAS is averaged for the
        smoothed IAS calculation. It may be negative, in which case smoothing
        is disabled, but we nevertheless store the number of seconds in case it
        may become useful later."""
        return self._iasSmoothingLength

    @property
    def realIASSmoothingLength(self):
        """Get the real smoothing length of IAS."""
        return max(self._iasSmoothingLength, 1)

    @iasSmoothingLength.setter
    def iasSmoothingLength(self, iasSmoothingLength):
        """Set the number of samples over which the IAS is averaged for the
        smoothed IAS calculation."""
        if iasSmoothingLength!=self._iasSmoothingLength:
            self._iasSmoothingLength = iasSmoothingLength
            self._modified = True

    @property
    def vsSmoothingLength(self):
        """Get the number of samples over which the VS is averaged for the
        smoothed VS calculation. It may be negative, in which case smoothing
        is disabled, but we nevertheless store the number of seconds in case it
        may become useful later."""
        return self._vsSmoothingLength

    @property
    def realVSSmoothingLength(self):
        """Get the real smoothing length of VS."""
        return max(self._vsSmoothingLength, 1)

    @vsSmoothingLength.setter
    def vsSmoothingLength(self, vsSmoothingLength):
        """Set the number of samples over which the VS is averaged for the
        smoothed VS calculation."""
        if vsSmoothingLength!=self._vsSmoothingLength:
            self._vsSmoothingLength = vsSmoothingLength
            self._modified = True

    @property
    def pirepDirectory(self):
        """Get the directory offered by default when saving a PIREP."""
        return self._pirepDirectory

    @pirepDirectory.setter
    def pirepDirectory(self, pirepDirectory):
        """Get the directory offered by default when saving a PIREP."""
        if pirepDirectory!=self._pirepDirectory and \
           (pirepDirectory!="" or self._pirepDirectory is not None):
            self._pirepDirectory = None if pirepDirectory=="" \
                                   else pirepDirectory
            self._modified = True

    def getMessageTypeLevel(self, messageType):
        """Get the level for the given message type."""
        return self._messageTypeLevels[messageType] \
               if messageType in self._messageTypeLevels \
               else const.MESSAGELEVEL_NONE

    def isMessageTypeFS(self, messageType):
        """Determine if the given message type is displayed in the
        simulator."""
        level = self.getMessageTypeLevel(messageType)
        return level==const.MESSAGELEVEL_FS or \
               level==const.MESSAGELEVEL_BOTH
        
    def setMessageTypeLevel(self, messageType, level):
        """Set the level of the given message type."""
        if messageType not in self._messageTypeLevels or \
           self._messageTypeLevels[messageType]!=level:
            self._messageTypeLevels[messageType] = level
            self._modified = True

    @property
    def enableSounds(self):
        """Get whether background sounds are enabled."""
        return self._enableSounds

    @enableSounds.setter
    def enableSounds(self, enableSounds):
        """Set whether background sounds are enabled."""
        if enableSounds!=self._enableSounds:
            self._enableSounds = enableSounds
            self._modified = True

    @property 
    def pilotControlsSounds(self):
        """Get whether the pilot controls the background sounds."""
        return self._pilotControlsSounds

    @pilotControlsSounds.setter
    def pilotControlsSounds(self, pilotControlsSounds):
        """Set whether the pilot controls the background sounds."""
        if pilotControlsSounds!=self._pilotControlsSounds:
            self._pilotControlsSounds = pilotControlsSounds
            self._modified = True

    @property
    def pilotHotkey(self):
        """Get the pilot's hotkey."""
        return self._pilotHotkey

    @pilotHotkey.setter
    def pilotHotkey(self, pilotHotkey):
        """Set the pilot's hotkey."""
        if pilotHotkey!=self._pilotHotkey:
            self._pilotHotkey = pilotHotkey
            self._modified = True

    # @property
    # def approachCallOuts(self):
    #     """Get whether the approach callouts should be played."""
    #     return self._approachCallOuts

    # @approachCallOuts.setter
    # def approachCallOuts(self, approachCallOuts):
    #     """Set whether the approach callouts should be played."""
    #     if approachCallOuts!=self._approachCallOuts:
    #         self._approachCallOuts = approachCallOuts
    #         self._modified = True

    @property
    def speedbrakeAtTD(self):
        """Get whether the speedbrake sounds should be played at touchdown."""
        return self._speedbrakeAtTD

    @speedbrakeAtTD.setter
    def speedbrakeAtTD(self, speedbrakeAtTD):
        """Set whether the speedbrake sounds should be played at touchdown."""
        if speedbrakeAtTD!=self._speedbrakeAtTD:
            self._speedbrakeAtTD = speedbrakeAtTD
            self._modified = True
        
    @property
    def enableChecklists(self):
        """Get whether aircraft-specific checklists should be played."""
        return self._enableChecklists

    @enableChecklists.setter
    def enableChecklists(self, enableChecklists):
        """Get whether aircraft-specific checklists should be played."""
        if enableChecklists!=self._enableChecklists:
            self._enableChecklists = enableChecklists
            self._modified = True

    @property
    def checklistHotkey(self):
        """Get the checklist hotkey."""
        return self._checklistHotkey

    @checklistHotkey.setter
    def checklistHotkey(self, checklistHotkey):
        """Set the checklist hotkey."""
        if checklistHotkey!=self._checklistHotkey:
            self._checklistHotkey = checklistHotkey
            self._modified = True

    @property
    def autoUpdate(self):
        """Get if an automatic update is needed."""
        return self._autoUpdate

    @autoUpdate.setter
    def autoUpdate(self, autoUpdate):
        """Set if an automatic update is needed."""
        if autoUpdate!=self._autoUpdate:
            self._autoUpdate = autoUpdate
            self._modified = True

    @property
    def updateURL(self):
        """Get the update URL."""
        return self._updateURL

    @updateURL.setter
    def updateURL(self, updateURL):
        """Set the update URL."""
        if updateURL!=self._updateURL:
            self._updateURL = updateURL
            self._modified = True

    def getChecklist(self, aircraftType):
        """Get the checklist for the given aircraft type."""
        return self._checklists[aircraftType]

    def setChecklist(self, aircraftType, checklist):
        """Set the checklist for the given aircraft type."""
        if checklist!=self._checklists[aircraftType]:
            self._checklists[aircraftType] = checklist.clone()
            self._modified = True

    def load(self):
        """Load the configuration from its default location."""
        config = ConfigParser.RawConfigParser()
        config.read(configPath)

        self._pilotID = self._get(config, "login", "id", "")
        self._password = self._get(config, "login", "password", "")
        self._rememberPassword = self._getBoolean(config, "login",
                                                  "rememberPassword", False)

        self._language = self._get(config, "general", "language", "")
        self._hideMinimizedWindow = self._getBoolean(config, "general",
                                                     "hideMinimizedWindow",
                                                     True)
        self._onlineGateSystem = self._getBoolean(config, "general",
                                                  "onlineGateSystem",
                                                  True)
        self._onlineACARS = self._getBoolean(config, "general",
                                             "onlineACARS", True)
        self._flareTimeFromFS = self._getBoolean(config, "general",
                                                 "flareTimeFromFS",
                                                 False)
        self._syncFSTime = self._getBoolean(config, "general",
                                            "syncFSTime",
                                            False)
        self._usingFS2Crew = self._getBoolean(config, "general",
                                              "usingFS2Crew",
                                              False)
        self._iasSmoothingLength = int(self._get(config, "general",
                                                 "iasSmoothingLength",
                                                 -2))
        self._vsSmoothingLength = int(self._get(config, "general",
                                                "vsSmoothingLength",
                                                -2))
        self._pirepDirectory = self._get(config, "general",
                                         "pirepDirectory", None)

        self._messageTypeLevels = {}
        for messageType in const.messageTypes:
            self._messageTypeLevels[messageType] = \
                self._getMessageTypeLevel(config, messageType)

        self._enableSounds = self._getBoolean(config, "sounds",
                                              "enable", True)
        self._pilotControlsSounds = self._getBoolean(config, "sounds",
                                                     "pilotControls", True)
        self._pilotHotkey.set(self._get(config, "sounds",
                                        "pilotHotkey", "C0"))
        #self._approachCallOuts = self._getBoolean(config, "sounds",
        #                                          "approachCallOuts", False)
        self._speedbrakeAtTD = self._getBoolean(config, "sounds",
                                                "speedbrakeAtTD", True)

        self._enableChecklists = self._getBoolean(config, "sounds",
                                                  "enableChecklists", False)
        self._checklistHotkey.set(self._get(config, "sounds",
                                            "checklistHotkey", "CS0"))
            
        self._autoUpdate = self._getBoolean(config, "update", "auto", True)
        self._updateURL = self._get(config, "update", "url",
                                    Config.DEFAULT_UPDATE_URL)

        for aircraftType in const.aircraftTypes:
            self._checklists[aircraftType] = \
                Checklist.fromConfig(config, aircraftType)

        self._modified = False

    def save(self):
        """Save the configuration file if it has been modified."""
        if not self._modified:
            return

        config = ConfigParser.RawConfigParser()

        config.add_section("login")
        config.set("login", "id", self._pilotID)
        config.set("login", "password", self._password)
        config.set("login", "rememberPassword",
                   "yes" if self._rememberPassword else "no")

        config.add_section("general")
        if self._language:
            config.set("general", "language", self._language)
        config.set("general", "hideMinimizedWindow",
                   "yes" if self._hideMinimizedWindow else "no")
        config.set("general", "onlineGateSystem",
                   "yes" if self._onlineGateSystem else "no")
        config.set("general", "onlineACARS",
                   "yes" if self._onlineACARS else "no")
        config.set("general", "flareTimeFromFS",
                   "yes" if self._flareTimeFromFS else "no")
        config.set("general", "syncFSTime",
                   "yes" if self._syncFSTime else "no")
        config.set("general", "usingFS2Crew",
                   "yes" if self._usingFS2Crew else "no")
        config.set("general", "iasSmoothingLength",
                   str(self._iasSmoothingLength))
        config.set("general", "vsSmoothingLength",
                   str(self._vsSmoothingLength))

        if self._pirepDirectory is not None:
            config.set("general", "pirepDirectory", self._pirepDirectory)

        config.add_section(Config._messageTypesSection)
        for messageType in const.messageTypes:
            if messageType in self._messageTypeLevels:
                option = self._getMessageTypeLevelOptionName(messageType)
                level = self._messageTypeLevels[messageType]                
                config.set(Config._messageTypesSection, option,
                           const.messageLevel2string(level))

        config.add_section("sounds")
        config.set("sounds", "enable",
                   "yes" if self._enableSounds else "no")
        config.set("sounds", "pilotControls",
                   "yes" if self._pilotControlsSounds else "no")
        config.set("sounds", "pilotHotkey", str(self._pilotHotkey))
        #config.set("sounds", "approachCallOuts",
        #           "yes" if self._approachCallOuts else "no")
        config.set("sounds", "speedbrakeAtTD",
                   "yes" if self._speedbrakeAtTD else "no")

        config.set("sounds", "enableChecklists",
                   "yes" if self._enableChecklists else "no")
        config.set("sounds", "checklistHotkey",
                   str(self._checklistHotkey))
        
        config.add_section("update")
        config.set("update", "auto",
                   "yes" if self._autoUpdate else "no")
        config.set("update", "url", self._updateURL)

        config.add_section(Checklist.SECTION)
        for aircraftType in const.aircraftTypes:
            self._checklists[aircraftType].toConfig(config, aircraftType)

        try:
            fd = os.open(configPath, os.O_CREAT|os.O_TRUNC|os.O_WRONLY,
                         0600)
            with os.fdopen(fd, "wt") as f:
                config.write(f)
            self._modified = False
        except Exception, e:
            print >> sys.stderr, "Failed to update config: " + str(e)

    def _getBoolean(self, config, section, option, default):
        """Get the given option as a boolean, if found in the given config,
        otherwise the default."""
        return config.getboolean(section, option) \
               if config.has_option(section, option) \
               else default
    
    def _get(self, config, section, option, default):
        """Get the given option as a string, if found in the given config,
        otherwise the default."""
        return config.get(section, option) \
               if config.has_option(section, option) \
               else default

    def _getMessageTypeLevel(self, config, messageType):
        """Get the message type level for the given message type."""
        option = self._getMessageTypeLevelOptionName(messageType)
        if config.has_option(Config._messageTypesSection, option):
            value = config.get(Config._messageTypesSection, option)
            return const.string2messageLevel(value)
        elif messageType in [const.MESSAGETYPE_LOGGER_ERROR,
                             const.MESSAGETYPE_FAULT,
                             const.MESSAGETYPE_NOGO,
                             const.MESSAGETYPE_GATE_SYSTEM,
                             const.MESSAGETYPE_HELP]:            
            return const.MESSAGELEVEL_BOTH
        else:
            return const.MESSAGELEVEL_FS

    def _getMessageTypeLevelOptionName(self, messageType):
        """Get the option name for the given message type level."""
        return const.messageType2string(messageType)

    def setupLocale(self):
        """Setup the locale based on the language set.

        Return True if a specific language was set, False otherwise."""
        import locale
        if self._language:
            print "Setting up locale for", self._language
            os.environ["LANGUAGE"] = self._language
            langAndEncoding = self._language + "." + locale.getpreferredencoding()
            os.environ["LANG"] = langAndEncoding
            os.environ["LC_MESSAGES"] = langAndEncoding
            os.environ["LC_COLLATE"] = langAndEncoding
            os.environ["LC_CTYPE"] = langAndEncoding
            os.environ["LC_MONETARY"] = langAndEncoding
            os.environ["LC_NUMERIC"] = langAndEncoding
            os.environ["LC_TIME"] = langAndEncoding
            return True
        else:
            return False

    def getLanguage(self):
        """Get the language to be used."""
        import locale
        if self._language:
            if os.name=="nt":
                if self._language in _languageMap:
                    locale.setlocale(locale.LC_ALL, _languageMap[self._language])
                else:
                    locale.setlocale(locale.LC_ALL, "")
            else:
                locale.setlocale(locale.LC_ALL, (self._language,
                                                 locale.getpreferredencoding()))
            return self._language
        else:
            locale.setlocale(locale.LC_ALL, "")
            return locale.getdefaultlocale()[0]

#-------------------------------------------------------------------------------
