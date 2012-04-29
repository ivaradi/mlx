# The GUI part of the update

#-------------------------------------------------------------------------------

from mlx.gui.common import *

from mlx.update import update
from mlx.i18n import xstr

import mlx.const as const

import threading
import os
import sys

#-------------------------------------------------------------------------------

class Updater(threading.Thread):
    """The updater thread."""

    # The removal or renaming of one file equals to the downloading of this
    # many bytes in time (for the progress calculation)
    REMOVE2BYTES = 100

    _progressWindow = None

    _progressLabel = None
    
    _progressBar = None
    
    _progressOKButton = None

    _sudoDialog = None

    @staticmethod
    def _createGUI(parentWindow):
        """Create the GUI elements, if needed."""
        if Updater._progressWindow is not None:
            return

        Updater._progressWindow = window = gtk.Window()
        window.set_title(WINDOW_TITLE_BASE + " " + xstr("update_title"))
        window.set_transient_for(parentWindow)
        #win.set_icon_from_file(os.path.join(iconDirectory, "logo.ico"))
        window.set_size_request(400, -1)
        window.set_resizable(False)
        window.set_modal(True)
        window.connect("delete-event", lambda a, b: True)
        window.set_deletable(False)
        window.set_position(gtk.WindowPosition.CENTER_ON_PARENT if pygobject
                            else gtk.WIN_POS_CENTER_ON_PARENT)

        mainAlignment = gtk.Alignment(xscale = 1.0)
        mainAlignment.set_padding(padding_top = 4, padding_bottom = 10,
                                  padding_left = 16, padding_right = 16)
        window.add(mainAlignment)

        mainVBox = gtk.VBox()
        mainAlignment.add(mainVBox)

        labelAlignment = gtk.Alignment(xalign = 0.0, xscale = 0.0)
        Updater._progressLabel = progressLabel = gtk.Label()
        labelAlignment.add(progressLabel)
        mainVBox.pack_start(labelAlignment, True, True, 4)
        
        Updater._progressBar = progressBar = gtk.ProgressBar()
        mainVBox.pack_start(progressBar, True, True, 4)

        buttonAlignment = gtk.Alignment(xalign = 0.5, xscale = 0.1)
        Updater._progressOKButton = progressOKButton = gtk.Button("OK")
        buttonAlignment.add(progressOKButton)        
        mainVBox.pack_start(buttonAlignment, True, True, 4)

        Updater._sudoDialog = sudoDialog = \
            gtk.Dialog(WINDOW_TITLE_BASE + " " + xstr("update_title"),
                       parentWindow,
                       gtk.DialogFlags.MODAL if pygobject else gtk.DIALOG_MODAL)
        sudoDialog.add_button(xstr("button_cancel"), 0)
        sudoDialog.add_button(xstr("button_ok"), 1)
                       
        infoLabelAlignment = gtk.Alignment(xalign = 0.5, xscale = 0.1)
        infoLabelAlignment.set_padding(padding_top = 4, padding_bottom = 10,
                                       padding_left = 16, padding_right = 16)

        infoLabel = gtk.Label(xstr("update_needsudo"))
        infoLabel.set_justify(gtk.Justification.CENTER if pygobject
                              else gtk.JUSTIFY_CENTER)
        infoLabelAlignment.add(infoLabel)
        sudoDialog.vbox.pack_start(infoLabelAlignment, True, True, 4)

        sudoDialog.set_position(gtk.WindowPosition.CENTER_ON_PARENT if pygobject
                                else gtk.WIN_POS_CENTER_ON_PARENT)

    def __init__(self, gui, programDirectory, updateURL, parentWindow):
        """Construct the updater. If not created yet, the windows used by the
        updater are also created."""
        super(Updater, self).__init__()

        self._gui = gui
        
        self._programDirectory = programDirectory
        self._updateURL = updateURL

        self._totalProgress = 0
        self._waitAfterFinish = False
        self._restart = False

        self._sudoReply = None
        self._sudoCondition = threading.Condition()

        Updater._createGUI(parentWindow)

    def run(self):
        """Execute the thread's operation."""
        gobject.idle_add(self._startUpdate)
        update(self._programDirectory, self._updateURL, self, fromGUI = True)
        if not self._waitAfterFinish:
            gobject.idle_add(self._progressWindow.hide)

    def downloadingManifest(self):
        """Called when the downloading of the manifest has started."""
        gobject.idle_add(self._downloadingManifest)

    def _downloadingManifest(self):
        """Called when the downloading of the manifest has started."""
        self._progressLabel.set_text(xstr("update_manifest_progress"))
        self._progressBar.set_fraction(0)

    def downloadedManifest(self):
        """Called when the downloading of the manifest has finished."""
        gobject.idle_add(self._downloadedManifest)

    def _downloadedManifest(self):
        """Called when the downloading of the manifest has finished."""
        self._progressLabel.set_text(xstr("update_manifest_done"))
        self._progressBar.set_fraction(0.05)

    def needSudo(self):
        """Called when the program is interested in whether we want to run a
        program with administrator rights to do the update."""
        gobject.idle_add(self._needSudo)
        with self._sudoCondition:
            while self._sudoReply is None:
                self._sudoCondition.wait(1)
            return self._sudoReply

    def _needSudo(self):
        """Called when the program is interested in whether we want to run a
        program with administrator rights to do the update."""
        self._sudoDialog.show_all()
        result = self._sudoDialog.run()
        self._sudoDialog.hide()
        with self._sudoCondition:
            self._sudoReply = result!=0
            self._sudoCondition.notify()
        
    def setTotalSize(self, numToModifyAndNew, totalSize, numToRemove,
                     numToRemoveLocal):
        """Called when the downloading of the files has started."""
        self._numToModifyAndNew = numToModifyAndNew
        self._numModifiedOrNew = 0
        self._totalSize = totalSize
        self._downloaded = 0
        self._numToRemove = numToRemove
        self._numToRemoveLocal = numToRemoveLocal
        self._numRemoved = 0

        self._totalProgress = self._totalSize + \
                              (self._numToModifyAndNew + \
                               self._numToRemove + self._numToRemoveLocal) * \
                              Updater.REMOVE2BYTES
        self._waitAfterFinish = self._totalSize > 0 or self._numToRemove > 0

    def _startDownload(self):
        """Called when the download has started."""
        self._progressLabel.set_text(xstr("update_files_progress"))

    def setDownloaded(self, downloaded):
        """Called when a certain number of bytes are downloaded."""
        self._downloaded = downloaded
        gobject.idle_add(self._setDownloaded, downloaded)

    def _setDownloaded(self, downloaded):
        """Called when a certain number of bytes are downloaded."""
        self._progressLabel.set_text(xstr("update_files_bytes") % \
                                     (downloaded, self._totalSize))
        self._setProgress()

    def startRenaming(self):
        """Called when the renaming of files has started."""
        gobject.idle_add(self._startRenaming)

    def _startRenaming(self):
        """Called when the renaming of files has started."""
        self._progressLabel.set_text(xstr("update_renaming"))

    def renamed(self, path, count):
        """Called when a file has been renamed."""
        self._numModifiedOrNew = count
        gobject.idle_add(self._renamed, path, count)

    def _renamed(self, path, count):
        """Called when a file has been renamed."""
        self._progressLabel.set_text(xstr("update_renamed") % (path,))
        self._setProgress()

    def startRemoving(self):
        """Called when the removing of files has started."""
        gobject.idle_add(self._startRemoving)

    def _startRemoving(self):
        """Called when the removing of files has started."""
        self._progressLabel.set_text(xstr("update_removing"))

    def removed(self, path, count):
        """Called when a file has been removed."""
        self._numRemoved = count
        gobject.idle_add(self._removed, path, count)

    def _removed(self, path, count):
        """Called when a file has been removed."""
        self._progressLabel.set_text(xstr("update_removed") % (path,))
        self._setProgress()

    def writingManifest(self):
        """Called when the writing of the new manifest file has started."""
        gobject.idle_add(self._writingManifest)

    def _writingManifest(self):
        """Called when the writing of the new manifest file has started."""
        self._progressLabel.set_text(xstr("update_writing_manifest"))
        
    def done(self):
        """Called when the update has been done."""
        gobject.idle_add(self._done)
        self._restart = self._waitAfterFinish

    def _done(self):
        """Called when the writing of the new manifest file has started."""
        self._progressBar.set_fraction(1)
        if self._totalProgress>0:
            self._progressLabel.set_text(xstr("update_finished"))
            self._progressOKButton.set_sensitive(True)
        else:
            self._progressLabel.set_text(xstr("update_nothing"))
        
    def _setProgress(self):
        """Set the progress bar based on the current stage."""
        if self._totalProgress>0:
            progress = self._downloaded + \
                       (self._numModifiedOrNew + self._numRemoved) * \
                       Updater.REMOVE2BYTES
            self._progressBar.set_fraction(0.05 + 0.94 * progress / self._totalProgress)

    def failed(self, what):
        """Called when the downloading has failed."""
        self._waitAfterFinish = True
        gobject.idle_add(self._failed, what)

    def _failed(self, what):
        """Called when the downloading has failed."""        
        self._progressLabel.set_text(xstr("update_failed"))
        self._progressBar.set_fraction(1)
        self._progressOKButton.set_sensitive(True)

    def _startUpdate(self):
        """Start the update.

        It resets the GUI elements."""
        self._progressLabel.set_text("")
        self._progressBar.set_fraction(0)
        self._progressWindow.show_all()
        self._progressOKButton.set_sensitive(False)
        self._progressOKButton.connect("clicked", self._progressOKClicked)

    def _progressOKClicked(self, button):
        """Called when the OK button on the progress window is clicked."""
        self._progressWindow.hide()
        if self._restart:
            self._gui.restart()

#-------------------------------------------------------------------------------
