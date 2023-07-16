# -*- encoding: utf-8 -*-

from . import const
from .util import secondaryInstallation, utf2unicode

import os
import sys
import traceback
import configparser

## @package mlx.config
#
# The handling of the configuration.
#
# The \ref Config class contains the main configuration and is capable of
# loading and saving the configuration. It contains getters and setters for the
# configuration options.
#
# Some parts of the configuration are not simple data items, like strings or
# booleans, but more complicated data. These have their own class, like \ref
# ApproachCallouts or \ref Checklist.

#-------------------------------------------------------------------------------

configPath = os.path.join(os.path.expanduser("~"),
                          "mlx.config" if os.name=="nt" else ".mlxrc") + \
                          ("-secondary" if secondaryInstallation else "")

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

    def __ne__(self, other):
        """Check if the given hotkey is not equal to the other one."""
        return not self==other

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

    def __ne__(self, other):
        """Determine if the checklist is not equal to the given other one."""
        return not self==other

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

class ApproachCallouts(object):
    """The approach callouts for a certain aircraft type."""
    # The name of the section of the approach callouts
    SECTION="callouts"

    @staticmethod
    def fromConfig(config, aircraftType):
        """Create a checklist for the given aircraft type from the given
        config."""
        baseName = "callouts." + const.icaoCodes[aircraftType] + "."
        mapping = {}
        while True:
            option = baseName + str(len(mapping))
            if config.has_option(ApproachCallouts.SECTION, option):
                value = config.get(ApproachCallouts.SECTION, option)
                (altitude, path) = value.split(",")
                altitude = int(altitude.strip())
                path = path.strip()
                mapping[altitude] = path
            else:
                break

        return ApproachCallouts(mapping)

    def __init__(self, mapping = None):
        """Construct the check list with the given mapping of altitudes to
        files."""
        self._mapping = {} if mapping is None else mapping.copy()

    def clone(self):
        """Clone the callout information."""
        return ApproachCallouts(self._mapping)

    def toConfig(self, config, aircraftType):
        """Add this checklist to the given config."""
        baseName = "callouts." + const.icaoCodes[aircraftType] + "."
        index = 0
        for (altitude, path) in self._mapping.items():
            option = baseName + str(index)
            config.set(ApproachCallouts.SECTION, option,
                       "%d, %s" % (altitude, path))
            index += 1

    def getAltitudes(self, descending = True):
        """Get the altitudes in decreasing order by default."""
        altitudes = list(self._mapping.keys())
        altitudes.sort(reverse = descending)
        return altitudes

    def __bool__(self):
        """Return if there is anything in the mapping."""
        return not not self._mapping

    def __eq__(self, other):
        """Determine if the approach callout mapping is equal to the given
        other one."""
        return self._mapping == other._mapping

    def __ne__(self, other):
        """Determine if the approach callout mapping is not equal to the given
        other one."""
        return not self==other

    def __len__(self):
        """Get the number of elements in the mapping."""
        return len(self._mapping)

    def __getitem__(self, altitude):
        """Get the file that is associated with the given altitude.

        If no such file found, return None."""
        return self._mapping[altitude] if altitude in self._mapping else None

    def __iter__(self):
        """Iterate over the pairs of altitudes and paths in decreasing order of
        the altitude."""
        altitudes = self.getAltitudes()

        for altitude in altitudes:
            yield (altitude, self._mapping[altitude])

#-------------------------------------------------------------------------------

