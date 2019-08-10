# Module for handling the time table and booking flights

#-----------------------------------------------------------------------------

from mlx.gui.common import *
from .flightlist import ColumnDescriptor
from mlx.rpc import ScheduledFlight

import mlx.const as const

import datetime
import random

#-----------------------------------------------------------------------------

class Timetable(Gtk.Alignment):
    """The widget for the time table."""
    def _getVIPRenderer():
        """Get the renderer for the VIP column."""
        renderer = Gtk.CellRendererToggle()
        renderer.set_activatable(True)
        return renderer

    defaultColumnDescriptors = [
        ColumnDescriptor("callsign", xstr("timetable_no"),
                         sortable = True, defaultSortable = True),
        ColumnDescriptor("aircraftType", xstr("timetable_type"),
                         sortable = True,
                         convertFn = lambda aircraftType, flight:
                             aircraftNames[aircraftType]),
        ColumnDescriptor("departureICAO", xstr("timetable_from"),
                         sortable = True),
        ColumnDescriptor("arrivalICAO", xstr("timetable_to"), sortable = True),
        ColumnDescriptor("departureTime", xstr("timetable_dep"),
                         sortable = True),
        ColumnDescriptor("arrivalTime", xstr("timetable_arr"), sortable = True),
        ColumnDescriptor("duration", xstr("timetable_duration"),
                         sortable = True,
                         convertFn = lambda duration, flight:
                         "%02d:%02d" % (duration/3600,
                                        (duration%3600)/60)),
        ColumnDescriptor("type", xstr("timetable_vip"), type = bool,
                         renderer = _getVIPRenderer(),
                         sortable = True,
                         convertFn = lambda type, flight:
                             type==ScheduledFlight.TYPE_VIP)
    ]

    columnOrdering = ["callsign", "aircraftType",
                      "date", "departureTime", "arrivalTime",
                      "departureICAO", "arrivalICAO", "duration", "type"]

    @staticmethod
    def isFlightSelected(flight, regularEnabled, vipEnabled, aircraftTypes):
        """Determine if the given flight is selected by the given
        filtering conditions."""
        return ((regularEnabled and flight.type==ScheduledFlight.TYPE_NORMAL) or \
                (vipEnabled and flight.type==ScheduledFlight.TYPE_VIP)) and \
               flight.aircraftType in aircraftTypes

    def __init__(self, columnDescriptors = defaultColumnDescriptors,
                 popupMenuProducer = None):
        """Construct the time table."""
        # FIXME: this is very similar to flightlist.FlightList
        self._columnDescriptors = columnDescriptors
        self._popupMenuProducer = popupMenuProducer
        self._popupMenu = None

        types = [int]
        defaultSortableIndex = None
        for columnDescriptor in self._columnDescriptors:
            if columnDescriptor.defaultSortable:
                defaultSortableIndex = len(types)
            columnDescriptor.appendType(types)

        self._model = Gtk.ListStore(*types)
        if defaultSortableIndex is not None:
            sortOrder = Gtk.SortType.DESCENDING \
              if self._columnDescriptors[defaultSortableIndex-1]._defaultDescending \
              else Gtk.SortType.ASCENDING
            self._model.set_sort_column_id(defaultSortableIndex, sortOrder)
        self._view = Gtk.TreeView(self._model)

        self._view.connect("motion-notify-event", self._updateTooltip)

        flightPairIndexColumn = Gtk.TreeViewColumn()
        flightPairIndexColumn.set_visible(False)
        self._view.append_column(flightPairIndexColumn)

        index = 1
        for columnDescriptor in self._columnDescriptors:
            column = columnDescriptor.getViewColumn(index)
            self._view.append_column(column)
            self._model.set_sort_func(index, self._compareFlights,
                                      columnDescriptor.attribute)
            index += 1

        self._view.connect("row-activated", self._rowActivated)
        self._view.connect("button-press-event", self._buttonPressEvent)

        selection = self._view.get_selection()
        selection.connect("changed", self._selectionChanged)

        scrolledWindow = Gtk.ScrolledWindow()
        scrolledWindow.add(self._view)
        scrolledWindow.set_size_request(800, -1)

        # FIXME: these should be constants in common.py
        scrolledWindow.set_policy(Gtk.PolicyType.AUTOMATIC,
                                  Gtk.PolicyType.AUTOMATIC)
        scrolledWindow.set_shadow_type(Gtk.ShadowType.IN)

        super(Timetable, self).__init__(xalign = 0.5, yalign = 0.0,
                                        xscale = 0.0, yscale = 1.0)
        self.add(scrolledWindow)

        self._flightPairs = []

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
    def hasFlightPairs(self):
        """Determine if the timetable contains any flights."""
        return len(self._flightPairs)>0

    def clear(self):
        """Clear the flight pairs."""
        self._model.clear()
        self._flightPairs = []

    def setFlightPairs(self, flightPairs):
        """Setup the table contents from the given list of
        rpc.ScheduledFlightPair objects."""
        self.clear()

        self._flightPairs = flightPairs

    def getFlightPair(self, index):
        """Get the flight pair with the given index."""
        return self._flightPairs[index]

    def updateList(self, regularEnabled, vipEnabled, types):
        """Update the actual list according to the given filter values."""
        index = 0
        self._model.clear()
        for flightPair in self._flightPairs:
            flight = flightPair.flight0
            if Timetable.isFlightSelected(flight, regularEnabled, vipEnabled,
                                          types):
                values = [index]
                for columnDescriptor in self._columnDescriptors:
                    values.append(columnDescriptor.getValueFrom(flight))
                self._model.append(values)
            index += 1

    def _getIndexForPath(self, path):
        """Get the index for the given path."""
        iter = self._model.get_iter(path)
        return self._model.get_value(iter, 0)

    def _rowActivated(self, flightList, path, column):
        """Called when a row is selected."""
        self.emit("row-activated", self._getIndexForPath(path))

    def _buttonPressEvent(self, widget, event):
        """Called when a mouse button is pressed or released."""
        if event.type!=Gdk.EventType.BUTTON_PRESS or event.button!=3 or \
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
        menu.popup(None, None, None, None, event.button, event.time)

    def _selectionChanged(self, selection):
        """Called when the selection has changed."""
        self.emit("selection-changed", self.selectedIndexes)

    def _compareFlights(self, model, iter1, iter2, mainColumn):
        """Compare the flights at the given iterators according to the given
        main column."""
        index1 = self._model.get_value(iter1, 0)
        index2 = self._model.get_value(iter2, 0)

        flightPair1 = self._flightPairs[index1]
        flightPair2 = self._flightPairs[index2]

        result = flightPair1.compareBy(flightPair2, mainColumn)
        if result==0:
            for column in Timetable.columnOrdering:
                if column!=mainColumn:
                    result = flightPair1.compareBy(flightPair2, column)
                    if result!=0:
                        break
        return result

    def _updateTooltip(self, widget, event):
        """Update the tooltip for the position of the given event."""
        try:
            result = widget.get_path_at_pos( int(event.x), int(event.y))
            if result is None:
                widget.set_tooltip_text("")
            else:
                (path, col, x, y) = result
                index = self._getIndexForPath(path)

                flight = self._flightPairs[index].flight0
                comment = flight.comment
                date = flight.date

                if comment or date!=const.defaultDate:
                    text = ""
                    if comment:
                        text = comment
                    if date!=const.defaultDate:
                        if text:
                            text += "; "
                        text += date.strftime("%Y-%m-%d")

                    widget.set_tooltip_text(text)
                else:
                    widget.set_tooltip_text("")
        except Exception as e:
            print(e)
            widget.set_tooltip_text("")

