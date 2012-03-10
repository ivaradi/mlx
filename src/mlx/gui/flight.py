# The flight handling "wizard"

from mlx.gui.common import *

#-----------------------------------------------------------------------------

class Page(gtk.VBox):
    """A page in the flight wizard."""
    def __init__(self, wizard):
        """Construct the page."""
        super(Page, self).__init__()
        self._wizard = wizard

#-----------------------------------------------------------------------------

class LoginPage(Page):
    """The login page."""
    def __init__(self, wizard):
        """Construct the login page."""
        super(LoginPage, self).__init__(wizard)

        alignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 0, yscale = 0.3)
        label = gtk.Label("Enter your pilot's ID and password to\n"
                          "log in to the MAVA website and download\n"
                          "your booked flights")
        label.set_justify(gtk.Justification.CENTER if pygobject
                          else gtk.JUSTIFY_CENTER)
        alignment.add(label)
        self.pack_start(alignment, True, True, 0)

        alignment = gtk.Alignment(xalign = 0.5, yalign = 0.5,
                                  xscale = 0, yscale = 0.0)

        table = gtk.Table(2, 2)
        table.set_row_spacings(4)
        table.set_col_spacings(32)
        alignment.add(table)

        labelAlignment = gtk.Alignment(xalign=1.0, xscale=0.0)
        labelAlignment.add(gtk.Label("Pilot ID:"))
        table.attach(labelAlignment, 0, 1, 0, 1)

        self._pilotID = gtk.Entry()
        self._pilotID.connect("changed", self._setLoginButton)
        table.attach(self._pilotID, 1, 2, 0, 1)

        labelAlignment = gtk.Alignment(xalign=1.0, xscale=0.0)
        labelAlignment.add(gtk.Label("Password:"))
        table.attach(labelAlignment, 0, 1, 1, 2)

        self._password = gtk.Entry()
        self._password.set_visibility(False)
        self._password.connect("changed", self._setLoginButton)
        table.attach(self._password, 1, 2, 1, 2)

        self.pack_start(alignment, True, True, 0)

        alignment = gtk.Alignment(xalign = 1.0, xscale=0.0)
        alignment.set_padding(padding_top = 4, padding_bottom = 10,
                              padding_left = 16, padding_right = 16)
        
        self._loginButton = gtk.Button("Login")
        self._loginButton.set_sensitive(False)
        self._loginButton.connect("clicked", self._loginClicked)
        
        alignment.add(self._loginButton)
        self.pack_start(alignment, False, False, 0)

        config = self._wizard.gui.config
        self._pilotID.set_text(config.pilotID)
        self._password.set_text(config.password)

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
                config.password = self._password.get_text()
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
        super(FlightSelectionPage, self).__init__(wizard)
        self.pack_start(gtk.Label("Hello, te lo!"), False, False, 0)

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
    
#-----------------------------------------------------------------------------

