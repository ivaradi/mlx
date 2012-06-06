# Module for editing checklists

#------------------------------------------------------------------------------

from common import *

from mlx.i18n import xstr
import mlx.const as const
import mlx.config as config

import os

#------------------------------------------------------------------------------

class ChecklistEditor(gtk.Dialog):
    """The dialog to edit the checklists."""
    def __init__(self, gui):
        super(ChecklistEditor, self).__init__(WINDOW_TITLE_BASE + " - " +
                                              xstr("chklst_title"),
                                              gui.mainWindow,
                                              DIALOG_MODAL)

        self.add_button(xstr("button_cancel"), RESPONSETYPE_REJECT)
        self.add_button(xstr("button_ok"), RESPONSETYPE_ACCEPT)

        self._gui = gui
        self._checklists = {}
        self._currentAircraftType = const.aircraftTypes[0]

        contentArea = self.get_content_area()

        typeBox = gtk.HBox()

        label = gtk.Label(xstr("chklst_aircraftType"))
        label.set_use_underline(True)

        typeBox.pack_start(label, False, False, 4)

        self._aircraftTypeModel = gtk.ListStore(str, int)
        for type in const.aircraftTypes:
            name = aircraftNames[type] if type in aircraftNames \
                   else "Aircraft type #%d" % (type,)
            self._aircraftTypeModel.append([name, type])
        self._aircraftType = gtk.ComboBox(model = self._aircraftTypeModel)
        renderer = gtk.CellRendererText()
        self._aircraftType.pack_start(renderer, True)
        self._aircraftType.add_attribute(renderer, "text", 0)
        self._aircraftType.set_tooltip_text(xstr("chklst_aircraftType_tooltip"))
        self._aircraftType.set_active(0)
        self._aircraftType.connect("changed", self._aircraftTypeChanged)
        label.set_mnemonic_widget(self._aircraftType)

        typeBox.pack_start(self._aircraftType, True, True, 4)

        typeBoxAlignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                         xscale = 0.0, yscale = 0.0)
        typeBoxAlignment.set_size_request(400, -1)
        typeBoxAlignment.add(typeBox)

        contentArea.pack_start(typeBoxAlignment, False, False, 12)

        fileBox = gtk.HBox()        

        self._fileChooser = gtk.FileChooserWidget()
        self._fileChooser.set_select_multiple(True)
        
        filter = gtk.FileFilter()
        filter.set_name(xstr("chklst_filter_audio"))
        filter.add_pattern("*.wav")
        filter.add_pattern("*.mp3")
        self._fileChooser.add_filter(filter)
            
        filter = gtk.FileFilter()
        filter.set_name(xstr("file_filter_all"))
        filter.add_pattern("*.*")
        self._fileChooser.add_filter(filter)

        self._fileChooser.connect("selection-changed",
                                  self._fileChooserSelectionChanged)

        fileBox.pack_start(self._fileChooser, True, True, 4)

        controlBox = gtk.VBox()
        controlAlignment = gtk.Alignment(xalign = 0.0, yalign = 0.0,
                                         xscale = 0.0, yscale = 0.0)
        controlAlignment.set_padding(padding_top = 0, padding_bottom = 0,
                                     padding_left = 32, padding_right = 32)
        controlAlignment.add(controlBox)
        fileBox.pack_start(controlAlignment, False, False, 0)

        self._addButton = gtk.Button(xstr("chklst_add"))
        self._addButton.set_use_underline(True)
        self._addButton.set_tooltip_text(xstr("chklst_add_tooltip"))
        self._addButton.connect("clicked", self._addButtonClicked)
        addAlignment = gtk.Alignment(xalign = 0.5, yalign = 0.0,
                                     xscale = 0.0, yscale = 0.0)
        addAlignment.set_padding(padding_top = 64, padding_bottom = 0,
                                 padding_left = 0, padding_right = 0)
        addAlignment.add(self._addButton)
        controlBox.pack_start(addAlignment, False, False, 0)

        self._removeButton = gtk.Button(xstr("chklst_remove"))
        self._removeButton.set_use_underline(True)
        self._removeButton.set_tooltip_text(xstr("chklst_remove_tooltip"))
        self._removeButton.set_sensitive(False)
        self._removeButton.connect("clicked", self._removeButtonClicked)

        removeAlignment = gtk.Alignment(xalign = 0.5, yalign = 0.0,
                                        xscale = 0.0, yscale = 0.0)
        removeAlignment.set_padding(padding_top = 64, padding_bottom = 0,
                                    padding_left = 0, padding_right = 0)
        removeAlignment.add(self._removeButton)
        controlBox.pack_start(removeAlignment, False, False, 0)

        self._moveUpButton = gtk.Button(xstr("chklst_moveUp"))
        self._moveUpButton.set_use_underline(True)
        self._moveUpButton.set_tooltip_text(xstr("chklst_moveUp_tooltip"))
        self._moveUpButton.set_sensitive(False)
        self._moveUpButton.connect("clicked", self._moveUpButtonClicked)

        moveUpAlignment = gtk.Alignment(xalign = 0.5, yalign = 0.0,
                                        xscale = 0.0, yscale = 0.0)
        moveUpAlignment.set_padding(padding_top = 16, padding_bottom = 0,
                                    padding_left = 0, padding_right = 0)
        moveUpAlignment.add(self._moveUpButton)
        controlBox.pack_start(moveUpAlignment, False, False, 0)

        self._moveDownButton = gtk.Button(xstr("chklst_moveDown"))
        self._moveDownButton.set_use_underline(True)
        self._moveDownButton.set_tooltip_text(xstr("chklst_moveDown_tooltip"))
        self._moveDownButton.set_sensitive(False)
        self._moveDownButton.connect("clicked", self._moveDownButtonClicked)

        moveDownAlignment = gtk.Alignment(xalign = 0.5, yalign = 0.0,
                                        xscale = 0.0, yscale = 0.0)
        moveDownAlignment.set_padding(padding_top = 4, padding_bottom = 0,
                                    padding_left = 0, padding_right = 0)
        moveDownAlignment.add(self._moveDownButton)
        controlBox.pack_start(moveDownAlignment, False, False, 0)

        self._fileListModel = gtk.ListStore(str, str)
        self._fileList = gtk.TreeView(model = self._fileListModel)
        column = gtk.TreeViewColumn(xstr("chklst_header"),
                                    gtk.CellRendererText(), text = 0)
        column.set_expand(True)
        column.set_clickable(False)
        column.set_reorderable(False)
        self._fileList.append_column(column)
        self._fileList.set_tooltip_column(1)
        self._fileList.set_reorderable(True)
        self._fileList.set_size_request(200, -1)
        selection = self._fileList.get_selection()
        selection.set_mode(SELECTION_MULTIPLE)
        selection.connect("changed", self._fileListSelectionChanged)

        fileBox.pack_start(self._fileList, False, False, 4)

        contentArea.pack_start(fileBox, True, True, 4)

        self.set_size_request(900, 500)

    def run(self):
        """Run the checklist editor dialog."""
        self._checklists = {}
        self._displayCurrentChecklist()
        self.show_all()
        response = super(ChecklistEditor, self).run()
        self.hide()

        if response==RESPONSETYPE_ACCEPT:
            self._saveChecklist()
            config = self._gui.config
            for (aircraftType, checklist) in self._checklists.iteritems():
                config.setChecklist(aircraftType, checklist)
            config.save()

    def _aircraftTypeChanged(self, comboBox):
        """Called when the aircraft's type has changed."""        
        self._saveChecklist()
        self._displayCurrentChecklist()
        
    def _fileChooserSelectionChanged(self, fileChooser):
        """Called when the selection of the given file chooser is changed."""
        numFiles = 0
        numSelected = 0
        for path in fileChooser.get_filenames():
            path = text2unicode(path)
            numSelected += 1
            if os.path.isfile(path): numFiles += 1

        self._addButton.set_sensitive(numFiles>0 and numFiles==numSelected)

    def _addButtonClicked(self, button):
        """Called when the Add button is clicked."""
        for path in self._fileChooser.get_filenames():
            path = text2unicode(path)
            self._fileListModel.append([os.path.basename(path),
                                        path])
        self._fileChooser.unselect_all()
        
    def _removeButtonClicked(self, button):
        """Called when the Remove button is clicked."""
        selection = self._fileList.get_selection()
        (model, paths) = selection.get_selected_rows()
        while paths:
            model.remove(model.get_iter(paths[0]))
            (model, paths) = selection.get_selected_rows()
        
    def _moveUpButtonClicked(self, button):
        """Called when the move up button is clicked."""
        self._moveSelected(True)
        
    def _moveDownButtonClicked(self, button):
        """Called when the move down button is clicked."""
        self._moveSelected(False)

    def _moveSelected(self, up):
        """Move the selected files up or down."""
        selection = self._fileList.get_selection()
        (model, paths) = selection.get_selected_rows()
        indexes = [(path.get_indices() if pygobject else path)[0]
                   for path in paths]
        indexes.sort()
        if not up:
            indexes.reverse()

        for index in indexes:
            fromIter = model.iter_nth_child(None, index)
            toIter = model.iter_nth_child(None, index-1 if up else index + 1)
            if up:
                model.move_before(fromIter, toIter)
            else:
                model.move_after(fromIter, toIter)
        
        self._moveUpButton.set_sensitive(indexes[0]>1 if up else True)
        numRows = model.iter_n_children(None)
        self._moveDownButton.set_sensitive(True if up else
                                           indexes[-1]<(numRows-2))

    def _fileListSelectionChanged(self, selection):
        """Called when the selection in the file list changes."""
        anySelected = selection.count_selected_rows()>0
        self._removeButton.set_sensitive(anySelected)

        if anySelected:
            (model, paths) = selection.get_selected_rows()
            minIndex = None
            maxIndex = None
            for path in paths:
                [index] = path.get_indices() if pygobject else path
                if minIndex is None or index<minIndex: minIndex = index
                if maxIndex is None or index>maxIndex: maxIndex = index
                        
            self._moveUpButton.set_sensitive(minIndex>0)

            numRows = model.iter_n_children(None)
            self._moveDownButton.set_sensitive(maxIndex<(numRows-1))
        else:
            self._moveUpButton.set_sensitive(False)
            self._moveDownButton.set_sensitive(False)

    def _getAircraftType(self):
        """Get the currently selected aircraft type."""
        index = self._aircraftType.get_active()
        return self._aircraftTypeModel[index][1]        

    def _saveChecklist(self):
        """Save the currently displayed checklist for the previously displayed
        aircraft type."""
        fileList = []
        model = self._fileListModel
        iter = model.get_iter_first()
        while iter is not None:
            path = model.get(iter, 1)[0]
            fileList.append(path)
            iter = model.iter_next(iter)

        self._checklists[self._currentAircraftType] = config.Checklist(fileList)
        
    def _displayCurrentChecklist(self):
        """Display the checklist for the currently selected aircraft type."""
        aircraftType = self._getAircraftType()
        self._currentAircraftType = aircraftType
        if aircraftType not in self._checklists:
            self._checklists[aircraftType] = \
                self._gui.config.getChecklist(aircraftType).clone()
        checklist = self._checklists[aircraftType]

        self._fileListModel.clear()
        for path in checklist:
            self._fileListModel.append([os.path.basename(path), path])
        
        
#------------------------------------------------------------------------------
