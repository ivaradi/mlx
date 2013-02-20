
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
    def _delayCodes():
        """Get an array of delay codes."""
        return [ (const.DELAYCODE_LOADING, xstr("info_delay_loading")),
                 (const.DELAYCODE_VATSIM, xstr("info_delay_vatsim")),
                 (const.DELAYCODE_NETWORK, xstr("info_delay_net")),
                 (const.DELAYCODE_CONTROLLER, xstr("info_delay_atc")),
                 (const.DELAYCODE_SYSTEM, xstr("info_delay_system")),
                 (const.DELAYCODE_NAVIGATION, xstr("info_delay_nav")),
                 (const.DELAYCODE_TRAFFIC, xstr("info_delay_traffic")),
                 (const.DELAYCODE_APRON, xstr("info_delay_apron")),
                 (const.DELAYCODE_WEATHER, xstr("info_delay_weather")),
                 (const.DELAYCODE_PERSONAL, xstr("info_delay_personal")) ]

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
        # FIXME: these should be constants
        scroller.set_policy(gtk.PolicyType.AUTOMATIC if pygobject
                            else gtk.POLICY_AUTOMATIC,
                            gtk.PolicyType.AUTOMATIC if pygobject
                            else gtk.POLICY_AUTOMATIC)
        scroller.set_shadow_type(gtk.ShadowType.IN if pygobject
                                 else gtk.SHADOW_IN)
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


        # self._delayTable = table = gtk.Table(5, 2)
        # table.set_col_spacings(16)

        # row = 0
        # column = 0

        # self._delayCodeWidgets = []
        # for (_code, label) in FlightInfo._delayCodes():
        #     button = gtk.CheckButton(label)
        #     button.set_use_underline(True)
        #     table.attach(button, column, column + 1, row, row + 1)
        #     self._delayCodeWidgets.append(button)
        #     if column==0:
        #         column += 1
        #     else:
        #         row += 1
        #         column = 0
        self._delayTable = table = DelayCodeTable()
        self._delayWindow = scrolledWindow = gtk.ScrolledWindow()
        scrolledWindow.add(table)
        scrolledWindow.set_size_request(400, 150)
        scrolledWindow.set_policy(gtk.PolicyType.ALWAYS if pygobject
                                  else gtk.POLICY_AUTOMATIC,
                                  gtk.PolicyType.ALWAYS if pygobject
                                  else gtk.POLICY_AUTOMATIC)
        scrolledWindow.set_shadow_type(gtk.ShadowType.IN if pygobject
                                       else gtk.SHADOW_IN)

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
        codes =  []
        delayCodes = FlightInfo._delayCodes()
        for index in range(0, len(delayCodes)):
            if self._delayCodeWidgets[index].get_active():
                codes.append(delayCodes[index][0])
        return codes

    def enable(self):
        """Enable the flight info tab."""
        self._comments.set_sensitive(True)
        self._flightDefects.set_sensitive(True)
        self._delayWindow.set_sensitive(True)

    def disable(self):
        """Enable the flight info tab."""
        self._comments.set_sensitive(False)
        self._flightDefects.set_sensitive(False)
        self._delayWindow.set_sensitive(False)

    def reset(self):
        """Reset the flight info tab."""
        self._comments.get_buffer().set_text("")
        self._flightDefects.get_buffer().set_text("")

        for widget in self._delayCodeWidgets:
            widget.set_active(False)

    def _commentsChanged(self, textbuffer):
        """Called when the comments have changed."""
        self._gui.updateRTO(inLoop = True)
