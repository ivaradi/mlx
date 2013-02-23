
from common import *

from mlx.gui.delaycodes import DelayCodeTable

from mlx.i18n import xstr
import mlx.const as const

#------------------------------------------------------------------------------

## @package mlx.gui.info
#
# The flight info tab.
#
# This module implements to \ref FlightInfo class, which is the widget for the
# extra information related to the flight. It contains text areas for the
# comments and the flight defects at the top next to each other, and the frame
# for the delay codes at the bottom in the centre.

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

    def __init__(self, gui):
        """Construct the flight info tab."""
        super(FlightInfo, self).__init__()
        self._gui = gui

        self._commentsAlignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                                xscale = 1.0, yscale = 1.0)
        commentsBox = gtk.HBox()

        (frame, self._comments) = FlightInfo._createCommentArea(xstr("info_comments"))
        commentsBox.pack_start(frame, True, True, 8)
        self._comments.get_buffer().connect("changed", self._commentsChanged)

        (frame, self._flightDefects) = \
             FlightInfo._createCommentArea(xstr("info_defects"))
        commentsBox.pack_start(frame, True, True, 8)

        self._commentsAlignment.add(commentsBox)
        self.pack_start(self._commentsAlignment, True, True, 8)

        frame = gtk.Frame(label = xstr("info_delay"))
        label = frame.get_label_widget()
        label.set_use_underline(True)

        alignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)
        alignment.set_padding(padding_top = 4, padding_bottom = 4,
                              padding_left = 8, padding_right = 8)

        self._delayCodeTable = table = DelayCodeTable()
        self._delayWindow = scrolledWindow = gtk.ScrolledWindow()
        scrolledWindow.add(table)
        scrolledWindow.set_size_request(600, 175)
        scrolledWindow.set_policy(POLICY_AUTOMATIC, POLICY_AUTOMATIC)
        scrolledWindow.set_shadow_type(SHADOW_IN)

        alignment.add(scrolledWindow)
        frame.add(alignment)

        self._delayAlignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                             xscale = 0.0, yscale = 0.0)
        self._delayAlignment.add(frame)

        self.pack_start(self._delayAlignment, False, False, 8)

    @property
    def comments(self):
        """Get the comments."""
        buffer = self._comments.get_buffer()
        return text2unicode(buffer.get_text(buffer.get_start_iter(),
                                            buffer.get_end_iter(), True))

    @property
    def hasComments(self):
        """Get whether there is any text in comments field."""
        return self._comments.get_buffer().get_char_count()>0

    @property
    def flightDefects(self):
        """Get the flight defects."""
        buffer = self._flightDefects.get_buffer()
        return text2unicode(buffer.get_text(buffer.get_start_iter(),
                                            buffer.get_end_iter(), True))

    @property
    def delayCodes(self):
        """Get the list of delay codes checked by the user."""
        return self._delayCodeTable.delayCodes

    def enable(self, aircraftType):
        """Enable the flight info tab."""
        self._comments.set_sensitive(True)
        self._flightDefects.set_sensitive(True)
        self._delayCodeTable.setType(aircraftType)
        self._delayWindow.set_sensitive(True)
        self._delayCodeTable.setStyle()

    def disable(self):
        """Enable the flight info tab."""
        self._comments.set_sensitive(False)
        self._flightDefects.set_sensitive(False)
        self._delayWindow.set_sensitive(False)
        self._delayCodeTable.setStyle()

    def reset(self):
        """Reset the flight info tab."""
        self._comments.get_buffer().set_text("")
        self._flightDefects.get_buffer().set_text("")
        self._delayCodeTable.reset()

    def _commentsChanged(self, textbuffer):
        """Called when the comments have changed."""
        self._gui.updateRTO(inLoop = True)
