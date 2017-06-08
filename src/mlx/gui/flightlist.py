# A widget which is a generic list of flights

#-----------------------------------------------------------------------------

from mlx.gui.common import *

import mlx.const as const

#-----------------------------------------------------------------------------

class ColumnDescriptor(object):
    """A descriptor for a column in the list."""
    def __init__(self, attribute, heading, type = str,
                 convertFn = None, renderer = None,
                 extraColumnAttributes = None, sortable = False,
                 defaultSortable = False, defaultDescending = False,
                 cellDataFn = None):
        """Construct the descriptor."""
        self._attribute = attribute
        self._heading = heading
        self._type = type
        self._convertFn = convertFn
        self._renderer = \
          gtk.CellRendererText() if renderer is None else renderer
        self._extraColumnAttributes = extraColumnAttributes
        self._sortable = sortable
        self._defaultSortable = defaultSortable
        self._defaultDescending = defaultDescending
        self._cellDataFn = cellDataFn

    @property
    def defaultSortable(self):
        """Determine if this column is the default sortable one."""
        return self._defaultSortable

    def appendType(self, types):
        """Append the type of this column to the given list of types."""
        types.append(self._type)

    def getViewColumn(self, index):
        """Get a new column object for a tree view.

        @param index is the 0-based index of the column."""
        if isinstance(self._renderer, gtk.CellRendererText):
            column = gtk.TreeViewColumn(self._heading, self._renderer,
                                        text = index)
        elif isinstance(self._renderer, gtk.CellRendererToggle):
            column = gtk.TreeViewColumn(self._heading, self._renderer,
                                        active = index)
        else:
            column = gtk.TreeViewColumn(self._heading, self._renderer)
        column.set_expand(True)
        if self._sortable:
            column.set_sort_column_id(index)
            column.set_sort_indicator(True)

        if self._extraColumnAttributes is not None:
            for (key, value) in self._extraColumnAttributes.iteritems():
                if key=="alignment":
                    self._renderer.set_alignment(value, 0.5)
                else:
                    raise Exception("unhandled extra column attribute '" +
                                    key + "'")
        if self._cellDataFn is not None:
            column.set_cell_data_func(self._renderer, self._cellDataFn)

        return column

    def getValueFrom(self, flight):
        """Get the value from the given flight."""
        attributes = self._attribute.split(".")
        value = getattr(flight, attributes[0])
        for attr in attributes[1:]:
            value = getattr(value, attr)
        return self._type(value) if self._convertFn is None \
            else self._convertFn(value, flight)

#-----------------------------------------------------------------------------

