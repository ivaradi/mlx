# Module to handle the GUI aspects of the table of the delay codes

#------------------------------------------------------------------------------

from mlx.gui.common import *

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

            # if alloc is not None:
            #     import gi.repository.cairo
            #     allocation1 = gi.repository.cairo.RectangleInt()
            #     allocation1.x = allocation.x
            #     allocation1.y = allocation.y
            #     allocation1.width = allocation.width
            #     allocation1.height = height = alloc[3] - allocation.y
            #     allocation = allocation1



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
            else:
                raise AttributeError("mlx.gui.delaycodes.DelayCodeTableBase: property %s is not handled in do_set_property" %
                                     (prop.name,))

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

        def _do_size_allocate(self, widget, allocation):
            """Handler of the size-allocate signal.

            Calls allocate_column_sizes()."""
            self.allocate_column_sizes(allocation)

#------------------------------------------------------------------------------

class DelayCodeTable(DelayCodeTableBase):
    """The delay code table."""
    def __init__(self):
        """Construct the delay code table."""
        super(DelayCodeTable, self).__init__()

        self._listStore = gtk.ListStore(str, str, str, str)
        self._treeView = gtk.TreeView(self._listStore)
        column = gtk.TreeViewColumn("IATA", gtk.CellRendererText())
        column.set_sizing(TREE_VIEW_COLUMN_FIXED)
        self._treeView.append_column(column)
        column = gtk.TreeViewColumn("Description", gtk.CellRendererText())
        column.set_sizing(TREE_VIEW_COLUMN_FIXED)
        self._treeView.append_column(column)

        self.pack_start(self._treeView, False, False, 0)

        self._table = gtk.Table(10, 2)
        for i in range(0, 10):
            self._table.attach(gtk.Label("ZZZ" + `i`), 0, 1, i, i+1)
            self._table.attach(gtk.Label("AAA" + `i`), 1, 2, i, i+1)

        self._viewport = self._createViewport()
        self._viewport.add(self._table)
        self._viewport.set_shadow_type(SHADOW_NONE)

        self.pack_start(self._viewport, True, True, 0)

        self._previousWidth = 0

    def allocate_column_sizes(self, allocation):
        """Allocate the column sizes."""
        if allocation.width!=self._previousWidth:
            self._previousWidth = allocation.width
            column0 = self._treeView.get_column(0)
            column0.set_fixed_width(allocation.width/2)
            column1 = self._treeView.get_column(1)
            column1.set_fixed_width(allocation.width/2)

#------------------------------------------------------------------------------
