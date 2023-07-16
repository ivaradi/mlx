
from .common import *

from mlx.i18n import xstr
import mlx.const as const
import mlx.config as config

import urllib.parse

#------------------------------------------------------------------------------

## @package mlx.gui.prefs
#
# The preferences dialog.
#
# This module implements the preferences dialog, allowing the editing of the
# configuration of the program. The preferences are grouped into tabs, each
# containing the necessary controls to set the various options.

#------------------------------------------------------------------------------

class Hotkey(Gtk.HBox):
    """A widget to handle a hotkey."""

    # Constant to denote that the status of the Ctrl modifier is changed
    CHANGED_CTRL = 1

    # Constant to denote that the status of the Shift modifier is changed
    CHANGED_SHIFT = 2

    # Constant to denote that the value of the key is changed
    CHANGED_KEY = 3

    def __init__(self, labelText, tooltips):
        """Construct the hotkey widget.

        labelText is the text for the label before the hotkey.

        The tooltips parameter is an array of the tooltips for:
        - the hotkey combo box,
        - the control check box, and
        - the shift check box."""
        super(Hotkey, self).__init__()

        label = Gtk.Label(labelText)
        label.set_use_underline(True)
        labelAlignment = Gtk.Alignment(xalign = 0.0, yalign = 0.5,
                                       xscale = 0.0, yscale = 0.0)
        labelAlignment.set_padding(padding_top = 0, padding_bottom = 0,
                                   padding_left = 0, padding_right = 4)
        labelAlignment.add(label)
        self.pack_start(labelAlignment, False, False, 0)

        self._ctrl = Gtk.CheckButton("Ctrl")
        self._ctrl.set_tooltip_text(tooltips[1])
        self._ctrl.connect("toggled", self._ctrlToggled)
        self.pack_start(self._ctrl, False, False, 4)

        self._shift = Gtk.CheckButton("Shift")
        self._shift.set_tooltip_text(tooltips[2])
        self._shift.connect("toggled", self._shiftToggled)
        self.pack_start(self._shift, False, False, 4)

        self._hotkeyModel = Gtk.ListStore(str)
        for keyCode in list(range(ord("0"), ord("9")+1)) + list(range(ord("A"), ord("Z")+1)):
            self._hotkeyModel.append([chr(keyCode)])

        self._hotkey = Gtk.ComboBox(model = self._hotkeyModel)
        cell = Gtk.CellRendererText()
        self._hotkey.pack_start(cell, True)
        self._hotkey.add_attribute(cell, 'text', 0)
        self._hotkey.set_tooltip_text(tooltips[0])
        self._hotkey.connect("changed", self._keyChanged)
        self.pack_start(self._hotkey, False, False, 4)

        label.set_mnemonic_widget(self._hotkey)

        self._setting = False

    @property
    def ctrl(self):
        """Get whether the Ctrl modifier is selected."""
        return self._ctrl.get_active()

    @ctrl.setter
    def ctrl(self, ctrl):
        """Get whether the Ctrl modifier is selected."""
        self._setting = True
        self._ctrl.set_active(ctrl)
        self._setting = False

    @property
    def shift(self):
        """Get whether the Shift modifier is selected."""
        return self._shift.get_active()

    @shift.setter
    def shift(self, shift):
        """Get whether the Shift modifier is selected."""
        self._setting = True
        self._shift.set_active(shift)
        self._setting = False

    @property
    def key(self):
        """Get the value of the key."""
        return self._hotkeyModel.get_value(self._hotkey.get_active_iter(), 0)

    @key.setter
    def key(self, key):
        """Set the value of the key."""
        self._setting = True

        hotkeyModel = self._hotkeyModel
        iter = hotkeyModel.get_iter_first()
        while iter is not None and \
              hotkeyModel.get_value(iter, 0)!=key:
            iter = hotkeyModel.iter_next(iter)

        if iter is None:
            iter = hotkeyModel.get_iter_first()

        self._hotkey.set_active_iter(iter)

        self._setting = False

    def set(self, hotkey):
        """Set the hotkey widget from the given hotkey."""
        self.ctrl = hotkey.ctrl
        self.shift = hotkey.shift
        self.key = hotkey.key

    def get(self):
        """Get a hotkey corresponding to the settings in the widghet."""

        key = self._hotkeyModel.get_value(self._hotkey.get_active_iter(), 0)

        return config.Hotkey(ctrl = self.ctrl, shift = self.shift,
                             key = self.key)

    def _ctrlToggled(self, checkButton):
        """Called when the status of the Ctrl modifier has changed."""
        if not self._setting:
            self.emit("hotkey-changed", Hotkey.CHANGED_CTRL)

    def _shiftToggled(self, checkButton):
        """Called when the status of the Shift modifier has changed."""
        if not self._setting:
            self.emit("hotkey-changed", Hotkey.CHANGED_SHIFT)

    def _keyChanged(self, comboBox):
        """Called when the value of the key has changed."""
        if not self._setting:
            self.emit("hotkey-changed", Hotkey.CHANGED_KEY)

    def __eq__(self, other):
        """Determine if the two hotkeys are equal."""
        return self.ctrl==other.ctrl and self.shift==other.shift and \
               self.key==other.key