#-----------------------------------------------------------------------------

GObject.signal_new("row-activated", Timetable, GObject.SIGNAL_RUN_FIRST,
                   None, (int,))

GObject.signal_new("selection-changed", Timetable, GObject.SIGNAL_RUN_FIRST,
                   None, (object,))

#-----------------------------------------------------------------------------

class CalendarWindow(Gtk.Window):
    """A window for a calendar."""
    def __init__(self):
        """Construct the window."""
        super(CalendarWindow, self).__init__()

        self.set_decorated(False)
        self.set_modal(True)
        self.connect("key-press-event", self._keyPressed)

        mainAlignment = Gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                      xscale = 1.0, yscale = 1.0)
        #mainAlignment.set_padding(padding_top = 0, padding_bottom = 12,
        #                              padding_left = 8, padding_right = 8)

        self._calendar = Gtk.Calendar()
        self._calendar.connect("day-selected-double-click", self._daySelectedDoubleClick)
        mainAlignment.add(self._calendar)

        self.add(mainAlignment)

    def setDate(self, date):
        """Set the current date to the given one."""
        self._calendar.select_month(date.month-1, date.year)
        self._calendar.select_day(date.day)

    def getDate(self):
        """Get the currently selected date."""
        (year, monthM1, day) = self._calendar.get_date()
        return datetime.date(year, monthM1+1, day)

    def _daySelectedDoubleClick(self, calendar):
        """Called when a date is double clicked."""
        self.emit("date-selected")

    def _keyPressed(self, window, event):
        """Called when a key is pressed in the window.

        If the Escape key is pressed, 'delete-event' is emitted to close the
        window."""
        keyName = Gdk.keyval_name(event.keyval)
        if keyName =="Escape":
            self.emit("delete-event", None)
            return True
        elif keyName =="Return":
            self.emit("date-selected")
            return True

