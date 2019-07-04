import os

#-----------------------------------------------------------------------------

## @package mlx.common
#
# Common definitions to be used by both the GUI and possible other parts
#
#---------------------------------------------------------------------------------------

MAVA_BASE_URL = os.environ.get("MAVA_BASE_URL", "http://virtualairlines.hu")

#-------------------------------------------------------------------------------

from gi.repository import GObject as gobject

#-------------------------------------------------------------------------------

def fixUnpickledValue(value):
    """Fix the given unpickled value.

    It handles some basic data, like scalars, lists and tuples. If it
    encounters byte arrays, they are decoded as 'utf-8' strings."""
    if isinstance(value, bytes):
        return str(value, "utf-8")
    elif isinstance(value, list):
        return [fixUnpickledValue(v) for v in value]
    elif isinstance(value, tuple):
        return tuple([fixUnpickledValue(v) for v in value])
    else:
        return value

#-------------------------------------------------------------------------------

def fixUnpickled(state):
    """Fix the given unpickled state.

    It checks keys and values, and if it encounters any byte arrays, they are
    decoded with the encoding 'utf-8'. It returns a new dictionary.
    """
    newDict = {}
    for (key, value) in iter(state.items()):
        newDict[fixUnpickledValue(key)] = fixUnpickledValue(value)

    return newDict
