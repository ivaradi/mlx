# Implementation of the status icon

#-------------------------------------------------------------------------------

from common import *

import mlx.const as const

#-------------------------------------------------------------------------------

class StatusIcon(FlightStatusHandler):
    """The class handling the status icon."""
    def __init__(self, iconDirectory, gui):
        """Construct the status icon."""
        super(StatusIcon, self).__init__()

        self._gui = gui
        self._selfToggling = False

        menu = gtk.Menu()

        if appIndicator:
            self._stageMenuItem = gtk.MenuItem()
            self._stageMenuItem.show()
            menu.append(self._stageMenuItem)

            self._ratingMenuItem = gtk.MenuItem()
            self._ratingMenuItem.show()
            menu.append(self._ratingMenuItem)

            separator = gtk.SeparatorMenuItem()
            separator.show()
            menu.append(separator)

        self._showHideMenuItem = gtk.CheckMenuItem()  
        self._showHideMenuItem.set_label("Show main window")  
        self._showHideMenuItem.set_active(True)
        self._showHideMenuItem.connect("toggled", self._showHideToggled)
        self._showHideMenuItem.show()  
        menu.append(self._showHideMenuItem)  

        self._quitMenuItem = gtk.MenuItem()  
        self._quitMenuItem.set_label("Quit")  
        self._quitMenuItem.show()  
        self._quitMenuItem.connect("activate", self._gui._quit)
        menu.append(self._quitMenuItem)  

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
        else:
            def popup_menu(status, button, time):
                menu.popup(None, None, gtk.status_icon_position_menu,
                           button, time, status)

            statusIcon = gtk.StatusIcon()
            statusIcon.set_from_file(iconFile)
            statusIcon.set_visible(True)
            statusIcon.connect('popup-menu', popup_menu)
            statusIcon.connect('activate',
                               lambda status: self._gui.toggleMainWindow())
            self._statusIcon = statusIcon

        self._updateFlightStatus()

    def mainWindowHidden(self):
        """Called when the main window is hidden."""
        if self._showHideMenuItem.get_active():
            self._selfToggling = True
            self._showHideMenuItem.set_active(False)

    def mainWindowShown(self):
        """Called when the main window is shown."""
        if not self._showHideMenuItem.get_active():
            self._selfToggling = True
            self._showHideMenuItem.set_active(True)

    def destroy(self):
        """Hide and destroy the status icon."""
        if appIndicator:
            if pygobject:
                self._indicator.set_status(appindicator.IndicatorStatus.PASSIVE)
            else:
                self._indicator.set_status(appindicator.STATUS_PASSIVE)
        else:
            self._statusIcon.set_visible(False)
        
    def _showHideToggled(self, menuitem):
        """Called when the show/hide menu item is toggled."""
        if self._selfToggling:
            self._selfToggling = False
        elif self._showHideMenuItem.get_active():
            self._gui.showMainWindow()
        else:
            self._gui.hideMainWindow()

    def _updateFlightStatus(self):
        """Update the flight status."""
        stage = "-" if self._stage is None else const.stage2string(self._stage)
        
        if self._noGoReason is None:
            rating = "%.0f%%" % (self._rating,)
        else:
            rating = self._noGoReason

        if appIndicator:
            self._stageMenuItem.set_label("Stage: %s" % (stage,))
            self._ratingMenuItem.set_label("Rating: %s" % (rating,))
        else:
            if self._noGoReason is not None:
                rating = '<span foreground="red">' + rating + '</span>'
            markup = "MAVA Logger X %s\n\nStage: %s\nRating: %s" %\
                     (const.VERSION, stage, rating)
            self._statusIcon.set_tooltip_markup(markup)
