# Module to display the status of the planes and the gates

#----------------------------------------------------------------------------

from mlx.gui.common import *

from mlx.i18n import xstr
import mlx.const as const

#-------------------------------------------------------------------------------

class FleetGateStatus(gtk.VBox):
    """The tab to display the fleet and gate status."""
    def __init__(self, gui):
        """Construct the tab."""
        super(FleetGateStatus, self).__init__()

        self._gui = gui

        mainAlignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                      xscale = 1.0, yscale = 1.0)
        mainAlignment.set_padding(padding_top = 4, padding_bottom = 4,
                                  padding_left = 12, padding_right = 12)
        self.add(mainAlignment)

        self._mainBox = mainBox = gtk.VBox()
        mainAlignment.add(mainBox)
    
        self._statusBox = statusBox = gtk.HBox()
        mainBox.pack_start(statusBox, True, True, 4)

        fleetFrame = gtk.Frame(label = xstr("gates_fleet_title"))
        fleetLabel = fleetFrame.get_label_widget()
        fleetLabel.set_use_underline(True)
        statusBox.pack_start(fleetFrame, False, False, 4)

        self._fleetStore = gtk.ListStore(str, str)
        self._fleetList = gtk.TreeView(self._fleetStore)
        self._fleetList.set_tooltip_markup(xstr("gates_planes_tooltip"))
        fleetLabel.set_mnemonic_widget(self._fleetList)
        column = gtk.TreeViewColumn(xstr("gates_tailno"), gtk.CellRendererText(),
                                    text = 0)
        column.set_expand(True)
        column.set_sort_column_id(0)
        self._fleetList.append_column(column)

        column = gtk.TreeViewColumn(xstr("gates_planestatus"), gtk.CellRendererText(),
                                    markup = 1)
        column.set_expand(True)
        column.set_sort_column_id(1)
        self._fleetList.append_column(column)

        scrolledWindow = gtk.ScrolledWindow()
        scrolledWindow.add(self._fleetList)
        scrolledWindow.set_size_request(200, -1)
        # FIXME: these should be constants in common.py
        scrolledWindow.set_policy(gtk.PolicyType.AUTOMATIC if pygobject
                                  else gtk.POLICY_AUTOMATIC,
                                  gtk.PolicyType.AUTOMATIC if pygobject
                                  else gtk.POLICY_AUTOMATIC)
        scrolledWindow.set_shadow_type(gtk.ShadowType.IN if pygobject
                                       else gtk.SHADOW_IN)


        self._fleetAlignment =  alignment = \
                               gtk.Alignment(xalign = 0.5, yalign = 0.0,
                                             xscale = 0.0, yscale = 1.0)
        alignment.set_padding(padding_top = 4, padding_bottom = 4,
                              padding_left = 4, padding_right = 4)
        alignment.add(scrolledWindow)
        fleetFrame.add(alignment)        
        
        self._gatesFrame = gatesFrame = gtk.Frame(label = xstr("gates_gates_title"))
        statusBox.pack_start(gatesFrame, True, True, 4)        

        self._gatesTable = table = gtk.Table(14, 4)
        table.set_tooltip_markup(xstr("gates_gates_tooltip"))
        alignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 1.0, yscale = 1.0)
        alignment.set_padding(padding_top = 4, padding_bottom = 4,
                              padding_left = 4, padding_right = 4)
        alignment.add(table)
        gatesFrame.add(alignment)
        
        self._gateLabels = {}
        column = 0
        row = 0
        for gateNumber in const.lhbpGateNumbers:
            label = gtk.Label()
            label.set_markup("<b>" + gateNumber + "</b>")
            table.attach(label, column, column + 1, row, row + 1)

            self._gateLabels[gateNumber] = label
            
            if column==1 and row==12:
                column = 2
                row = 1
            elif row==13:
                column += 1
                row = 0
            else:
                row += 1
                
        button = gtk.Button(xstr("gates_refresh"))
        button.set_use_underline(True)
        button.set_tooltip_text(xstr("gates_refresh_tooltip"))
        button.connect("clicked", self._refreshClicked)

        alignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
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
            for (gateNumber, label) in self._gateLabels.iteritems():
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
            self._fleetStore.set_sort_column_id(0,
                                                gtk.SortType.ASCENDING if pygobject
                                                else gtk.SORT_ASCENDING)

            occupiedGateNumbers = fleet.getOccupiedGateNumbers()
            for gateNumber in const.lhbpGateNumbers:
                markup = gateNumber
                if gateNumber in occupiedGateNumbers:
                    markup = '<span foreground="orange">' + markup + '</span>'
                markup = '<b>' + markup + '</b>'
                self._gateLabels[gateNumber].set_markup(markup)
            
        self._fleetList.set_sensitive(fleet is not None)
        self._gatesTable.set_sensitive(fleet is not None)

#----------------------------------------------------------------------------
