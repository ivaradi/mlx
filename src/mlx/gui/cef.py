from common import *

from mava_simbrief import MavaSimbriefIntegrator

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

SIMBRIEF_PROGRESS_SEARCHING_BROWSER = MavaSimbriefIntegrator.PROGRESS_SEARCHING_BROWSER
SIMBRIEF_PROGRESS_LOADING_FORM = MavaSimbriefIntegrator.PROGRESS_LOADING_FORM
SIMBRIEF_PROGRESS_FILLING_FORM = MavaSimbriefIntegrator.PROGRESS_FILLING_FORM
SIMBRIEF_PROGRESS_WAITING_LOGIN = MavaSimbriefIntegrator.PROGRESS_WAITING_LOGIN
SIMBRIEF_PROGRESS_LOGGING_IN = MavaSimbriefIntegrator.PROGRESS_LOGGING_IN
SIMBRIEF_PROGRESS_WAITING_RESULT = MavaSimbriefIntegrator.PROGRESS_WAITING_RESULT

SIMBRIEF_PROGRESS_RETRIEVING_BRIEFING = MavaSimbriefIntegrator.PROGRESS_MAX + 1
SIMBRIEF_PROGRESS_DONE = 1000

SIMBRIEF_RESULT_NONE = MavaSimbriefIntegrator.RESULT_NONE
SIMBRIEF_RESULT_OK = MavaSimbriefIntegrator.RESULT_OK
SIMBRIEF_RESULT_ERROR_OTHER = MavaSimbriefIntegrator.RESULT_ERROR_OTHER
SIMBRIEF_RESULT_ERROR_NO_FORM = MavaSimbriefIntegrator.RESULT_ERROR_NO_FORM
SIMBRIEF_RESULT_ERROR_NO_POPUP = MavaSimbriefIntegrator.RESULT_ERROR_NO_POPUP
SIMBRIEF_RESULT_ERROR_LOGIN_FAILED = MavaSimbriefIntegrator.RESULT_ERROR_LOGIN_FAILED

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

        self._driver = None

        self._simBriefBrowser = None

        self._toQuit = False

    @property
    def programDirectory(self):
        """Get the program directory."""
        return self._programDirectory

    @property
    def simBriefInitURL(self):
        """Get the initial URL for the SimBrief browser."""
        return "file://" + os.path.join(self.programDirectory, "simbrief.html")

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
        driver = self._driver = webdriver.Chrome(chrome_options = options)
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

    def initializeSimBrief(self):
        """Create and initialize the browser used for Simbrief."""
        windowInfo = cefpython.WindowInfo()
        windowInfo.SetAsOffscreen(int(0))

        url = self.simBriefInitURL
        self._simBriefBrowser = \
          cefpython.CreateBrowserSync(windowInfo, browserSettings = {},
                                      navigateUrl = self.simBriefInitURL)
        self._simBriefBrowser.SetClientHandler(OffscreenRenderHandler())
        self._simBriefBrowser.SetFocus(True)

    def callSimBrief(self, plan, getCredentials, updateProgress,
                     htmlFilePath):
        """Call SimBrief with the given plan."""
        self._enqueue(lambda:
                      self._callSimBrief(plan, self._driver,
                                         getCredentials, updateProgress,
                                         htmlFilePath))

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

    def _callSimBrief(self, plan, driver,
                      getCredentials, updateProgress, htmlFilePath):
        """Perform the SimBrief call."""
        integrator = MavaSimbriefIntegrator(plan = plan, driver = driver)
        link = integrator.get_xml_link(getCredentials, updateProgress,
                                       local_xml_debug = False,
                                       local_html_debug = False)

        if link is not None:
            updateProgress(SIMBRIEF_PROGRESS_RETRIEVING_BRIEFING,
                           SIMBRIEF_RESULT_NONE, None)

            try:
                flight_info = integrator.get_results(link,
                                                     html_file_path =
                                                     htmlFilePath)

                updateProgress(SIMBRIEF_PROGRESS_DONE,
                               SIMBRIEF_RESULT_OK, flight_info)
            except Exception, e:
                print "Failed retrieving the briefing:", e
                updateProgress(SIMBRIEF_PROGRESS_RETRIEVING_BRIEFING,
                               SIMBRIEF_RESULT_ERROR_OTHER, None)

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

class OffscreenRenderHandler(object):
    def GetRootScreenRect(self, browser, rect):
        #print "GetRootScreenRect"
        rect += [0, 0, 800, 600]
        return True

    def GetViewRect(self, browser, rect):
        #print "GetViewRect"
        rect += [0, 0, 800, 600]
        return True

    def GetScreenPoint(self, browser, viewX, viewY, screenCoordinates):
        #print "GetScreenPoint", viewX, viewY
        rect += [viewX, viewY]
        return True

    def GetScreenInfo(self, browser, screenInfo):
        #print "GetScreenInfo"
        pass

    def OnPopupShow(self, browser, show):
        #print "OnPopupShow", show
        pass

    def OnPopupSize(self, browser, rect):
        #print "OnPopupSize", rect
        pass

    def OnPaint(self, browser, paintElementType, dirtyRects, buffer, width, height):
        #print "OnPaint", paintElementType, dirtyRects, buffer, width, height
        pass

    def OnCursorChange(self, browser, cursor):
        #print "OnCursorChange", cursor
        pass

    def OnScrollOffsetChanged(self, browser):
        #print "OnScrollOffsetChange"
        pass

    def OnBeforePopup(self, browser, frame, targetURL, targetFrameName,
                      popupFeatures, windowInfo, client, browserSettings,
                      noJavascriptAccess):
        wInfo = cefpython.WindowInfo()
        wInfo.SetAsOffscreen(int(0))

        windowInfo.append(wInfo)

        return False

#------------------------------------------------------------------------------

def initializeSimBrief():
    """Initialize the (hidden) browser window for SimBrief."""
    _seleniumHandler.initializeSimBrief()

#------------------------------------------------------------------------------

def callSimBrief(plan, getCredentials, updateProgress, htmlFilePath):
    """Call SimBrief with the given plan."""
    _seleniumHandler.callSimBrief(plan, getCredentials,
                                  updateProgress, htmlFilePath)

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
