# Module for editing checklists

#------------------------------------------------------------------------------

from common import *

from mlx.i18n import xstr

#------------------------------------------------------------------------------

class ChecklistEditor(gtk.Dialog):
    """The dialog to edit the checklists."""
    def __init__(self, gui):
        super(ChecklistEditor, self).__init__(WINDOW_TITLE_BASE + " " +
                                              xstr("chklst_title"),
                                              gui.mainWindow,
                                              DIALOG_MODAL)

        self.add_button(xstr("button_cancel"), RESPONSETYPE_REJECT)
        self.add_button(xstr("button_ok"), RESPONSETYPE_ACCEPT)

        contentArea = self.get_content_area()


        self._fileChooser = gtk.FileChooserWidget()
        self._fileChooser.set_select_multiple(True)

        self._fileChooser.set_current_folder("/home/vi")
        
        contentArea.pack_start(self._fileChooser, True, True, 4)

    def run(self):
        """Run the checklist editor dialog."""
        self.show_all()
        response = super(ChecklistEditor, self).run()
        self.hide()

#------------------------------------------------------------------------------
