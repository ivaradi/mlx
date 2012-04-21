#The Flight Info tab

from common import *

import mlx.const as const

class FlightInfo(gtk.VBox):
    """The flight info tab."""
    _delayCodes = [ (const.DELAYCODE_LOADING, "L_oading problems"),
                    (const.DELAYCODE_VATSIM, "_VATSIM problem"),
                    (const.DELAYCODE_NETWORK, "_Net problems"),
                    (const.DELAYCODE_CONTROLLER, "Controller's _fault"),
                    (const.DELAYCODE_SYSTEM, "S_ystem crash/freeze"),
                    (const.DELAYCODE_NAVIGATION, "Navi_gation problem"),
                    (const.DELAYCODE_TRAFFIC, "T_raffic problems"),
                    (const.DELAYCODE_APRON, "_Apron navigation problem"),
                    (const.DELAYCODE_WEATHER, "_Weather problems"),
                    (const.DELAYCODE_PERSONAL, "_Personal reasons") ]
    
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

        (frame, self._comments) = FlightInfo._createCommentArea("_Comments")
        commentsBox.pack_start(frame, True, True, 8)

        (frame, self._flightDefects) = FlightInfo._createCommentArea("Flight _defects")
        commentsBox.pack_start(frame, True, True, 8)

        self._commentsAlignment.add(commentsBox)
        self.pack_start(self._commentsAlignment, True, True, 8)

        frame = gtk.Frame(label = "Delay codes")
        label = frame.get_label_widget()
        label.set_use_underline(True)

        alignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 0.0, yscale = 0.0)
        alignment.set_padding(padding_top = 4, padding_bottom = 4,
                              padding_left = 8, padding_right = 8)

        table = gtk.Table(5, 2)
        table.set_col_spacings(16)

        row = 0
        column = 0

        self._delayCodeWidgets = []
        for (_code, label) in FlightInfo._delayCodes:
            button = gtk.CheckButton(label)
            button.set_use_underline(True)
            table.attach(button, column, column + 1, row, row + 1)
            self._delayCodeWidgets.append(button)
            if column==0:
                column += 1
            else:
                row += 1
                column = 0

        alignment.add(table)
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
    def flightDefects(self):
        """Get the flight defects."""
        buffer = self._flightDefects.get_buffer()
        return text2unicode(buffer.get_text(buffer.get_start_iter(),
                                            buffer.get_end_iter(), True))

    @property
    def delayCodes(self):
        """Get the list of delay codes checked by the user."""
        codes =  []
        for index in range(0, len(FlightInfo._delayCodes)):
            if self._delayCodeWidgets[index].get_active():
                codes.append(FlightInfo._delayCodes[index][0])
        return codes
            
    def enable(self):
        """Enable the flight info tab."""
        #gobject.idle_add(self.set_sensitive, True)
        self._commentsAlignment.set_sensitive(True)
        self._delayAlignment.set_sensitive(True)
        
    def disable(self):
        """Enable the flight info tab."""
        #gobject.idle_add(self.set_sensitive, False)
        self._commentsAlignment.set_sensitive(False)
        self._delayAlignment.set_sensitive(False)

    def reset(self):
        """Reset the flight info tab."""
        self._comments.get_buffer().set_text("")
        self._flightDefects.get_buffer().set_text("")

        self._loadingProblems.set_active(False)
        self._vatsimProblem.set_active(False)
        self._netProblems.set_active(False)
        self._controllersFault.set_active(False)
        self._systemCrash.set_active(False)
        self._navigationProblem.set_active(False)
        self._trafficProblems.set_active(False)
        self._apronProblem.set_active(False)
        self._weatherProblems.set_active(False)
        self._personalReasons.set_active(False)
