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
    _formURLBase = MAVA_BASE_URL + "/simbrief_form.php"

    _resultURLBase = MAVA_BASE_URL + "/simbrief_briefing.php"

    @staticmethod
    def getFormURL(plan):
        """Get the form URL for the given plan."""
        return SimBriefHandler._formURLBase + "?" + \
            urllib.parse.urlencode(plan)

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
          cefpython.CreateBrowserSync(windowInfo, browserSettings = {})
        self._browser.SetClientHandler(OffscreenRenderHandler())
        self._browser.SetFocus(True)
        self._browser.SetClientCallback("OnLoadEnd", self._onLoadEnd)
        self._browser.SetClientCallback("OnLoadError", self._onLoadError)
        self._browser.SetClientCallback("OnBeforeBrowse",
                                        lambda browser, frame, request,
                                        user_gesture, is_redirect: False)

    def call(self, plan, getCredentials, updateProgress, htmlFilePath):
        """Call SimBrief with the given plan."""
        self._timeoutID = GObject.timeout_add(120*1000, self._timedOut)

        self._plan = plan
        self._getCredentials = getCredentials
        self._getCredentialsCount = 0
        self._updateProgressFn = updateProgress
        self._htmlFilePath = htmlFilePath

        self._browser.LoadUrl(SimBriefHandler.getFormURL(plan))
        self._updateProgress(SIMBRIEF_PROGRESS_LOADING_FORM,
                             SIMBRIEF_RESULT_NONE, None)

    def finalize(self):
        """Close the browser and release it."""
        self._browser.CloseBrowser()
        self._browser = None

    def _onLoadEnd(self, browser, frame, http_code):
        """Called when a page has been loaded in the SimBrief browser."""
        url = frame.GetUrl()
        print("gui.cef.SimBriefHandler._onLoadEnd", http_code, url)
        if http_code>=300:
            self._updateProgress(self._lastProgress,
                                 SIMBRIEF_RESULT_ERROR_OTHER, None)
        elif url.startswith(SimBriefHandler._formURLBase):
            self._updateProgress(SIMBRIEF_PROGRESS_WAITING_LOGIN,
                                 SIMBRIEF_RESULT_NONE, None)
        elif url.startswith("https://www.simbrief.com/system/login.api.sso.php"):
            js = "document.getElementsByClassName(\"login_option navigraph\")[0].click();"
            frame.ExecuteJavascript(js)
        elif url.startswith("https://identity.api.navigraph.com/login?"):
            (user, password) = self._getCredentials(self._getCredentialsCount)
            if user is None or password is None:
                self._updateProgress(SIMBRIEF_PROGRESS_WAITING_LOGIN,
                                     SIMBRIEF_RESULT_ERROR_LOGIN_FAILED, None)
                return

            self._getCredentialsCount += 1

            js = "form=document.getElementsByName(\"form\")[0];"
            js +="form.username.value=\"" + user + "\";"
            js +="form.password.value=\"" + password + "\";"
            js +="form.submit();"
            frame.ExecuteJavascript(js)
        elif url.startswith("https://www.simbrief.com/ofp/ofp.loader.api.php"):
            self._updateProgress(SIMBRIEF_PROGRESS_WAITING_RESULT,
                                 SIMBRIEF_RESULT_NONE, None)
        elif url.startswith(SimBriefHandler._resultURLBase):
            self._updateProgress(SIMBRIEF_PROGRESS_RETRIEVING_BRIEFING,
                                 SIMBRIEF_RESULT_OK, None)

    def _onLoadError(self, browser, frame, error_code, error_text_out,
                     failed_url):
        """Called when loading of an URL fails."""
        print("gui.cef.SimBriefHandler._onLoadError", browser, frame, error_code, error_text_out, failed_url)
        self._updateProgress(self._lastProgress,
                             SIMBRIEF_RESULT_ERROR_OTHER, None)

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
    if os.name=="nt":
        _initializeCEF1(args, initializedCallback)
    else:
        GObject.timeout_add(100, _initializeCEF1, args, initializedCallback)

#------------------------------------------------------------------------------

def _initializeCEF1(args, initializedCallback):
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
        "windowless_rendering_enabled": True,
        "cache_path": os.path.join(GLib.get_user_cache_dir(),
                                   "mlxcef")
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
    return False

#------------------------------------------------------------------------------

def getContainer():
    """Get a container object suitable for running a browser instance
    within."""
    container = Gtk.DrawingArea()
    container.set_property("can-focus", True)
    container.connect("size-allocate", _handleSizeAllocate)
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
        windowRect = [0, 0, 1, 1]
    else:
        container.set_visual(container.get_screen().lookup_visual(0x21))
        windowID = container.get_window().get_xid()
        windowRect = None

    windowInfo = cefpython.WindowInfo()
    if windowID is not None:
        windowInfo.SetAsChild(windowID, windowRect = windowRect)

    browser = cefpython.CreateBrowserSync(windowInfo,
                                          browserSettings = browserSettings,
                                          navigateUrl = url)
    container.browser = browser

    return browser

#------------------------------------------------------------------------------

class OffscreenRenderHandler(object):
    def GetRootScreenRect(self, browser, rect_out):
        #print "GetRootScreenRect"
        rect_out += [0, 0, 1920, 1080]
        return True

    def GetViewRect(self, browser, rect_out):
        #print "GetViewRect"
        rect_out += [0, 40, 1920, 1040]
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

    def OnBeforePopup(self, browser, frame, target_url, target_frame_name,
                      target_disposition, user_gesture,
                      popup_features, window_info_out, client,
                      browser_settings_out, no_javascript_access_out,
                      **kwargs):
        wInfo = cefpython.WindowInfo()
        wInfo.SetAsOffscreen(int(0))

        window_info_out.append(wInfo)

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

    _simBriefHandler.finalize()

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
    if os.name=="nt":
        if widget is not None and hasattr(widget, "windowID"):
            cefpython.WindowUtils.OnSize(widget.windowID, 0, 0, 0)
    else:
         if widget is not None and hasattr(widget, "browser") and \
            widget.browser is not None:
             widget.browser.SetBounds(sizeAlloc.x, sizeAlloc.y,
                                      sizeAlloc.width, sizeAlloc.height)
