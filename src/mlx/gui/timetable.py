# Module for handling the time table and booking flights

#-----------------------------------------------------------------------------

from mlx.gui.common import *
from flightlist import ColumnDescriptor

import mlx.const as const

import datetime

#-----------------------------------------------------------------------------

class Timetable(gtk.Alignment):
    """The widget for the time table."""
    def _getVIPRenderer():
        """Get the renderer for the VIP column."""
        renderer = gtk.CellRendererToggle()
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
        ColumnDescriptor("spec", xstr("timetable_vip"), type = bool,
                         renderer = _getVIPRenderer(),
                         sortable = True,
                         convertFn = lambda spec, flight: spec==1)
    ]

    @staticmethod
    def isFlightSelected(flight, regularEnabled, vipEnabled, aircraftTypes):
        """Determine if the given flight is selected by the given
        filtering conditions."""
        return ((regularEnabled and flight.spec==0) or \
                (vipEnabled and flight.spec==1)) and \
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

        self._model = gtk.ListStore(*types)
        if defaultSortableIndex is not None:
            sortOrder = SORT_DESCENDING \
              if self._columnDescriptors[defaultSortableIndex-1]._defaultDescending \
              else SORT_ASCENDING
            self._model.set_sort_column_id(defaultSortableIndex, sortOrder)
        self._view = gtk.TreeView(self._model)

        flightPairIndexColumn = gtk.TreeViewColumn()
        flightPairIndexColumn.set_visible(False)
        self._view.append_column(flightPairIndexColumn)

        index = 1
        for columnDescriptor in self._columnDescriptors:
            column = columnDescriptor.getViewColumn(index)
            self._view.append_column(column)
            index += 1

        self._view.connect("row-activated", self._rowActivated)
        self._view.connect("button-press-event", self._buttonPressEvent)

        selection = self._view.get_selection()
        selection.connect("changed", self._selectionChanged)

        scrolledWindow = gtk.ScrolledWindow()
        scrolledWindow.add(self._view)
        scrolledWindow.set_size_request(800, -1)

        # FIXME: these should be constants in common.py
        scrolledWindow.set_policy(gtk.PolicyType.AUTOMATIC if pygobject
                                  else gtk.POLICY_AUTOMATIC,
                                  gtk.PolicyType.AUTOMATIC if pygobject
                                  else gtk.POLICY_AUTOMATIC)
        scrolledWindow.set_shadow_type(gtk.ShadowType.IN if pygobject
                                       else gtk.SHADOW_IN)

        super(Timetable, self).__init__(xalign = 0.5, yalign = 0.0,
                                        xscale = 0.0, yscale = 1.0)
        self.add(scrolledWindow)

        self._flightPairs = []

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

    def _rowActivated(self, flightList, path, column):
        """Called when a row is selected."""
        print "_rowActivated"

    def _buttonPressEvent(self, widget, event):
        """Called when a mouse button is pressed or released."""
        print "_buttonPressEvent", event

    def _selectionChanged(self, selection):
        """Called when the selection has changed."""
        print "_selectionChanged"

#-----------------------------------------------------------------------------

class CalendarWindow(gtk.Window):
    """A window for a calendar."""
    def __init__(self):
        """Construct the window."""
        super(CalendarWindow, self).__init__()

        self.set_decorated(False)
        self.set_modal(True)
        self.connect("key-press-event", self._keyPressed)

        mainAlignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                      xscale = 1.0, yscale = 1.0)
        #mainAlignment.set_padding(padding_top = 0, padding_bottom = 12,
        #                              padding_left = 8, padding_right = 8)

        self._calendar = gtk.Calendar()
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
        keyName = gdk.keyval_name(event.keyval)
        if keyName =="Escape":
            self.emit("delete-event", None)
            return True
        elif keyName =="Return":
            self.emit("date-selected")
            return True

gobject.signal_new("date-selected", CalendarWindow, gobject.SIGNAL_RUN_FIRST,
                   None, ())

#-----------------------------------------------------------------------------

