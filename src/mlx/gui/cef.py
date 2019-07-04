from .common import *

from mlx.util import secondaryInstallation

from cefpython3 import cefpython

import platform
import json
import time
import os
import re
import _thread
import threading
import tempfile
import traceback
import ctypes
import urllib.request, urllib.error, urllib.parse
from lxml import etree
from io import StringIO
import lxml.html

#------------------------------------------------------------------------------

## @package mlx.gui.cef
#
# Some helper stuff related to the Chrome Embedded Framework

#------------------------------------------------------------------------------

# Indicate if we should quit
_toQuit = False

# The SimBrief handler
_simBriefHandler = None

#------------------------------------------------------------------------------

SIMBRIEF_PROGRESS_SEARCHING_BROWSER = 1
SIMBRIEF_PROGRESS_LOADING_FORM = 2
SIMBRIEF_PROGRESS_FILLING_FORM = 3
SIMBRIEF_PROGRESS_WAITING_LOGIN = 4
SIMBRIEF_PROGRESS_LOGGING_IN = 5
SIMBRIEF_PROGRESS_WAITING_RESULT = 6

SIMBRIEF_PROGRESS_RETRIEVING_BRIEFING = 7
SIMBRIEF_PROGRESS_DONE = 1000

SIMBRIEF_RESULT_NONE = 0
SIMBRIEF_RESULT_OK = 1
SIMBRIEF_RESULT_ERROR_OTHER = 2
SIMBRIEF_RESULT_ERROR_NO_FORM = 11
SIMBRIEF_RESULT_ERROR_NO_POPUP = 12
SIMBRIEF_RESULT_ERROR_LOGIN_FAILED = 13

#------------------------------------------------------------------------------

