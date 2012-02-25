# Implementation of the status icon

#-------------------------------------------------------------------------------

from common import *

#-------------------------------------------------------------------------------

class StatusIcon(object):
    """The class handling the status icon."""
    def __init__(self, iconDirectory, gui):
        """Construct the status icon."""
        self._gui = gui
        
        menu = gtk.Menu()

        self._showHideMenuItem = gtk.CheckMenuItem()  
        self._showHideMenuItem.set_label("Show main window")  
        self._showHideMenuItem.set_active(True)
        self._showHideMenuItem.connect("toggled", self._showHideToggled)
        self._showHideMenuItem.show()  
        menu.append(self._showHideMenuItem)  

        menu.show()  

        iconFile = os.path.join(iconDirectory, "logo.ico")

        if appIndicator:
            if pygobject:
                indicator = appindicator.Indicator.new ("mava-logger-x", iconFile,
                                                        appindicator.IndicatorCategory.APPLICATION_STATUS)
                indicator.set_status (appindicator.IndicatorStatus.ACTIVE)
            else:
                indicator = appindicator.Indicator ("mava-logger-x", iconFile,
                                                    appindicator.CATEGORY_APPLICATION_STATUS)
                indicator.set_status (appindicator.STATUS_ACTIVE)

            indicator.set_menu(menu)
            self._indicator = indicator
            self._usingIndicator = True
        else:
            def popup_menu(status, button, time):
                menu.popup(None, None, gtk.status_icon_position_menu,
                           button, time, status)

            statusIcon = gtk.StatusIcon()
            statusIcon.set_from_file(iconFile)
            statusIcon.set_tooltip_markup("MAVA Logger X")
            statusIcon.set_visible(True)
            statusIcon.connect('popup-menu', popup_menu)
            statusIcon.connect('activate',
                               lambda status: self._gui.toggleMainWindow())
            self._statusIcon = statusIcon
            self._usingIndicator = False

    def mainWindowHidden(self):
        """Called when the main window is hidden."""
        self._showHideMenuItem.set_active(False)

    def mainWindowShown(self):
        """Called when the main window is shown."""
        self._showHideMenuItem.set_active(True)
        
    def _showHideToggled(self, menuitem):
        """Called when the show/hide menu item is toggled."""
        if self._showHideMenuItem.get_active():
            self._gui.showMainWindow()
        else:
            self._gui.hideMainWindow()