class FlightList(gtk.Alignment):
    """Construct the flight list.

    This is a complete widget with a scroll window. It is alignment centered
    horizontally and expandable vertically."""

    defaultColumnDescriptors = [
        ColumnDescriptor("callsign", xstr("flightsel_no")),
        ColumnDescriptor("departureTime", xstr("flightsel_deptime"),
                         sortable = True, defaultSortable = True),
        ColumnDescriptor("departureICAO", xstr("flightsel_from"),
                         sortable = True),
        ColumnDescriptor("arrivalICAO", xstr("flightsel_to"), sortable = True)
    ]

    def __init__(self, columnDescriptors = defaultColumnDescriptors,
                 popupMenuProducer = None, widthRequest = None,
                 multiSelection = False):
        """Construct the flight list with the given column descriptors."""

        self._columnDescriptors = columnDescriptors
        self._popupMenuProducer = popupMenuProducer
        self._popupMenu = None

        types = [int]
        defaultSortableIndex = None
        for columnDescriptor in self._columnDescriptors:
            if columnDescriptor.defaultSortable:
                defaultSortableIndex = len(types)
            columnDescriptor.appendType(types)

        self._model = gtk.ListStore(*types)
        if defaultSortableIndex is not None:
            sortOrder = SORT_DESCENDING \
              if self._columnDescriptors[defaultSortableIndex-1]._defaultDescending \
              else SORT_ASCENDING
            self._model.set_sort_column_id(defaultSortableIndex, sortOrder)
        self._view = gtk.TreeView(self._model)

        flightIndexColumn = gtk.TreeViewColumn()
        flightIndexColumn.set_visible(False)
        self._view.append_column(flightIndexColumn)

        index = 1
        for columnDescriptor in self._columnDescriptors:
            column = columnDescriptor.getViewColumn(index)
            self._view.append_column(column)
            index += 1

        self._view.connect("row-activated", self._rowActivated)
        self._view.connect("button-press-event", self._buttonPressEvent)

        selection = self._view.get_selection()
        selection.connect("changed", self._selectionChanged)
        if multiSelection:
            selection.set_mode(SELECTION_MULTIPLE)

        scrolledWindow = gtk.ScrolledWindow()
        scrolledWindow.add(self._view)
        if widthRequest is not None:
            scrolledWindow.set_size_request(widthRequest, -1)
        # FIXME: these should be constants in common.py
        scrolledWindow.set_policy(gtk.PolicyType.AUTOMATIC if pygobject
                                  else gtk.POLICY_AUTOMATIC,
                                  gtk.PolicyType.AUTOMATIC if pygobject
                                  else gtk.POLICY_AUTOMATIC)
        scrolledWindow.set_shadow_type(gtk.ShadowType.IN if pygobject
                                       else gtk.SHADOW_IN)

        super(FlightList, self).__init__(xalign = 0.5, yalign = 0.0,
                                         xscale = 0.0, yscale = 1.0)
        self.add(scrolledWindow)

    @property
    def selectedIndexes(self):
        """Get the indexes of the selected entries, if any.

        The indexes are sorted."""
        selection = self._view.get_selection()
        (model, rows) = selection.get_selected_rows()

        indexes = [self._getIndexForPath(path) for path in rows]
        indexes.sort()
        return indexes

    @property
    def hasFlights(self):
        """Determine if there are any flights in the list."""
        return self._model.get_iter_root() is not None

    def clear(self):
        """Clear the model."""
        self._model.clear()

    def addFlight(self, flight):
        """Add the given booked flight."""
        values = [self._model.iter_n_children(None)]
        for columnDescriptor in self._columnDescriptors:
            values.append(columnDescriptor.getValueFrom(flight))
        self._model.append(values)

    def removeFlights(self, indexes):
        """Remove the flights with the given indexes."""
        model = self._model
        idx = 0
        iter = model.get_iter_first()
        while iter is not None:
            nextIter = model.iter_next(iter)
            if model.get_value(iter, 0) in indexes:
                model.remove(iter)
            else:
                model.set_value(iter, 0, idx)
                idx += 1
            iter = nextIter

    def _getIndexForPath(self, path):
        """Get the index for the given path."""
        iter = self._model.get_iter(path)
        return self._model.get_value(iter, 0)

    def _rowActivated(self, flightList, path, column):
        """Called when a row is selected."""
        self.emit("row-activated", self._getIndexForPath(path))

    def _buttonPressEvent(self, widget, event):
        """Called when a mouse button is pressed or released."""
        if event.type!=EVENT_BUTTON_PRESS or event.button!=3 or \
           self._popupMenuProducer is None:
            return

        (path, _, _, _) = self._view.get_path_at_pos(int(event.x),
                                                     int(event.y))
        selection = self._view.get_selection()
        selection.unselect_all()
        selection.select_path(path)

        if self._popupMenu is None:
            self._popupMenu = self._popupMenuProducer()
        menu = self._popupMenu
        if pygobject:
            menu.popup(None, None, None, None, event.button, event.time)
        else:
            menu.popup(None, None, None, event.button, event.time)

    def _selectionChanged(self, selection):
        """Called when the selection has changed."""
        self.emit("selection-changed", self.selectedIndexes)

#-------------------------------------------------------------------------------

gobject.signal_new("row-activated", FlightList, gobject.SIGNAL_RUN_FIRST,
                   None, (int,))

gobject.signal_new("selection-changed", FlightList, gobject.SIGNAL_RUN_FIRST,
                   None, (object,))