class SimBriefHandler(object):
    """An object to store the state of a SimBrief query."""
    _formURL = "http://flare.privatedns.org/mava_simbrief/simbrief_form.html"

    _querySettings = {
        'navlog': True,
        'etops': True,
        'stepclimbs': True,
        'tlr': True,
        'notams': True,
        'firnot': True,
        'maps': 'Simple',
        };


    def __init__(self):
        """Construct the handler."""
        self._browser = None
        self._plan = None
        self._getCredentials = None
        self._getCredentialsCount = 0
        self._updateProgressFn = None
        self._htmlFilePath = None
        self._lastProgress = SIMBRIEF_PROGRESS_SEARCHING_BROWSER
        self._timeoutID = None

    def initialize(self):
        """Create and initialize the browser used for Simbrief."""
        windowInfo = cefpython.WindowInfo()
        windowInfo.SetAsOffscreen(int(0))

        self._browser = \
          cefpython.CreateBrowserSync(windowInfo, browserSettings = {},
                                      navigateUrl = SimBriefHandler._formURL)
        self._browser.SetClientHandler(OffscreenRenderHandler())
        self._browser.SetFocus(True)
        self._browser.SetClientCallback("OnLoadEnd", self._onLoadEnd)

        bindings = cefpython.JavascriptBindings(bindToFrames=True,
                                                bindToPopups=True)
        bindings.SetFunction("briefingData", self._briefingDataAvailable)
        bindings.SetFunction("formFilled", self._formFilled)
        self._browser.SetJavascriptBindings(bindings)

    def call(self, plan, getCredentials, updateProgress, htmlFilePath):
        """Call SimBrief with the given plan."""
        self._timeoutID = GObject.timeout_add(120*1000, self._timedOut)

        self._plan = plan
        self._getCredentials = getCredentials
        self._getCredentialsCount = 0
        self._updateProgressFn = updateProgress
        self._htmlFilePath = htmlFilePath

        self._browser.LoadUrl(SimBriefHandler._formURL)
        self._updateProgress(SIMBRIEF_PROGRESS_LOADING_FORM,
                             SIMBRIEF_RESULT_NONE, None)

    def _onLoadEnd(self, browser, frame, http_code):
        """Called when a page has been loaded in the SimBrief browser."""
        url = frame.GetUrl()
        print("gui.cef.SimBriefHandler._onLoadEnd", http_code, url)
        if http_code>=300:
            self._updateProgress(self._lastProgress,
                                 SIMBRIEF_RESULT_ERROR_OTHER, None)
        elif url.startswith("http://flare.privatedns.org/mava_simbrief/simbrief_form.html"):
            if self._plan is None:
                return

            self._updateProgress(SIMBRIEF_PROGRESS_FILLING_FORM,
                                 SIMBRIEF_RESULT_NONE, None)

            js = "form=document.getElementById(\"sbapiform\");"
            for (name, value) in self._plan.items():
                js += "form." + name + ".value=\"" + value + "\";"
            for (name, value) in SimBriefHandler._querySettings.items():
                if isinstance(value, bool):
                    js += "form." + name + ".checked=" + \
                      ("true" if value else "false") + ";"
                elif isinstance(value, str):
                    js += "form." + name + ".value=\"" + value + "\";"

            js += "form.submitform.click();"
            js += "window.formFilled();"

            frame.ExecuteJavascript(js)
        elif url.startswith("http://www.simbrief.com/system/login.api.php"):
            (user, password) = self._getCredentials(self._getCredentialsCount)
            if user is None or password is None:
                self._updateProgress(SIMBRIEF_PROGRESS_WAITING_LOGIN,
                                     SIMBRIEF_RESULT_ERROR_LOGIN_FAILED, None)
                return

            self._getCredentialsCount += 1
            js = "form=document.forms[0];"
            js += "form.user.value=\"" + user + "\";"
            js += "form.pass.value=\"" + password + "\";"
            js += "form.submit();"
            frame.ExecuteJavascript(js)
        elif url.startswith("http://www.simbrief.com/ofp/ofp.loader.api.php"):
            self._updateProgress(SIMBRIEF_PROGRESS_WAITING_RESULT,
                                 SIMBRIEF_RESULT_NONE, None)
        elif url.startswith("http://flare.privatedns.org/mava_simbrief/simbrief_briefing.php"):
            js = "form=document.getElementById(\"hiddenform\");"
            js += "window.briefingData(form.hidden_is_briefing_available.value, form.hidden_link.value);";
            frame.ExecuteJavascript(js)

    def _formFilled(self):
        """Called when the form has been filled and submitted."""
        self._updateProgress(SIMBRIEF_PROGRESS_WAITING_LOGIN,
                             SIMBRIEF_RESULT_NONE, None)

    def _briefingDataAvailable(self, available, link):
        """Called when the briefing data is available."""
        if available:
            link ="http://www.simbrief.com/ofp/flightplans/xml/" + link + ".xml"

            self._updateProgress(SIMBRIEF_PROGRESS_RETRIEVING_BRIEFING,
                                 SIMBRIEF_RESULT_NONE, None)

            thread = threading.Thread(target = self._getResults, args = (link,))
            _thread.daemon = True
            _thread.start()
        else:
            self._updateProgress(SIMBRIEF_PROGRESS_RETRIEVING_BRIEFING,
                                 SIMBRIEF_RESULT_ERROR_OTHER, None)

    def _resultsAvailable(self, flightInfo):
        """Called from the result retrieval thread when the result is
        available.

        It checks for the plan being not None, as we may time out."""
        if self._plan is not None:
            self._updateProgress(SIMBRIEF_PROGRESS_DONE,
                                 SIMBRIEF_RESULT_OK, flightInfo)

    def _updateProgress(self, progress, results, flightInfo):
        """Update the progress."""
        self._lastProgress = progress
        if results!=SIMBRIEF_RESULT_NONE:
            if self._timeoutID is not None:
                GObject.source_remove(self._timeoutID)
            self._plan = None

        if self._updateProgressFn is not None:
            self._updateProgressFn(progress, results, flightInfo)

    def _timedOut(self):
        """Called when the timeout occurs."""
        if self._lastProgress==SIMBRIEF_PROGRESS_LOADING_FORM:
            result = SIMBRIEF_RESULT_ERROR_NO_FORM
        elif self._lastProgress==SIMBRIEF_PROGRESS_WAITING_LOGIN:
            result = SIMBRIEF_RESULT_ERROR_NO_POPUP
        else:
            result = SIMBRIEF_RESULT_ERROR_OTHER

        self._updateProgress(self._lastProgress, result, None)

        return False

    def _getResults(self, link):
        """Get the result from the given link."""
        availableInfo = {}
        ## Holds analysis data to be used
        flightInfo = {}

        # Obtaining the xml
        response = urllib.request.urlopen(link)
        xmlContent = response.read()
        # Processing xml
        content = etree.iterparse(StringIO(xmlContent))

        for (action, element) in content:
            # Processing tags that occur multiple times
            if element.tag == "weather":
                weatherElementList = list(element)
                for weatherElement in weatherElementList:
                    flightInfo[weatherElement.tag] = weatherElement.text
            else:
                availableInfo[element.tag] = element.text

        # Processing plan_html
        ## Obtaining chart links
        imageLinks = []
        for imageLinkElement in lxml.html.find_class(availableInfo["plan_html"],
                                                     "ofpmaplink"):
            for imageLink in imageLinkElement.iterlinks():
                if imageLink[1] == 'src':
                    imageLinks.append(imageLink[2])
        flightInfo["image_links"] = imageLinks
        print((sorted(availableInfo.keys())))
        htmlFilePath = "simbrief_plan.html" if self._htmlFilePath is None \
          else self._htmlFilePath
        with open(htmlFilePath, 'w') as f:
            f.write(availableInfo["plan_html"])

        GObject.idle_add(self._resultsAvailable, flightInfo)