class Config(object):
    """Our configuration."""
    DEFAULT_UPDATE_URL = "https://mlx.varadiistvan.hu/update"

    _messageTypesSection = "messageTypes"

    def __init__(self):
        """Construct the configuration with default values."""

        self._pilotID = ""
        self._password = ""
        self._rememberPassword = False

        self._language = ""
        self._hideMinimizedWindow = True
        self._quitOnClose = False
        self._onlineGateSystem = not secondaryInstallation
        self._onlineACARS = not secondaryInstallation
        self._flareTimeFromFS = False
        self._syncFSTime = False
        self._usingFS2Crew = False
        self._iasSmoothingLength = -2
        self._vsSmoothingLength = -2

        self._useSimBrief = False
        self._useInternalBrowserForSimBrief = False
        self._simBriefUserName = ""
        self._simBriefPassword = ""
        self._rememberSimBriefPassword = False

        self._pirepDirectory = None
        self._pirepAutoSave = False

        self._defaultMSFS = os.name=="nt"

        self._enableSounds = not secondaryInstallation

        self._pilotControlsSounds = True
        self._pilotHotkey = Hotkey(ctrl = True, shift = False, key = "0")

        self._taxiSoundOnPushback = False

        self._enableApproachCallouts = False
        self._speedbrakeAtTD = True

        self._enableChecklists = False
        self._checklistHotkey = Hotkey(ctrl = True, shift = True, key = "0")

        self._autoUpdate = True
        self._updateURL = Config.DEFAULT_UPDATE_URL

        self._xplaneRemote = False
        self._xplaneAddress = ""

        self._messageTypeLevels = {}

        self._checklists = {}
        self._approachCallouts = {}
        for aircraftType in const.aircraftTypes:
            self._checklists[aircraftType] = Checklist()
            self._approachCallouts[aircraftType] = ApproachCallouts()

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
    def quitOnClose(self):
        """Get whether the application should quit when the close button is
        clicked."""
        return self._quitOnClose

    @quitOnClose.setter
    def quitOnClose(self, quitOnClose):
        """Set whether the application should quit when the close button is
        clicked."""
        if quitOnClose!=self._quitOnClose:
            self._quitOnClose = quitOnClose
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
    def useSimBrief(self):
        """Check if SimBrief should be used."""
        return self._useSimBrief

    @useSimBrief.setter
    def useSimBrief(self, useSimBrief):
        """Check if SimBrief should be used."""
        if self._useSimBrief != useSimBrief:
            self._useSimBrief = useSimBrief
            self._modified = True

    @property
    def useInternalBrowserForSimBrief(self):
        """Get if we should use the internal browser to handle SimBrief."""
        return self._useInternalBrowserForSimBrief

    @useInternalBrowserForSimBrief.setter
    def useInternalBrowserForSimBrief(self, useInternalBrowserForSimBrief):
        """Set if we should use the internal browser to handle SimBrief."""
        if useInternalBrowserForSimBrief!=self._useInternalBrowserForSimBrief:
            self._useInternalBrowserForSimBrief = useInternalBrowserForSimBrief
            self._modified = True

    @property
    def simBriefUserName(self):
        """Get the SimBrief user name last used"""
        return self._simBriefUserName

    @simBriefUserName.setter
    def simBriefUserName(self, simBriefUserName):
        """Set the SimBrief user name to be used next."""
        if self._simBriefUserName != simBriefUserName:
            self._simBriefUserName = simBriefUserName
            self._modified = True

    @property
    def simBriefPassword(self):
        """Get the SimBrief password last used"""
        return self._simBriefPassword

    @simBriefPassword.setter
    def simBriefPassword(self, simBriefPassword):
        """Set the SimBrief password to be used next."""
        if self._simBriefPassword != simBriefPassword:
            self._simBriefPassword = simBriefPassword
            self._modified = True

    @property
    def rememberSimBriefPassword(self):
        """Get if we should remember the SimBrief password."""
        return self._rememberSimBriefPassword

    @rememberSimBriefPassword.setter
    def rememberSimBriefPassword(self, rememberSimBriefPassword):
        """Set if we should remember the SimBrief password."""
        if rememberSimBriefPassword!=self._rememberSimBriefPassword:
            self._rememberSimBriefPassword = rememberSimBriefPassword
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
            if self._pirepDirectory is None:
                self._pirepAutoSave = False
            self._modified = True

    @property
    def pirepAutoSave(self):
        """Get whether the PIREP should be saved automatically when it becomes
        saveable."""
        return self._pirepAutoSave

    @pirepAutoSave.setter
    def pirepAutoSave(self, pirepAutoSave):
        """Set whether the PIREP should be saved automatically when it becomes
        saveable."""
        pirepAutoSave = pirepAutoSave and self._pirepDirectory is not None
        if pirepAutoSave!=self._pirepAutoSave:
            self._pirepAutoSave = pirepAutoSave
            self._modified = True

    @property
    def defaultMSFS(self):
        """Get if the default simulator type is MS FS."""
        return self._defaultMSFS

    @defaultMSFS.setter
    def defaultMSFS(self, defaultMSFS):
        """Set if the default simulator type is MS FS."""
        if defaultMSFS!=self._defaultMSFS:
            self._defaultMSFS = defaultMSFS
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

    @property
    def taxiSoundOnPushback(self):
        """Get whether the taxi sound should be played as soon as pushback starts."""
        return self._taxiSoundOnPushback

    @taxiSoundOnPushback.setter
    def taxiSoundOnPushback(self, taxiSoundOnPushback):
        """Set whether the taxi sound should be played as soon as pushback starts."""
        if taxiSoundOnPushback!=self._taxiSoundOnPushback:
            self._taxiSoundOnPushback = taxiSoundOnPushback
            self._modified = True

    @property
    def enableApproachCallouts(self):
        """Get whether the approach callouts should be played."""
        return self._enableApproachCallouts

    @enableApproachCallouts.setter
    def enableApproachCallouts(self, enableApproachCallouts):
        """Set whether the approach callouts should be played."""
        if enableApproachCallouts!=self._enableApproachCallouts:
            self._enableApproachCallouts = enableApproachCallouts
            self._modified = True

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

    @property
    def xplaneRemote(self):
        """Indicate if X-Plane should be accessed remotely."""
        return self._xplaneRemote

    @xplaneRemote.setter
    def xplaneRemote(self, xplaneRemote):
        """Set if X-Plane should be accessed remotely."""
        if xplaneRemote!=self._xplaneRemote:
            self._xplaneRemote = xplaneRemote
            self._modified = True

    @property
    def xplaneAddress(self):
        """Get the address of the machine running X-Plane"""
        return self._xplaneAddress

    @xplaneAddress.setter
    def xplaneAddress(self, xplaneAddress):
        """Set the address of the machine running X-Plane."""
        if xplaneAddress!=self._xplaneAddress:
            self._xplaneAddress = xplaneAddress
            self._modified = True

    def getChecklist(self, aircraftType):
        """Get the checklist for the given aircraft type."""
        return self._checklists[aircraftType]

    def setChecklist(self, aircraftType, checklist):
        """Set the checklist for the given aircraft type."""
        if checklist!=self._checklists[aircraftType]:
            self._checklists[aircraftType] = checklist.clone()
            self._modified = True

    def getApproachCallouts(self, aircraftType):
        """Get the approach callouts for the given aircraft type."""
        return self._approachCallouts[aircraftType]

    def setApproachCallouts(self, aircraftType, approachCallouts):
        """Set the approach callouts for the given aircraft type."""
        if not approachCallouts==self._approachCallouts[aircraftType]:
            self._approachCallouts[aircraftType] = approachCallouts.clone()
            self._modified = True

    def load(self):
        """Load the configuration from its default location."""
        try:
            config = configparser.RawConfigParser()
            config.read(configPath)
        except:
            traceback.print_exc()
            return

        self._pilotID = self._get(config, "login", "id", "")
        self._password = self._get(config, "login", "password", "")
        self._rememberPassword = self._getBoolean(config, "login",
                                                  "rememberPassword", False)

        self._language = self._get(config, "general", "language", "")

        self._hideMinimizedWindow = self._getBoolean(config, "general",
                                                     "hideMinimizedWindow",
                                                     True)
        self._quitOnClose = self._getBoolean(config, "general",
                                             "quitOnClose", False)

        self._onlineGateSystem = self._getBoolean(config, "general",
                                                  "onlineGateSystem",
                                                  not secondaryInstallation)
        self._onlineACARS = self._getBoolean(config, "general",
                                             "onlineACARS",
                                             not secondaryInstallation)
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

        self._useSimBrief = self._getBoolean(config, "simbrief",
                                             "use", False)
        self._useInternalBrowserForSimBrief = self._getBoolean(config, "simbrief",
                                                               "useInternalBrowser",
                                                               False)
        self._simBriefUserName = self._get(config, "simbrief",
                                           "username", "")
        self._simBriefPassword = self._get(config, "simbrief",
                                           "password", "")
        self._rememberSimBriefPassword = self._getBoolean(config, "simbrief",
                                                          "rememberPassword",
                                                          False)

        self._pirepDirectory = self._get(config, "general",
                                         "pirepDirectory", None)

        self._pirepAutoSave = self._getBoolean(config, "general",
                                               "pirepAutoSave", False)
        if self._pirepDirectory is None:
            self._pirepAutoSave = False

        self._messageTypeLevels = {}
        for messageType in const.messageTypes:
            self._messageTypeLevels[messageType] = \
                self._getMessageTypeLevel(config, messageType)

        self._enableSounds = self._getBoolean(config, "sounds", "enable",
                                              not secondaryInstallation)
        self._pilotControlsSounds = self._getBoolean(config, "sounds",
                                                     "pilotControls", True)
        self._pilotHotkey.set(self._get(config, "sounds",
                                        "pilotHotkey", "C0"))

        self._taxiSoundOnPushback = \
            self._getBoolean(config, "sounds", "taxiSoundOnPushback", False)
        self._enableApproachCallouts = \
            self._getBoolean(config, "sounds", "enableApproachCallouts", False)
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
            self._approachCallouts[aircraftType] = \
                ApproachCallouts.fromConfig(config, aircraftType)

        self._defaultMSFS = self._getBoolean(config, "general",
                                             "defaultMSFS", os.name=="nt")

        self._xplaneRemote = self._getBoolean(config, "general",
                                              "xplaneRemote", False)
        self._xplaneAddress = self._get(config, "general",
                                        "xplaneAddress", "")

        self._modified = False

    def save(self):
        """Save the configuration file if it has been modified."""
        if not self._modified:
            return

        config = configparser.RawConfigParser()

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
        config.set("general", "quitOnClose",
                   "yes" if self._quitOnClose else "no")
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

        config.add_section("simbrief")
        config.set("simbrief", "use",
                   "yes" if self._useSimBrief else "no")
        config.set("simbrief", "useInternalBrowser",
                   "yes" if self._useInternalBrowserForSimBrief else "no")
        config.set("simbrief", "username", self._simBriefUserName)
        config.set("simbrief", "password", self._simBriefPassword)
        config.set("simbrief", "rememberPassword",
                   "yes" if self._rememberSimBriefPassword else "no")

        if self._pirepDirectory is not None:
            config.set("general", "pirepDirectory", self._pirepDirectory)
        config.set("general", "pirepAutoSave",
                   "yes" if self._pirepAutoSave else "no")

        config.set("general", "defaultMSFS",
                   "yes" if self._defaultMSFS else "no")

        config.set("general", "xplaneRemote",
                   "yes" if self._xplaneRemote else "no")
        config.set("general", "xplaneAddress", self._xplaneAddress)

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
        config.set("sounds", "taxiSoundOnPushback",
                   "yes" if self._taxiSoundOnPushback else "no")
        config.set("sounds", "enableApproachCallouts",
                   "yes" if self._enableApproachCallouts else "no")
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
        config.add_section(ApproachCallouts.SECTION)
        for aircraftType in const.aircraftTypes:
            self._checklists[aircraftType].toConfig(config, aircraftType)
            self._approachCallouts[aircraftType].toConfig(config, aircraftType)

        try:
            fd = os.open(configPath, os.O_CREAT|os.O_TRUNC|os.O_WRONLY,
                         0o600)
            with os.fdopen(fd, "wt") as f:
                config.write(f)
            self._modified = False

            print("Configuration saved:")
            self.log()

        except Exception as e:
            print("Failed to update config: " + \
                                 utf2unicode(str(e)), file=sys.stderr)

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
        elif secondaryInstallation:
            return const.MESSAGELEVEL_NONE
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
            print("Setting up locale for", self._language)
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

    def log(self):
        """Log the configuration by printing the values"""
        print("  pilot ID:", self._pilotID)
        print("  rememberPassword:", self._rememberPassword)

        print("  language:", self._language)

        print("  hideMinimizedWindow:", self._hideMinimizedWindow)
        print("  quitOnClose:", self._quitOnClose)

        print("  onlineGateSystem:", self._onlineGateSystem)
        print("  onlineACARS:", self._onlineACARS)

        print("  flareTimeFromFS:", self._flareTimeFromFS)
        print("  syncFSTime:", self._syncFSTime)
        print("  usingFS2Crew:", self._usingFS2Crew)

        print("  iasSmoothingLength:", self._iasSmoothingLength)
        print("  vsSmoothingLength:", self._vsSmoothingLength)

        print("  useSimBrief:", self._useSimBrief)
        print("  useInternalBrowserForSimBrief:", self._useInternalBrowserForSimBrief)
        print("  simBriefUserName:", self._simBriefUserName)
        print("  rememberSimBriefPassword:", self._rememberSimBriefPassword)

        print("  pirepDirectory:", self._pirepDirectory)
        print("  pirepAutoSave:", self._pirepAutoSave)

        print("  defaultMSFS:", self._defaultMSFS)
        print("  xplaneRemote:", self._xplaneRemote)
        print("  xplaneAddress:", self._xplaneAddress)

        print("  enableSounds:", self._enableSounds)

        print("  pilotControlsSounds:", self._pilotControlsSounds)
        print("  pilotHotkey:", str(self._pilotHotkey))

        print("  taxiSoundOnPushback:", self._taxiSoundOnPushback)

        print("  enableApproachCallouts:", self._enableApproachCallouts)
        print("  speedbrakeAtTD:", self._speedbrakeAtTD)

        print("  enableChecklists:", self._enableChecklists)
        print("  checklistHotkey:", str(self._checklistHotkey))

        print("  autoUpdate:", self._autoUpdate)
        print("  updateURL:", self._updateURL)

        print("  messageTypeLevels:")
        for (type, level) in self._messageTypeLevels.items():
            print("    %s: %s" % (const.messageType2string(type),
                                  const.messageLevel2string(level)))

        print("  checklists:")
        for (type, checklist) in self._checklists.items():
            print("    %s:" % (const.icaoCodes[type],))
            for path in checklist:
                print("      " + path)

        print("  approachCallouts:")
        for (type, approachCallouts) in self._approachCallouts.items():
            print("    %s:" % (const.icaoCodes[type],))
            for (altitude, path) in approachCallouts:
                print("      %d: %s" % (altitude, path))

#-------------------------------------------------------------------------------
