
from mlx.gui.common import *

from mlx.i18n import xstr
from mlx.checks import PayloadChecker

#-------------------------------------------------------------------------------

## @package mlx.gui.weighthelp
#
# The weight calculation help tab.
#
# This module implements the tab containing the weight calculation help. 

#-------------------------------------------------------------------------------

class WeightHelp(gtk.VBox):
    """The weight calculation help tab."""
    @staticmethod
    def _getMarkup(value, expectedValue = None, tolerance = None):
        """Get the markup for the given value.

        If it is too much different from the expected value, it will be
        colored yellow (if within the tolerance), or red (if out of the tolerance)."""
        markup = "%.0f" % (value,)
        if expectedValue is not None and tolerance is not None:
            colour = None
            diff = abs(value - expectedValue)
            if diff>tolerance: colour = "red"
            elif (diff*10)>=tolerance: colour = "orange"
            else: colour = "darkgreen"
            if colour is not None:
                markup = '<span foreground="' + colour + '">' + markup + '</span>'
        return markup

    def __init__(self, gui):
        """Construct the tab."""
        super(WeightHelp, self).__init__()

        self._gui = gui

        mainAlignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                      xscale = 1.0, yscale = 1.0)
        mainAlignment.set_padding(padding_top = 4, padding_bottom = 4,
                                  padding_left = 12, padding_right = 12)
        self.add(mainAlignment)

        self._mainBox = mainBox = gtk.VBox()
        mainAlignment.add(mainBox)

        self._usingHelp = gtk.CheckButton(xstr("weighthelp_usinghelp"))
        self._usingHelp.set_use_underline(True)
        self._usingHelp.set_tooltip_text(xstr("weighthelp_usinghelp_tooltip"))
        self._usingHelp.connect("toggled", self._usingHelpToggled)
        mainBox.pack_start(self._usingHelp, False, False, 4)

        
        self._weightsTable = table = gtk.Table(17, 5)
        table.set_homogeneous(False)
        table.set_row_spacings(4)
        table.set_col_spacings(16)
        alignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)
        alignment.add(table)
        mainBox.pack_start(alignment, True, True, 4)

        alignment = gtk.Alignment(xalign = 1.0, yalign = 0.0,
                                  xscale = 0.0, yscale = 0.0)
        alignment.set_padding(padding_bottom = 16, padding_top = 0,
                              padding_left = 0, padding_right = 0)
        label = gtk.Label(xstr("weighthelp_header_calculated"))
        label.set_use_markup(True)
        # FIXME: should be a constant in common
        label.set_justify(gtk.Justification.CENTER if pygobject
                          else gtk.JUSTIFY_CENTER)        
        alignment.add(label)
        table.attach(alignment, 1, 2, 0, 1)
        
        alignment = gtk.Alignment(xalign = 1.0, yalign = 0.0,
                                  xscale = 0.0, yscale = 0.0)
        alignment.set_padding(padding_bottom = 16, padding_top = 0,
                              padding_left = 0, padding_right = 0)
        button = gtk.Button(xstr("weighthelp_header_simulator"))
        button.set_tooltip_markup(xstr("weighthelp_header_simulator_tooltip"))
        button.connect("clicked", self._fsButtonClicked)
        label = button.get_child()
        label.set_justify(gtk.Justification.CENTER if pygobject
                          else gtk.JUSTIFY_CENTER)        
        alignment.add(button)
        table.attach(alignment, 3, 4, 0, 1)
        

        self._cockpitCrewLabel = \
          gtk.Label(xstr("weighthelp_cockpit_crew") % ("99",))
        alignment = gtk.Alignment(xalign = 0.0, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)
        alignment.add(self._cockpitCrewLabel)
        table.attach(alignment, 0, 1, 1, 2)

        self._cockpitCrewWeight = gtk.Label("0")
        alignment = gtk.Alignment(xalign = 1.0, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)
        alignment.add(self._cockpitCrewWeight)
        table.attach(alignment, 1, 2, 1, 2)
        
        table.attach(gtk.Label("kg"), 2, 3, 1, 2)

        self._cabinCrewLabel = \
          gtk.Label(xstr("weighthelp_cabin_crew") % ("99",))
        alignment = gtk.Alignment(xalign = 0.0, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)
        alignment.add(self._cabinCrewLabel)
        table.attach(alignment, 0, 1, 2, 3)

        self._cabinCrewWeight = gtk.Label("0")
        alignment = gtk.Alignment(xalign = 1.0, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)
        alignment.add(self._cabinCrewWeight)
        table.attach(alignment, 1, 2, 2, 3)
        
        table.attach(gtk.Label("kg"), 2, 3, 2, 3)

        text = xstr("weighthelp_pax") % ("999",)
        self._paxLabel = gtk.Label(text)
        self._paxLabel.set_width_chars(len(text))
        self._paxLabel.set_alignment(0.0, 0.5)
        alignment = gtk.Alignment(xalign = 0.0, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)
        alignment.add(self._paxLabel)
        table.attach(alignment, 0, 1, 3, 4)

        self._paxWeight = gtk.Label("20000")
        alignment = gtk.Alignment(xalign = 1.0, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)
        alignment.add(self._paxWeight)
        table.attach(alignment, 1, 2, 3, 4)
        
        table.attach(gtk.Label("kg"), 2, 3, 3, 4)
        
        label = gtk.Label(xstr("weighthelp_baggage"))
        alignment = gtk.Alignment(xalign = 0.0, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)
        alignment.add(label)
        table.attach(alignment, 0, 1, 4, 5)

        self._bagWeight = gtk.Label("2000")
        alignment = gtk.Alignment(xalign = 1.0, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)
        alignment.add(self._bagWeight)
        table.attach(alignment, 1, 2, 4, 5)
        
        table.attach(gtk.Label("kg"), 2, 3, 4, 5)
        
        label = gtk.Label(xstr("weighthelp_cargo"))
        alignment = gtk.Alignment(xalign = 0.0, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)
        alignment.add(label)
        table.attach(alignment, 0, 1, 5, 6)

        self._cargoWeight = gtk.Label("2000")
        alignment = gtk.Alignment(xalign = 1.0, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)
        alignment.add(self._cargoWeight)
        table.attach(alignment, 1, 2, 5, 6)
        
        table.attach(gtk.Label("kg"), 2, 3, 5, 6)
        
        label = gtk.Label(xstr("weighthelp_mail"))
        alignment = gtk.Alignment(xalign = 0.0, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)
        alignment.add(label)
        table.attach(alignment, 0, 1, 6, 7)

        self._mailWeight = gtk.Label("2000")
        alignment = gtk.Alignment(xalign = 1.0, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)
        alignment.add(self._mailWeight)
        table.attach(alignment, 1, 2, 6, 7)
        
        table.attach(gtk.Label("kg"), 2, 3, 6, 7)

        table.attach(gtk.HSeparator(), 1, 2, 7, 8)

        label = gtk.Label("<b>" + xstr("weighthelp_payload") + "</b>")
        label.set_use_markup(True)
        alignment = gtk.Alignment(xalign = 0.0, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)
        alignment.add(label)
        table.attach(alignment, 0, 1, 8, 9)

        self._payload = gtk.Label("<b>32000</b>")
        self._payload.set_use_markup(True)
        alignment = gtk.Alignment(xalign = 1.0, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)
        alignment.add(self._payload)
        table.attach(alignment, 1, 2, 8, 9)
        
        table.attach(gtk.Label("kg"), 2, 3, 8, 9)

        self._fsPayload = gtk.Label("<b>32001</b>")
        self._fsPayload.set_use_markup(True)
        alignment = gtk.Alignment(xalign = 1.0, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)
        alignment.add(self._fsPayload)
        table.attach(alignment, 3, 4, 8, 9)
        
        table.attach(gtk.Label("kg"), 4, 5, 8, 9)

        label = gtk.Label(xstr("weighthelp_dow"))
        label.set_use_markup(True)
        alignment = gtk.Alignment(xalign = 0.0, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)
        alignment.add(label)
        table.attach(alignment, 0, 1, 9, 10)

        self._dow = gtk.Label("35000")
        alignment = gtk.Alignment(xalign = 1.0, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)
        alignment.add(self._dow)
        table.attach(alignment, 1, 2, 9, 10)
        
        table.attach(gtk.Label("kg"), 2, 3, 9, 10)

        self._fsDOW = gtk.Label("33012")
        alignment = gtk.Alignment(xalign = 1.0, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)
        alignment.add(self._fsDOW)
        table.attach(alignment, 3, 4, 9, 10)
        
        table.attach(gtk.Label("kg"), 4, 5, 9, 10)

        table.attach(gtk.HSeparator(), 1, 2, 10, 11)

        table.attach(gtk.HSeparator(), 3, 4, 10, 11)

        label = gtk.Label("<b>" + xstr("weighthelp_zfw") + "</b>")
        label.set_use_markup(True)
        alignment = gtk.Alignment(xalign = 0.0, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)
        alignment.add(label)
        table.attach(alignment, 0, 1, 11, 12)

        self._zfw = gtk.Label("<b>122000</b>")
        self._zfw.set_use_markup(True)
        alignment = gtk.Alignment(xalign = 1.0, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)
        alignment.add(self._zfw)
        table.attach(alignment, 1, 2, 11, 12)
        
        table.attach(gtk.Label("kg"), 2, 3, 11, 12)

        self._fsZFW = gtk.Label("<b>124000</b>")
        self._fsZFW.set_use_markup(True)
        alignment = gtk.Alignment(xalign = 1.0, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)
        alignment.add(self._fsZFW)
        table.attach(alignment, 3, 4, 11, 12)
        
        table.attach(gtk.Label("kg"), 4, 5, 11, 12)

        table.attach(gtk.HSeparator(), 0, 5, 12, 13)
        
        label = gtk.Label(xstr("weighthelp_gross"))
        label.set_use_markup(True)
        alignment = gtk.Alignment(xalign = 0.0, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)
        alignment.add(label)
        table.attach(alignment, 0, 1, 13, 14)

        self._fsGross = gtk.Label("124000")
        alignment = gtk.Alignment(xalign = 1.0, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)
        alignment.add(self._fsGross)
        table.attach(alignment, 3, 4, 13, 14)
        
        table.attach(gtk.Label("kg"), 4, 5, 13, 14)

        label = gtk.Label(xstr("weighthelp_mzfw"))
        label.set_use_markup(True)
        alignment = gtk.Alignment(xalign = 0.0, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)
        alignment.add(label)
        table.attach(alignment, 0, 1, 14, 15)

        self._mzfw = gtk.Label("35000")
        alignment = gtk.Alignment(xalign = 1.0, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)
        alignment.add(self._mzfw)
        table.attach(alignment, 1, 2, 14, 15)
        
        table.attach(gtk.Label("kg"), 2, 3, 14, 15)

        label = gtk.Label(xstr("weighthelp_mtow"))
        label.set_use_markup(True)
        alignment = gtk.Alignment(xalign = 0.0, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)
        alignment.add(label)
        table.attach(alignment, 0, 1, 15, 16)

        self._mtow = gtk.Label("35000")
        alignment = gtk.Alignment(xalign = 1.0, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)
        alignment.add(self._mtow)
        table.attach(alignment, 1, 2, 15, 16)
        
        table.attach(gtk.Label("kg"), 2, 3, 15, 16)

        label = gtk.Label(xstr("weighthelp_mlw"))
        label.set_use_markup(True)
        alignment = gtk.Alignment(xalign = 0.0, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)
        alignment.add(label)
        table.attach(alignment, 0, 1, 16, 17)

        self._mlw = gtk.Label("35000")
        alignment = gtk.Alignment(xalign = 1.0, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)
        alignment.add(self._mlw)
        table.attach(alignment, 1, 2, 16, 17)
        
        table.attach(gtk.Label("kg"), 2, 3, 16, 17)

        self.show_all()

    def disable(self):
        """Disable the widget."""
        self._mainBox.set_sensitive(False)
    
    def enable(self):
        """Enable the widget."""
        self._mainBox.set_sensitive(True)
    
    def reset(self):
        """Reset all calculated and FS data."""
        
        self._usingHelp.set_active(False)
        self._usingHelp.set_sensitive(True)
        self._weightsTable.set_sensitive(False)
        
        self._cockpitCrew = -1
        self._cabinCrew = -1
        self._pax = -1
        self._dowCockpit = 2
        self._cockpitCrewMemberWeight = 85.0
        self._dowCabin = 2
        self._cabinCrewMemberWeight = 75.0
        self._humanWeight = 84.0
        self._bag = -1
        self._cargo = -1
        self._mail = -1        
        self._dowValue = -1
        self._mzfwValue = -1
        self._mtowValue = -1
        self._mlwValue = -1

        self._fsPayloadValue = -1
        self._fsDOWValue = -1
        self._fsZFWValue = -1
        self._fsGrossValue = -1
        
        self._setupCalculated()
        self._setupFS()

    def _setupCalculated(self):
        """Setup the labels for the calculated values."""
        if self._cockpitCrew<0:
            self._cockpitCrewLabel.set_text(xstr("weighthelp_cockpit_crew") % ("-",))
            self._cockpitCrewWeight.set_text("-")
        else:
            self._cockpitCrewLabel.set_text(xstr("weighthelp_cockpit_crew") %
                                            (str(self._cockpitCrew),))
            crewWeight = (self._cockpitCrew - self._dowCockpit) * self._cockpitCrewMemberWeight
            self._cockpitCrewWeight.set_text("%.0f" % (crewWeight,))
            
        if self._cabinCrew<0:
            self._cabinCrewLabel.set_text(xstr("weighthelp_cabin_crew") % ("-",))
            self._cabinCrewWeight.set_text("-")
        else:
            self._cabinCrewLabel.set_text(xstr("weighthelp_cabin_crew") %
                                          (str(self._cabinCrew),))
            crewWeight = (self._cabinCrew - self._dowCabin) * self._cabinCrewMemberWeight
            self._cabinCrewWeight.set_text("%.0f" % (crewWeight,))
            
        if self._pax<0:
            self._paxLabel.set_text(xstr("weighthelp_pax") % ("-",))
            self._paxWeight.set_text("-")
        else:
            self._paxLabel.set_text(xstr("weighthelp_pax") % (str(self._pax),))
            paxWeight = self._pax * self._humanWeight
            self._paxWeight.set_text("%.0f" % (paxWeight,))

        self._setWeightLabel(self._bagWeight, self._bag)

        self._setWeightLabel(self._cargoWeight, self._cargo)
        
        self._setWeightLabel(self._mailWeight, self._mail)
            
        (payload, zfw) = self._calculateWeights()

        self._setWeightLabel(self._payload, payload, bold = True)
            
        self._setWeightLabel(self._dow, self._dowValue)

        if zfw<0:
            self._zfw.set_text("-")
        else:
            markup = "%.0f" % (zfw,)
            if self._mzfwValue>0 and zfw>self._mzfwValue:
                markup = '<span foreground="red">' + markup + '</span>'
            markup = '<b>' + markup + '</b>'
            self._zfw.set_markup(markup)

        self._setWeightLabel(self._mzfw, self._mzfwValue)
        
        self._setWeightLabel(self._mtow, self._mtowValue)
        
        self._setWeightLabel(self._mlw, self._mlwValue)

    def _setupFS(self):
        if self._dowValue<0:
            self._dow.set_text("-")
        else:
            self._dow.set_text("%.0f" % (self._dowValue,))

        """Setup the labels for the FS values."""        
        (payload, zfw) = self._calculateWeights()

        if self._fsPayloadValue<0:
            self._fsPayload.set_text("-")
        else:
            markup = WeightHelp._getMarkup(self._fsPayloadValue, payload,
                                           PayloadChecker.TOLERANCE)
            self._fsPayload.set_markup("<b>" + markup + "</b>")

        if self._fsDOWValue<0:
            self._fsDOW.set_text("-")
        else:            
            markup = WeightHelp._getMarkup(self._fsDOWValue,  self._dowValue,
                                           PayloadChecker.TOLERANCE)
            self._fsDOW.set_markup(markup)

        if self._fsZFWValue<0:
            self._fsZFW.set_text("-")
        else:
            markup = WeightHelp._getMarkup(self._fsZFWValue,  zfw,
                                           PayloadChecker.TOLERANCE)
            self._fsZFW.set_markup("<b>" + markup + "</b>")

        self._setWeightLabel(self._fsGross, self._fsGrossValue)

    def _calculateWeights(self):
        """Calculate the payload and the zero-fuel weight.

        It returns a tuple with these two items. If any of the items cannot be
        calculated, that is -1."""
        if self._cockpitCrew<0 or self._cabinCrew<0 or self._pax<0 or \
               self._bag<0 or self._cargo<0 or self._mail<0:
            payload = -1
        else:
            payload = \
              (self._cockpitCrew - self._dowCockpit) * \
              self._cockpitCrewMemberWeight + \
              (self._cabinCrew - self._dowCabin) * \
              self._cabinCrewMemberWeight + \
              self._pax * self._humanWeight + \
              self._bag + self._cargo + self._mail

        if payload<0 or self._dowValue<0:
            zfw = -1
        else:
            zfw = payload + self._dowValue

        return (payload, zfw)

    def _usingHelpToggled(self, button):
        """Called when the Using help button is toggled."""
        assert self._usingHelp.get_active()
        self._usingHelp.set_sensitive(False)

        self._gui.logger.untimedMessage("The weight calculation help function was used by the pilot")

        self._cockpitCrew = self._gui.numCockpitCrew
        self._cabinCrew = self._gui.numCabinCrew
        self._pax = self._gui.numPassengers
        self._bag = self._gui.bagWeight
        self._cargo = self._gui.cargoWeight
        self._mail = self._gui.mailWeight
        
        aircraft = self._gui.flight.aircraft
        self._dowCockpit = aircraft.dowCockpit
        self._cockpitCrewMemberWeight = aircraft.cockpitCrewWeight
        self._dowCabin = aircraft.dowCabin
        self._cabinCrewMemberWeight = aircraft.cabinCrewWeight
        self._humanWeight = aircraft.humanWeight
        self._dowValue = aircraft.dow
        self._mzfwValue = aircraft.mzfw
        self._mtowValue = aircraft.mtow
        self._mlwValue = aircraft.mlw

        self._setupCalculated()
        self._weightsTable.set_sensitive(True)

    def _fsButtonClicked(self, button):
        """Callback for the FS button being clicked."""
        gui = self._gui
        gui.beginBusy(xstr("weighthelp_busy"))
        gui.simulator.requestWeights(self._handleWeights)

    def _handleWeights(self, dow, payload, zfw, grossWeight):
        """Handle the given weights."""
        gobject.idle_add(self._processWeights, dow, payload, zfw, grossWeight)

    def _processWeights(self, dow, payload, zfw, grossWeight):
        """Process the given weights."""
        self._gui.endBusy()
        if self._usingHelp.get_active():
            self._fsPayloadValue = payload
            self._fsDOWValue = dow
            self._fsZFWValue = zfw
            self._fsGrossValue = grossWeight
            self._setupFS()

    def _setWeightLabel(self, label, weight, bold = False):
        """Set the given weight label to the given weight."""
        if weight<0:
            label.set_text("-")
        else:
            markup = "%.0f" % (weight,)
            if bold: markup = "<b>" + markup + "</b>"
            label.set_markup(markup)
                
        
