# Module to provide a widget displaying faults that occured during the flight
# and giving the user some space to explain it

#-------------------------------------------------------------------------------

from mlx.gui.common import *

#-------------------------------------------------------------------------------

## @package mlx.gui.faultexplain
#
# The widget and associated logic to display faults and allow the pilot to
# explain them. Each fault is displayed as the text it is accompanied by in the
# log and there is a text entry field where the user can enter the
# corresponding explanation. \ref FaultFrame belongs to one fault, while
# \ref FaultExplainWidget contains the collection of all frames, which is a
# VBox in a scrolled window.

#-------------------------------------------------------------------------------

class FaultFrame(gtk.Frame):
    """A frame containing the information about a single fault.

    It consists of a text view with the text of the fault and an editable text
    view for the explanation."""
    def __init__(self, faultText):
        """Construct the frame."""
        gtk.Frame.__init__(self)

        self._faultText = faultText

        vbox = gtk.VBox()

        self._fault = fault = gtk.TextView()
        fault.set_editable(False)
        fault.set_can_focus(False)
        fault.set_wrap_mode(WRAP_WORD)

        buffer = fault.get_buffer()
        self._faultTag  = buffer.create_tag("fault", weight=WEIGHT_BOLD)

        self.faultText = faultText

        faultAlignment = gtk.Alignment(xalign = 0.0, yalign = 0.0,
                                       xscale = 1.0, yscale = 0.0)
        faultAlignment.set_padding(padding_top = 0, padding_bottom = 0,
                                   padding_left = 2, padding_right = 2)
        faultAlignment.add(fault)
        vbox.pack_start(faultAlignment, True, True, 4)

        self._explanation = explanation = gtk.TextView()
        explanation.set_wrap_mode(WRAP_WORD)
        explanation.set_accepts_tab(False)
        explanation.set_size_request(-1, 100)

        buffer = explanation.get_buffer()
        buffer.connect("changed", self._explanationChanged)

        vbox.pack_start(explanation, True, True, 4)

        self.add(vbox)
        self.show_all()

        if pygobject:
            styleContext = self.get_style_context()
            color = styleContext.get_background_color(gtk.StateFlags.NORMAL)
            fault.override_background_color(0, color)
        else:
            style = self.rc_get_style()
            fault.modify_base(0, style.bg[0])

        self._hasExplanation = False

    @property
    def faultText(self):
        """Get the text of the fault."""
        return self._faultText

    @faultText.setter
    def faultText(self, faultText):
        """Update the text of the fault."""
        self._faultText = faultText

        buffer = self._fault.get_buffer()
        buffer.set_text(faultText)
        buffer.apply_tag(self._faultTag,
                         buffer.get_start_iter(), buffer.get_end_iter())

    @property
    def explanation(self):
        """Get the text of the explanation."""
        buffer = self._explanation.get_buffer()
        return buffer.get_text(buffer.get_start_iter(),
                               buffer.get_end_iter(), True)

    @explanation.setter
    def explanation(self, explanation):
        """Set the explanation."""
        self._explanation.get_buffer().set_text(explanation)

    @property
    def hasExplanation(self):
        """Determine if there is a valid explanation."""
        return self._hasExplanation

    @property
    def html(self):
        """Convert the contents of the widget into HTML."""
        return self._faultText + "<br/></b>" + self.explanation + "<b>"

    def setMnemonicFor(self, widget):
        """Set the explanation text view as the mnemonic widget for the given
        one."""
        widget.set_mnemonic_widget(self._explanation)

    def _explanationChanged(self, textBuffer):
        """Called when the explanation's text has changed."""
        hasExplanation = len(textBuffer.get_text(textBuffer.get_start_iter(),
                                                 textBuffer.get_end_iter(),
                                                 True))>3
        if self._hasExplanation != hasExplanation:
            self._hasExplanation = hasExplanation
            self.emit("explanation-changed", hasExplanation)

#-------------------------------------------------------------------------------

gobject.signal_new("explanation-changed", FaultFrame, gobject.SIGNAL_RUN_FIRST,
                   None, (bool,))

#-------------------------------------------------------------------------------

