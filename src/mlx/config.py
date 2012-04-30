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
        self._flareTimeFromFS = False
        
        self._autoUpdate = True        
        self._updateURL = Config.DEFAULT_UPDATE_URL

        self._messageTypeLevels = {}
        
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

    def getMessageTypeLevel(self, messageType):
        """Get the level for the given message type."""
        return self._messageTypeLevels[messageType] \
               if messageType in self._messageTypeLevels \
               else const.MESSAGELEVEL_NONE

    def setMessageTypeLevel(self, messageType, level):
        """Set the level of the given message type."""
        if messageType not in self._messageTypeLevels or \
           self._messageTypeLevels[messageType]!=level:
            self._messageTypeLevels[messageType] = level
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

    def load(self):
        """Load the configuration from its default location."""
        config = ConfigParser.RawConfigParser()
        config.read(configPath)

        self._pilotID = self._get(config, "login", "id", "")
        self._password = self._get(config, "login", "password", "")
        self._rememberPassword = self._getBoolean(config, "login",
                                                  "rememberPassword", False)

        self._language = self._get(config, "general", "language", "")
        self._flareTimeFromFS = self._getBoolean(config, "general",
                                                 "flareTimeFromFS",
                                                 False)

        self._messageTypeLevels = {}
        for messageType in const.messageTypes:
            self._messageTypeLevels[messageType] = \
                self._getMessageTypeLevel(config, messageType)
            
        self._autoUpdate = self._getBoolean(config, "update", "auto", True)
        self._updateURL = self._get(config, "update", "url",
                                    Config.DEFAULT_UPDATE_URL)

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
        config.set("general", "flareTimeFromFS",
                   "yes" if self._flareTimeFromFS else "no")

        config.add_section(Config._messageTypesSection)
        for messageType in const.messageTypes:
            if messageType in self._messageTypeLevels:
                option = self._getMessageTypeLevelOptionName(messageType)
                level = self._messageTypeLevels[messageType]                
                config.set(Config._messageTypesSection, option,
                           const.messageLevel2string(level))
        
        config.add_section("update")
        config.set("update", "auto",
                   "yes" if self._autoUpdate else "no")
        config.set("update", "url", self._updateURL)

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
        else:
            return const.MESSAGELEVEL_NONE

    def _getMessageTypeLevelOptionName(self, messageType):
        """Get the option name for the given message type level."""
        return const.messageType2string(messageType)
        
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