#-----------------------------------------------------------------------------

class PendingFlightsFrame(gtk.Frame):
    """A frame for a list of pending (reported or rejected) flights.

    It contains the list and the buttons available."""
    @staticmethod
    def getAircraft(tailNumber, bookedFlight):
        """Get the aircraft from the given booked flight.

        This is the tail number followed by the ICAO code of the aircraft's
        type."""
        return tailNumber + \
            " (" + const.icaoCodes[bookedFlight.aircraftType] + ")"

    def _getAcft(tailNumber, bookedFlight):
        return PendingFlightsFrame.getAircraft(tailNumber, bookedFlight)

    columnDescriptors = [
        ColumnDescriptor("callsign", xstr("flightsel_no")),
        ColumnDescriptor("departureTime", xstr("flightsel_deptime"),
                         sortable = True, defaultSortable = True),
        ColumnDescriptor("departureICAO", xstr("flightsel_from"),
                         sortable = True),
        ColumnDescriptor("arrivalICAO", xstr("flightsel_to"),
                         sortable = True),
        ColumnDescriptor("tailNumber", xstr("pendflt_acft"),
                         convertFn = _getAcft)
    ]

    def __init__(self, which, wizard, window, pirepEditable = False):
        """Construct the frame with the given title."""
        super(PendingFlightsFrame, self).__init__(xstr("pendflt_title_" + which))

        self._which = which
        self._wizard = wizard
        self._window = window
        self._pirepEditable = pirepEditable

        alignment = gtk.Alignment(xscale = 1.0, yscale = 1.0)
        alignment.set_padding(padding_top = 2, padding_bottom = 8,
                              padding_left = 4, padding_right = 4)

        hbox = gtk.HBox()

        self._flights = []
        self._flightList = FlightList(columnDescriptors =
                                      PendingFlightsFrame.columnDescriptors,
                                      widthRequest = 500, multiSelection = True)
        self._flightList.connect("selection-changed", self._selectionChanged)

        hbox.pack_start(self._flightList, True, True, 4)

        buttonBox = gtk.VBox()

        self._editButton = gtk.Button(xstr("pendflt_" +
                                           ("edit" if pirepEditable else
                                            "view") + "_" + which))
        self._editButton.set_sensitive(False)
        self._editButton.connect("clicked", self._editClicked)
        buttonBox.pack_start(self._editButton, False, False, 2)

        self._reflyButton = gtk.Button(xstr("pendflt_refly_" + which))
        self._reflyButton.set_sensitive(False)
        self._reflyButton.connect("clicked", self._reflyClicked)
        buttonBox.pack_start(self._reflyButton, False, False, 2)

        self._deleteButton = gtk.Button(xstr("pendflt_delete_" + which))
        self._deleteButton.set_sensitive(False)
        self._deleteButton.connect("clicked", self._deleteClicked)
        buttonBox.pack_start(self._deleteButton, False, False, 2)

        hbox.pack_start(buttonBox, False, False, 4)

        alignment.add(hbox)
        self.add(alignment)

    @property
    def hasFlights(self):
        """Determine if there are any flights in the list."""
        return self._flightList.hasFlights

    def clear(self):
        """Clear the lists."""
        self._flights = []
        self._flightList.clear()

    def addFlight(self, flight):
        """Add a flight to the list."""
        self._flights.append(flight)
        self._flightList.addFlight(flight)

    def _selectionChanged(self, flightList, selectedIndexes):
        """Called when the selection in the list has changed."""
        self._editButton.set_sensitive(len(selectedIndexes)==1)
        self._reflyButton.set_sensitive(len(selectedIndexes)>0)
        self._deleteButton.set_sensitive(len(selectedIndexes)>0)

    def _editClicked(self, button):
        """Called when the Edit button is clicked."""
        gui = self._wizard.gui
        gui.beginBusy(xstr("pendflt_pirep_busy"))
        self.set_sensitive(False)

        indexes = self._flightList.selectedIndexes
        assert(len(indexes)==1)

        flightID = self._flights[indexes[0]].id
        gui.webHandler.getPIREP(self._pirepResultCallback, flightID)

    def _pirepResultCallback(self, returned, result):
        """Called when the PIREP query result is available."""
        gobject.idle_add(self._handlePIREPResult, returned, result)

    def _handlePIREPResult(self, returned, result):
        """Handle the refly result."""

        self.set_sensitive(True)
        gui = self._wizard.gui
        gui.endBusy()

        if returned:
            if self._pirepEditable:
                gui.editPIREP(result.pirep)
            else:
                gui.viewMessagedPIREP(result.pirep)

    def _reflyClicked(self, button):
        """Called when the Refly button is clicked."""
        if askYesNo(xstr("pendflt_refly_question"), parent = self._window):
            gui = self._wizard.gui
            gui.beginBusy(xstr("pendflt_refly_busy"))
            self.set_sensitive(False)

            flightIDs = [self._flights[i].id
                        for i in self._flightList.selectedIndexes]
            gui.webHandler.reflyFlights(self._reflyResultCallback, flightIDs)

    def _reflyResultCallback(self, returned, result):
        """Called when the refly result is available."""
        gobject.idle_add(self._handleReflyResult, returned, result)

    def _handleReflyResult(self, returned, result):
        """Handle the refly result."""

        self.set_sensitive(True)
        gui = self._wizard.gui
        gui.endBusy()

        print "PendingFlightsFrame._handleReflyResult", returned, result

        if returned:
            indexes = self._flightList.selectedIndexes

            flights = [self._flights[index] for index in indexes]

            self._flightList.removeFlights(indexes)
            for index in indexes[::-1]:
                del self._flights[index]

            for flight in flights:
                self._wizard.reflyFlight(flight)
            self._window.checkFlights()
        else:
            communicationErrorDialog()

    def _deleteClicked(self, button):
        """Called when the Delete button is clicked."""
        if askYesNo(xstr("flight_delete_question"), parent = self._window):
            gui = self._wizard.gui
            gui.beginBusy(xstr("pendflt_refly_busy"))
            self.set_sensitive(False)

            flightIDs = [self._flights[i].id
                        for i in self._flightList.selectedIndexes]
            gui.webHandler.deleteFlights(self._deleteResultCallback, flightIDs)

    def _deleteResultCallback(self, returned, result):
        """Called when the deletion result is available."""
        gobject.idle_add(self._handleDeleteResult, returned, result)

    def _handleDeleteResult(self, returned, result):
        """Handle the delete result."""

        self.set_sensitive(True)
        gui = self._wizard.gui
        gui.endBusy()

        print "PendingFlightsFrame._handleDeleteResult", returned, result

        if returned:
            indexes = self._flightList.selectedIndexes

            flights = [self._flights[index] for index in indexes]

            self._flightList.removeFlights(indexes)
            for index in indexes[::-1]:
                del self._flights[index]

            for flight in flights:
                self._wizard.deleteFlight(flight)
            self._window.checkFlights()
        else:
            communicationErrorDialog()

