# Configuration and related stuff

#-------------------------------------------------------------------------------

class Config(object):
    """Our configuration."""
    def __init__(self):
        """Construct the configuration with default values."""
        self.autoUpdate = True
        
        self.updateURL = \
            "http://mlx.varadiistvan.hu/update"

#-------------------------------------------------------------------------------