#------------------------------------------------------------------------------

def initialize(initializedCallback):
    """Initialize the Chrome Embedded Framework."""
    global _toQuit, _simBriefHandler
    _toQuit = False

    GObject.threads_init()

    _simBriefHandler = SimBriefHandler()
    _initializeCEF([], initializedCallback)

#------------------------------------------------------------------------------

def _initializeCEF(args, initializedCallback):
    """Perform the actual initialization of CEF using the given arguments."""
    print("Initializing CEF with args:", args)

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
            print("Unhandled switch", arg)

    cefpython.Initialize(settings, switches)

    GObject.timeout_add(10, _handleTimeout)

    print("Initialized, executing callback...")
    initializedCallback()

#------------------------------------------------------------------------------

def getContainer():
    """Get a container object suitable for running a browser instance
    within."""
    if os.name=="nt":
        container = Gtk.DrawingArea()
        container.set_property("can-focus", True)
        container.connect("size-allocate", _handleSizeAllocate)
    else:
        container = Gtk.DrawingArea()

    container.show()

    return container

#------------------------------------------------------------------------------

def startInContainer(container, url, browserSettings = {}):
    """Start a browser instance in the given container with the given URL."""
    if os.name=="nt":
        Gdk.threads_enter()
        ctypes.pythonapi.PyCapsule_GetPointer.restype = ctypes.c_void_p
        ctypes.pythonapi.PyCapsule_GetPointer.argtypes = \
            [ctypes.py_object]
        gpointer = ctypes.pythonapi.PyCapsule_GetPointer(
            container.get_property("window").__gpointer__, None)
        libgdk = ctypes.CDLL("libgdk-3-0.dll")
        windowID = libgdk.gdk_win32_window_get_handle(gpointer)
        container.windowID = windowID
        Gdk.threads_leave()
    else:
        container.set_visual(container.get_screen().lookup_visual(0x21))
        windowID = container.get_window().get_xid()

    windowInfo = cefpython.WindowInfo()
    if windowID is not None:
        windowInfo.SetAsChild(windowID)

    return cefpython.CreateBrowserSync(windowInfo,
                                       browserSettings = browserSettings,
                                       navigateUrl = url)

#------------------------------------------------------------------------------

class OffscreenRenderHandler(object):
    def GetRootScreenRect(self, browser, rect_out):
        #print "GetRootScreenRect"
        rect_out += [0, 0, 800, 600]
        return True

    def GetViewRect(self, browser, rect_out):
        #print "GetViewRect"
        rect_out += [0, 0, 800, 600]
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

    def OnPaint(self, browser, element_type, dirty_rects, paint_buffer, width, height):
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
    _simBriefHandler.initialize()

#------------------------------------------------------------------------------

def callSimBrief(plan, getCredentials, updateProgress, htmlFilePath):
    """Call SimBrief with the given plan.

    The callbacks will be called in the main GUI thread."""
    _simBriefHandler.call(plan, getCredentials, updateProgress, htmlFilePath)

#------------------------------------------------------------------------------

def finalize():
    """Finalize the Chrome Embedded Framework."""
    global _toQuit
    _toQuit = True
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
    """Handle the size-allocate event on Windows."""
    if widget is not None:
        cefpython.WindowUtils.OnSize(widget.windowID, 0, 0, 0)