#------------------------------------------------------------------------------

GObject.signal_new("hotkey-changed", Hotkey, GObject.SIGNAL_RUN_FIRST,
                   None, (int,))

#------------------------------------------------------------------------------

class Preferences(Gtk.Dialog):
    """The preferences dialog."""
    def __init__(self, gui):
        """Construct the dialog."""
        super(Preferences, self).__init__(WINDOW_TITLE_BASE + " " +
                                          xstr("prefs_title"),
                                          gui.mainWindow,
                                          Gtk.DialogFlags.MODAL)

        self.add_button(xstr("button_cancel"), Gtk.ResponseType.REJECT)
        self.add_button(xstr("button_ok"), Gtk.ResponseType.ACCEPT)
        self.set_resizable(False)

        self._gui = gui
        self._settingFromConfig = False

        contentArea = self.get_content_area()

        notebook = Gtk.Notebook()
        contentArea.pack_start(notebook, True, True, 4)

        general = self._buildGeneral()
        label = Gtk.Label(xstr("prefs_tab_general"))
        label.set_use_underline(True)
        label.set_tooltip_text(xstr("prefs_tab_general_tooltip"))
        notebook.append_page(general, label)

        messages = self._buildMessages()
        label = Gtk.Label(xstr("prefs_tab_messages"))
        label.set_use_underline(True)
        label.set_tooltip_text(xstr("prefs_tab_message_tooltip"))
        notebook.append_page(messages, label)

        sounds = self._buildSounds()
        label = Gtk.Label(xstr("prefs_tab_sounds"))
        label.set_use_underline(True)
        label.set_tooltip_text(xstr("prefs_tab_sounds_tooltip"))
        notebook.append_page(sounds, label)

        advanced = self._buildAdvanced()
        label = Gtk.Label(xstr("prefs_tab_advanced"))
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

        if response==Gtk.ResponseType.ACCEPT:
            self._toConfig(config)
            config.save()

    def _fromConfig(self, config):
        """Setup the dialog from the given configuration."""
        self._settingFromConfig = True

        self._setLanguage(config.language)
        self._hideMinimizedWindow.set_active(config.hideMinimizedWindow)
        self._quitOnClose.set_active(config.quitOnClose)
        self._onlineGateSystem.set_active(config.onlineGateSystem)
        self._onlineACARS.set_active(config.onlineACARS)
        self._flareTimeFromFS.set_active(config.flareTimeFromFS)
        self._syncFSTime.set_active(config.syncFSTime)
        self._usingFS2Crew.set_active(config.usingFS2Crew)

        self._setSmoothing(self._iasSmoothingEnabled, self._iasSmoothingLength,
                           config.iasSmoothingLength)
        self._setSmoothing(self._vsSmoothingEnabled, self._vsSmoothingLength,
                           config.vsSmoothingLength)

        self._useSimBrief.set_active(config.useSimBrief)

        pirepDirectory = config.pirepDirectory
        self._pirepDirectory.set_text("" if pirepDirectory is None
                                      else pirepDirectory)
        self._pirepAutoSave.set_active(config.pirepAutoSave)
        if not pirepDirectory:
            self._pirepAutoSave.set_sensitive(False)

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
        self._enableApproachCallouts.set_active(config.enableApproachCallouts)
        self._speedbrakeAtTD.set_active(config.speedbrakeAtTD)

        self._enableChecklists.set_active(config.enableChecklists)
        self._checklistHotkey.set(config.checklistHotkey)

        self._taxiSoundOnPushback.set_active(config.taxiSoundOnPushback)

        self._autoUpdate.set_active(config.autoUpdate)
        if not config.autoUpdate:
            self._warnedAutoUpdate = True

        self._updateURL.set_text(config.updateURL)

        self._xplaneRemote.set_active(config.xplaneRemote)
        self._xplaneAddress.set_text(config.xplaneAddress)

        self._settingFromConfig = False

    def _toConfig(self, config):
        """Setup the given config from the settings in the dialog."""
        config.language = self._getLanguage()
        config.hideMinimizedWindow = self._hideMinimizedWindow.get_active()
        config.quitOnClose = self._quitOnClose.get_active()
        config.onlineGateSystem = self._onlineGateSystem.get_active()
        config.onlineACARS = self._onlineACARS.get_active()
        config.flareTimeFromFS = self._flareTimeFromFS.get_active()
        config.syncFSTime = self._syncFSTime.get_active()
        config.usingFS2Crew = self._usingFS2Crew.get_active()
        config.iasSmoothingLength = self._getSmoothing(self._iasSmoothingEnabled,
                                                       self._iasSmoothingLength)
        config.vsSmoothingLength = self._getSmoothing(self._vsSmoothingEnabled,
                                                       self._vsSmoothingLength)
        config.useSimBrief = self._useSimBrief.get_active()
        config.pirepDirectory = self._pirepDirectory.get_text()
        config.pirepAutoSave = self._pirepAutoSave.get_active()

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
        config.enableApproachCallouts = self._enableApproachCallouts.get_active()
        config.speedbrakeAtTD = self._speedbrakeAtTD.get_active()

        config.enableChecklists = self._enableChecklists.get_active()
        config.checklistHotkey = self._checklistHotkey.get()

        config.taxiSoundOnPushback = self._taxiSoundOnPushback.get_active()

        config.autoUpdate = self._autoUpdate.get_active()
        config.updateURL = self._updateURL.get_text()

        config.xplaneRemote = self._xplaneRemote.get_active()
        config.xplaneAddress = self._xplaneAddress.get_text()

    def _buildGeneral(self):
        """Build the page for the general settings."""
        mainAlignment = Gtk.Alignment(xalign = 0.0, yalign = 0.0,
                                      xscale = 1.0, yscale = 0.0)
        mainAlignment.set_padding(padding_top = 0, padding_bottom = 8,
                                  padding_left = 4, padding_right = 4)
        mainBox = Gtk.VBox()
        mainAlignment.add(mainBox)

        guiBox = self._createFrame(mainBox, xstr("prefs_frame_gui"))

        languageBox = Gtk.HBox()
        guiBox.pack_start(languageBox, False, False, 4)

        label = Gtk.Label(xstr("prefs_language"))
        label.set_use_underline(True)

        languageBox.pack_start(label, False, False, 4)

        self._languageList = Gtk.ListStore(str, str)
        for language in const.languages:
            self._languageList.append([xstr("prefs_lang_" + language),
                                       language])

        self._languageComboBox = languageComboBox = \
            Gtk.ComboBox(model = self._languageList)
        cell = Gtk.CellRendererText()
        languageComboBox.pack_start(cell, True)
        languageComboBox.add_attribute(cell, 'text', 0)
        languageComboBox.set_tooltip_text(xstr("prefs_language_tooltip"))
        languageComboBox.connect("changed", self._languageChanged)
        languageBox.pack_start(languageComboBox, False, False, 4)

        label.set_mnemonic_widget(languageComboBox)

        self._changingLanguage = False
        self._warnedRestartNeeded = False

        self._hideMinimizedWindow = Gtk.CheckButton(xstr("prefs_hideMinimizedWindow"))
        self._hideMinimizedWindow.set_use_underline(True)
        self._hideMinimizedWindow.set_tooltip_text(xstr("prefs_hideMinimizedWindow_tooltip"))
        guiBox.pack_start(self._hideMinimizedWindow, False, False, 4)

        self._quitOnClose = Gtk.CheckButton(xstr("prefs_quitOnClose"))
        self._quitOnClose.set_use_underline(True)
        self._quitOnClose.set_tooltip_text(xstr("prefs_quitOnClose_tooltip"))
        guiBox.pack_start(self._quitOnClose, False, False, 4)

        onlineBox = self._createFrame(mainBox, xstr("prefs_frame_online"))

        self._onlineGateSystem = Gtk.CheckButton(xstr("prefs_onlineGateSystem"))
        self._onlineGateSystem.set_use_underline(True)
        self._onlineGateSystem.set_tooltip_text(xstr("prefs_onlineGateSystem_tooltip"))
        onlineBox.pack_start(self._onlineGateSystem, False, False, 4)

        self._onlineACARS = Gtk.CheckButton(xstr("prefs_onlineACARS"))
        self._onlineACARS.set_use_underline(True)
        self._onlineACARS.set_tooltip_text(xstr("prefs_onlineACARS_tooltip"))
        onlineBox.pack_start(self._onlineACARS, False, False, 4)

        simulatorBox = self._createFrame(mainBox, xstr("prefs_frame_simulator"))

        self._flareTimeFromFS = Gtk.CheckButton(xstr("prefs_flaretimeFromFS"))
        self._flareTimeFromFS.set_use_underline(True)
        self._flareTimeFromFS.set_tooltip_text(xstr("prefs_flaretimeFromFS_tooltip"))
        simulatorBox.pack_start(self._flareTimeFromFS, False, False, 4)

        self._syncFSTime = Gtk.CheckButton(xstr("prefs_syncFSTime"))
        self._syncFSTime.set_use_underline(True)
        self._syncFSTime.set_tooltip_text(xstr("prefs_syncFSTime_tooltip"))
        simulatorBox.pack_start(self._syncFSTime, False, False, 4)

        self._usingFS2Crew = Gtk.CheckButton(xstr("prefs_usingFS2Crew"))
        self._usingFS2Crew.set_use_underline(True)
        self._usingFS2Crew.set_tooltip_text(xstr("prefs_usingFS2Crew_tooltip"))
        simulatorBox.pack_start(self._usingFS2Crew, False, False, 4)

        (iasSmoothingBox, self._iasSmoothingEnabled,
         self._iasSmoothingLength) = \
           self._createSmoothingBox(xstr("prefs_iasSmoothingEnabled"),
                                    xstr("prefs_iasSmoothingEnabledTooltip"))
        simulatorBox.pack_start(iasSmoothingBox, False, False, 4)

        (vsSmoothingBox, self._vsSmoothingEnabled,
         self._vsSmoothingLength) = \
           self._createSmoothingBox(xstr("prefs_vsSmoothingEnabled"),
                                    xstr("prefs_vsSmoothingEnabledTooltip"))
        simulatorBox.pack_start(vsSmoothingBox, False, False, 4)

        self._useSimBrief = Gtk.CheckButton(xstr("prefs_useSimBrief"))
        self._useSimBrief.set_use_underline(True)
        self._useSimBrief.set_tooltip_text(xstr("prefs_useSimBrief_tooltip"))
        mainBox.pack_start(self._useSimBrief, False, False, 0)

        pirepBox = Gtk.HBox()
        mainBox.pack_start(pirepBox, False, False, 8)

        label = Gtk.Label(xstr("prefs_pirepDirectory"))
        label.set_use_underline(True)
        pirepBox.pack_start(label, False, False, 4)

        self._pirepDirectory = Gtk.Entry()
        self._pirepDirectory.set_tooltip_text(xstr("prefs_pirepDirectory_tooltip"))
        self._pirepDirectory.connect("changed", self._pirepDirectoryChanged)
        label.set_mnemonic_widget(self._pirepDirectory)
        pirepBox.pack_start(self._pirepDirectory, True, True, 4)

        self._pirepDirectoryButton = Gtk.Button(xstr("button_browse"))
        self._pirepDirectoryButton.connect("clicked",
                                           self._pirepDirectoryButtonClicked)
        pirepBox.pack_start(self._pirepDirectoryButton, False, False, 4)

        self._pirepAutoSave = Gtk.CheckButton(xstr("prefs_pirepAutoSave"))
        self._pirepAutoSave.set_use_underline(True)
        self._pirepAutoSave.set_tooltip_text(xstr("prefs_pirepAutoSave_tooltip"))
        mainBox.pack_start(self._pirepAutoSave, False, False, 0)

        return mainAlignment

    def _createFrame(self, mainBox, label):
        """Create a frame with an inner alignment and VBox.

        Return the vbox."""
        frame = Gtk.Frame(label = label)
        mainBox.pack_start(frame, False, False, 4)
        alignment = Gtk.Alignment(xalign = 0.0, yalign = 0.0,
                                  xscale = 1.0, yscale = 0.0)
        alignment.set_padding(padding_top = 4, padding_bottom = 0,
                              padding_left = 0, padding_right = 0)
        frame.add(alignment)
        vbox = Gtk.VBox()
        alignment.add(vbox)

        return vbox

    def _createSmoothingBox(self, checkBoxLabel, checkBoxTooltip,
                            maxSeconds = 10):
        """Create a HBox that contains entry fields for smoothing some value."""
        smoothingBox = Gtk.HBox()

        smoothingEnabled = Gtk.CheckButton(checkBoxLabel)
        smoothingEnabled.set_use_underline(True)
        smoothingEnabled.set_tooltip_text(checkBoxTooltip)

        smoothingBox.pack_start(smoothingEnabled, False, False, 0)

        smoothingLength = Gtk.SpinButton()
        smoothingLength.set_numeric(True)
        smoothingLength.set_range(2, maxSeconds)
        smoothingLength.set_increments(1, 1)
        smoothingLength.set_alignment(1.0)
        smoothingLength.set_width_chars(2)

        smoothingBox.pack_start(smoothingLength, False, False, 0)

        smoothingBox.pack_start(Gtk.Label(xstr("prefs_smoothing_seconds")),
                                False, False, 4)

        smoothingEnabled.connect("toggled", self._smoothingToggled,
                                 smoothingLength)
        smoothingLength.set_sensitive(False)

        return (smoothingBox, smoothingEnabled, smoothingLength)

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
            dialog = Gtk.MessageDialog(parent = self,
                                       type = Gtk.MessageType.INFO,
                                       message_format = xstr("prefs_restart"))
            dialog.add_button(xstr("button_ok"), Gtk.ResponseType.OK)
            dialog.set_title(self.get_title())
            dialog.format_secondary_markup(xstr("prefs_language_restart_sec"))
            dialog.run()
            dialog.hide()
            self._warnedRestartNeeded = True

    def _smoothingToggled(self, smoothingEnabled, smoothingLength):
        """Called when a smoothing enabled check box is toggled."""
        sensitive = smoothingEnabled.get_active()
        smoothingLength.set_sensitive(sensitive)
        if sensitive:
            smoothingLength.grab_focus()

    def _setSmoothing(self, smoothingEnabled, smoothingLength, smoothing):
        """Set the smoothing controls from the given value.

        If the value is less than 2, smoothing is disabled. The smoothing
        length is the absolute value of the value."""
        smoothingEnabled.set_active(smoothing>=2)
        smoothingLength.set_value(abs(smoothing))

    def _getSmoothing(self, smoothingEnabled, smoothingLength):
        """Get the smoothing value from the given controls.

        The returned value is the value of smoothingLength multiplied by -1, if
        smoothing is disabled."""
        value = smoothingLength.get_value_as_int()
        if not smoothingEnabled.get_active():
            value *= -1
        return value

    def _pirepDirectoryButtonClicked(self, button):
        """Called when the PIREP directory button is clicked."""
        dialog = Gtk.FileChooserDialog(title = WINDOW_TITLE_BASE + " - " +
                                       xstr("prefs_pirepDirectory_browser_title"),
                                       action = Gtk.FileChooserAction.SELECT_FOLDER,
                                       buttons = (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                                  Gtk.STOCK_OK, Gtk.ResponseType.OK),
                                       parent = self)
        dialog.set_modal(True)
        dialog.set_transient_for(self)

        directory = self._pirepDirectory.get_text()
        if directory:
            dialog.select_filename(directory)

        result = dialog.run()
        dialog.hide()

        if result==Gtk.ResponseType.OK:
            self._pirepDirectory.set_text(dialog.get_filename())

    def _pirepDirectoryChanged(self, entry):
        """Called when the PIREP directory is changed."""
        if self._pirepDirectory.get_text():
            self._pirepAutoSave.set_sensitive(True)
        else:
            self._pirepAutoSave.set_active(False)
            self._pirepAutoSave.set_sensitive(False)

    def _buildMessages(self):
        """Build the page for the message settings."""

        mainAlignment = Gtk.Alignment(xalign = 0.0, yalign = 0.0,
                                      xscale = 0.0, yscale = 0.0)
        mainAlignment.set_padding(padding_top = 16, padding_bottom = 8,
                                  padding_left = 4, padding_right = 4)
        mainBox = Gtk.VBox()
        mainAlignment.add(mainBox)

        table = Gtk.Table(len(const.messageTypes) + 1, 3)
        table.set_row_spacings(8)
        table.set_col_spacings(32)
        table.set_homogeneous(False)
        mainBox.pack_start(table, False, False, 4)

        label = Gtk.Label(xstr("prefs_msgs_fs"))
        label.set_justify(Gtk.Justification.CENTER)
        label.set_alignment(0.5, 1.0)
        table.attach(label, 1, 2, 0, 1)

        label = Gtk.Label(xstr("prefs_msgs_sound"))
        label.set_justify(Gtk.Justification.CENTER)
        label.set_alignment(0.5, 1.0)
        table.attach(label, 2, 3, 0, 1)

        self._msgFSCheckButtons = {}
        self._msgSoundCheckButtons = {}
        row = 1
        for messageType in const.messageTypes:
            messageTypeStr = const.messageType2string(messageType)
            label = Gtk.Label(xstr("prefs_msgs_type_" + messageTypeStr))
            label.set_justify(Gtk.Justification.CENTER)
            label.set_use_underline(True)
            label.set_alignment(0.5, 0.5)
            table.attach(label, 0, 1, row, row+1)

            fsCheckButton = Gtk.CheckButton()
            alignment = Gtk.Alignment(xscale = 0.0, yscale = 0.0,
                                      xalign = 0.5, yalign = 0.5)
            alignment.add(fsCheckButton)
            table.attach(alignment, 1, 2, row, row+1)
            self._msgFSCheckButtons[messageType] = fsCheckButton

            soundCheckButton = Gtk.CheckButton()
            alignment = Gtk.Alignment(xscale = 0.0, yscale = 0.0,
                                      xalign = 0.5, yalign = 0.5)
            alignment.add(soundCheckButton)
            table.attach(alignment, 2, 3, row, row+1)
            self._msgSoundCheckButtons[messageType] = soundCheckButton

            mnemonicWidget = Gtk.Label("")
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
        mainAlignment = Gtk.Alignment(xalign = 0.0, yalign = 0.0,
                                      xscale = 1.0, yscale = 1.0)
        mainAlignment.set_padding(padding_top = 8, padding_bottom = 8,
                                  padding_left = 4, padding_right = 4)

        mainBox = Gtk.VBox()
        mainAlignment.add(mainBox)

        backgroundFrame = Gtk.Frame(label = xstr("prefs_sounds_frame_bg"))
        mainBox.pack_start(backgroundFrame, False, False, 4)

        backgroundAlignment = Gtk.Alignment(xalign = 0.0, yalign = 0.0,
                                            xscale = 1.0, yscale = 0.0)
        backgroundAlignment.set_padding(padding_top = 4, padding_bottom = 4,
                                        padding_left = 4, padding_right = 4)
        backgroundFrame.add(backgroundAlignment)

        backgroundBox = Gtk.VBox()
        backgroundAlignment.add(backgroundBox)

        self._enableSounds = Gtk.CheckButton(xstr("prefs_sounds_enable"))
        self._enableSounds.set_use_underline(True)
        self._enableSounds.set_tooltip_text(xstr("prefs_sounds_enable_tooltip"))
        self._enableSounds.connect("toggled", self._enableSoundsToggled)
        alignment = Gtk.Alignment(xalign = 0.0, yalign = 0.5,
                                  xscale = 1.0, yscale = 0.0)
        alignment.add(self._enableSounds)
        backgroundBox.pack_start(alignment, False, False, 4)

        self._pilotControlsSounds = Gtk.CheckButton(xstr("prefs_sounds_pilotControls"))
        self._pilotControlsSounds.set_use_underline(True)
        self._pilotControlsSounds.set_tooltip_text(xstr("prefs_sounds_pilotControls_tooltip"))
        self._pilotControlsSounds.connect("toggled", self._pilotControlsSoundsToggled)
        backgroundBox.pack_start(self._pilotControlsSounds, False, False, 4)

        self._pilotHotkey = Hotkey(xstr("prefs_sounds_pilotHotkey"),
                                   [xstr("prefs_sounds_pilotHotkey_tooltip"),
                                    xstr("prefs_sounds_pilotHotkeyCtrl_tooltip"),
                                    xstr("prefs_sounds_pilotHotkeyShift_tooltip")])

        backgroundBox.pack_start(self._pilotHotkey, False, False, 4)

        self._taxiSoundOnPushback = Gtk.CheckButton(xstr("prefs_sounds_taxiSoundOnPushback"))
        self._taxiSoundOnPushback.set_use_underline(True)
        self._taxiSoundOnPushback.set_tooltip_text(xstr("prefs_sounds_taxiSoundOnPushback_tooltip"))
        backgroundBox.pack_start(self._taxiSoundOnPushback, False, False, 4)

        self._enableApproachCallouts = Gtk.CheckButton(xstr("prefs_sounds_approachCallouts"))
        self._enableApproachCallouts.set_use_underline(True)
        self._enableApproachCallouts.set_tooltip_text(xstr("prefs_sounds_approachCallouts_tooltip"))
        backgroundBox.pack_start(self._enableApproachCallouts, False, False, 4)

        self._speedbrakeAtTD = Gtk.CheckButton(xstr("prefs_sounds_speedbrakeAtTD"))
        self._speedbrakeAtTD.set_use_underline(True)
        self._speedbrakeAtTD.set_tooltip_text(xstr("prefs_sounds_speedbrakeAtTD_tooltip"))
        backgroundBox.pack_start(self._speedbrakeAtTD, False, False, 4)

        checklistFrame = Gtk.Frame(label = xstr("prefs_sounds_frame_checklists"))
        mainBox.pack_start(checklistFrame, False, False, 4)

        checklistAlignment = Gtk.Alignment(xalign = 0.0, yalign = 0.0,
                                           xscale = 1.0, yscale = 0.0)
        checklistAlignment.set_padding(padding_top = 4, padding_bottom = 4,
                                       padding_left = 4, padding_right = 4)
        checklistFrame.add(checklistAlignment)

        checklistBox = Gtk.VBox()
        checklistAlignment.add(checklistBox)

        self._enableChecklists = Gtk.CheckButton(xstr("prefs_sounds_enableChecklists"))
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

        self._pilotHotkey.connect("hotkey-changed", self._reconcileHotkeys,
                                  self._checklistHotkey)
        self._checklistHotkey.connect("hotkey-changed", self._reconcileHotkeys,
                                      self._pilotHotkey)

        return mainAlignment

    def _enableSoundsToggled(self, button):
        """Called when the enable sounds button is toggled."""
        active = button.get_active()
        self._pilotControlsSounds.set_sensitive(active)
        self._pilotControlsSoundsToggled(self._pilotControlsSounds)
        self._taxiSoundOnPushback.set_sensitive(active)
        self._enableApproachCallouts.set_sensitive(active)
        self._speedbrakeAtTD.set_sensitive(active)

    def _pilotControlsSoundsToggled(self, button):
        """Called when the enable sounds button is toggled."""
        active = button.get_active() and self._enableSounds.get_active()
        self._pilotHotkey.set_sensitive(active)
        if active and self._checklistHotkey.get_sensitive():
            self._reconcileHotkeys(self._checklistHotkey, Hotkey.CHANGED_SHIFT,
                                   self._pilotHotkey)

    def _enableChecklistsToggled(self, button):
        """Called when the enable checklists button is toggled."""
        active = button.get_active()
        self._checklistHotkey.set_sensitive(active)
        if active and self._pilotHotkey.get_sensitive():
            self._reconcileHotkeys(self._pilotHotkey, Hotkey.CHANGED_SHIFT,
                                   self._checklistHotkey)

    def _reconcileHotkeys(self, changedHotkey, what, otherHotkey):
        """Reconcile the given hotkeys so that they are different.

        changedHotkey is the hotkey that has changed. what is one of the
        Hotkey.CHANGED_XXX constants denoting what has changed. otherHotkey is
        the other hotkey that must be reconciled.

        If the other hotkey is not sensitive or is not equal to the changed
        one, nothing happens.

        Otherwise, if the status of the Ctrl modifier has changed, the status
        of the Ctrl modifier on the other hotkey will be negated. Similarly, if
        the Shift modifier has changed. If the key has changed, the Shift
        modifier is negated in the other hotkey."""
        if otherHotkey.get_sensitive() and changedHotkey==otherHotkey:
            if what==Hotkey.CHANGED_CTRL:
                otherHotkey.ctrl = not changedHotkey.ctrl
            elif what==Hotkey.CHANGED_SHIFT or what==Hotkey.CHANGED_KEY:
                otherHotkey.shift = not changedHotkey.shift

    def _buildAdvanced(self):
        """Build the page for the advanced settings."""

        mainAlignment = Gtk.Alignment(xalign = 0.0, yalign = 0.0,
                                      xscale = 1.0, yscale = 0.0)
        mainAlignment.set_padding(padding_top = 16, padding_bottom = 8,
                                  padding_left = 4, padding_right = 4)
        mainBox = Gtk.VBox()
        mainAlignment.add(mainBox)

        frame = Gtk.Frame.new()

        self._autoUpdate = Gtk.CheckButton(xstr("prefs_update_auto"))
        frame.set_label_widget(self._autoUpdate)
        frame.set_label_align(0.025, 0.5)
        mainBox.pack_start(frame, False, False, 4)

        self._autoUpdate.set_use_underline(True)
        self._autoUpdate.connect("toggled", self._autoUpdateToggled)
        self._autoUpdate.set_tooltip_text(xstr("prefs_update_auto_tooltip"))
        self._warnedAutoUpdate = False

        updateURLBox = Gtk.HBox()
        label = Gtk.Label(xstr("prefs_update_url"))
        label.set_use_underline(True)
        updateURLBox.pack_start(label, False, False, 4)

        self._updateURL = Gtk.Entry()
        label.set_mnemonic_widget(self._updateURL)
        self._updateURL.set_width_chars(40)
        self._updateURL.set_tooltip_text(xstr("prefs_update_url_tooltip"))
        self._updateURL.connect("changed", self._updateURLChanged)
        updateURLBox.pack_start(self._updateURL, True, True, 4)

        updateURLBox.set_margin_top(6)
        updateURLBox.set_margin_bottom(6)
        updateURLBox.set_margin_left(4)
        updateURLBox.set_margin_right(4)
        frame.add(updateURLBox)

        frame = Gtk.Frame.new()
        self._xplaneRemote = Gtk.CheckButton(xstr("prefs_xplane_remote"))
        frame.set_label_widget(self._xplaneRemote)
        frame.set_label_align(0.025, 0.5)
        mainBox.pack_start(frame, False, False, 4)

        self._xplaneRemote.set_use_underline(True)
        self._xplaneRemote.set_tooltip_text(xstr("prefs_xplane_remote_tooltip"))
        self._xplaneRemote.connect("toggled", self._xplaneRemoteToggled)

        xplaneAddressBox = Gtk.HBox()
        label = Gtk.Label(xstr("prefs_xplane_address"))
        label.set_use_underline(True)
        xplaneAddressBox.pack_start(label, False, False, 4)

        self._xplaneAddress = Gtk.Entry()
        label.set_mnemonic_widget(self._xplaneAddress)
        self._xplaneAddress.set_width_chars(40)
        self._xplaneAddress.set_tooltip_text(xstr("prefs_xplane_address_tooltip"))
        self._xplaneAddress.connect("changed", self._xplaneAddressChanged)
        xplaneAddressBox.pack_start(self._xplaneAddress, True, True, 4)

        xplaneAddressBox.set_margin_top(6)
        xplaneAddressBox.set_margin_bottom(6)
        xplaneAddressBox.set_margin_left(4)
        xplaneAddressBox.set_margin_right(4)
        frame.add(xplaneAddressBox)

        return mainAlignment

    def _setOKButtonSensitivity(self):
        """Set the sensitive state of the OK button."""
        sensitive = False
        try:
            result = urllib.parse.urlparse(self._updateURL.get_text())
            sensitive = result.scheme!="" and (result.netloc + result.path)!=""
        except:
            pass

        if sensitive:
            sensitive = not self._xplaneRemote.get_active() or \
                len(self._xplaneAddress.get_text())>0

        okButton = self.get_widget_for_response(Gtk.ResponseType.ACCEPT)
        okButton.set_sensitive(sensitive)

    def _autoUpdateToggled(self, button):
        """Called when the auto update check button is toggled."""
        if not self._settingFromConfig and not self._warnedAutoUpdate and \
           not self._autoUpdate.get_active():
            dialog = Gtk.MessageDialog(parent = self,
                                       type = Gtk.MessageType.INFO,
                                       message_format = xstr("prefs_update_auto_warning"))
            dialog.add_button(xstr("button_ok"), Gtk.ResponseType.OK)
            dialog.set_title(self.get_title())
            dialog.run()
            dialog.hide()
            self._warnedAutoUpdate = True

    def _updateURLChanged(self, entry):
        """Called when the update URL is changed."""
        self._setOKButtonSensitivity()

    def _xplaneRemoteToggled(self, button):
        """Called when the X-Plane remote access checkbox is toggled."""
        self._setOKButtonSensitivity()

    def _xplaneAddressChanged(self, entry):
        """Called when the X-Plane address is changed."""
        self._setOKButtonSensitivity()
