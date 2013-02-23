# Module to handle the GUI aspects of the table of the delay codes

#------------------------------------------------------------------------------

from mlx.gui.common import *

import mlx.const as const

#------------------------------------------------------------------------------

if pygobject:

#------------------------------------------------------------------------------

    class Viewport(gtk.Viewport):
        """Viewport implementation that alleviates the problem with improper
        resizing by the VBox."""
        def __init__(self):
            """Construct the viewport."""
            gtk.Viewport.__init__(self)
            self._recursive = False
            self._vboxHeight = None

        def setVBOXHeight(self, vboxHeight):
            """Set the height of the VBox which will be used to calculate the
            viewport's height."""
            self._vboxHeight = vboxHeight

        def do_size_allocate(self, allocation):
            """Called when the viewport's size is allocated.

            The height in the allocation object is modified so that it is only
            so high to fit into the VBox."""
            if self._vboxHeight is not None:
                allocation.height = self._vboxHeight - allocation.y
                self._vboxHeight = None
            gtk.Viewport.do_size_allocate(self, allocation)

    class DelayCodeTableBase(gtk.VBox, gtk.Scrollable):
        """PyGObject-specific base class for the delay code table."""
        __gproperties__ = {
            "vscroll-policy" : ( gtk.ScrollablePolicy,
                                 "vscroll-policy",
                                 "The vertical scrolling policy",
                                 gtk.ScrollablePolicy.MINIMUM,
                                 gobject.PARAM_READWRITE ),
            "vadjustment" : ( gtk.Adjustment,
                              "vadjustment",
                              "The vertical adjustment",
                              gobject.PARAM_READWRITE ),
            "hscroll-policy" : ( gtk.ScrollablePolicy,
                                 "hscroll-policy",
                                 "The horizontal scrolling policy",
                                 gtk.ScrollablePolicy.MINIMUM,
                                 gobject.PARAM_READWRITE ),
            "hadjustment" : ( gtk.Adjustment,
                              "hadjustment",
                              "The horizontal adjustment",
                              gobject.PARAM_READWRITE )  }


        @staticmethod
        def _createViewport():
            """Create an instance of the viewport class used by this base class."""
            return Viewport()

        def __init__(self):
            """Construct the delay code table."""
            super(DelayCodeTableBase, self).__init__()

        def do_size_allocate(self, allocation):
            """Allocate the size for the table and its children.

            This sets up the VBox height in the viewport and then calls the
            do_size_allocate() function of VBox()."""
            self._viewport.setVBOXHeight(allocation.height)
            gtk.VBox.do_size_allocate(self, allocation)
            self.allocate_column_sizes(allocation)

        def do_get_property(self, prop):
            """Get the value of one of the properties defined above.

            The request is forwarded to the viewport."""
            if prop.name=="vscroll-policy":
                return self._viewport.get_vscroll_policy()
            elif prop.name=="hscroll-policy":
                return self._viewport.get_hscroll_policy()
            elif prop.name=="vadjustment":
                return self._viewport.get_vadjustment()
            elif prop.name=="hadjustment":
                return self._viewport.get_hadjustment()
            else:
                raise AttributeError("mlx.gui.delaycodes.DelayCodeTableBase: property %s is not handled in do_get_property" %
                                     (prop.name,))

        def do_set_property(self, prop, value):
            """Set the value of the adjustment properties defined above.

            The adjustments are forwarded to the viewport."""
            if prop.name=="vadjustment":
                self._viewport.set_vadjustment(value)
            elif prop.name=="hadjustment":
                self._viewport.set_hadjustment(value)
                self._treeView.set_hadjustment(value)
            else:
                raise AttributeError("mlx.gui.delaycodes.DelayCodeTableBase: property %s is not handled in do_set_property" %
                                     (prop.name,))

        def setStyle(self):
            """Set the style of the event box from the treeview."""

    class Alignment(gtk.Alignment):
        """An alignment that remembers the width it was given."""
        def __init__(self, xalign = 0.0, yalign=0.0,
                     xscale = 0.0, yscale = 0.0 ):
            """Construct the alignment."""
            super(Alignment, self).__init__(xalign = xalign, yalign = yalign,
                                            xscale = xscale, yscale = yscale)
            self.allocatedWidth = 0

        def do_size_allocate(self, allocation):
            """Called with the new size allocation."""
            self.allocatedWidth = allocation.width
            gtk.Alignment.do_size_allocate(self, allocation)

