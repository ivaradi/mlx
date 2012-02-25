# Implementation of the status icon

#-------------------------------------------------------------------------------

from common import *

import mlx.const as const

#-------------------------------------------------------------------------------

class StatusIcon(object):
    """The class handling the status icon."""
    def __init__(self, iconDirectory, gui):
        """Construct the status icon."""
        self._gui = gui

        self._stage = None
        self._rating = 100
        self._noGoReason = None
        
        menu = gtk.Menu()

        if appIndicator:
            self._stageMenuItem = gtk.MenuItem()
            self._stageMenuItem.set_label("Stage: -")
            self._stageMenuItem.show()
            menu.append(self._stageMenuItem)

            self._ratingMenuItem = gtk.MenuItem()
            self._ratingMenuItem.set_label("Rating: 100%")
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
            self._setTooltip()

    def mainWindowHidden(self):
        """Called when the main window is hidden."""
        self._showHideMenuItem.set_active(False)

    def mainWindowShown(self):
        """Called when the main window is shown."""
        self._showHideMenuItem.set_active(True)

    def resetFlightStatus(self):
        """Reset the status of the flight."""
        if not appIndicator:
            self._statusIcon.set_blinking(False)
        self._noGoReason = None
        self.setStage(None)
        self.setRating(100)
        
    def setStage(self, stage):
        """Set the stage of the flight."""
        self._stage = stage
        if appIndicator:
            label = "Stage: %s" % ("-" if self._stage is None \
                                   else (const.stage2string(stage),))
            self._stageMenuItem.set_label(label)
        else:
            self._setTooltip()

    def setRating(self, rating):
        """Set the rating to the given value."""
        if rating==self._rating:
            return
        self._rating = rating

        if appIndicator:
            if self._noGoReason is None:
                self._ratingMenuItem.set_label("Rating: %.0f%%" % (rating,))
            else:
                self._setTooltip()

    def setNoGo(self, reason):
        """Set a No-Go condition with the given reason."""
        if self._noGoReason is not None:
            return

        self._noGoReason = reason
        if appIndicator:
            self._ratingMenuItem.set_label("Rating: %s" % (reason,))
        else:
            self._setTooltip()
            self._statusIcon.set_blinking(True)

    def _showHideToggled(self, menuitem):
        """Called when the show/hide menu item is toggled."""
        if self._showHideMenuItem.get_active():
            self._gui.showMainWindow()
        else:
            self._gui.hideMainWindow()

    def _setTooltip(self):
        """Set the tooltip of the status icon."""
        if self._noGoReason is None:
            rating = "%.0f%%" % (self._rating,)
        else:
            rating = '<span foreground="red">' + self._noGoReason + '</span>'

        markup = "MAVA Logger X %s\n\nStage: %s\nRating: %s" %\
                 (const.VERSION, ("-" if self._stage is None else
                                  const.stage2string(self._stage)),
                  rating)
        
        self._statusIcon.set_tooltip_markup(markup)
        
