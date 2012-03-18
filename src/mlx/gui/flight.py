# The flight handling "wizard"

from mlx.gui.common import *

#-----------------------------------------------------------------------------

class Page(gtk.Alignment):
    """A page in the flight wizard."""
    def __init__(self, wizard, title, help):
        """Construct the page."""
        super(Page, self).__init__(xalign = 0.0, yalign = 0.0,
                                   xscale = 1.0, yscale = 1.0)
        self.set_padding(padding_top = 4, padding_bottom = 4,
                         padding_left = 12, padding_right = 12)

        frame = gtk.Frame()
        self.add(frame)

        style = self.get_style() if pygobject else self.rc_get_style()

        self._vbox = gtk.VBox()
        frame.add(self._vbox)

        eventBox = gtk.EventBox()
        eventBox.modify_bg(0, style.bg[3])

        alignment = gtk.Alignment(xalign = 0.0, xscale = 0.0)
        
        label = gtk.Label(title)
        label.modify_fg(0, style.fg[3])
        label.modify_font(pango.FontDescription("bold 24"))
        alignment.set_padding(padding_top = 4, padding_bottom = 4,
                              padding_left = 6, padding_right = 0)
                              
        alignment.add(label)
        eventBox.add(alignment)
        
        self._vbox.pack_start(eventBox, False, False, 0)

        alignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 0, yscale = 0.3)
        label = gtk.Label(help)
        label.set_justify(gtk.Justification.CENTER if pygobject
                          else gtk.JUSTIFY_CENTER)
        alignment.add(label)
        self._vbox.pack_start(alignment, True, True, 0)

        self._mainAlignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                            xscale = 0, yscale = 0.0)
        self._vbox.pack_start(self._mainAlignment, True, True, 0)

        buttonAlignment =  gtk.Alignment(xalign = 1.0, xscale=0.0)
        buttonAlignment.set_padding(padding_top = 4, padding_bottom = 10,
                                    padding_left = 16, padding_right = 16)

        self._buttonBox = gtk.HButtonBox()
        self._defaultButton = None
        buttonAlignment.add(self._buttonBox)

        self._vbox.pack_start(buttonAlignment, False, False, 0)

        self._wizard = wizard

    def setMainWidget(self, widget):
        """Set the given widget as the main one."""
        self._mainAlignment.add(widget)

    def addButton(self, label, default = False):
        """Add a button with the given label.

        Return the button object created."""
        button = gtk.Button(label)
        self._buttonBox.add(button)
        if default:
            button.set_can_default(True)
            self._defaultButton = button
        return button

    def grabDefault(self):
        """If the page has a default button, make it the default one."""
        if self._defaultButton is not None:
            self._defaultButton.grab_default()
    
#-----------------------------------------------------------------------------