#------------------------------------------------------------------------------

else: # pygobject

#------------------------------------------------------------------------------

    class DelayCodeTableBase (gtk.VBox):
        """Base class of the delay code table for PyGtk."""

        __gsignals__ = {
            "set-scroll-adjustments": (
                gobject.SIGNAL_RUN_LAST,
                gobject.TYPE_NONE, (gtk.Adjustment, gtk.Adjustment))
                }

        @staticmethod
        def _createViewport():
            """Create an instance of the viewport class used by this base class."""
            return gtk.Viewport()

        def __init__(self):
            """Construct the base class."""
            super(DelayCodeTableBase, self).__init__()
            self.set_set_scroll_adjustments_signal("set-scroll-adjustments")
            self.connect("size-allocate", self._do_size_allocate)

        def do_set_scroll_adjustments(self, hAdjustment, vAdjustment):
            """Set the adjustments on the viewport."""
            self._viewport.set_hadjustment(hAdjustment)
            self._viewport.set_vadjustment(vAdjustment)
            self._treeView.set_hadjustment(hAdjustment)

        def _do_size_allocate(self, widget, allocation):
            """Handler of the size-allocate signal.

            Calls allocate_column_sizes()."""
            self.allocate_column_sizes(allocation)

        def setStyle(self):
            """Set the style of the event box from the treeview."""
            if self._treeView is not None:
                style = self._treeView.rc_get_style()
                self._eventBox.modify_bg(0, style.bg[2])
                self._eventBox.modify_fg(0, style.fg[2])

    class Alignment(gtk.Alignment):
        """An alignment that remembers the width it was given."""
        def __init__(self, xalign = 0.0, yalign=0.0,
                     xscale = 0.0, yscale = 0.0 ):
            """Construct the alignment."""
            super(Alignment, self).__init__(xalign = xalign, yalign = yalign,
                                            xscale = xscale, yscale = yscale)
            self.allocatedWidth = 0
            self.connect("size-allocate", self._do_size_allocate)

        def _do_size_allocate(self, widget, allocation):
            """Called with the new size allocation."""
            self.allocatedWidth = allocation.width

#------------------------------------------------------------------------------

class CheckButton(gtk.CheckButton):
    """A check button that contains a reference to a row in the delay code
    data table."""
    def __init__(self, delayCodeRow):
        """Construct the check button."""
        super(CheckButton, self).__init__()
        self.delayCodeRow = delayCodeRow

#------------------------------------------------------------------------------

CAPTION = 1

DELAYCODE = 2

_data1 = ( lambda row: row[0].strip(),
           ["Num", "Code", "Title", "Description"],
           [ (CAPTION, "Others"),
             (DELAYCODE, ("      6", "OA  ", "NO GATES/STAND AVAILABLE",
                          "Due to own airline activity")),
             (DELAYCODE, ("9", "SG", "SCHEDULED GROUND TIME",
                          "Planned turnaround time less than declared minimum")),
             (CAPTION, "Passenger and baggage"),
             (DELAYCODE, ("11", "PD", "LATE CHECK-IN",
                          "Check-in reopened for late passengers")),
             (DELAYCODE, ("12", "PL", "LATE CHECK-IN",
                          "Check-in not completed by flight closure time")),
             (DELAYCODE, ("13", "PE", "CHECK-IN ERROR",
                          "Error with passenger or baggage details")) ] )

_data2 = ( lambda row: row[0].strip(),
           ["MA", "IATA", "Description"],
           [ (CAPTION, "Passenger and baggage"),
             (DELAYCODE, ("    012", "01   ",
                          "Late shipping of parts and/or materials")),
             (DELAYCODE, ("    111", "11",
                          "Check-in reopened for late passengers")),
             (DELAYCODE, ("    121", "12",
                          "Check-in not completed by flight closure time")),
             (DELAYCODE, ("    132", "13",
                          "Error with passenger or baggage details"))
            ])

#------------------------------------------------------------------------------