class TimetableWindow(gtk.Window):
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

        mainAlignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                      xscale = 1.0, yscale = 1.0)
        mainAlignment.set_padding(padding_top = 0, padding_bottom = 12,
                                  padding_left = 8, padding_right = 8)

        vbox = gtk.VBox()

        filterAlignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                        xscale = 1.0, yscale = 1.0)

        filterFrame = gtk.Frame(xstr("timetable_filter"))

        filterVBox = gtk.VBox()

        topAlignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                     xscale = 0.0, yscale = 0.0)
        topHBox = gtk.HBox()

        label = gtk.Label(xstr("timetable_flightdate"))
        label.set_use_underline(True)
        topHBox.pack_start(label, False, False, 4)

        self._flightDate = gtk.Button()
        self._flightDate.connect("clicked", self._flightDateClicked)
        self._flightDate.set_tooltip_text(xstr("timetable_flightdate_tooltip"))
        label.set_mnemonic_widget(self._flightDate)
        topHBox.pack_start(self._flightDate, False, False, 4)

        filler = gtk.Alignment()
        filler.set_size_request(48, 2)
        topHBox.pack_start(filler, False, True, 0)

        self._regularFlights = gtk.CheckButton(xstr("timetable_show_regular"))
        self._regularFlights.set_use_underline(True)
        self._regularFlights.set_tooltip_text(xstr("timetable_show_regular_tooltip"))
        self._regularFlights.set_active(True)
        self._regularFlights.connect("toggled", self._filterChanged)
        topHBox.pack_start(self._regularFlights, False, False, 8)

        self._vipFlights = gtk.CheckButton(xstr("timetable_show_vip"))
        self._vipFlights.set_use_underline(True)
        self._vipFlights.set_tooltip_text(xstr("timetable_show_vip_tooltip"))
        self._vipFlights.set_active(True)
        self._vipFlights.connect("toggled", self._filterChanged)
        topHBox.pack_start(self._vipFlights, False, False, 8)

        topAlignment.add(topHBox)

        filterVBox.pack_start(topAlignment, False, False, 4)

        separator = gtk.HSeparator()
        filterVBox.pack_start(separator, False, False, 4)

        typeAlignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                      xscale = 0.0, yscale = 0.0)

        numColumns = 4
        numRows = (len(TimetableWindow.typeFamilies)+numColumns-1)/numColumns

        typeTable = gtk.Table(numRows, numColumns)
        typeTable.set_col_spacings(8)
        row = 0
        column = 0
        self._typeFamilyButtons = {}
        for typeFamily in TimetableWindow.typeFamilies:
            checkButton = gtk.CheckButton(aircraftFamilyNames[typeFamily])
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

        self._timetable = Timetable()
        vbox.pack_start(self._timetable, True, True, 2)

        alignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)
        self._closeButton = gtk.Button(xstr("button_ok"))
        self._closeButton.connect("clicked", self._closeClicked)
        alignment.add(self._closeButton)
        vbox.pack_start(alignment, False, False, 2)

        mainAlignment.add(vbox)

        self._calendarWindow = calendarWindow = CalendarWindow()
        calendarWindow.set_transient_for(self)
        calendarWindow.connect("delete-event", self._calendarWindowDeleted)
        calendarWindow.connect("date-selected", self._calendarWindowDateSelected)

        self.add(mainAlignment)

        self.setDate(datetime.date.today())

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

        for (typeFamily, checkButton) in self._typeFamilyButtons.iteritems():
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
        self._calendarWindow.set_position(gtk.WIN_POS_MOUSE)
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
        if gdk.keyval_name(event.keyval) == "Escape":
            self.emit("delete-event", None)
            return True

    def _updateList(self):
        """Update the timetable list."""
        aircraftTypes = []
        for (aircraftFamily, button) in self._typeFamilyButtons.iteritems():
            if button.get_active():
                aircraftTypes += const.aircraftFamily2Types[aircraftFamily]

        self._timetable.updateList(self.isRegularEnabled,
                                   self.isVIPEnabled,
                                   aircraftTypes)
