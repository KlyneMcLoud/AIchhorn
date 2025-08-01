# fluxframe/gui.py
import sys
import threading
from PyQt5 import QtWidgets, QtCore, QtGui

class LogPanel(QtWidgets.QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
    def log(self, msg):
        self.append(msg)
        self.moveCursor(QtGui.QTextCursor.End)

class FluxFrameGUI(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FluxFrame v0.1")
        self.setGeometry(200, 200, 700, 400)

        # Zentrales Widget
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)

        # Log Panel
        self.log_panel = LogPanel()
        layout.addWidget(self.log_panel)

        # Button-Panel
        button_panel = QtWidgets.QHBoxLayout()
        self.btn_start = QtWidgets.QPushButton("Watchdog START")
        self.btn_stop = QtWidgets.QPushButton("Watchdog STOP")
        self.btn_stop.setEnabled(False)
        button_panel.addWidget(self.btn_start)
        button_panel.addWidget(self.btn_stop)
        layout.addLayout(button_panel)

        # Checkbox: Sync-Ordner überwachen
        self.chk_sync_watch = QtWidgets.QCheckBox("Sync-Ordner überwachen")
        layout.addWidget(self.chk_sync_watch)

        # Intervallfeld
        time_panel = QtWidgets.QHBoxLayout()
        self.lbl_interval = QtWidgets.QLabel("Update-Intervall (Sek.):")
        self.input_interval = QtWidgets.QLineEdit("10")
        self.input_interval.setValidator(QtGui.QIntValidator(1, 9999))
        self.input_interval.setMaximumWidth(70)
        self.input_interval.setEnabled(False)
        time_panel.addWidget(self.lbl_interval)
        time_panel.addWidget(self.input_interval)
        layout.addLayout(time_panel)

        # Signals
        self.btn_start.clicked.connect(self.start_watchdog)
        self.btn_stop.clicked.connect(self.stop_watchdog)
        self.chk_sync_watch.stateChanged.connect(self.toggle_sync_watchdog)

        # Thread-Objekt für den Watchdog
        self.watchdog_thread = None
        self.watchdog_running = threading.Event()

    def log(self, msg):
        self.log_panel.log(msg)

    def start_watchdog(self):
        if self.watchdog_thread and self.watchdog_thread.is_alive():
            self.log("Watchdog already running.")
            return
        self.watchdog_running.set()
        self.watchdog_thread = threading.Thread(target=self.watchdog_loop)
        self.watchdog_thread.start()
        self.log("Watchdog gestartet.")
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)

    def stop_watchdog(self):
        self.watchdog_running.clear()
        self.log("Watchdog gestoppt (wird beim nächsten Event beendet).")
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)

    def watchdog_loop(self):
        self.log("Watchdog-Thread aktiv (Mock-Modus).")
        while self.watchdog_running.is_set():
            QtCore.QThread.msleep(500)
        self.log("Watchdog-Thread wurde beendet.")

    def toggle_sync_watchdog(self, state):
        if state == QtCore.Qt.Checked:
            self.input_interval.setEnabled(True)
            self.log("Sync-Ordner Überwachung AKTIVIERT")
            from fluxframe.watchdog import start_sync_watchdog
            interval_getter = lambda: self.input_interval.text()
            start_sync_watchdog(self.log, interval_getter)
        else:
            self.input_interval.setEnabled(False)
            self.log("Sync-Ordner Überwachung DEAKTIVIERT")
            from fluxframe.watchdog import stop_sync_watchdog
            stop_sync_watchdog(self.log)

def run_gui():
    app = QtWidgets.QApplication(sys.argv)
    gui = FluxFrameGUI()
    gui.show()
    sys.exit(app.exec_())
