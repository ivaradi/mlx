
from .common import *

from mlx.i18n import xstr
import mlx.const as const
import mlx.config as config

import os

#------------------------------------------------------------------------------

## @package mlx.gui.bugreport
#
# The bug report dialog
#
# This module implements the bug report dialog.

#------------------------------------------------------------------------------

class BugReportDialog(Gtk.Dialog):
    """The dialog to report a bug."""
    def __init__(self, gui):
        super(BugReportDialog, self).__init__(WINDOW_TITLE_BASE + " - " +
                                              xstr("bugreport_title"),
                                              gui.mainWindow,
                                              Gtk.DialogFlags.MODAL)

        self.add_button(xstr("button_cancel"), Gtk.ResponseType.REJECT)
        self._sendButton = self.add_button(xstr("button_send"), Gtk.ResponseType.ACCEPT)
        self._sendButton.set_can_default(True)
        self._gui = gui

        contentArea = self.get_content_area()

        contentAlignment = Gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                         xscale = 0.0, yscale = 0.0)
        contentAlignment.set_padding(padding_top = 4, padding_bottom = 16,
                                     padding_left = 8, padding_right = 8)

        contentArea.pack_start(contentAlignment, False, False, 0)

        contentVBox = Gtk.VBox()
        contentAlignment.add(contentVBox)

        label = Gtk.Label(xstr("bugreport_summary"))
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)

        contentVBox.pack_start(label, False, False, 4)

        self._summary = summary = Gtk.Entry()
        summary.connect("changed", self._summaryChanged)
        summary.set_tooltip_text(xstr("bugreport_summary_tooltip"))
        summary.set_width_chars(80)
        label.set_mnemonic_widget(summary)
        contentVBox.pack_start(summary, True, True, 4)

        label = Gtk.Label(xstr("bugreport_description"))
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)

        contentVBox.pack_start(label, False, False, 4)

        self._description = description = Gtk.TextView()
        description.set_tooltip_text(xstr("bugreport_description_tooltip"))
        description.set_wrap_mode(Gtk.WrapMode.WORD)
        label.set_mnemonic_widget(description)

        scrolledWindow = Gtk.ScrolledWindow()
        scrolledWindow.add(description)
        scrolledWindow.set_size_request(-1, 200)
        scrolledWindow.set_policy(Gtk.PolicyType.AUTOMATIC,
                                  Gtk.PolicyType.AUTOMATIC)
        scrolledWindow.set_shadow_type(Gtk.ShadowType.IN)

        alignment = Gtk.Alignment(xalign = 0.5, yalign = 0.0, xscale = 1.0, yscale = 1.0)
        alignment.add(scrolledWindow)

        contentVBox.pack_start(alignment, True, True, 4)

        self._hasGitLabUser = hasGitLabUser = \
            Gtk.CheckButton(xstr("bugreport_has_gitlab"))
        hasGitLabUser.set_use_underline(True)
        hasGitLabUser.set_tooltip_text(xstr("bugreport_has_gitlab_tooltip"))

        contentVBox.pack_start(hasGitLabUser, False, False, 4)

    def run(self):
        """Run the checklist editor dialog."""
        self.set_sensitive(True)
        self._description.set_sensitive(True)
        self._hasGitLabUser.set_active(self._gui.config.gitlabRefreshToken)
        self._updateButtons()
        self._sendButton.grab_default()
        self.show_all()
        response = super(BugReportDialog, self).run()

        print("response", response, Gtk.ResponseType.ACCEPT)
        if response==Gtk.ResponseType.ACCEPT:
            self._send()
        else:
            self.hide()

    def _summaryChanged(self, entry):
        """Called when the summary has changed."""
        self._updateButtons()

    def _updateButtons(self):
        """Update the sensitivity of the buttoms."""
        self._sendButton.set_sensitive(self._summary.get_text()!="")

    def _send(self):
        """Send the bug report."""
        descriptionBuffer = self._description.get_buffer()
        description = \
          descriptionBuffer.get_text(descriptionBuffer.get_start_iter(),
                                     descriptionBuffer.get_end_iter(),
                                     False)
        self.set_sensitive(False)
        self._gui.sendBugReport(self._summary.get_text(),
                                description,
                                self._hasGitLabUser.get_active(),
                                self._bugReportSent)

    def _bugReportSent(self, returned, result):
        """Called when the bug report was sent."""
        self.set_sensitive(True)
        self._description.set_sensitive(True)
        if returned and result.success:
            self.hide()
            self._summary.set_text("")
            self._description.get_buffer().set_text("")
            self._gui.config.save()
        else:
            self.run()
