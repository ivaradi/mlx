# Module for the preferences dialog

#------------------------------------------------------------------------------

from common import *

from mlx.i18n import xstr
import mlx.const as const
import mlx.config as config

import urlparse

#------------------------------------------------------------------------------

class Hotkey(gtk.HBox):
    """A widget to handle a hotkey."""
    def __init__(self, labelText, tooltips):
        """Construct the hotkey widget.

        labelText is the text for the label before the hotkey.

        The tooltips parameter is an array of the tooltips for:
        - the hotkey combo box,
        - the control check box, and
        - the shift check box."""
        super(Hotkey, self).__init__()
        
        label = gtk.Label(labelText)
        label.set_use_underline(True)
        labelAlignment = gtk.Alignment(xalign = 0.0, yalign = 0.5,
                                       xscale = 0.0, yscale = 0.0)
        labelAlignment.add(label)
        self.pack_start(labelAlignment, False, False, 8)

        self._ctrl = gtk.CheckButton("Ctrl")
        self._ctrl.set_tooltip_text(tooltips[1])
        self.pack_start(self._ctrl, False, False, 4)
            
        self._shift = gtk.CheckButton("Shift")
        self._shift.set_tooltip_text(tooltips[2])
        self.pack_start(self._shift, False, False, 4)

        self._hotkeyModel = gtk.ListStore(str)
        for keyCode in range(ord("0"), ord("9")) + range(ord("A"), ord("Z")):
            self._hotkeyModel.append([chr(keyCode)])

        self._hotkey = gtk.ComboBox(model = self._hotkeyModel)
        cell = gtk.CellRendererText()
        self._hotkey.pack_start(cell, True)
        self._hotkey.add_attribute(cell, 'text', 0)
        self._hotkey.set_tooltip_text(tooltips[0])
        self.pack_start(self._hotkey, False, False, 4)

        self._setting = False

    def set(self, hotkey):
        """Set the hotkey widget from the given hotkey."""
        self._setting = True

        self._ctrl.set_active(hotkey.ctrl)
        self._shift.set_active(hotkey.shift)

        hotkeyModel = self._hotkeyModel
        iter = hotkeyModel.get_iter_first()
        while iter is not None and \
              hotkeyModel.get_value(iter, 0)!=hotkey.key:
            iter = hotkeyModel.iter_next(iter)

        if iter is None:
            iter = hotkeyModel.get_iter_first()

        self._hotkey.set_active_iter(iter)            
        
        self._setting = False

    def get(self):
        """Get a hotkey corresponding to the settings in the widghet."""

        key = self._hotkeyModel.get_value(self._hotkey.get_active_iter(), 0)

        return config.Hotkey(ctrl = self._ctrl.get_active(),
                             shift = self._shift.get_active(),
                             key = key)

#------------------------------------------------------------------------------

