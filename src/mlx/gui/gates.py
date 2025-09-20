
from mlx.gui.common import *

from mlx.i18n import xstr
import mlx.const as const
from mlx.gates import Gates, lhbpGates

#-------------------------------------------------------------------------------

## @package mlx.gui.gates
#
# The gate status display.
#
# This module contains the \ref mlx.gui.gates.FleetGateStatus "FleetGateStatus"
# widget, which is the tab displaying the status of the MAVA Fleet and the
# gates at LHBP. The left side of the widget is the table with the list of the
# planes and their states. The right side displays the numbers of the gates and
# their occupation status.

#-------------------------------------------------------------------------------

class FleetGateStatus(Gtk.VBox):
    """The tab to display the fleet and gate status."""
    def __init__(self, gui):
        """Construct the tab."""
        super(FleetGateStatus, self).__init__()

        self._gui = gui

        mainAlignment = Gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                      xscale = 1.0, yscale = 1.0)
        mainAlignment.set_padding(padding_top = 4, padding_bottom = 4,
                                  padding_left = 12, padding_right = 12)
        self.add(mainAlignment)

        self._mainBox = mainBox = Gtk.VBox()
        mainAlignment.add(mainBox)
    
        self._statusBox = statusBox = Gtk.HBox()
        mainBox.pack_start(statusBox, True, True, 4)

        fleetFrame = Gtk.Frame(label = xstr("gates_fleet_title"))
        fleetLabel = fleetFrame.get_label_widget()
        fleetLabel.set_use_underline(True)
        statusBox.pack_start(fleetFrame, False, False, 4)

        self._fleetStore = Gtk.ListStore(str, str)
        self._fleetList = Gtk.TreeView(self._fleetStore)
        self._fleetList.set_tooltip_markup(xstr("gates_planes_tooltip"))
        fleetLabel.set_mnemonic_widget(self._fleetList)
        column = Gtk.TreeViewColumn(xstr("gates_tailno"), Gtk.CellRendererText(),
                                    markup = 0)
        column.set_expand(True)
        column.set_sort_column_id(0)
        self._fleetList.append_column(column)

        column = Gtk.TreeViewColumn(xstr("gates_planestatus"), Gtk.CellRendererText(),
                                    markup = 1)
        column.set_expand(True)
        column.set_sort_column_id(1)
        self._fleetList.append_column(column)

        scrolledWindow = Gtk.ScrolledWindow()
        scrolledWindow.add(self._fleetList)
        scrolledWindow.set_size_request(200, -1)
        # FIXME: these should be constants in common.py
        scrolledWindow.set_policy(Gtk.PolicyType.AUTOMATIC,
                                  Gtk.PolicyType.AUTOMATIC)
        scrolledWindow.set_shadow_type(Gtk.ShadowType.IN)


        self._fleetAlignment =  alignment = \
                               Gtk.Alignment(xalign = 0.5, yalign = 0.0,
                                             xscale = 0.0, yscale = 1.0)
        alignment.set_padding(padding_top = 4, padding_bottom = 4,
                              padding_left = 4, padding_right = 4)
        alignment.add(scrolledWindow)
        fleetFrame.add(alignment)        
        
        self._gatesFrame = gatesFrame = Gtk.Frame(label = xstr("gates_gates_title"))
        statusBox.pack_start(gatesFrame, True, True, 4)        

        self._gatesTable = table = Gtk.Table(lhbpGates.numRows,
                                             lhbpGates.numColumns)
        table.set_tooltip_markup(xstr("gates_gates_tooltip"))
        alignment = Gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 1.0, yscale = 1.0)
        alignment.set_padding(padding_top = 4, padding_bottom = 4,
                              padding_left = 4, padding_right = 4)
        alignment.add(table)
        gatesFrame.add(alignment)
        
        self._gateLabels = {}
        column = 0
        row = 0
        for (type, data) in lhbpGates.displayInfos:
            if type==Gates.DISPLAY_GATE:
                gate = data

                label = Gtk.Label()
                label.set_markup("<b>" + gate.number + "</b>")
                table.attach(label, column, column + 1, row, row + 1)

                self._gateLabels[gate.number] = label
                row += 1
            elif type==Gates.DISPLAY_SPACE:
                row += 1
            elif type==Gates.DISPLAY_NEW_COLUMN:
                row = 0
                column += 1

        button = Gtk.Button(xstr("gates_refresh"))
        button.set_use_underline(True)
        button.set_tooltip_text(xstr("gates_refresh_tooltip"))
        button.connect("clicked", self._refreshClicked)

        alignment = Gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)
        alignment.add(button)
        mainBox.pack_start(alignment, False, False, 4)

        self._fleetList.set_sensitive(False)
        self._gatesTable.set_sensitive(False)
        
    def disable(self):
        """Disable the widget."""
        self._mainBox.set_sensitive(False)
    
    def enable(self):
        """Enable the widget."""
        self._mainBox.set_sensitive(True)

    def _refreshClicked(self, button):
        """Called when the Refresh data button is clicked."""
        self._gui.getFleet(force = True)

    def handleFleet(self, fleet):
        """Handle new fleet information.

        If fleet is None, the data will be cleared."""
        self._fleetStore.clear()
        if fleet is None:
            for (gateNumber, label) in self._gateLabels.items():
                label.set_markup("<b>" + gateNumber + "</b>")
        else:        
            for plane in fleet:
                conflicting = False
                tailNumber = plane.tailNumber
                if plane.status==const.PLANE_HOME:
                    status = "LHBP - %s" % (plane.gateNumber,)
                    conflicting = fleet.isGateConflicting(plane)
                elif plane.status==const.PLANE_AWAY:
                    status = xstr("gates_plane_away")
                elif plane.status==const.PLANE_PARKING:
                    status = xstr("gates_plane_parking")
                else:
                    status = xstr("gates_plane_unknown")

                if conflicting:
                    tailNumber = '<span foreground="red">' + tailNumber + '</span>'
                    status = '<span foreground="red">' + status + '</span>'

                self._fleetStore.append([tailNumber, status])
            # FIXME: this should be a constant in common.py
            self._fleetStore.set_sort_column_id(0, Gtk.SortType.ASCENDING)

            occupiedGateNumbers = fleet.getOccupiedGateNumbers()
            for gate in lhbpGates.gates:
                gateNumber = gate.number
                markup = gateNumber
                if gateNumber in occupiedGateNumbers:
                    markup = '<span foreground="orange">' + markup + '</span>'
                markup = '<b>' + markup + '</b>'
                self._gateLabels[gateNumber].set_markup(markup)
            
        self._fleetList.set_sensitive(fleet is not None)
        self._gatesTable.set_sensitive(fleet is not None)

#----------------------------------------------------------------------------