GObject.signal_new("date-selected", CalendarWindow, GObject.SIGNAL_RUN_FIRST,
                   None, ())

#-----------------------------------------------------------------------------

class BookDialog(Gtk.Dialog):
    """The dialog box to select additional data for a booking."""
    def __init__(self, timetableWindow, flightPair, planes):
        """Construct the dialog box."""
        super(BookDialog, self).__init__(title = WINDOW_TITLE_BASE +
                                         " - " +
                                         xstr("timetable_book_title"),
                                         parent = timetableWindow)
        contentArea = self.get_content_area()

        frame = Gtk.Frame(label = xstr("timetable_book_frame_title"))
        frame.set_size_request(600, -1)

        mainAlignment = Gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                      xscale = 0.0, yscale = 0.0)
        mainAlignment.set_padding(padding_top = 16, padding_bottom = 12,
                                  padding_left = 8, padding_right = 8)

        table = Gtk.Table(6, 2)
        table.set_row_spacings(8)
        table.set_col_spacings(16)

        row = 0
        label = Gtk.Label()
        label.set_markup(xstr("timetable_book_callsign"))
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, row, row + 1)

        text = flightPair.flight0.callsign
        if flightPair.flight1 is not None:
            text += " / " + flightPair.flight1.callsign
        label = Gtk.Label(text)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 1, 2, row, row + 1)

        row += 1

        label = Gtk.Label()
        label.set_markup(xstr("timetable_book_from_to"))
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, row, row + 1)

        text = flightPair.flight0.departureICAO + " - " + \
               flightPair.flight0.arrivalICAO
        if flightPair.flight1 is not None:
            text += " - " + flightPair.flight1.arrivalICAO
        label = Gtk.Label(text)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 1, 2, row, row + 1)

        row += 1

        if flightPair.flight0.type==ScheduledFlight.TYPE_VIP and \
           flightPair.flight0.date!=const.defaultDate:
            label = Gtk.Label()
            label.set_markup(xstr("timetable_book_flightDate"))
            label.set_use_underline(True)
            label.set_alignment(0.0, 0.5)
            table.attach(label, 0, 1, row, row + 1)

            self._flightDate = Gtk.Button()
            self._flightDate.connect("clicked", self._flightDateClicked)
            self._flightDate.set_tooltip_text(xstr("timetable_book_flightDate_tooltip"))
            label.set_mnemonic_widget(self._flightDate)

            table.attach(self._flightDate, 1, 2, row, row + 1)

            self._calendarWindow = calendarWindow = CalendarWindow()
            calendarWindow.set_transient_for(self)
            calendarWindow.connect("delete-event", self._calendarWindowDeleted)
            calendarWindow.connect("date-selected", self._calendarWindowDateSelected)

            self._setDate(flightPair.flight0.date)

            row += 1
        else:
            self._flightDate = None
            self._calendarWindow = None

        label = Gtk.Label()
        label.set_markup(xstr("timetable_book_dep_arr"))
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, row, row + 1)

        text = str(flightPair.flight0.departureTime) + " - " + \
               str(flightPair.flight0.arrivalTime)
        if flightPair.flight1 is not None:
            text += " / " + str(flightPair.flight1.departureTime) + " - " + \
                    str(flightPair.flight1.arrivalTime)
        label = Gtk.Label(text)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 1, 2, row, row + 1)

        row += 1

        label = Gtk.Label()
        label.set_markup(xstr("timetable_book_duration"))
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, row, row + 1)


        duration = flightPair.flight0.duration
        text = "%02d:%02d" % (duration/3600, (duration%3600)/60)
        if flightPair.flight1 is not None:
            duration = flightPair.flight0.duration
            text += " / %02d:%02d" % (duration/3600, (duration%3600)/60)
        label = Gtk.Label(text)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 1, 2, row, row + 1)

        row += 2

        label = Gtk.Label()
        label.set_markup(xstr("timetable_book_tailNumber"))
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, row, row + 1)

        self._planes = planes
        tailNumbersModel = Gtk.ListStore(str)
        for plane in planes:
            tailNumbersModel.append((plane.tailNumber,))

        self._tailNumber = Gtk.ComboBox(model = tailNumbersModel)
        renderer = Gtk.CellRendererText()
        self._tailNumber.pack_start(renderer, True)
        self._tailNumber.add_attribute(renderer, "text", 0)
        self._tailNumber.set_tooltip_text(xstr("timetable_book_tailNumber_tooltip"))
        self._tailNumber.set_active(random.randint(0, len(planes)-1))

        table.attach(self._tailNumber, 1, 2, row, row + 1)

        mainAlignment.add(table)

        frame.add(mainAlignment)
        contentArea.pack_start(frame, True, True, 4)

        self.add_button(xstr("button_cancel"), Gtk.ResponseType.CANCEL)

        self._okButton = self.add_button(xstr("button_book"), Gtk.ResponseType.OK)
        self._okButton.set_use_underline(True)
        self._okButton.set_can_default(True)

    @property
    def plane(self):
        """Get the currently selected plane."""
        return self._planes[self._tailNumber.get_active()]

    @property
    def date(self):
        """Get the flight date, if selected."""
        return None if self._calendarWindow is None \
          else self._calendarWindow.getDate()

    def _setDate(self, date):
        """Set the date to the given one."""
        self._flightDate.set_label(date.strftime("%Y-%m-%d"))
        self._calendarWindow.setDate(date)

    def _flightDateClicked(self, button):
        """Called when the flight date button is clicked."""
        self._calendarWindow.set_position(Gtk.WindowPosition.MOUSE)
        self.set_focus(self._calendarWindow)
        self._calendarWindow.show_all()

    def _calendarWindowDeleted(self, window, event):
        """Called when the flight date window is deleted."""
        self._calendarWindow.hide()

    def _calendarWindowDateSelected(self, window):
        """Called when the flight date window is deleted."""
        self._calendarWindow.hide()
        date = window.getDate()
        self._flightDate.set_label(date.strftime("%Y-%m-%d"))

