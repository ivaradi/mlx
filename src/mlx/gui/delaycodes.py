# Module to handle the GUI aspects of the table of the delay codes

#------------------------------------------------------------------------------

from .dcdata import CAPTION, DELAYCODE, getTable

from mlx.gui.common import *

import mlx.const as const

#------------------------------------------------------------------------------

class Viewport(Gtk.Viewport):
    """Viewport implementation that alleviates the problem with improper
    resizing by the VBox."""
    def __init__(self):
        """Construct the viewport."""
        Gtk.Viewport.__init__(self)
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
            allocation.y += 1
            allocation.height = self._vboxHeight - allocation.y
            self._vboxHeight = None
        Gtk.Viewport.do_size_allocate(self, allocation)

class DelayCodeTableBase(Gtk.VBox, Gtk.Scrollable):
    """PyGObject-specific base class for the delay code table."""
    __gproperties__ = {
        "vscroll-policy" : ( Gtk.ScrollablePolicy,
                             "vscroll-policy",
                             "The vertical scrolling policy",
                             Gtk.ScrollablePolicy.MINIMUM,
                             GObject.PARAM_READWRITE ),
        "vadjustment" : ( Gtk.Adjustment,
                          "vadjustment",
                          "The vertical adjustment",
                          GObject.PARAM_READWRITE ),
        "hscroll-policy" : ( Gtk.ScrollablePolicy,
                             "hscroll-policy",
                             "The horizontal scrolling policy",
                             Gtk.ScrollablePolicy.MINIMUM,
                             GObject.PARAM_READWRITE ),
        "hadjustment" : ( Gtk.Adjustment,
                          "hadjustment",
                          "The horizontal adjustment",
                          GObject.PARAM_READWRITE )  }


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
        Gtk.VBox.do_size_allocate(self, allocation)
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

class Alignment(Gtk.Alignment):
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
        Gtk.Alignment.do_size_allocate(self, allocation)

class TreeView(Gtk.TreeView):
    def do_size_allocate(self, allocation):
        allocation.height += 1
        Gtk.TreeView.do_size_allocate(self, allocation)

#------------------------------------------------------------------------------

class CheckButton(Gtk.CheckButton):
    """A check button that contains a reference to a row in the delay code
    data table."""
    def __init__(self, delayCodeRow):
        """Construct the check button."""
        super(CheckButton, self).__init__()
        self.delayCodeRow = delayCodeRow

#------------------------------------------------------------------------------

# CAPTION = 1

# DELAYCODE = 2

# _data1 = ( lambda row: row[0].strip(),
#            ["Num", "Code", "Title", "Description"],
#            [ (CAPTION, "Others"),
#              (DELAYCODE, ("        6", "OA     ", "NO GATES/STAND AVAILABLE",
#                           "Due to own airline activity")),
#              (DELAYCODE, ("9", "SG", "SCHEDULED GROUND TIME",
#                           "Planned turnaround time less than declared minimum")),
#              (CAPTION, "Passenger and baggage"),
#              (DELAYCODE, ("11", "PD", "LATE CHECK-IN",
#                           "Check-in reopened for late passengers")),
#              (DELAYCODE, ("12", "PL", "LATE CHECK-IN",
#                           "Check-in not completed by flight closure time")),
#              (DELAYCODE, ("13", "PE", "CHECK-IN ERROR",
#                           "Error with passenger or baggage details")) ] )

# _data2 = ( lambda row: row[0].strip(),
#            ["MA", "IATA", "Description"],
#            [ (CAPTION, "Passenger and baggage"),
#              (DELAYCODE, (" 012", "01   ",
#                           "Late shipping of parts and/or materials")),
#              (DELAYCODE, (" 111", "11",
#                           "Check-in reopened for late passengers")),
#              (DELAYCODE, (" 121", "12",
#                           "Check-in not completed by flight closure time")),
#              (DELAYCODE, (" 132", "13",
#                           "Error with passenger or baggage details"))
#             ])

#------------------------------------------------------------------------------

