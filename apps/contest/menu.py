"""
apps/contest/menu.py
ON3RT Radio Suite - Contest Logbook
"""

from PySide6.QtGui import QAction


def create_menu(window):
    menubar = window.menuBar()

    file_menu = menubar.addMenu("&Fichier")

    act_new = QAction("Nouveau concours", window)
    act_open = QAction("Ouvrir...", window)
    act_save = QAction("Enregistrer", window)
    act_exit = QAction("Quitter", window)

    act_new.triggered.connect(window.new_contest)
    act_open.triggered.connect(window.open_contest)
    act_save.triggered.connect(window.save_contest_as)
    act_exit.triggered.connect(window.close)

    file_menu.addAction(act_new)
    file_menu.addAction(act_open)
    file_menu.addSeparator()
    file_menu.addAction(act_save)
    file_menu.addSeparator()
    file_menu.addAction(act_exit)

    contest_menu = menubar.addMenu("&Contest")
    act_import_adif = QAction("Import ADIF", window)
    act_export_adif = QAction("Export ADIF", window)
    act_export_cabrillo = QAction("Export Cabrillo", window)
    act_import_adif.triggered.connect(window.import_adif)
    act_export_adif.triggered.connect(window.export_adif)
    act_export_cabrillo.triggered.connect(window.export_cabrillo)
    contest_menu.addAction(act_import_adif)
    contest_menu.addAction(act_export_adif)
    contest_menu.addAction(act_export_cabrillo)

    tools_menu = menubar.addMenu("&Outils")
    act_prefs = QAction("Préférences", window)
    act_prefs.triggered.connect(window.edit_contest_properties)
    tools_menu.addAction(act_prefs)

    help_menu = menubar.addMenu("&Aide")
    act_about = QAction("À propos", window)
    act_about.triggered.connect(window.show_about)
    help_menu.addAction(act_about)

    return menubar
