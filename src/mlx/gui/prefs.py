# Module for the preferences dialog

#------------------------------------------------------------------------------

from common import *

from mlx.i18n import xstr
import mlx.const as const

import urlparse

#------------------------------------------------------------------------------

class Preferences(gtk.Dialog):
    """The preferences dialog."""
    def __init__(self, gui):
        """Construct the dialog."""
        super(Preferences, self).__init__(WINDOW_TITLE_BASE + " " +
                                          xstr("prefs_title"),
                                          gui.mainWindow,
                                          DIALOG_MODAL,
                                          (gtk.STOCK_CANCEL,
                                           RESPONSETYPE_REJECT,
                                           gtk.STOCK_OK,
                                           RESPONSETYPE_ACCEPT))
        self._gui = gui

        contentArea = self.get_content_area()

        notebook = gtk.Notebook()
        contentArea.pack_start(notebook, True, True, 4)

        general = self._buildGeneral()
        label = gtk.Label(xstr("prefs_tab_general"))
        label.set_use_underline(True)
        label.set_tooltip_text(xstr("prefs_tab_general_tooltip"))
        notebook.append_page(general, label)

        advanced = self._buildAdvanced()
        label = gtk.Label(xstr("prefs_tab_advanced"))
        label.set_use_underline(True)
        label.set_tooltip_text(xstr("prefs_tab_advanced_tooltip"))
        notebook.append_page(advanced, label)

    def run(self, config):
        """Run the preferences dialog.

        The dialog will be set up from data in the given configuration. If the
        changes are accepted by the user, the configuration is updated and saved."""
        self._fromConfig(config)

        self.show_all()
        response = super(Preferences, self).run()
        self.hide()

        if response==RESPONSETYPE_ACCEPT:
            self._toConfig(config)
            config.save()

    def _fromConfig(self, config):
        """Setup the dialog from the given configuration."""
        self._setLanguage(config.language)

        self._togglingAutoUpdate = True
        self._autoUpdate.set_active(config.autoUpdate)
        self._togglingAutoUpdate = False
        if not config.autoUpdate:
            self._warnedAutoUpdate = True

        self._updateURL.set_text(config.updateURL)

    def _toConfig(self, config):
        """Setup the given config from the settings in the dialog."""
        config.language = self._getLanguage()
        config.autoUpdate = self._autoUpdate.get_active()
        config.updateURL = self._updateURL.get_text()

    def _buildGeneral(self):
        """Build the page for the general settings."""
        mainAlignment = gtk.Alignment(xalign = 0.0, yalign = 0.0,
                                      xscale = 0.0, yscale = 0.0)
        mainAlignment.set_padding(padding_top = 16, padding_bottom = 32,
                                  padding_left = 4, padding_right = 48)
        mainBox = gtk.VBox()
        mainAlignment.add(mainBox)

        languageBox = gtk.HBox()
        mainBox.pack_start(languageBox, False, False, 4)

        label = gtk.Label(xstr("prefs_language"))
        label.set_use_underline(True)

        languageBox.pack_start(label, False, False, 4)

        self._languageList = gtk.ListStore(str, str)
        for language in const.languages:
            self._languageList.append([xstr("prefs_lang_" + language),
                                       language])

        self._languageComboBox = languageComboBox = \
            gtk.ComboBox(model = self._languageList)                   
        cell = gtk.CellRendererText()
        languageComboBox.pack_start(cell, True)
        languageComboBox.add_attribute(cell, 'text', 0)
        languageComboBox.set_tooltip_text(xstr("prefs_language_tooltip"))
        languageComboBox.connect("changed", self._languageChanged)
        languageBox.pack_start(languageComboBox, False, False, 4)

        self._changingLanguage = False
        self._warnedRestartNeeded = False

        label.set_mnemonic_widget(languageComboBox)
                                       
        return mainAlignment

    def _setLanguage(self, language):
        """Set the language to the given one."""
        iter = self._languageList.get_iter_first()
        while iter is not None:
            (lang,) = self._languageList.get(iter, 1)
            if (not language and lang=="$system") or \
               lang==language:
                self._changingLanguage = True
                self._languageComboBox.set_active_iter(iter)
                self._changingLanguage = False
                break
            else:
                iter = self._languageList.iter_next(iter)

    def _getLanguage(self):
        """Get the language selected by the user."""        
        iter = self._languageComboBox.get_active_iter()
        (lang,) = self._languageList.get(iter, 1)
        return "" if lang=="$system" else lang

    def _languageChanged(self, comboBox):
        """Called when the language has changed."""
        if not self._changingLanguage and not self._warnedRestartNeeded:
            dialog = gtk.MessageDialog(parent = self,
                                       type = MESSAGETYPE_INFO,
                                       buttons = BUTTONSTYPE_OK,
                                       message_format = xstr("prefs_restart"))
            dialog.set_title(self.get_title())
            dialog.format_secondary_markup(xstr("prefs_language_restart_sec"))
            dialog.run()
            dialog.hide()
            self._warnedRestartNeeded = True

    def _buildAdvanced(self):
        """Build the page for the advanced settings."""

        mainAlignment = gtk.Alignment(xalign = 0.0, yalign = 0.0,
                                      xscale = 0.0, yscale = 0.0)
        mainAlignment.set_padding(padding_top = 16, padding_bottom = 32,
                                  padding_left = 4, padding_right = 48)
        mainBox = gtk.VBox()
        mainAlignment.add(mainBox)

        self._autoUpdate = gtk.CheckButton(xstr("prefs_update_auto"))
        mainBox.pack_start(self._autoUpdate, False, False, 4)

        self._autoUpdate.set_use_underline(True)
        self._autoUpdate.connect("toggled", self._autoUpdateToggled)
        self._autoUpdate.set_tooltip_text(xstr("prefs_update_auto_tooltip"))
        self._warnedAutoUpdate = False
        self._togglingAutoUpdate = False
        
        updateURLBox = gtk.HBox()
        mainBox.pack_start(updateURLBox, False, False, 4)
        label = gtk.Label(xstr("prefs_update_url"))
        label.set_use_underline(True)
        updateURLBox.pack_start(label, False, False, 4)

        self._updateURL = gtk.Entry()
        label.set_mnemonic_widget(self._updateURL)
        self._updateURL.set_width_chars(40)
        self._updateURL.set_tooltip_text(xstr("prefs_update_url_tooltip"))
        self._updateURL.connect("changed", self._updateURLChanged)
        updateURLBox.pack_start(self._updateURL, False, False, 4)

        return mainAlignment

    def _setOKButtonSensitivity(self):
        """Set the sensitive state of the OK button."""
        sensitive = False
        try:
            result = urlparse.urlparse(self._updateURL.get_text())
            sensitive = result.scheme!="" and (result.netloc + result.path)!=""
        except:
            pass

        okButton = self.get_widget_for_response(RESPONSETYPE_ACCEPT)
        okButton.set_sensitive(sensitive)

    def _autoUpdateToggled(self, button):
        """Called when the auto update check button is toggled."""
        if not self._togglingAutoUpdate and not self._warnedAutoUpdate and \
           not self._autoUpdate.get_active():
            dialog = gtk.MessageDialog(parent = self,
                                       type = MESSAGETYPE_INFO,
                                       buttons = BUTTONSTYPE_OK,
                                       message_format = xstr("prefs_update_auto_warning"))
            dialog.set_title(self.get_title())
            dialog.run()
            dialog.hide()
            self._warnedAutoUpdate = True
            
    def _updateURLChanged(self, entry):
        """Called when the update URL is changed."""
        self._setOKButtonSensitivity()
        
            