#-----------------------------------------------------------------------------

class PendingFlightsWindow(gtk.Window):
    """The window to display the lists of the pending (reported or rejected)
    flights."""
    def __init__(self, wizard):
        """Construct the window"""
        super(PendingFlightsWindow, self).__init__()

        gui = wizard.gui

        self.set_title(WINDOW_TITLE_BASE + " - " + xstr("pendflt_title"))
        self.set_size_request(-1, 450)
        self.set_transient_for(gui.mainWindow)
        self.set_modal(True)

        mainAlignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                      xscale = 1.0, yscale = 1.0)
        mainAlignment.set_padding(padding_top = 0, padding_bottom = 12,
                                  padding_left = 8, padding_right = 8)

        vbox = gtk.VBox()

        self._reportedFrame = PendingFlightsFrame("reported", wizard, self,
                                                  True)
        vbox.pack_start(self._reportedFrame, True, True, 2)

        self._rejectedFrame = PendingFlightsFrame("rejected", wizard, self)
        vbox.pack_start(self._rejectedFrame, True, True, 2)

        alignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)
        self._closeButton = gtk.Button(xstr("button_ok"))
        self._closeButton.connect("clicked", self._closeClicked)
        alignment.add(self._closeButton)
        vbox.pack_start(alignment, False, False, 2)

        mainAlignment.add(vbox)

        self.add(mainAlignment)

        self.connect("key-press-event", self._keyPressed)

    @property
    def hasFlights(self):
        """Determine if the window has any flights."""
        return self._reportedFrame.hasFlights or self._rejectedFrame.hasFlights

    def clear(self):
        """Clear the lists."""
        self._reportedFrame.clear()
        self._rejectedFrame.clear()

    def addReportedFlight(self, flight):
        """Add a reported flight."""
        self._reportedFrame.addFlight(flight)

    def addRejectedFlight(self, flight):
        """Add a rejected flight."""
        self._rejectedFrame.addFlight(flight)

    def checkFlights(self):
        """Check if there are any flights in any of the lists, and close the
        window if not."""
        if not self.hasFlights:
            self.emit("delete-event", None)

    def _closeClicked(self, button):
        """Called when the Close button is clicked.

        A 'delete-event' is emitted to close the window."""
        self.emit("delete-event", None)

    def _keyPressed(self, window, event):
        """Called when a key is pressed in the window.

        If the Escape key is pressed, 'delete-event' is emitted to close the
        window."""
        if gdk.keyval_name(event.keyval) == "Escape":
            self.emit("delete-event", None)
            return True

