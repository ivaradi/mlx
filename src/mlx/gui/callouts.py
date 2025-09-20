
from .common import *

from mlx.i18n import xstr
import mlx.const as const
import mlx.config as config

import os
import re

#------------------------------------------------------------------------------

## @package mlx.gui.callouts
#
# Editor dialog for approach callouts.
#
# The dialog consists of an aircraft type selector box at the top, and a table
# with two buttons below it. The table contains the callout files with the
# corresponding altitudes, and is sorted according to the altitude. When a new
# file is added, the program finds out a new altitude for it. If the file's
# name contains numbers that are not used as altitudes yet, the most suitable
# of those numbers will be used. Otherwise a 'usual' altitude is searched for,
# in the direction according to the sort order, and if that fails too, the
# altitudes are tried one-by-one. See the
# \ref mlx.gui.callouts.ApproachCalloutsEditor._getNewAltitude
# "ApproachCalloutsEditor._getNewAltitude"  function for more details.

#------------------------------------------------------------------------------

class ApproachCalloutsEditor(Gtk.Dialog):
    """The dialog to edit the approach callouts."""
    integerRE = re.compile("[0-9]+")

    # A list of "usual" altitudes for callouts
    _usualAltitudes = [10, 20, 30, 40, 50, 100, 200, 300, 400, 500, 1000,
                       1500, 2000, 2500, 3000, 3500, 4000, 4500, 5000]

    @staticmethod
    def _getNextUsualAltitude(altitude, descending):
        """Get the next altitude coming after the given one in the
        given direction."""
        if descending:
            previous = None
            for alt in ApproachCalloutsEditor._usualAltitudes:
                if alt>=altitude: return previous
                previous = alt
        else:
            for alt in ApproachCalloutsEditor._usualAltitudes:
                if alt>altitude: return alt                
                    
        return None

    def __init__(self, gui):
        super(ApproachCalloutsEditor, self).__init__(WINDOW_TITLE_BASE + " - " +
                                                     xstr("callouts_title"),
                                                     gui.mainWindow,
                                                     Gtk.DialogFlags.MODAL)

        self.add_button(xstr("button_cancel"), Gtk.ResponseType.REJECT)
        self.add_button(xstr("button_ok"), Gtk.ResponseType.ACCEPT)

        self._gui = gui
        self._approachCallouts = {}
        self._currentAircraftType = const.aircraftTypes[0]
        self._fileOpenDialog = None

        contentArea = self.get_content_area()

        # FIXME: common code with the checklist editor
        typeBox = Gtk.HBox()

        label = Gtk.Label(xstr("callouts_aircraftType"))
        label.set_use_underline(True)

        typeBox.pack_start(label, False, False, 4)

        self._aircraftTypeModel = Gtk.ListStore(str, int)
        for type in const.aircraftTypes:
            name = aircraftNames[type] if type in aircraftNames \
                   else "Aircraft type #%d" % (type,)
            self._aircraftTypeModel.append([name, type])
        self._aircraftType = Gtk.ComboBox(model = self._aircraftTypeModel)
        renderer = Gtk.CellRendererText()
        self._aircraftType.pack_start(renderer, True)
        self._aircraftType.add_attribute(renderer, "text", 0)
        self._aircraftType.set_tooltip_text(xstr("callouts_aircraftType_tooltip"))
        self._aircraftType.set_active(0)
        self._aircraftType.connect("changed", self._aircraftTypeChanged)
        label.set_mnemonic_widget(self._aircraftType)

        typeBox.pack_start(self._aircraftType, True, True, 4)

        typeBoxAlignment = Gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                         xscale = 0.0, yscale = 0.0)
        typeBoxAlignment.set_size_request(400, -1)
        typeBoxAlignment.add(typeBox)

        contentArea.pack_start(typeBoxAlignment, False, False, 12)
        # FIXME: common code until here, but note that some texts are different

        contentBox = Gtk.HBox()        

        controlBox = Gtk.VBox()
        controlAlignment = Gtk.Alignment(xalign = 0.0, yalign = 0.0,
                                         xscale = 0.0, yscale = 0.0)
        controlAlignment.set_padding(padding_top = 0, padding_bottom = 0,
                                     padding_left = 32, padding_right = 32)
        controlAlignment.add(controlBox)
        contentBox.pack_start(controlAlignment, False, False, 0)

        self._addButton = Gtk.Button(xstr("callouts_add"))
        self._addButton.set_use_underline(True)
        self._addButton.set_tooltip_text(xstr("callouts_add_tooltip"))
        self._addButton.connect("clicked", self._addButtonClicked)
        addAlignment = Gtk.Alignment(xalign = 0.5, yalign = 0.0,
                                     xscale = 0.0, yscale = 0.0)
        addAlignment.set_padding(padding_top = 24, padding_bottom = 0,
                                 padding_left = 0, padding_right = 0)
        addAlignment.add(self._addButton)
        controlBox.pack_start(addAlignment, False, False, 0)

        self._removeButton = Gtk.Button(xstr("callouts_remove"))
        self._removeButton.set_use_underline(True)
        self._removeButton.set_tooltip_text(xstr("callouts_remove_tooltip"))
        self._removeButton.set_sensitive(False)
        self._removeButton.connect("clicked", self._removeButtonClicked)

        removeAlignment = Gtk.Alignment(xalign = 0.5, yalign = 0.0,
                                        xscale = 0.0, yscale = 0.0)
        removeAlignment.set_padding(padding_top = 24, padding_bottom = 0,
                                    padding_left = 0, padding_right = 0)
        removeAlignment.add(self._removeButton)
        controlBox.pack_start(removeAlignment, False, False, 0)

        self._fileListModel = Gtk.ListStore(int, str, str)
        self._fileListModel.set_sort_column_id(0, Gtk.SortType.DESCENDING)

        self._addingFile = False
        self._fileListModel.connect("row-inserted", self._fileAdded)
        self._lastAddedAltitude = None
        
        self._fileList = Gtk.TreeView(model = self._fileListModel)

        renderer = Gtk.CellRendererSpin()
        renderer.set_property("editable", True)

        adjustment = Gtk.Adjustment(0, 0, 5000, 10, 100)
        renderer.set_property("adjustment", adjustment);
        renderer.connect("edited", self._altitudeEdited)
        
        column = Gtk.TreeViewColumn(xstr("callouts_header_altitude"),
                                    renderer, text = 0)
        self._fileList.append_column(column)
        column.set_expand(True)
        column.set_clickable(True)
        column.set_reorderable(False)
        column.set_sort_indicator(True)
        column.set_sort_column_id(0)
        column.set_sort_order(Gtk.SortType.DESCENDING)
        column.set_expand(False)

        column = Gtk.TreeViewColumn(xstr("callouts_header_path"),
                                    Gtk.CellRendererText(), text = 1)
        self._fileList.append_column(column)
        column.set_expand(True)
        column.set_clickable(False)
        column.set_reorderable(False)
        column.set_expand(True)
        
        self._fileList.set_tooltip_column(2)
        self._fileList.set_size_request(300, -1)
        self._fileList.set_reorderable(False)
        self._fileList.connect("button-press-event",
                               self._fileListButtonPressed)
        selection = self._fileList.get_selection()
        selection.set_mode(Gtk.SelectionMode.MULTIPLE)
        selection.connect("changed", self._fileListSelectionChanged)

        self._buildFileListPopupMenu()

        scrolledWindow = Gtk.ScrolledWindow()
        scrolledWindow.add(self._fileList)
        scrolledWindow.set_size_request(300, -1)
        scrolledWindow.set_policy(Gtk.PolicyType.AUTOMATIC,
                                  Gtk.PolicyType.AUTOMATIC)
        scrolledWindow.set_shadow_type(Gtk.ShadowType.IN)
        
        fileListAlignment = Gtk.Alignment(xscale=1.0, yscale=1.0, 
                                          xalign=0.5, yalign=0.5)
        fileListAlignment.set_padding(padding_top = 0, padding_bottom = 16,
                                      padding_left = 0, padding_right = 8)
        fileListAlignment.add(scrolledWindow)
        
        contentBox.pack_start(fileListAlignment, False, False, 4)

        contentArea.pack_start(contentBox, True, True, 4)

        self.set_size_request(-1, 300)

    def run(self):
        """Run the approach callouts editor dialog."""
        self._approachCallouts = {}
        self._displayCurrentApproachCallouts()
        self.show_all()
        response = super(ApproachCalloutsEditor, self).run()
        self.hide()

        if response==Gtk.ResponseType.ACCEPT:
            self._saveApproachCallouts()
            config = self._gui.config
            for (aircraftType, approachCallouts) in \
                    self._approachCallouts.items():
                config.setApproachCallouts(aircraftType, approachCallouts)
            config.save()

    def _aircraftTypeChanged(self, comboBox):
        """Called when the aircraft's type has changed."""        
        self._saveApproachCallouts()
        self._displayCurrentApproachCallouts()
        
    def _addButtonClicked(self, button):
        """Called when the Add button is clicked."""
        dialog = self._getFileOpenDialog()
        
        dialog.show_all()
        result = dialog.run()
        dialog.hide()

        if result==Gtk.ResponseType.OK:
            filePath = dialog.get_filename()
            baseName = os.path.basename(filePath)
            altitude = self._getNewAltitude(baseName)
            self._addingFile = True
            self._lastAddedAltitude = altitude
            self._fileListModel.append([altitude, baseName, filePath])
            self._addingFile = False

    def _fileAdded(self, model, path, iter):
        """Called when a file is added to the list of callouts.

        Makes the treeview to edit the altitude in the given row."""
        if self._addingFile:
            GObject.idle_add(self._selectFile)
            self._fileList.grab_focus()
            self.grab_focus()

    def _selectFile(self):
        """Select the file with the last added altitude."""
        if self._lastAddedAltitude is None: return

        model = self._fileListModel
        iter = model.get_iter_first()
        while iter is not None:
            if model.get_value(iter, 0)==self._lastAddedAltitude: break
            iter = model.iter_next(iter)
        if iter is not None:
            self._fileList.set_cursor(model.get_path(iter),
                                      self._fileList.get_column(0), True)
        self._lastAddedAltitude = None
                             
    def _removeButtonClicked(self, button):
        """Called when the Remove button is clicked."""
        self._removeSelected()
        
    def _removeSelected(self):
        """Remove the selected files."""
        selection = self._fileList.get_selection()
        (model, paths) = selection.get_selected_rows()

        iters = [model.get_iter(path) for path in paths]

        for i in iters:
            if i is not None:
                model.remove(i)
        
    def _fileListSelectionChanged(self, selection):
        """Called when the selection in the file list changes."""
        anySelected = selection.count_selected_rows()>0
        self._removeButton.set_sensitive(anySelected)

    def _getAircraftType(self):
        """Get the currently selected aircraft type."""
        # FIXME: the same code as in the checklist editor
        index = self._aircraftType.get_active()
        return self._aircraftTypeModel[index][1]        

    def _altitudeEdited(self, widget, path, value):
        """Called when an altitude is edited"""
        newAltitude = int(value)

        model = self._fileListModel
        editedIter = model.get_iter_from_string(path)
        editedPath = model.get_path(editedIter)
        otherPath = self._hasAltitude(newAltitude, ignorePath = editedPath)
        if otherPath is not None:
            dialog = Gtk.MessageDialog(parent = self,
                                       type = Gtk.MessageType.QUESTION,
                                       message_format =
                                       xstr("callouts_altitude_clash"))
            dialog.format_secondary_markup(xstr("callouts_altitude_clash_sec"))
            dialog.add_button(xstr("button_no"), Gtk.ResponseType.NO)
            dialog.add_button(xstr("button_yes"), Gtk.ResponseType.YES)
            dialog.set_title(WINDOW_TITLE_BASE)

            result = dialog.run()
            dialog.hide()

            if result!=Gtk.ResponseType.YES:
                newAltitude = None
                
        if newAltitude is not None:
            model[editedPath][0] = newAltitude
            if otherPath is not None:
                model.remove(model.get_iter(otherPath))

    def _saveApproachCallouts(self):
        """Save the currently displayed list of approach callouts for the
        previously displayed aircraft type."""
        mapping = {}
        model = self._fileListModel
        iter = model.get_iter_first()
        while iter is not None:
            altitude = int(model.get(iter, 0)[0])
            path = model.get(iter, 2)[0]
            mapping[altitude] = path
            iter = model.iter_next(iter)

        self._approachCallouts[self._currentAircraftType] = \
            config.ApproachCallouts(mapping)
        
    def _displayCurrentApproachCallouts(self):
        """Display the approach callouts for the currently selected aircraft
        type."""
        aircraftType = self._getAircraftType()
        self._currentAircraftType = aircraftType
        if aircraftType not in self._approachCallouts:
            self._approachCallouts[aircraftType] = \
                self._gui.config.getApproachCallouts(aircraftType).clone()
        approachCallouts = self._approachCallouts[aircraftType]

        self._fileListModel.clear()
        for (altitude, path) in approachCallouts:
            self._fileListModel.append([altitude, os.path.basename(path), path])        

    def _getFileOpenDialog(self):
        """Get the dialog to open a file.

        If it does not exist yet, it will be created."""
        if self._fileOpenDialog is None:
            dialog = Gtk.FileChooserDialog(title = WINDOW_TITLE_BASE + " - " +
                                           xstr("callouts_open_title"),
                                           action = Gtk.FileChooserAction.OPEN,
                                           buttons = (Gtk.STOCK_CANCEL,
                                                      Gtk.ResponseType.CANCEL,
                                                      Gtk.STOCK_OK, Gtk.ResponseType.OK),
                                           parent = self)
            dialog.set_modal(True)            
            dialog.set_do_overwrite_confirmation(True)
      
            # FIXME: create the filters in one location and use them
            # from there
            filter = Gtk.FileFilter()
            filter.set_name(xstr("file_filter_audio"))
            filter.add_pattern("*.wav")
            filter.add_pattern("*.mp3")
            dialog.add_filter(filter)

            filter = Gtk.FileFilter()
            filter.set_name(xstr("file_filter_all"))
            filter.add_pattern("*.*")
            dialog.add_filter(filter)
            
            self._fileOpenDialog = dialog

        return self._fileOpenDialog
    
    def _getNewAltitude(self, baseName):
        """Get a new, unique altitude for the audio file with the given
        base name.

        First the given file name is searched for suitable
        numbers. Otherwise the smallest altitude in the model is
        considered, and, depending on the actual ordering of the
        table, a suitable smaller or greater value is found. It is
        ensured that the number is unique, unless all numbers are
        taken.
        
        If there is no entry in the table yet, 2500 is returned if the
        table is sorted descending, 10 otherwise."""
        altitude = self._getNewAltitudeFromFileName(baseName)
        if altitude is not None: return altitude

        descending = self._fileList.get_column(0).get_sort_order()==Gtk.SortType.DESCENDING
        model = self._fileListModel
        numEntries = model.iter_n_children(None)
        if numEntries==0:
            return 2500 if descending else 10
        else:
            selection = self._fileList.get_selection()
            (_model, paths) = selection.get_selected_rows()

            if paths:
                startIter = model.get_iter(max(paths))
            else:
                startIter = model.iter_nth_child(None, numEntries-1)

            startValue = model.get_value(startIter, 0)

            altitude = self._getNextValidUsualAltitude(startValue, descending)
            if altitude is None:
                altitude = self._getNextValidUsualAltitude(startValue,
                                                           not descending)

            if altitude is None:
                for altitude in range(0 if descending else 4999,
                                      4999 if descending else 0,
                                      1 if descending else -1):
                    if not self._hasAltitude(altitude): break
                                   
            return altitude

    def _getNewAltitudeFromFileName(self, baseName):
        """Get a new altitude value from the given file name.

        The name is traversed for numbers. If a number is less than
        5000 and there is no such altitude yet in the table, it is
        checked if it is divisible by 100 or 1000, and if so, it gets
        a score of 2. If it is divisible by 10, the score will be 1,
        otherwise 0. The first highest scoring number is returned, if
        there are any at all, otherwise None."""
        candidateAltitude = None
        candidateScore = None
        
        (baseName, _) = os.path.splitext(baseName)
        numbers = ApproachCalloutsEditor.integerRE.findall(baseName)
        for number in numbers:
            value = int(number)
            if value<5000 and not self._hasAltitude(value):
                score = 2 if (value%100)==0 or (value%1000)==0 \
                    else 1 if (value%10)==0 else 0
                if candidateAltitude is None or score>candidateScore:
                    candidateAltitude = value
                    candidateScore = score

        return candidateAltitude        
        
    def _hasAltitude(self, altitude, ignorePath = None):
        """Determine if the model already contains the given altitude
        or not.
        
        ignorePath is a path in the model to ignore.

        Returns the path of the element found, if any, or None, if the
        altitude is not found."""        
        model = self._fileListModel
        iter = model.get_iter_first()
        while iter is not None:
            path = model.get_path(iter)
            if path!=ignorePath and altitude==model[path][0]:
                return path
            iter = model.iter_next(iter)

        return None

    def _getNextValidUsualAltitude(self, startValue, descending):
        """Get the next valid usual altitude."""
        value = startValue
        while value is not None and self._hasAltitude(value):
            value = \
                ApproachCalloutsEditor._getNextUsualAltitude(value, 
                                                             descending)        

        return value
        
    def _fileListButtonPressed(self, widget, event):
        """Called when a mouse button is pressed on the file list."""
        if event.type!=Gdk.EventType.BUTTON_PRESS or event.button!=3:
            return

        menu = self._fileListPopupMenu
        menu.popup(None, None, None, None, event.button, event.time)

    def _buildFileListPopupMenu(self):
        """Build the file list popup menu."""
        menu = Gtk.Menu()

        menuItem = Gtk.MenuItem()
        menuItem.set_label(xstr("callouts_remove"))
        menuItem.set_use_underline(True)
        menuItem.connect("activate", self._popupRemove)
        menuItem.show()
        self._popupRemoveItem = menuItem

        menu.append(menuItem)

        self._fileListPopupMenu = menu

    def _popupRemove(self, menuItem):
        """Remove the currently selected menu items."""
        self._removeSelected()

#------------------------------------------------------------------------------
