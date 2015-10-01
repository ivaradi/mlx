from common import *

from mlx.util import secondaryInstallation

from cefpython3 import cefpython
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

import platform
import json
import time
import os
import re
import threading
import tempfile
import traceback

#------------------------------------------------------------------------------

## @package mlx.gui.cef
#
# Some helper stuff related to the Chrome Embedded Framework

#------------------------------------------------------------------------------

# Indicate if we should quit
_toQuit = False

# The Selenium thread
_seleniumHandler = None

#------------------------------------------------------------------------------

def getArgsFilePath():
    """Get the path of the argument file."""
    if os.name=="nt":
        return os.path.join(tempfile.gettempdir(),
                            "mlxcef.args" +
                            (".secondary" if secondaryInstallation else ""))
    else:
        import pwd
        return os.path.join(tempfile.gettempdir(),
                            "mlxcef." + pwd.getpwuid(os.getuid())[0] + ".args" +
                            (".secondary" if secondaryInstallation else ""))

#------------------------------------------------------------------------------

class ArgsFileWaiter(threading.Thread):
    """A thread to wait for the appearance of the arguments file."""
    def __init__(self, initializedCallback):
        """Construct the thread."""
        threading.Thread.__init__(self)
        self.daemon = True

        self._initializedCallback = initializedCallback

    def run(self):
        """Repeatedly check for the existence of the arguments file.

        If it is found, read it, extract the arguments and insert a job into
        the GUI loop to perform the actual initialization of CEF."""
        argsFilePath = getArgsFilePath()
        print "Waiting for the arguments file '%s' to appear" % (argsFilePath,)

        while not os.path.exists(argsFilePath):
            time.sleep(0.1)

        print "Got arguments, reading them."""

        with open(argsFilePath, "rt") as f:
            args = f.read().split()

        gobject.idle_add(_initializeCEF, args, self._initializedCallback)

#------------------------------------------------------------------------------

class SeleniumHandler(threading.Thread):
    """Thread to handle Selenium operations."""
    def __init__(self, programDirectory):
        """Construct the thread."""
        threading.Thread.__init__(self)
        self.daemon = False

        self._programDirectory = programDirectory

        self._commandsCondition = threading.Condition()
        self._commands = []

        self._toQuit = False

    def run(self):
        """Create the Selenium driver and the perform any operations
        requested."""
        scriptName = "mlx_cef_caller"
        if secondaryInstallation:
            scriptName += "_secondary"
        scriptName += ".bat" if os.name=="nt" else ".sh"

        scriptPath = os.path.join(self._programDirectory, scriptName)
        print "Creating the Selenium driver to call script", scriptPath

        options = Options()
        options.binary_location = scriptPath
        driver = webdriver.Chrome(chrome_options = options)
        # try:
        # except:
        #     traceback.print_exc()

        print "Created Selenium driver."
        while not self._toQuit:
            with self._commandsCondition:
                while not self._commands:
                    self._commandsCondition.wait()

                command = self._commands[0]
                del self._commands[0]

            command()

        driver.quit()

    def quit(self):
        """Instruct the thread to quit and then join it."""
        self._enqueue(self._quit)
        self.join()

    def _enqueue(self, command):
        """Enqueue the given command.

        command should be a function to be executed in the thread."""
        with self._commandsCondition:
            self._commands.append(command)
            self._commandsCondition.notify()

    def _quit(self):
        """Set the _toQuit member variable to indicate that the thread should
        quit."""
        self._toQuit = True

#------------------------------------------------------------------------------

def initialize(programDirectory, initializedCallback):
    """Initialize the Chrome Embedded Framework."""
    global _toQuit, _seleniumHandler
    _toQuit = False

    gobject.threads_init()

    argsFilePath = getArgsFilePath()
    try:
        os.unlink(argsFilePath)
    except:
        pass

    _seleniumHandler = SeleniumHandler(programDirectory)
    _seleniumHandler.start()

    ArgsFileWaiter(initializedCallback).start()

#------------------------------------------------------------------------------

def _initializeCEF(args, initializedCallback):
    """Perform the actual initialization of CEF using the given arguments."""
    print "Initializing CEF with args:", args

    settings = {
        "debug": True, # cefpython debug messages in console and in log_file
        "log_severity": cefpython.LOGSEVERITY_VERBOSE, # LOGSEVERITY_VERBOSE
        "log_file": "", # Set to "" to disable
        "release_dcheck_enabled": True, # Enable only when debugging
        # This directories must be set on Linux
        "locales_dir_path": os.path.join(cefpython.GetModuleDirectory(), "locales"),
        "resources_dir_path": cefpython.GetModuleDirectory(),
        "browser_subprocess_path": "%s/%s" % \
            (cefpython.GetModuleDirectory(), "subprocess"),
    }

    switches={}
    for arg in args:
        if arg.startswith("--"):
            if arg != "--enable-logging":
                assignIndex = arg.find("=")
                if assignIndex<0:
                    switches[arg[2:]] = ""
                else:
                    switches[arg[2:assignIndex]] = arg[assignIndex+1:]
        else:
            print "Unhandled switch", arg

    cefpython.Initialize(settings, switches)

    gobject.timeout_add(10, _handleTimeout)

    print "Initialized, executing callback..."
    initializedCallback()

#------------------------------------------------------------------------------

def getContainer():
    """Get a container object suitable for running a browser instance
    within."""
    if os.name=="nt":
        container = gtk.DrawingArea()
        container.set_property("can-focus", True)
        container.connect("size-allocate", _handleSizeAllocate)
    else:
        container = gtk.VBox(True, 0)

    container.show()

    return container

#------------------------------------------------------------------------------

def startInContainer(container, url, browserSettings = {}):
    """Start a browser instance in the given container with the given URL."""
    if os.name=="nt":
        windowID = container.get_window().handle
    else:
        m = re.search("GtkVBox at 0x(\w+)", str(container))
        hexID = m.group(1)
        windowID = int(hexID, 16)

    windowInfo = cefpython.WindowInfo()
    windowInfo.SetAsChild(windowID)

    return cefpython.CreateBrowserSync(windowInfo,
                                       browserSettings = browserSettings,
                                       navigateUrl = url)

#------------------------------------------------------------------------------

def finalize():
    """Finalize the Chrome Embedded Framework."""
    global _toQuit, _seleniumHandler
    toQuit = True
    _seleniumHandler.quit()
    cefpython.Shutdown()

#------------------------------------------------------------------------------

def _handleTimeout():
    """Handle the timeout by running the CEF message loop."""
    if _toQuit:
        return False
    else:
        cefpython.MessageLoopWork()
        return True

#------------------------------------------------------------------------------

def _handleSizeAllocate(widget, sizeAlloc):
    """Handle the size-allocate event."""
    cefpython.WindowUtils.OnSize(widget.get_window().handle, 0, 0, 0)
