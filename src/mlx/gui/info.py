#The Flight Info tab

from common import *

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

        self._loadingProblems = gtk.CheckButton("L_oading problems")
        self._loadingProblems.set_use_underline(True)
        table.attach(self._loadingProblems, 0, 1, 0, 1)

        self._vatsimProblem = gtk.CheckButton("_VATSIM problem")
        self._vatsimProblem.set_use_underline(True)
        table.attach(self._vatsimProblem, 1, 2, 0, 1)

        self._netProblems = gtk.CheckButton("_Net problems")
        self._netProblems.set_use_underline(True)
        table.attach(self._netProblems, 0, 1, 1, 2)

        self._controllersFault = gtk.CheckButton("Controllers _fault")
        self._controllersFault.set_use_underline(True)
        table.attach(self._controllersFault, 1, 2, 1, 2)

        self._systemCrash = gtk.CheckButton("S_ystem crash/freeze")
        self._systemCrash.set_use_underline(True)
        table.attach(self._systemCrash, 0, 1, 2, 3)

        self._navigationProblem = gtk.CheckButton("Navi_gation problem")
        self._navigationProblem.set_use_underline(True)
        table.attach(self._navigationProblem, 1, 2, 2, 3)

        self._trafficProblems = gtk.CheckButton("T_raffic problems")
        self._trafficProblems.set_use_underline(True)
        table.attach(self._trafficProblems, 0, 1, 3, 4)

        self._apronProblem = gtk.CheckButton("_Apron navigation problem")
        self._apronProblem.set_use_underline(True)
        table.attach(self._apronProblem, 1, 2, 3, 4)

        self._weatherProblems = gtk.CheckButton("_Weather problems")
        self._weatherProblems.set_use_underline(True)
        table.attach(self._weatherProblems, 0, 1, 4, 5)

        self._personalReasons = gtk.CheckButton("_Personal reasons")
        self._personalReasons.set_use_underline(True)
        table.attach(self._personalReasons, 1, 2, 4, 5)

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
