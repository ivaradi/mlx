
from common import *

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

class BugReportDialog(gtk.Dialog):
    """The dialog to report a bug."""
    def __init__(self, gui):
        super(BugReportDialog, self).__init__(WINDOW_TITLE_BASE + " - " +
                                              xstr("bugreport_title"),
                                              gui.mainWindow,
                                              DIALOG_MODAL)

        self.add_button(xstr("button_cancel"), RESPONSETYPE_REJECT)
        self._sendButton = self.add_button(xstr("button_send"), RESPONSETYPE_ACCEPT)
        self._sendButton.set_can_default(True)
        self._gui = gui

        contentArea = self.get_content_area()

        contentAlignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                         xscale = 0.0, yscale = 0.0)
        contentAlignment.set_padding(padding_top = 4, padding_bottom = 16,
                                     padding_left = 8, padding_right = 8)

        contentArea.pack_start(contentAlignment, False, False, 0)

        contentVBox = gtk.VBox()
        contentAlignment.add(contentVBox)

        label = gtk.Label(xstr("bugreport_summary"))
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)

        contentVBox.pack_start(label, False, False, 4)

        self._summary = summary = gtk.Entry()
        summary.connect("changed", self._summaryChanged)
        summary.set_tooltip_text(xstr("bugreport_summary_tooltip"))
        summary.set_width_chars(80)
        label.set_mnemonic_widget(summary)
        contentVBox.pack_start(summary, True, True, 4)

        label = gtk.Label(xstr("bugreport_description"))
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)

        contentVBox.pack_start(label, False, False, 4)

        self._description = description = gtk.TextView()
        description.set_tooltip_text(xstr("bugreport_description_tooltip"))
        label.set_mnemonic_widget(description)

        scrolledWindow = gtk.ScrolledWindow()
        scrolledWindow.add(description)
        scrolledWindow.set_size_request(-1, 200)
        scrolledWindow.set_policy(POLICY_AUTOMATIC, POLICY_AUTOMATIC)
        scrolledWindow.set_shadow_type(SHADOW_IN)

        alignment = gtk.Alignment(xalign = 0.5, yalign = 0.0, xscale = 1.0, yscale = 1.0)
        alignment.add(scrolledWindow)

        contentVBox.pack_start(alignment, True, True, 4)

        emailBox = gtk.HBox()
        contentVBox.pack_start(emailBox, False, False, 4)

        label = gtk.Label(xstr("bugreport_email"))
        label.set_use_underline(True)
        label.set_alignment(0.0, 0.5)

        emailBox.pack_start(label, False, False, 0)

        alignment = gtk.Alignment()
        emailBox.pack_start(alignment, False, False, 8)

        self._email = email = gtk.Entry()
        email.set_tooltip_text(xstr("bugreport_email_tooltip"))
        label.set_mnemonic_widget(email)
        emailBox.pack_start(email, True, True, 0)


    def run(self):
        """Run the checklist editor dialog."""
        self.set_sensitive(True)
        self._description.set_sensitive(True)
        self._updateButtons()
        self._sendButton.grab_default()
        self.show_all()
        response = super(BugReportDialog, self).run()

        print "response", response, RESPONSETYPE_ACCEPT
        if response==RESPONSETYPE_ACCEPT:
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
        description = text2unicode(description)
        self.set_sensitive(False)
        self._gui.sendBugReport(text2unicode(self._summary.get_text()),
                                description,
                                text2unicode(self._email.get_text()),
                                self._bugReportSent)

    def _bugReportSent(self, returned, result):
        """Called when the bug report was sent."""
        self.set_sensitive(True)
        self._description.set_sensitive(True)
        if returned and result.success:
            self.hide()
            self._summary.set_text("")
            self._description.get_buffer().set_text("")
            self._email.set_text("")
        else:
            self.run()