#-----------------------------------------------------------------------------

class TimetableWindow(Gtk.Window):
    """The window to display the timetable."""
    typeFamilies = [
        const.AIRCRAFT_FAMILY_B737NG,
        const.AIRCRAFT_FAMILY_DH8D,
        const.AIRCRAFT_FAMILY_B767,

        const.AIRCRAFT_FAMILY_B737CL,
        const.AIRCRAFT_FAMILY_CRJ2,
        const.AIRCRAFT_FAMILY_F70,

        const.AIRCRAFT_FAMILY_T134,
        const.AIRCRAFT_FAMILY_T154
        ]

    def __init__(self, gui):
        super(TimetableWindow, self).__init__()

        self._gui = gui
        self.set_title(WINDOW_TITLE_BASE + " - " + xstr("timetable_title"))
        self.set_size_request(-1, 600)
        self.set_transient_for(gui.mainWindow)
        self.set_modal(True)
        self.connect("key-press-event", self._keyPressed)

        mainAlignment = Gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                      xscale = 1.0, yscale = 1.0)
        mainAlignment.set_padding(padding_top = 0, padding_bottom = 12,
                                  padding_left = 8, padding_right = 8)

        vbox = Gtk.VBox()

        filterAlignment = Gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                        xscale = 1.0, yscale = 1.0)

        filterFrame = Gtk.Frame()
        filterFrame.set_label(xstr("timetable_filter"))

        filterVBox = Gtk.VBox()

        topAlignment = Gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                     xscale = 0.0, yscale = 0.0)
        topHBox = Gtk.HBox()

        label = Gtk.Label(xstr("timetable_flightdate"))
        label.set_use_underline(True)
        topHBox.pack_start(label, False, False, 4)

        self._flightDate = Gtk.Button()
        self._flightDate.connect("clicked", self._flightDateClicked)
        self._flightDate.connect("clicked", self._flightDateClicked)
        self._flightDate.set_tooltip_text(xstr("timetable_flightdate_tooltip"))
        label.set_mnemonic_widget(self._flightDate)
        topHBox.pack_start(self._flightDate, False, False, 4)

        filler = Gtk.Alignment()
        filler.set_size_request(48, 2)
        topHBox.pack_start(filler, False, True, 0)

        self._regularFlights = Gtk.CheckButton(xstr("timetable_show_regular"))
        self._regularFlights.set_use_underline(True)
        self._regularFlights.set_tooltip_text(xstr("timetable_show_regular_tooltip"))
        self._regularFlights.set_active(True)
        self._regularFlights.connect("toggled", self._filterChanged)
        topHBox.pack_start(self._regularFlights, False, False, 8)

        self._vipFlights = Gtk.CheckButton(xstr("timetable_show_vip"))
        self._vipFlights.set_use_underline(True)
        self._vipFlights.set_tooltip_text(xstr("timetable_show_vip_tooltip"))
        self._vipFlights.set_active(True)
        self._vipFlights.connect("toggled", self._filterChanged)
        topHBox.pack_start(self._vipFlights, False, False, 8)

        topAlignment.add(topHBox)

        filterVBox.pack_start(topAlignment, False, False, 4)

        separator = Gtk.HSeparator()
        filterVBox.pack_start(separator, False, False, 4)

        typeAlignment = Gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                      xscale = 0.0, yscale = 0.0)

        numColumns = 4
        numRows = (len(TimetableWindow.typeFamilies)+numColumns-1)/numColumns

        typeTable = Gtk.Table(numRows, numColumns)
        typeTable.set_col_spacings(8)
        row = 0
        column = 0
        self._typeFamilyButtons = {}
        for typeFamily in TimetableWindow.typeFamilies:
            checkButton = Gtk.CheckButton(aircraftFamilyNames[typeFamily])
            checkButton.set_active(True)
            checkButton.connect("toggled", self._filterChanged)
            self._typeFamilyButtons[typeFamily] = checkButton

            typeTable.attach(checkButton, column, column + 1, row, row+1)

            column += 1
            if column>=numColumns:
                row += 1
                column = 0

        typeAlignment.add(typeTable)
        filterVBox.pack_start(typeAlignment, False, False, 4)

        filterFrame.add(filterVBox)

        filterAlignment.add(filterFrame)
        vbox.pack_start(filterAlignment, False, False, 2)

        self._timetable = Timetable(popupMenuProducer =
                                        self._createTimetablePopupMenu)
        self._timetable.connect("row-activated", self._rowActivated)
        self._timetable.connect("selection-changed", self._selectionChanged)
        vbox.pack_start(self._timetable, True, True, 2)

        alignment = Gtk.Alignment(xalign = 1.0, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)
        buttonBox = Gtk.HBox()

        self._bookButton = Gtk.Button(xstr("button_book"))
        self._bookButton.set_use_underline(True)
        self._bookButton.set_can_default(True)
        self._bookButton.connect("clicked", self._bookClicked)
        self._bookButton.set_sensitive(False)
        buttonBox.pack_start(self._bookButton, False, False, 4);

        self._closeButton = Gtk.Button(xstr("button_close"))
        self._closeButton.set_use_underline(True)
        self._closeButton.connect("clicked", self._closeClicked)
        buttonBox.pack_start(self._closeButton, False, False, 4);

        alignment.add(buttonBox)
        vbox.pack_start(alignment, False, False, 2)

        mainAlignment.add(vbox)

        self._calendarWindow = calendarWindow = CalendarWindow()
        calendarWindow.set_transient_for(self)
        calendarWindow.connect("delete-event", self._calendarWindowDeleted)
        calendarWindow.connect("date-selected", self._calendarWindowDateSelected)

        self.add(mainAlignment)

        self.setDate(datetime.date.today())

        self._flightPairToBook = None

    @property
    def hasFlightPairs(self):
        """Determine if there any flight pairs displayed in the window."""
        return self._timetable.hasFlightPairs

    @property
    def isRegularEnabled(self):
        """Determine if regular flights are enabled."""
        return self._regularFlights.get_active()!=0

    @property
    def isVIPEnabled(self):
        """Determine if VIP flights are enabled."""
        return self._vipFlights.get_active()!=0

    def setTypes(self, aircraftTypes):
        """Enable/disable the type family checkboxes according to the given
        list of types."""
        typeFamilies = set()
        for aircraftType in aircraftTypes:
            typeFamilies.add(const.aircraftType2Family(aircraftType))

        for (typeFamily, checkButton) in self._typeFamilyButtons.items():
            checkButton.set_sensitive(typeFamily in typeFamilies)

    def clear(self):
        """Clear all flight pairs."""
        self._timetable.clear()

    def setFlightPairs(self, flightPairs):
        """Set the flight pairs."""
        self._timetable.setFlightPairs(flightPairs)
        self._updateList()

    def setDate(self, date):
        """Set the date to the given one."""
        self._flightDate.set_label(date.strftime("%Y-%m-%d"))
        self._calendarWindow.setDate(date)

    def _closeClicked(self, button):
        """Called when the Close button is clicked.

        A 'delete-event' is emitted to close the window."""
        self.emit("delete-event", None)

    def _flightDateClicked(self, button):
        """Called when the flight date button is clicked."""
        self._calendarWindow.set_position(Gtk.WindowPosition.MOUSE)
        self.set_focus(self._calendarWindow)
        self._calendarWindow.show_all()

    def _calendarWindowDeleted(self, window, event):
        """Called when the flight date window is deleted."""
        self._calendarWindow.hide()

    def _calendarWindowDateSelected(self, window):
        """Called when the flight date window is deleted."""
        self._calendarWindow.hide()
        date = window.getDate()
        self._flightDate.set_label(date.strftime("%Y-%m-%d"))
        self._gui.updateTimeTable(date)

    def _filterChanged(self, checkButton):
        """Called when the filter conditions have changed."""
        self._updateList()

    def _keyPressed(self, window, event):
        """Called when a key is pressed in the window.

        If the Escape key is pressed, 'delete-event' is emitted to close the
        window."""
        if Gdk.keyval_name(event.keyval) == "Escape":
            self.emit("delete-event", None)
            return True

    def _updateList(self):
        """Update the timetable list."""
        aircraftTypes = []
        for (aircraftFamily, button) in self._typeFamilyButtons.items():
            if button.get_active():
                aircraftTypes += const.aircraftFamily2Types[aircraftFamily]

        self._timetable.updateList(self.isRegularEnabled,
                                   self.isVIPEnabled,
                                   aircraftTypes)

    def _bookClicked(self, button):
        """Called when the book button has been clicked."""
        self._book(self._timetable.getFlightPair(self._timetable.selectedIndexes[0]))

    def _rowActivated(self, timetable, index):
        """Called when a row has been activated (e.g. double-clicked) in the
        timetable."""
        self._book(self._timetable.getFlightPair(index))

    def _selectionChanged(self, timetable, indexes):
        """Called when the selection has changed.

        It sets the sensitivity of the book button based on whether a row is
        selected or not."""
        self._bookButton.set_sensitive(len(indexes)>0)

    def _book(self, flightPair):
        """Try to book the given flight pair."""
        self._flightPairToBook = flightPair
        self._gui.getFleet(callback = self._continueBook,
                           busyCallback = self._busyCallback)

    def _busyCallback(self, busy):
        """Called when the busy state has changed."""
        self.set_sensitive(not busy)

    def _continueBook(self, fleet):
        """Continue booking, once the fleet is available."""
        flightPair = self._flightPairToBook
        aircraftType = flightPair.flight0.aircraftType
        planes = [plane for plane in fleet
                  if plane.aircraftType == aircraftType]
        planes.sort(key = lambda p: p.tailNumber)

        dialog = BookDialog(self, flightPair, planes)
        dialog.show_all()
        result = dialog.run()
        dialog.hide()
        if result==Gtk.ResponseType.OK:
            flightIDs = [flightPair.flight0.id]
            if flightPair.flight1 is not None:
                flightIDs.append(flightPair.flight1.id)

            date = dialog.date
            if date is None:
                date = self._calendarWindow.getDate()

            self._gui.bookFlights(self._bookFlightsCallback,
                                  flightIDs, date, dialog.plane.tailNumber,
                                  busyCallback = self._busyCallback)

    def _bookFlightsCallback(self, returned, result):
        """Called when the booking has finished."""
        if returned:
            dialog = Gtk.MessageDialog(parent = self,
                                       type = Gtk.MessageType.INFO,
                                       message_format = xstr("bookflights_successful"))
            dialog.format_secondary_markup(xstr("bookflights_successful_secondary"))
        else:
            dialog = Gtk.MessageDialog(parent = self,
                                       type = Gtk.MessageType.ERROR,
                                       message_format = xstr("bookflights_failed"))
            dialog.format_secondary_markup(xstr("bookflights_failed_secondary"))

        dialog.add_button(xstr("button_ok"), Gtk.ResponseType.OK)
        dialog.set_title(WINDOW_TITLE_BASE)

        dialog.run()
        dialog.hide()

    def _createTimetablePopupMenu(self):
        """Get the popuop menu for the timetable."""
        menu = Gtk.Menu()

        menuItem = Gtk.MenuItem()
        menuItem.set_label(xstr("timetable_popup_book"))
        menuItem.set_use_underline(True)
        menuItem.connect("activate", self._popupBook)
        menuItem.show()

        menu.append(menuItem)

        return menu

    def _popupBook(self, menuItem):
        """Try to book the given flight pair."""
        index = self._timetable.selectedIndexes[0]
        self._book(self._timetable.getFlightPair(index))