class DelayCodeTable(DelayCodeTableBase):
    """The delay code table."""
    def __init__(self):
        """Construct the delay code table."""
        super(DelayCodeTable, self).__init__()

        self._delayCodeData = None

        self._treeView = None

        self._treeView = gtk.TreeView(gtk.ListStore(str, str))
        self._treeView.set_rules_hint(True)

        self.pack_start(self._treeView, False, False, 0)

        self._alignments = []
        self._checkButtons = []

        self._eventBox = gtk.EventBox()

        self._table = None

        self._viewport = self._createViewport()
        self._viewport.add(self._eventBox)
        self._viewport.set_shadow_type(SHADOW_NONE)

        self.pack_start(self._viewport, True, True, 0)

        self._previousWidth = 0

    @property
    def delayCodes(self):
        """Get a list of the delay codes checked by the user."""
        codes = []

        if self._delayCodeData is not None:
            codeExtractor = self._delayCodeData[0]
            for checkButton in self._checkButtons:
                if checkButton.get_active():
                    codes.append(codeExtractor(checkButton.delayCodeRow))

        return codes

    def allocate_column_sizes(self, allocation):
        """Allocate the column sizes."""
        if allocation.width!=self._previousWidth:
            self._previousWidth = allocation.width
            index = 0
            for alignment in self._alignments:
                column = self._treeView.get_column(index)
                width = alignment.allocatedWidth + (8 if index==0 else 16)
                column.set_fixed_width(width)
                index += 1

    def setType(self, aircraftType):
        """Setup the delay code table according to the given aircraft type."""
        if aircraftType==const.AIRCRAFT_B736:
            data = _data1
        else:
            data = _data2

        self._delayCodeData = data

        columns = self._treeView.get_columns()
        for column in columns:
            self._treeView.remove_column(column)

        (_extractor, headers, rows) = data
        numColumns = len(headers) + 1
        numRows = len(rows)

        column = gtk.TreeViewColumn("", gtk.CellRendererText())
        column.set_sizing(TREE_VIEW_COLUMN_FIXED)
        self._treeView.append_column(column)

        for header in headers:
            column = gtk.TreeViewColumn(header, gtk.CellRendererText())
            column.set_sizing(TREE_VIEW_COLUMN_FIXED)
            self._treeView.append_column(column)

        self._table = gtk.Table(numRows, numColumns)
        self._table.set_homogeneous(False)
        self._table.set_col_spacings(16)
        self._table.set_row_spacings(4)
        self._eventBox.add(self._table)

        self._alignments = []
        self._checkButtons = []

        firstDelayCodeRow = True
        for i in range(0, numRows):
            (type, elements) = rows[i]
            if type==CAPTION:
                alignment = gtk.Alignment(xalign = 0.0, yalign = 0.5,
                                          xscale = 1.0)
                label = gtk.Label("<b>" + elements + "</b>")
                label.set_use_markup(True)
                label.set_alignment(0.0, 0.5)
                alignment.add(label)
                self._table.attach(alignment, 1, numColumns, i, i+1)
                self._table.set_row_spacing(i, 8)
            elif type==DELAYCODE:
                checkButton = CheckButton(elements)
                self._checkButtons.append(checkButton)
                alignment = Alignment(xalign = 0.5, yalign = 0.5, xscale = 1.0)
                alignment.add(checkButton)
                self._table.attach(alignment, 0, 1, i, i+1)
                if firstDelayCodeRow:
                    self._alignments.append(alignment)

                for j in range(0, len(elements)):
                    label = gtk.Label(elements[j])
                    label.set_alignment(1.0 if j==0 else 0.0, 0.5)
                    alignment = Alignment(xalign = 0.5, yalign = 0.5,
                                          xscale = 1.0)
                    alignment.add(label)
                    self._table.attach(alignment, j+1, j+2, i, i+1)
                    if firstDelayCodeRow:
                        self._alignments.append(alignment)
                firstDelayCodeRow = False

        self._previousWidth = 0
        self.show_all()

    def reset(self):
        """Reset the delay code table."""
        columns = self._treeView.get_columns()
        for column in columns:
            self._treeView.remove_column(column)
        self._eventBox.remove(self._table)
        self._table = None
        self.show_all()

#------------------------------------------------------------------------------