class DelayCodeTable(DelayCodeTableBase):
    """The delay code table."""
    def __init__(self, info):
        """Construct the delay code table."""
        super(DelayCodeTable, self).__init__()

        self._info = info

        self._delayCodeData = None

        self._treeView = TreeView(Gtk.ListStore(str, str))
        self._treeView.set_rules_hint(True)

        self.pack_start(self._treeView, False, False, 0)

        self._alignments = []
        self._checkButtons = []

        self._eventBox = Gtk.EventBox()

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

    @property
    def hasDelayCode(self):
        """Determine if there is at least one delay code selected."""
        if self._delayCodeData is not None:
            for checkButton in self._checkButtons:
                if checkButton.get_active():
                    return True

        return False

    def allocate_column_sizes(self, allocation):
        """Allocate the column sizes."""
        if allocation.width!=self._previousWidth:
            self._previousWidth = allocation.width
            index = 0
            lastIndex = len(self._alignments) - 1
            for alignment in self._alignments:
                column = self._treeView.get_column(index)
                width = alignment.allocatedWidth
                width += 8 if (index==0 or index==lastIndex) else 16
                column.set_fixed_width(width)
                index += 1

    def setType(self, aircraftType):
        """Setup the delay code table according to the given aircraft type."""
        self._delayCodeData = data = getTable(aircraftType)
        if data is None:
            return

        columns = self._treeView.get_columns()
        for column in columns:
            self._treeView.remove_column(column)

        (_extractor, headers, rows) = data
        numColumns = len(headers) + 1
        numRows = len(rows)

        column = Gtk.TreeViewColumn("", Gtk.CellRendererText())
        column.set_sizing(TREE_VIEW_COLUMN_FIXED)
        self._treeView.append_column(column)

        for header in headers:
            column = Gtk.TreeViewColumn(header, Gtk.CellRendererText())
            column.set_sizing(TREE_VIEW_COLUMN_FIXED)
            self._treeView.append_column(column)

        self._table = Gtk.Table(numRows, numColumns)
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
                alignment = Gtk.Alignment(xalign = 0.0, yalign = 0.5,
                                          xscale = 1.0)
                label = Gtk.Label("<b>" + elements + "</b>")
                label.set_use_markup(True)
                label.set_alignment(0.0, 0.5)
                alignment.add(label)
                self._table.attach(alignment, 1, numColumns, i, i+1,
                                   yoptions = FILL)
                self._table.set_row_spacing(i, 8)
            elif type==DELAYCODE:
                checkButton = CheckButton(elements)
                checkButton.connect("toggled", self._delayCodesChanged)
                self._checkButtons.append(checkButton)
                alignment = Alignment(xalign = 0.5, yalign = 0.5, xscale = 1.0)
                alignment.add(checkButton)
                self._table.attach(alignment, 0, 1, i, i+1,
                                   xoptions = FILL, yoptions = FILL)
                if firstDelayCodeRow:
                    self._alignments.append(alignment)

                for j in range(0, numColumns-1):
                    label = Gtk.Label(elements[j])
                    label.set_alignment(0.0, 0.5)
                    alignment = Alignment(xalign = 0.5, yalign = 0.5,
                                          xscale = 1.0)
                    alignment.add(label)
                    xoptions = FILL
                    if j==(numColumns-2): xoptions |= EXPAND
                    self._table.attach(alignment, j+1, j+2, i, i+1,
                                       xoptions = xoptions, yoptions = FILL)
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
        if self._table is not None:
            self._eventBox.remove(self._table)
        self._table = None
        self.show_all()

    def activateCode(self, code):
        """Check the checkbox for the given code."""
        index = 0
        for (type, data) in self._delayCodeData[2]:
            if type==DELAYCODE:
                if code==data[0].strip():
                    self._checkButtons[index].set_active(True)
                    break
                index += 1

    def _delayCodesChanged(self, button):
        """Called when one of the delay codes have changed."""
        self._info.delayCodesChanged()

#------------------------------------------------------------------------------