class Preferences(gtk.Dialog):
    """The preferences dialog."""
    def __init__(self, gui):
        """Construct the dialog."""
        super(Preferences, self).__init__(WINDOW_TITLE_BASE + " " +
                                          xstr("prefs_title"),
                                          gui.mainWindow,
                                          DIALOG_MODAL)

        self.add_button(xstr("button_cancel"), RESPONSETYPE_REJECT)
        self.add_button(xstr("button_ok"), RESPONSETYPE_ACCEPT)
        
        self._gui = gui
        self._settingFromConfig = False

        contentArea = self.get_content_area()

        notebook = gtk.Notebook()
        contentArea.pack_start(notebook, True, True, 4)

        general = self._buildGeneral()
        label = gtk.Label(xstr("prefs_tab_general"))
        label.set_use_underline(True)
        label.set_tooltip_text(xstr("prefs_tab_general_tooltip"))
        notebook.append_page(general, label)

        messages = self._buildMessages()
        label = gtk.Label(xstr("prefs_tab_messages"))
        label.set_use_underline(True)
        label.set_tooltip_text(xstr("prefs_tab_message_tooltip"))
        notebook.append_page(messages, label)

        sounds = self._buildSounds()
        label = gtk.Label(xstr("prefs_tab_sounds"))
        label.set_use_underline(True)
        label.set_tooltip_text(xstr("prefs_tab_sounds_tooltip"))
        notebook.append_page(sounds, label)

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
        self._settingFromConfig = True

        self._setLanguage(config.language)
        self._hideMinimizedWindow.set_active(config.hideMinimizedWindow)
        self._onlineGateSystem.set_active(config.onlineGateSystem)
        self._onlineACARS.set_active(config.onlineACARS)
        self._flareTimeFromFS.set_active(config.flareTimeFromFS)
        self._syncFSTime.set_active(config.syncFSTime)

        pirepDirectory = config.pirepDirectory
        self._pirepDirectory.set_text("" if pirepDirectory is None
                                      else pirepDirectory)

        for messageType in const.messageTypes:
            level = config.getMessageTypeLevel(messageType)
            button = self._msgFSCheckButtons[messageType]
            button.set_active(level == const.MESSAGELEVEL_FS or
                              level == const.MESSAGELEVEL_BOTH)
            button = self._msgSoundCheckButtons[messageType]
            button.set_active(level == const.MESSAGELEVEL_SOUND or
                              level == const.MESSAGELEVEL_BOTH)

        self._enableSounds.set_active(config.enableSounds)
        self._pilotControlsSounds.set_active(config.pilotControlsSounds)
        self._pilotHotkey.set(config.pilotHotkey)
        #self._approachCallOuts.set_active(config.approachCallOuts)
        self._speedbrakeAtTD.set_active(config.speedbrakeAtTD)

        self._enableChecklists.set_active(config.enableChecklists)        
        self._checklistHotkey.set(config.checklistHotkey)

        self._autoUpdate.set_active(config.autoUpdate)
        if not config.autoUpdate:
            self._warnedAutoUpdate = True

        self._updateURL.set_text(config.updateURL)

        self._settingFromConfig = False

    def _toConfig(self, config):
        """Setup the given config from the settings in the dialog."""
        config.language = self._getLanguage()
        config.hideMinimizedWindow = self._hideMinimizedWindow.get_active()
        config.onlineGateSystem = self._onlineGateSystem.get_active()
        config.onlineACARS = self._onlineACARS.get_active()
        config.flareTimeFromFS = self._flareTimeFromFS.get_active()
        config.syncFSTime = self._syncFSTime.get_active()
        config.pirepDirectory = text2unicode(self._pirepDirectory.get_text())

        for messageType in const.messageTypes:
            fsButtonActive = self._msgFSCheckButtons[messageType].get_active()
            soundButtonActive = self._msgSoundCheckButtons[messageType].get_active()
            if fsButtonActive:
                level = const.MESSAGELEVEL_BOTH if soundButtonActive \
                        else const.MESSAGELEVEL_FS
            elif soundButtonActive:
                level = const.MESSAGELEVEL_SOUND
            else:
                level = const.MESSAGELEVEL_NONE
            config.setMessageTypeLevel(messageType, level)

        config.enableSounds = self._enableSounds.get_active()
        config.pilotControlsSounds = self._pilotControlsSounds.get_active()
        config.pilotHotkey = self._pilotHotkey.get()
        #config.approachCallOuts = self._approachCallOuts.get_active()
        config.speedbrakeAtTD = self._speedbrakeAtTD.get_active()

        config.enableChecklists = self._enableChecklists.get_active()
        config.checklistHotkey = self._checklistHotkey.get()

        config.autoUpdate = self._autoUpdate.get_active()
        config.updateURL = self._updateURL.get_text()

    def _buildGeneral(self):
        """Build the page for the general settings."""
        mainAlignment = gtk.Alignment(xalign = 0.0, yalign = 0.0,
                                      xscale = 1.0, yscale = 0.0)
        mainAlignment.set_padding(padding_top = 16, padding_bottom = 8,
                                  padding_left = 4, padding_right = 4)
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

        label.set_mnemonic_widget(languageComboBox)

        self._changingLanguage = False
        self._warnedRestartNeeded = False

        self._hideMinimizedWindow = gtk.CheckButton(xstr("prefs_hideMinimizedWindow"))
        self._hideMinimizedWindow.set_use_underline(True)
        self._hideMinimizedWindow.set_tooltip_text(xstr("prefs_hideMinimizedWindow_tooltip"))
        mainBox.pack_start(self._hideMinimizedWindow, False, False, 4)

        self._onlineGateSystem = gtk.CheckButton(xstr("prefs_onlineGateSystem"))
        self._onlineGateSystem.set_use_underline(True)
        self._onlineGateSystem.set_tooltip_text(xstr("prefs_onlineGateSystem_tooltip"))
        mainBox.pack_start(self._onlineGateSystem, False, False, 4)

        self._onlineACARS = gtk.CheckButton(xstr("prefs_onlineACARS"))
        self._onlineACARS.set_use_underline(True)
        self._onlineACARS.set_tooltip_text(xstr("prefs_onlineACARS_tooltip"))
        mainBox.pack_start(self._onlineACARS, False, False, 4)

        self._flareTimeFromFS = gtk.CheckButton(xstr("prefs_flaretimeFromFS"))
        self._flareTimeFromFS.set_use_underline(True)
        self._flareTimeFromFS.set_tooltip_text(xstr("prefs_flaretimeFromFS_tooltip"))
        mainBox.pack_start(self._flareTimeFromFS, False, False, 4)
                                       
        self._syncFSTime = gtk.CheckButton(xstr("prefs_syncFSTime"))
        self._syncFSTime.set_use_underline(True)
        self._syncFSTime.set_tooltip_text(xstr("prefs_syncFSTime_tooltip"))
        mainBox.pack_start(self._syncFSTime, False, False, 4)

        pirepBox = gtk.HBox()
        mainBox.pack_start(pirepBox, False, False, 4)

        label = gtk.Label(xstr("prefs_pirepDirectory"))
        label.set_use_underline(True)
        pirepBox.pack_start(label, False, False, 4)

        self._pirepDirectory = gtk.Entry()
        self._pirepDirectory.set_tooltip_text(xstr("prefs_pirepDirectory_tooltip"))
        label.set_mnemonic_widget(self._pirepDirectory)
        pirepBox.pack_start(self._pirepDirectory, True, True, 4)

        self._pirepDirectoryButton = gtk.Button(xstr("button_browse"))
        self._pirepDirectoryButton.connect("clicked",
                                           self._pirepDirectoryButtonClicked)
        pirepBox.pack_start(self._pirepDirectoryButton, False, False, 4)
        
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
                                       message_format = xstr("prefs_restart"))
            dialog.add_button(xstr("button_ok"), RESPONSETYPE_OK)
            dialog.set_title(self.get_title())
            dialog.format_secondary_markup(xstr("prefs_language_restart_sec"))
            dialog.run()
            dialog.hide()
            self._warnedRestartNeeded = True
       
    def _pirepDirectoryButtonClicked(self, button):
        """Called when the PIREP directory button is clicked."""
        dialog = gtk.FileChooserDialog(title = WINDOW_TITLE_BASE + " - " +
                                       xstr("prefs_pirepDirectory_browser_title"),
                                       action = FILE_CHOOSER_ACTION_SELECT_FOLDER,
                                       buttons = (gtk.STOCK_CANCEL, RESPONSETYPE_CANCEL,
                                                  gtk.STOCK_OK, RESPONSETYPE_OK),
                                       parent = self)
        dialog.set_modal(True)
        dialog.set_transient_for(self)

        directory = self._pirepDirectory.get_text()
        if directory:
            dialog.select_filename(directory)
        
        result = dialog.run()
        dialog.hide()

        if result==RESPONSETYPE_OK:
            self._pirepDirectory.set_text(dialog.get_filename())
        
    def _buildMessages(self):
        """Build the page for the message settings."""

        mainAlignment = gtk.Alignment(xalign = 0.0, yalign = 0.0,
                                      xscale = 0.0, yscale = 0.0)
        mainAlignment.set_padding(padding_top = 16, padding_bottom = 8,
                                  padding_left = 4, padding_right = 4)
        mainBox = gtk.VBox()
        mainAlignment.add(mainBox)

        table = gtk.Table(len(const.messageTypes) + 1, 3)
        table.set_row_spacings(8)
        table.set_col_spacings(32)
        table.set_homogeneous(False)
        mainBox.pack_start(table, False, False, 4)
        
        label = gtk.Label(xstr("prefs_msgs_fs"))
        label.set_justify(JUSTIFY_CENTER)
        label.set_alignment(0.5, 1.0)
        table.attach(label, 1, 2, 0, 1)
        
        label = gtk.Label(xstr("prefs_msgs_sound"))
        label.set_justify(JUSTIFY_CENTER)
        label.set_alignment(0.5, 1.0)
        table.attach(label, 2, 3, 0, 1)

        self._msgFSCheckButtons = {}
        self._msgSoundCheckButtons = {}        
        row = 1
        for messageType in const.messageTypes:
            messageTypeStr = const.messageType2string(messageType)
            label = gtk.Label(xstr("prefs_msgs_type_" + messageTypeStr))
            label.set_justify(JUSTIFY_CENTER)
            label.set_use_underline(True)
            label.set_alignment(0.5, 0.5)
            table.attach(label, 0, 1, row, row+1)

            fsCheckButton = gtk.CheckButton()
            alignment = gtk.Alignment(xscale = 0.0, yscale = 0.0,
                                      xalign = 0.5, yalign = 0.5)
            alignment.add(fsCheckButton)
            table.attach(alignment, 1, 2, row, row+1)
            self._msgFSCheckButtons[messageType] = fsCheckButton
            
            soundCheckButton = gtk.CheckButton()
            alignment = gtk.Alignment(xscale = 0.0, yscale = 0.0,
                                      xalign = 0.5, yalign = 0.5)
            alignment.add(soundCheckButton)
            table.attach(alignment, 2, 3, row, row+1)            
            self._msgSoundCheckButtons[messageType] = soundCheckButton

            mnemonicWidget = gtk.Label("")
            table.attach(mnemonicWidget, 3, 4, row, row+1)
            label.set_mnemonic_widget(mnemonicWidget)
            mnemonicWidget.connect("mnemonic-activate",
                                   self._msgLabelActivated,
                                   messageType)

            row += 1

        return mainAlignment

    def _msgLabelActivated(self, button, cycle_group, messageType):
        """Called when the mnemonic of a label is activated.

        It cycles the corresponding options."""
        fsCheckButton = self._msgFSCheckButtons[messageType]
        soundCheckButton = self._msgSoundCheckButtons[messageType]

        num = 1 if fsCheckButton.get_active() else 0
        num += 2 if soundCheckButton.get_active() else 0
        num += 1

        fsCheckButton.set_active((num&0x01)==0x01)
        soundCheckButton.set_active((num&0x02)==0x02)

        return True

    def _buildSounds(self):
        """Build the page for the sounds."""
        mainAlignment = gtk.Alignment(xalign = 0.0, yalign = 0.0,
                                      xscale = 1.0, yscale = 1.0)
        mainAlignment.set_padding(padding_top = 8, padding_bottom = 8,
                                  padding_left = 4, padding_right = 4)

        mainBox = gtk.VBox()
        mainAlignment.add(mainBox)

        backgroundFrame = gtk.Frame(label = xstr("prefs_sounds_frame_bg"))
        mainBox.pack_start(backgroundFrame, False, False, 4)

        backgroundAlignment = gtk.Alignment(xalign = 0.0, yalign = 0.0,
                                            xscale = 1.0, yscale = 0.0)
        backgroundAlignment.set_padding(padding_top = 4, padding_bottom = 4,
                                        padding_left = 4, padding_right = 4)
        backgroundFrame.add(backgroundAlignment)

        backgroundBox = gtk.VBox()
        backgroundAlignment.add(backgroundBox)

        self._enableSounds = gtk.CheckButton(xstr("prefs_sounds_enable"))
        self._enableSounds.set_use_underline(True)
        self._enableSounds.set_tooltip_text(xstr("prefs_sounds_enable_tooltip"))
        self._enableSounds.connect("toggled", self._enableSoundsToggled)
        alignment = gtk.Alignment(xalign = 0.0, yalign = 0.5,
                                  xscale = 1.0, yscale = 0.0)
        alignment.add(self._enableSounds)
        backgroundBox.pack_start(alignment, False, False, 4)

        self._pilotControlsSounds = gtk.CheckButton(xstr("prefs_sounds_pilotControls"))
        self._pilotControlsSounds.set_use_underline(True)
        self._pilotControlsSounds.set_tooltip_text(xstr("prefs_sounds_pilotControls_tooltip"))
        backgroundBox.pack_start(self._pilotControlsSounds, False, False, 4)

        self._pilotHotkey = Hotkey(xstr("prefs_sounds_pilotHotkey"),
                                   [xstr("prefs_sounds_pilotHotkey_tooltip"),
                                    xstr("prefs_sounds_pilotHotkeyCtrl_tooltip"),
                                    xstr("prefs_sounds_pilotHotkeyShift_tooltip")])
        
        backgroundBox.pack_start(self._pilotHotkey, False, False, 4)

        # self._approachCallOuts = gtk.CheckButton(xstr("prefs_sounds_approachCallOuts"))
        # self._approachCallOuts.set_use_underline(True)
        # self._approachCallOuts.set_tooltip_text(xstr("prefs_sounds_approachCallOuts_tooltip"))
        # backgroundBox.pack_start(self._approachCallOuts, False, False, 4)
        
        self._speedbrakeAtTD = gtk.CheckButton(xstr("prefs_sounds_speedbrakeAtTD"))
        self._speedbrakeAtTD.set_use_underline(True)
        self._speedbrakeAtTD.set_tooltip_text(xstr("prefs_sounds_speedbrakeAtTD_tooltip"))
        backgroundBox.pack_start(self._speedbrakeAtTD, False, False, 4)

        checklistFrame = gtk.Frame(label = xstr("prefs_sounds_frame_checklists"))
        mainBox.pack_start(checklistFrame, False, False, 4)

        checklistAlignment = gtk.Alignment(xalign = 0.0, yalign = 0.0,
                                           xscale = 1.0, yscale = 0.0)
        checklistAlignment.set_padding(padding_top = 4, padding_bottom = 4,
                                       padding_left = 4, padding_right = 4)
        checklistFrame.add(checklistAlignment)

        checklistBox = gtk.VBox()
        checklistAlignment.add(checklistBox)
        
        self._enableChecklists = gtk.CheckButton(xstr("prefs_sounds_enableChecklists"))
        self._enableChecklists.set_use_underline(True)
        self._enableChecklists.set_tooltip_text(xstr("prefs_sounds_enableChecklists_tooltip"))
        self._enableChecklists.connect("toggled", self._enableChecklistsToggled)
        checklistBox.pack_start(self._enableChecklists, False, False, 4)

        self._checklistHotkey = Hotkey(xstr("prefs_sounds_checklistHotkey"),
                                       [xstr("prefs_sounds_checklistHotkey_tooltip"),
                                        xstr("prefs_sounds_checklistHotkeyCtrl_tooltip"),
                                        xstr("prefs_sounds_checklistHotkeyShift_tooltip")])

        checklistBox.pack_start(self._checklistHotkey, False, False, 4)

        self._enableSoundsToggled(self._enableSounds)
        self._enableChecklistsToggled(self._enableChecklists)

        return mainAlignment

    def _enableSoundsToggled(self, button):
        """Called when the enable sounds button is toggled."""
        active = button.get_active()
        self._pilotControlsSounds.set_sensitive(active)
        self._pilotHotkey.set_sensitive(active)
        #self._approachCallOuts.set_sensitive(active)
        self._speedbrakeAtTD.set_sensitive(active)

    def _enableChecklistsToggled(self, button):
        """Called when the enable checklists button is toggled."""
        active = button.get_active()
        self._checklistHotkey.set_sensitive(active)

    def _buildAdvanced(self):
        """Build the page for the advanced settings."""

        mainAlignment = gtk.Alignment(xalign = 0.0, yalign = 0.0,
                                      xscale = 1.0, yscale = 0.0)
        mainAlignment.set_padding(padding_top = 16, padding_bottom = 8,
                                  padding_left = 4, padding_right = 4)
        mainBox = gtk.VBox()
        mainAlignment.add(mainBox)

        self._autoUpdate = gtk.CheckButton(xstr("prefs_update_auto"))
        mainBox.pack_start(self._autoUpdate, False, False, 4)

        self._autoUpdate.set_use_underline(True)
        self._autoUpdate.connect("toggled", self._autoUpdateToggled)
        self._autoUpdate.set_tooltip_text(xstr("prefs_update_auto_tooltip"))
        self._warnedAutoUpdate = False
        
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
        updateURLBox.pack_start(self._updateURL, True, True, 4)

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
        if not self._settingFromConfig and not self._warnedAutoUpdate and \
           not self._autoUpdate.get_active():
            dialog = gtk.MessageDialog(parent = self,
                                       type = MESSAGETYPE_INFO,
                                       message_format = xstr("prefs_update_auto_warning"))
            dialog.add_button(xstr("button_ok"), RESPONSETYPE_OK)
            dialog.set_title(self.get_title())
            dialog.run()
            dialog.hide()
            self._warnedAutoUpdate = True
            
    def _updateURLChanged(self, entry):
        """Called when the update URL is changed."""
        self._setOKButtonSensitivity()
