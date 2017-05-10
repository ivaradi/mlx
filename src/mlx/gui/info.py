
from common import *

from mlx.gui.delaycodes import DelayCodeTable
from mlx.gui.faultexplain import FaultExplainWidget

from mlx.i18n import xstr
import mlx.const as const

#------------------------------------------------------------------------------

## @package mlx.gui.info
#
# The flight info tab.
#
# This module implements to \ref FlightInfo class, which is the widget for the
# extra information related to the flight. It contains a text area for the
# comments, the fault list widget, and the frame for the delay codes at the
# bottom in the centre.

#------------------------------------------------------------------------------

class FlightInfo(gtk.VBox):
    """The flight info tab."""
    @staticmethod
    def _createCommentArea(label):
        """Create a comment area.

        Returns a tuple of two items:
        - the top-level widget of the comment area, and
        - the comment text editor."""

        frame = gtk.Frame(label = label)
        label = frame.get_label_widget()
        label.set_use_underline(True)

        alignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 1.0, yscale = 1.0)
        alignment.set_padding(padding_top = 4, padding_bottom = 4,
                              padding_left = 8, padding_right = 8)

        scroller = gtk.ScrolledWindow()
        scroller.set_policy(POLICY_AUTOMATIC, POLICY_AUTOMATIC)
        scroller.set_shadow_type(SHADOW_IN)

        comments = gtk.TextView()
        comments.set_wrap_mode(WRAP_WORD)
        scroller.add(comments)
        alignment.add(scroller)
        frame.add(alignment)

        label.set_mnemonic_widget(comments)

        return (frame, comments)

    def __init__(self, gui, callbackObject = None):
        """Construct the flight info tab."""
        super(FlightInfo, self).__init__()
        self._gui = gui
        self._callbackObject = callbackObject

        self._commentsAlignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                                xscale = 1.0, yscale = 1.0)
        commentsBox = gtk.HBox()
        commentsBox.set_homogeneous(True)

        (frame, self._comments) = FlightInfo._createCommentArea(xstr("info_comments"))
        commentsBox.pack_start(frame, True, True, 8)
        self._comments.get_buffer().connect("changed", self._commentsChanged)

        self._faultExplainWidget = FaultExplainWidget(gui)
        self._faultExplainWidget.connect("explanations-changed",
                                         self._faultExplanationsChanged)
        commentsBox.pack_start(self._faultExplainWidget, True, True, 8)

        self._commentsAlignment.add(commentsBox)
        self.pack_start(self._commentsAlignment, True, True, 8)

        frame = gtk.Frame(label = xstr("info_delay"))
        label = frame.get_label_widget()
        label.set_use_underline(True)

        alignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 1.0, yscale = 1.0)
        alignment.set_padding(padding_top = 4, padding_bottom = 4,
                              padding_left = 8, padding_right = 8)

        self._delayCodeTable = table = DelayCodeTable(self)
        self._delayWindow = scrolledWindow = gtk.ScrolledWindow()
        scrolledWindow.add(table)
        scrolledWindow.set_size_request(-1, 185)
        scrolledWindow.set_policy(POLICY_AUTOMATIC, POLICY_AUTOMATIC)
        scrolledWindow.set_shadow_type(SHADOW_IN)

        alignment.add(scrolledWindow)
        frame.add(alignment)

        self._delayAlignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                             xscale = 1.0, yscale = 1.0)
        self._delayAlignment.add(frame)
        self._delayAlignment.set_padding(padding_top = 0, padding_bottom = 0,
                                         padding_left = 8, padding_right = 8)

        self.pack_start(self._delayAlignment, False, False, 8)

    @property
    def comments(self):
        """Get the comments."""
        buffer = self._comments.get_buffer()
        return text2unicode(buffer.get_text(buffer.get_start_iter(),
                                            buffer.get_end_iter(), True))

    @comments.setter
    def comments(self, comments):
        """Set the comments."""
        self._comments.get_buffer().set_text(comments)

    @property
    def hasComments(self):
        """Get whether there is any text in comments field."""
        return self._comments.get_buffer().get_char_count()>0

    @property
    def faultsAndExplanations(self):
        """Get the faults and explanations as HTML."""
        return self._faultExplainWidget.html

    @property
    def delayCodes(self):
        """Get the list of delay codes checked by the user."""
        return self._delayCodeTable.delayCodes

    @property
    def hasDelayCode(self):
        """Determine if there is at least one delay code selected."""
        return self._delayCodeTable.hasDelayCode

    @property
    def faultsFullyExplained(self):
        """Determine if all the faults have been explained by the pilot."""
        return self._faultExplainWidget.fullyExplained

    def addFault(self, id, faultText):
        """Add a fault to the list of faults."""
        self._faultExplainWidget.addFault(id, faultText)

    def updateFault(self, id, faultText):
        """Update a fault to the list of faults."""
        self._faultExplainWidget.updateFault(id, faultText)

    def clearFault(self, id):
        """Clear a fault to the list of faults."""
        self._faultExplainWidget.clearFault(id)

    def setExplanation(self, id, explanation):
        """Set the explanation of the given fault."""
        self._faultExplainWidget.setExplanation(id, explanation)

    def enable(self, aircraftType):
        """Enable the flight info tab."""
        self._comments.set_sensitive(True)
        self._faultExplainWidget.set_sensitive(True)
        self._delayCodeTable.setType(aircraftType)
        self._delayWindow.set_sensitive(True)
        self._delayCodeTable.setStyle()

    def disable(self):
        """Enable the flight info tab."""
        self._comments.set_sensitive(False)
        self._faultExplainWidget.set_sensitive(False)
        self._delayWindow.set_sensitive(False)
        self._delayCodeTable.setStyle()

    def reset(self):
        """Reset the flight info tab."""
        self._comments.get_buffer().set_text("")
        self._faultExplainWidget.reset()
        self._delayCodeTable.reset()

    def activateDelayCode(self, code):
        """Active the checkbox corresponding to the given code."""
        self._delayCodeTable.activateCode(code)

    def delayCodesChanged(self):
        """Callewd when the delay codes have changed."""
        if self._callbackObject is None:
            self._gui.delayCodesChanged()
        else:
            self._callbackObject.delayCodesChanged()

    def _commentsChanged(self, textbuffer):
        """Called when the comments have changed."""
        if self._callbackObject is None:
            self._gui.commentsChanged()
        else:
            self._callbackObject.commentsChanged()

    def _faultExplanationsChanged(self, faultExplainWidget, fullyExplained):
        """Called when the status of the fault explanations has changed."""
        if self._callbackObject is None:
            self._gui.faultExplanationsChanged()
        else:
            self._callbackObject.faultExplanationsChanged()