#-----------------------------------------------------------------------------

class AcceptedFlightsWindow(gtk.Window):
    """A window for a list of accepted flights."""
    def getFlightDuration(flightTimeStart, flight):
        """Get the flight duration for the given flight."""
        minutes = int(round((flight.flightTimeEnd - flightTimeStart)/60.0))
        return "%02d:%02d" % (minutes/60, minutes%60)

    columnDescriptors = [
        ColumnDescriptor("bookedFlight.callsign", xstr("flightsel_no")),
        ColumnDescriptor("bookedFlight.departureTime", xstr("flightsel_deptime"),
                         sortable = True, defaultSortable = True,
                         defaultDescending = True),
        ColumnDescriptor("bookedFlight.departureICAO", xstr("flightsel_from"),
                         sortable = True),
        ColumnDescriptor("bookedFlight.arrivalICAO", xstr("flightsel_to"),
                         sortable = True),
        ColumnDescriptor("bookedFlight.tailNumber", xstr("pendflt_acft"),
                         convertFn = lambda value, flight:
                         PendingFlightsFrame.getAircraft(value,
                                                         flight.bookedFlight)),
        ColumnDescriptor("flightTimeStart", xstr("acceptedflt_flight_duration"),
                         convertFn = getFlightDuration, sortable = True,
                         extraColumnAttributes =
                             { "alignment": 0.5 } ),
        ColumnDescriptor("numPassengers", xstr("acceptedflt_num_pax"),
                         type = int, sortable = True,
                         extraColumnAttributes =
                             { "alignment": 1.0 } ),
        ColumnDescriptor("fuelUsed", xstr("acceptedflt_fuel"),
                         type = int, sortable = True,
                         extraColumnAttributes =
                             { "alignment": 1.0 } ),
        ColumnDescriptor("rating", xstr("acceptedflt_rating"),
                         type = float, sortable = True,
                         extraColumnAttributes =
                             { "alignment": 1.0 },
                         cellDataFn = lambda col, cell, model, iter:
                             cell.set_property("text",
                                               "%.0f" %
                                               (model.get(iter, 9)[0],)))
    ]

    def __init__(self, gui):
        """Construct the window."""
        super(AcceptedFlightsWindow, self).__init__()

        self._gui = gui

        self.set_title(WINDOW_TITLE_BASE + " - " + xstr("acceptedflt_title"))
        self.set_size_request(-1, 700)
        self.set_transient_for(gui.mainWindow)

        alignment = gtk.Alignment(xscale = 1.0, yscale = 1.0)
        alignment.set_padding(padding_top = 2, padding_bottom = 8,
                              padding_left = 4, padding_right = 4)

        vbox = gtk.VBox()

        hbox = gtk.HBox()
        vbox.pack_start(hbox, True, True, 4)

        self._flights = []
        self._flightList = FlightList(columnDescriptors =
                                      AcceptedFlightsWindow.columnDescriptors,
                                      widthRequest = 750,
                                      multiSelection = False)
        self._flightList.connect("selection-changed", self._selectionChanged)

        hbox.pack_start(self._flightList, True, True, 4)

        buttonBox = gtk.VBox()

        self._refreshButton = gtk.Button(xstr("acceptedflt_refresh"))
        self._refreshButton.set_sensitive(True)
        self._refreshButton.connect("clicked", self._refreshClicked)
        buttonBox.pack_start(self._refreshButton, False, False, 2)

        filler = gtk.Alignment(xalign = 0.0, yalign = 0.0,
                               xscale = 1.0, yscale = 1.0)
        filler.set_size_request(-1, 4)
        buttonBox.pack_start(filler, False, False, 0)

        self._viewButton = gtk.Button(xstr("acceptedflt_view"))
        self._viewButton.set_sensitive(False)
        self._viewButton.connect("clicked", self._viewClicked)
        buttonBox.pack_start(self._viewButton, False, False, 2)

        hbox.pack_start(buttonBox, False, False, 4)

        buttonAlignment = gtk.Alignment(xscale = 0.0, yscale = 0.0,
                                        xalign = 0.5, yalign = 0.5)

        self._closeButton =  gtk.Button(xstr("button_ok"))
        self._closeButton.connect("clicked", self._closeClicked)

        buttonAlignment.add(self._closeButton)
        vbox.pack_start(buttonAlignment, False, False, 2)

        alignment.add(vbox)

        self.add(alignment)

        self.connect("key-press-event", self._keyPressed)

    @property
    def hasFlights(self):
        """Determine if there are any flights that we know of."""
        return len(self._flights)>0

    def clear(self):
        """Clear the flight list."""
        self._flights = []
        self._flightList.clear()

    def addFlight(self, flight):
        """Add the given flight."""
        self._flights.append(flight)
        self._flightList.addFlight(flight)

    def _selectionChanged(self, flightList, selectedIndexes):
        """Called when the selection has changed."""
        self._viewButton.set_sensitive(len(selectedIndexes)==1)

    def _refreshClicked(self, button):
        """Called when the refresh button has been clicked."""
        self.clear()
        self._gui.showFlights(None)

    def _viewClicked(self, button):
        """Called when the view button has been clicked."""
        gui = self._gui
        gui.beginBusy(xstr("pendflt_pirep_busy"))
        self.set_sensitive(False)

        indexes = self._flightList.selectedIndexes
        assert(len(indexes)==1)

        flightID = self._flights[indexes[0]].bookedFlight.id
        gui.webHandler.getPIREP(self._pirepResultCallback, flightID)

    def _pirepResultCallback(self, returned, result):
        """Called when the PIREP query result is available."""
        gobject.idle_add(self._handlePIREPResult, returned, result)

    def _handlePIREPResult(self, returned, result):
        """Handle the refly result."""
        self.set_sensitive(True)
        gui = self._gui
        gui.endBusy()

        if returned:
            gui.viewMessagedPIREP(result.pirep)

    def _closeClicked(self, button):
        """Called when the Close button is clicked.

        A 'delete-event' is emitted to close the window."""
        self.emit("delete-event", None)

    def _keyPressed(self, window, event):
        """Called when a key is pressed in the window.

        If the Escape key is pressed, 'delete-event' is emitted to close the
        window."""
        if gdk.keyval_name(event.keyval) == "Escape":
            self.emit("delete-event", None)
            return True

#-----------------------------------------------------------------------------
