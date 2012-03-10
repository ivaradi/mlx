# Configuration and related stuff

#-------------------------------------------------------------------------------

import os
import ConfigParser

#-------------------------------------------------------------------------------

configPath = os.path.join(os.path.expanduser("~"),
                          "mlx.config" if os.name=="nt" else ".mlxrc")

#-------------------------------------------------------------------------------

class Config(object):
    """Our configuration."""
    DEFAULT_UPDATE_URL = "http://mlx.varadiistvan.hu/update"
    
    def __init__(self):
        """Construct the configuration with default values."""

        self._pilotID = ""
        self._password = ""

        self._autoUpdate = True        
        self._updateURL = Config.DEFAULT_UPDATE_URL

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

        config.add_section("update")
        config.set("update", "auto", self._autoUpdate)
        config.set("update", "url", self._updateURL)

        try:
            with open(configPath, "wt") as f:
                config.write(f)
            self._modified = False
        except Exception, e:
            print >> sys.stderr("Failed to update config: " + str(e))

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

#-------------------------------------------------------------------------------