class FaultExplainWidget(gtk.Frame):
    """The widget for the failts and their explanations."""
    @staticmethod
    def getFaultFrame(alignment):
        """Get the fault frame from the given alignment."""
        return alignment.get_children()[0]

    def __init__(self, gui):
        gtk.Frame.__init__(self)

        self._gui = gui
        self.set_label(xstr("info_faults"))
        label = self.get_label_widget()
        label.set_use_underline(True)

        alignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 1.0, yscale = 1.0)
        alignment.set_padding(padding_top = 4, padding_bottom = 4,
                              padding_left = 4, padding_right = 4)

        self._outerBox = outerBox = gtk.EventBox()
        outerBox.add(alignment)

        self._innerBox = innerBox = gtk.EventBox()
        alignment.add(self._innerBox)

        alignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 1.0, yscale = 1.0)
        alignment.set_padding(padding_top = 0, padding_bottom = 0,
                              padding_left = 0, padding_right = 0)

        innerBox.add(alignment)

        scroller = gtk.ScrolledWindow()
        scroller.set_policy(POLICY_AUTOMATIC, POLICY_AUTOMATIC)
        scroller.set_shadow_type(SHADOW_NONE)

        self._faults = gtk.VBox()
        self._faults.set_homogeneous(False)
        scroller.add_with_viewport(self._faults)

        alignment.add(scroller)

        self._faultWidgets = {}

        self.add(outerBox)
        self.show_all()

        self._numFaults = 0
        self._numExplanations = 0

    @property
    def fullyExplained(self):
        """Indicate if the faults have been fully explained."""
        return self._numExplanations>=self._numFaults

    @property
    def html(self):
        """Convert the contents of the widget into HTML."""
        html = ""
        for alignment in self._faults.get_children():
            faultFrame = FaultExplainWidget.getFaultFrame(alignment)
            if html:
                html += "<br><br>"
            html += faultFrame.html
        return html

    def addFault(self, id, faultText):
        """Add a fault with the given ID and text."""

        alignment = gtk.Alignment(xalign = 0.0, yalign = 0.0,
                                      xscale = 1.0, yscale = 0.0)
        alignment.set_padding(padding_top = 2, padding_bottom = 2,
                              padding_left = 4, padding_right = 4)

        faultFrame = FaultFrame(faultText)
        if self._numFaults==0:
            faultFrame.setMnemonicFor(self.get_label_widget())
        faultFrame.connect("explanation-changed", self._explanationChanged)

        alignment.add(faultFrame)
        self._faults.pack_start(alignment, False, False, 4)
        self._faults.show_all()

        self._faultWidgets[id] = (alignment, faultFrame)

        self._updateStats(numFaults = self._numFaults + 1)

    def updateFault(self, id, faultText):
        """Update the text of the fault with the given ID."""
        self._faultWidgets[id][1].faultText = faultText

    def clearFault(self, id):
        """Clear (remove) the fault with the given ID."""
        (alignment, faultFrame) = self._faultWidgets[id]
        hasExplanation = faultFrame.hasExplanation

        children = self._faults.get_children()
        if alignment is children[0] and len(children)>1:
            faultFrame = FaultExplainWidget.getFaultFrame(children[1])
            faultFrame.setMnemonicFor(self.get_label_widget())

        self._faults.remove(alignment)
        self._faults.show_all()

        del self._faultWidgets[id]

        self._updateStats(numFaults = self._numFaults - 1,
                          numExplanations = self._numExplanations -
                          (1 if hasExplanation else 0))

    def setExplanation(self, id, explanation):
        """Set the explanation for the fault with the given ID"""
        self._faultWidgets[id][1].explanation = explanation

    def reset(self):
        """Reset the widget by removing all faults."""
        for (alignment, faultFrame) in self._faultWidgets.itervalues():
            self._faults.remove(alignment)
        self._faults.show_all()

        self._faultWidgets = {}
        self._numFaults = self._numExplanations = 0
        self._setColor()

    def set_sensitive(self, sensitive):
        """Set the sensitiviy of the widget.

        The outer event box's sensitivity is changed only."""
        self._outerBox.set_sensitive(sensitive)

    def _updateStats(self, numFaults = None, numExplanations = None):
        """Update the statistics.

        If the explanation status has changed, emit the corresponding
        signal."""
        before = self.fullyExplained

        if numFaults is None:
            numFaults = self._numFaults

        if numExplanations is None:
            numExplanations = self._numExplanations

        after = numExplanations >= numFaults

        self._numFaults = numFaults
        self._numExplanations = numExplanations

        if before!=after:
            self._setColor()
            self.emit("explanations-changed", after)

    def _explanationChanged(self, faultFrame, hasExplanation):
        """Called when the status of an explanation has changed."""
        self._updateStats(numExplanations = (self._numExplanations +
                                             (1 if hasExplanation else -1)))

    def _setColor(self):
        """Set the color to indicate if an unexplained fault is present or
        not."""
        allExplained = self._numExplanations >= self._numFaults
        if pygobject:
            styleContext = self.get_style_context()
            if allExplained:
                outerColour = innerColour = gdk.RGBA(red = 0.0, green=0.0,
                                                     blue=0.0, alpha=0.0)
            else:
                outerColour = \
                  styleContext.get_background_color(gtk.StateFlags.SELECTED)
                innerColour = self._gui.backgroundColour

            self._outerBox.override_background_color(gtk.StateFlags.NORMAL,
                                                     outerColour)
            self._innerBox.override_background_color(gtk.StateFlags.NORMAL,
                                                     innerColour)
        else:
            style = self.rc_get_style()
            self._outerBox.modify_bg(0, style.bg[0 if allExplained else 3])

#-------------------------------------------------------------------------------

gobject.signal_new("explanations-changed", FaultExplainWidget,
                   gobject.SIGNAL_RUN_FIRST, None, (bool,))