class LoginPage(Page):
    """The login page."""
    def __init__(self, wizard):
        """Construct the login page."""
        help = "Enter your MAVA pilot's ID and password to\n" \
        "log in to the MAVA website and download\n" \
        "your booked flights."
        super(LoginPage, self).__init__(wizard, "Login", help)

        table = gtk.Table(2, 3)
        table.set_row_spacings(4)
        table.set_col_spacings(32)
        self.setMainWidget(table)

        labelAlignment = gtk.Alignment(xalign=1.0, xscale=0.0)
        label = gtk.Label("Pilot _ID:")
        label.set_use_underline(True)
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, 0, 1)

        self._pilotID = gtk.Entry()
        self._pilotID.connect("changed", self._setLoginButton)
        self._pilotID.set_tooltip_text("Enter your MAVA pilot's ID. This "
                                       "usually starts with a "
                                       "'P' followed by 3 digits.")
        table.attach(self._pilotID, 1, 2, 0, 1)
        label.set_mnemonic_widget(self._pilotID)

        labelAlignment = gtk.Alignment(xalign=1.0, xscale=0.0)
        label = gtk.Label("_Password:")
        label.set_use_underline(True)
        labelAlignment.add(label)
        table.attach(labelAlignment, 0, 1, 1, 2)

        self._password = gtk.Entry()
        self._password.set_visibility(False)
        self._password.connect("changed", self._setLoginButton)
        self._password.set_tooltip_text("Enter the password for your pilot's ID")
        table.attach(self._password, 1, 2, 1, 2)
        label.set_mnemonic_widget(self._password)

        self._rememberButton = gtk.CheckButton("_Remember password")
        self._rememberButton.set_use_underline(True)
        self._rememberButton.set_tooltip_text("If checked, your password will "
                                              "be stored, so that you should "
                                              "not have to enter it every time. "
                                              "Note, however, that the password "
                                              "is stored as text, and anybody "
                                              "who can access your files will "
                                              "be able to read it.")
        table.attach(self._rememberButton, 1, 2, 2, 3, ypadding = 8)

        self._loginButton = self.addButton("_Login", default = True)
        self._loginButton.set_sensitive(False)
        self._loginButton.set_use_underline(True)
        self._loginButton.connect("clicked", self._loginClicked)
        self._loginButton.set_tooltip_text("Click to log in.")
        
        config = self._wizard.gui.config
        self._pilotID.set_text(config.pilotID)
        self._password.set_text(config.password)
        self._rememberButton.set_active(config.rememberPassword)

    def _setLoginButton(self, entry):
        """Set the login button's sensitivity.

        The button is sensitive only if both the pilot ID and the password
        fields contain values."""
        self._loginButton.set_sensitive(self._pilotID.get_text()!="" and
                                        self._password.get_text()!="")

    def _loginClicked(self, button):
        """Called when the login button was clicked."""
        self._wizard.gui.webHandler.login(self._pilotID.get_text(),
                                          self._password.get_text(),
                                          self._loginResultCallback)

    def _loginResultCallback(self, returned, result):
        """The login result callback, called in the web handler's thread."""
        gobject.idle_add(self._handleLoginResult, returned, result)

    def _handleLoginResult(self, returned, result):
        """Handle the login result."""
        if returned:
            if result.loggedIn:
                config = self._wizard.gui.config

                config.pilotID = self._pilotID.get_text()

                rememberPassword = self._rememberButton.get_active()                
                config.password = self._password.get_text() if rememberPassword  \
                                  else ""

                config.rememberPassword = rememberPassword
                
                config.save()
                self._wizard.nextPage()
            else:
                dialog = gtk.MessageDialog(type = MESSAGETYPE_ERROR,
                                           buttons = BUTTONSTYPE_OK,
                                           message_format =
                                           "Invalid pilot's ID or password.")
                dialog.format_secondary_markup("Check the ID and try to reenter"
                                               " the password.")
                dialog.run()
                dialog.hide()
        else:
            dialog = gtk.MessageDialog(type = MESSAGETYPE_ERROR,
                                       buttons = BUTTONSTYPE_OK,
                                       message_format = 
                                       "Failed to connect to the MAVA website.")
            dialog.format_secondary_markup("Try again in a few minutes.")
            dialog.run()
            dialog.hide()

#-----------------------------------------------------------------------------

class FlightSelectionPage(Page):
    """The page to select the flight."""
    def __init__(self, wizard):
        """Construct the flight selection page."""
        super(FlightSelectionPage, self).__init__(wizard, "Flight selection",
                                                  "Hello, te lo!")

#-----------------------------------------------------------------------------

class Wizard(gtk.VBox):
    """The flight wizard."""
    def __init__(self, gui):
        """Construct the wizard."""
        super(Wizard, self).__init__()

        self.gui = gui

        self._pages = []
        self._currentPage = None
        
        self._pages.append(LoginPage(self))
        self._pages.append(FlightSelectionPage(self))

        self.setCurrentPage(0)

    def setCurrentPage(self, index):
        """Set the current page to the one with the given index."""
        assert index < len(self._pages)
        
        if self._currentPage is not None:
            self.remove(self._pages[self._currentPage])

        self._currentPage = index
        self.add(self._pages[index])
        self.show_all()

    def nextPage(self):
        """Go to the next page."""
        self.setCurrentPage(self._currentPage + 1)

    def grabDefault(self):
        """Make the default button of the current page the default."""
        self._pages[self._currentPage].grabDefault()
    
#-----------------------------------------------------------------------------

