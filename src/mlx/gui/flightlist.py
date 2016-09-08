# A widget which is a generic list of flights

#-----------------------------------------------------------------------------

from mlx.gui.common import *

#-----------------------------------------------------------------------------

class ColumnDescriptor(object):
    """A descriptor for a column in the list."""
    def __init__(self, attribute, heading, type = str,
                 convertFn = None, renderer = gtk.CellRendererText(),
                 extraColumnAttributes = None):
        """Construct the descriptor."""
        self._attribute = attribute
        self._heading = heading
        self._type = type
        self._convertFn = convertFn
        self._renderer = renderer
        self._extraColumnAttributes = extraColumnAttributes

    def appendType(self, types):
        """Append the type of this column to the given list of types."""
        types.append(self._type)

    def getViewColumn(self, index):
        """Get a new column object for a tree view.

        @param index is the 0-based index of the column."""
        if self._extraColumnAttributes is None:
            if isinstance(self._renderer, gtk.CellRendererText):
                extraColumnAttributes = {"text" : index}
            else:
                extraColumnAttributes = {}
        else:
            extraColumnAttributes = self._extraColumnAttributes

        column = gtk.TreeViewColumn(self._heading, self._renderer,
                                    text = index)
        column.set_expand(True)

        return column

    def getValueFrom(self, flight):
        """Get the value from the given flight."""
        value = getattr(flight, self._attribute)
        return self._type(value) if self._convertFn is None \
            else self._convertFn(value)

#-----------------------------------------------------------------------------

class FlightList(gtk.Alignment):
    """Construct the flight list.

    This is a complete widget with a scroll window. It is alignment centered
    horizontally and expandable vertically."""
    def __init__(self, columnDescriptors, popupMenuProducer = None,
                 widthRequest = None):
        """Construct the flight list with the given column descriptors."""

        self._columnDescriptors = columnDescriptors
        self._popupMenuProducer = popupMenuProducer
        self._popupMenu = None

        types = []
        for columnDescriptor in self._columnDescriptors:
            columnDescriptor.appendType(types)

        self._model = gtk.ListStore(*types)
        self._view = gtk.TreeView(self._model)

        index = 0
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
    def selectedIndex(self):
        """Get the index of the selected entry, if any."""
        selection = self._view.get_selection()
        (model, iter) = selection.get_selected()
        if iter is None:
            return None
        else:
            path = model.get_path(iter)
            [index] = path.get_indices() if pygobject else path
            return index

    def clear(self):
        """Clear the model."""
        self._model.clear()

    def addFlight(self, flight):
        """Add the given booked flight."""
        values = []
        for columnDescriptor in self._columnDescriptors:
            values.append(columnDescriptor.getValueFrom(flight))
        self._model.append(values)

    def _rowActivated(self, flightList, path, column):
        """Called when a row is selected."""
        self.emit("row-activated", self.selectedIndex)

    def _buttonPressEvent(self, widget, event):
        """Called when a mouse button is pressed or released."""
        if event.type!=EVENT_BUTTON_PRESS or event.button!=3:
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
        self.emit("selection-changed", self.selectedIndex)

#-------------------------------------------------------------------------------

gobject.signal_new("row-activated", FlightList, gobject.SIGNAL_RUN_FIRST,
                   None, (int,))

gobject.signal_new("selection-changed", FlightList, gobject.SIGNAL_RUN_FIRST,
                   None, (object,))

#-----------------------------------------------------------------------------
