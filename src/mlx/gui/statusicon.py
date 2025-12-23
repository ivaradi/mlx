
from .common import *

import mlx.const as const
from mlx.i18n import xstr

#-------------------------------------------------------------------------------

## @package mlx.gui.statusicon
#
# The status icon.
#
# This module implements that status icon displayed on the Windows or the GNOME
# taskbar, or whatever the place for status icons is called in the used
# environment. It works with both the more modern appindicator interface
# (mainly found on Ubuntu), if that is available, or with the older status icon
# support in Gtk (which is used on Windows as well). In this latter case, the
# icon has a tooltip with the flight stage and rating information, while these
# data are placed into the menu in case of appindicator.

#-------------------------------------------------------------------------------

class StatusIcon(FlightStatusHandler):
    """The class handling the status icon."""
    def __init__(self, iconDirectory, gui):
        """Construct the status icon."""
        super(StatusIcon, self).__init__()

        self._gui = gui
        self._selfToggling = False

        self._menu = menu = Gtk.Menu()

        if appIndicator:
            self._stageMenuItem = Gtk.MenuItem("-")
            self._stageMenuItem.show()
            menu.append(self._stageMenuItem)

            self._ratingMenuItem = Gtk.MenuItem("-")
            self._ratingMenuItem.show()
            menu.append(self._ratingMenuItem)

            separator = Gtk.SeparatorMenuItem()
            separator.show()
            menu.append(separator)

        self._showHideMenuItem = Gtk.CheckMenuItem()
        self._showHideMenuItem.set_label(xstr("statusicon_showmain"))
        self._showHideMenuItem.set_active(True)
        self._showHideMenuItem.connect("toggled", self._showHideToggled)
        self._showHideMenuItem.show()
        menu.append(self._showHideMenuItem)

        self._showMonitorMenuItem = Gtk.CheckMenuItem()
        self._showMonitorMenuItem.set_label(xstr("statusicon_showmonitor"))
        self._showMonitorMenuItem.set_active(False)
        self._showMonitorMenuItem.connect("toggled", self._showMonitorToggled)
        self._showMonitorMenuItem.show()
        menu.append(self._showMonitorMenuItem)

        separator = Gtk.SeparatorMenuItem()
        separator.show()
        menu.append(separator)

        self._quitMenuItem = Gtk.MenuItem()
        self._quitMenuItem.set_label(xstr("statusicon_quit"))
        self._quitMenuItem.show()
        self._quitMenuItem.connect("activate", self._gui._quit)
        menu.append(self._quitMenuItem)

        menu.show()

        iconFile = os.path.join(iconDirectory, "logo.ico")

        if appIndicator:
            indicator = AppIndicator3.Indicator.new ("mava-logger-x", iconFile,
                                                     AppIndicator3.IndicatorCategory.APPLICATION_STATUS)
            indicator.set_status (AppIndicator3.IndicatorStatus.ACTIVE)

            indicator.set_menu(menu)
            self._indicator = indicator
        else:
            def popup_menu(status, button, time):
                def focus_out(window, event):
                    window.destroy()
                    return False

                # Seemingly known trick on Windows to make the menu
                # disappear when a mouse click occurs outside the menu
                hidden = Gtk.Window()
                hidden.set_resizable(False)
                hidden.set_decorated(False)
                hidden.set_skip_taskbar_hint(True)
                hidden.set_skip_pager_hint(True)
                hidden.set_size_request(0, 0)
                hidden.set_transient_for(None)
                hidden.connect("focus-out-event", focus_out)
                hidden.show()

                menu.popup(None, None, None, None,
                           button, time)

            def notify(object, pspec):
                print("notify", object, pspec)

            def focus(menu, event):
                print("focus", event)

            statusIcon = Gtk.StatusIcon()
            statusIcon.set_from_file(iconFile)
            statusIcon.set_visible(True)
            statusIcon.connect('popup-menu', popup_menu)
            statusIcon.connect('notify', notify)
            statusIcon.connect('activate',
                               lambda status: self._gui.toggleMainWindow())
            self._statusIcon = statusIcon

            menu.connect("focus_out_event", focus)

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

    def monitorWindowHidden(self):
        """Called when the monitor window is hidden."""
        if self._showMonitorMenuItem.get_active():
            self._selfToggling = True
            self._showMonitorMenuItem.set_active(False)

    def monitorWindowShown(self):
        """Called when the monitor window is shown."""
        if not self._showMonitorMenuItem.get_active():
            self._selfToggling = True
            self._showMonitorMenuItem.set_active(True)

    def destroy(self):
        """Hide and destroy the status icon."""
        if appIndicator:
            self._indicator.set_status(AppIndicator3.IndicatorStatus.PASSIVE)
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

    def _showMonitorToggled(self, menuitem):
        """Called when the show/hide monitor window menu item is toggled."""
        if self._selfToggling:
            self._selfToggling = False
        elif self._showMonitorMenuItem.get_active():
            self._gui.showMonitorWindow()
        else:
            self._gui.hideMonitorWindow()

    def _updateFlightStatus(self):
        """Update the flight status."""
        stage = "-" if self._stage is None \
                else xstr("flight_stage_" + const.stage2string(self._stage))

        if self._noGoReason is None:
            rating = "%.1f%%" % (self._rating,)
        else:
            rating = self._noGoReason

        if appIndicator:
            self._stageMenuItem.set_label("%s: %s" % \
                                          (xstr("statusicon_stage"),
                                           stage))
            self._ratingMenuItem.set_label("%s: %s" % \
                                           (xstr("statusicon_rating"),
                                            rating))
        else:
            if self._noGoReason is not None:
                rating = '<span foreground="red">' + rating + '</span>'
            markup = "MAVA Logger X %s\n\n%s: %s\n%s: %s" %\
                     (const.VERSION, xstr("statusicon_stage"), stage,
                      xstr("statusicon_rating"), rating)
            self._statusIcon.set_tooltip_markup(markup)
