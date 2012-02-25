# The main program

from .gui.gui import GUI

def main():
    """The main operation of the program."""
    # menu = gtk.Menu()  
    # item = gtk.MenuItem()  
    # item.set_label("Menu Item")  
    # item.show()  
    # menu.append(item)  

    # menu.show()  

    # if appIndicator:
    #     if pygobject:
    #         ind = appindicator.Indicator.new ("mava-logger-x",
    #                                           "/home/vi/munka/repules/mlx/src/logo.ico",
    #                                           #"indicator-messages",
    #                                           appindicator.IndicatorCategory.APPLICATION_STATUS)
    #         ind.set_status (appindicator.IndicatorStatus.ACTIVE)
    #     else:
    #         ind = appindicator.Indicator ("mava-logger-x",
    #                                       "/home/vi/munka/repules/mlx/src/logo.ico",
    #                                       appindicator.CATEGORY_APPLICATION_STATUS)
    #         ind.set_status (appindicator.STATUS_ACTIVE)

    #     ind.set_menu(menu)
    #     #ind.set_icon("distributor-logo")
    # else:
    #     def popup_menu(status, button, time):
    #         menu.popup(None, None, gtk.status_icon_position_menu,
    #                    button, time, status)
    #     statusIcon = gtk.StatusIcon()
    #     #statusIcon.set_from_stock(gtk.STOCK_FIND)
    #     statusIcon.set_from_file("logo.ico")
    #     statusIcon.set_tooltip_markup("MAVA Logger X")
    #     statusIcon.set_visible(True)
    #     statusIcon.connect('popup-menu', popup_menu)

    gui = GUI()
    gui.build()
    gui.run()

if __name__ == "__main__":
    main()


