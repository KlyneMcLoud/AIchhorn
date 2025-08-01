import sys
from PyQt5 import QtWidgets, QtCore, QtGui
from .watchdog import SyncFolderWatcher

class LogPanel(QtWidgets.QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)

    @QtCore.pyqtSlot(str)
    def log(self, msg):
        self.append(msg)
        self.moveCursor(QtGui.QTextCursor.End)

class FluxFrameGUI(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FluxFrame (QThread)")
        self.setGeometry(200, 200, 700, 400)
        self.sync_path = "F:/transfer/_sync_test"
        self.watcher = None

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        v = QtWidgets.QVBoxLayout(central)

        self.log_panel = LogPanel()
        v.addWidget(self.log_panel)

        path_layout = QtWidgets.QHBoxLayout()
        self.path_input = QtWidgets.QLineEdit()
        self.path_input.setText(self.sync_path)
        self.btn_browse = QtWidgets.QPushButton("Ordner wählen")
        self.btn_browse.clicked.connect(self.choose_folder)
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(self.btn_browse)
        v.addLayout(path_layout)

        btn_layout = QtWidgets.QHBoxLayout()
        self.btn_start = QtWidgets.QPushButton("Start")
        self.btn_stop = QtWidgets.QPushButton("Stop")
        self.btn_stop.setEnabled(False)
        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_stop)
        v.addLayout(btn_layout)

        interval_layout = QtWidgets.QHBoxLayout()
        interval_layout.addWidget(QtWidgets.QLabel("Intervall (Sek):"))
        self.input_interval = QtWidgets.QLineEdit("10")
        self.input_interval.setValidator(QtGui.QIntValidator(1,9999))
        self.input_interval.setMaximumWidth(60)
        interval_layout.addWidget(self.input_interval)
        v.addLayout(interval_layout)

        self.lbl_status = QtWidgets.QLabel("Bereit.")
        v.addWidget(self.lbl_status)

        self.btn_start.clicked.connect(self.on_start)
        self.btn_stop.clicked.connect(self.on_stop)

    def log(self, msg):
        self.log_panel.log(msg)

    def choose_folder(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Sync-Ordner wählen")
        if path:
            self.sync_path = path
            self.path_input.setText(path)
            self.log(f"Sync-Ordner: {path}")

    def on_start(self):
        if not self.sync_path:
            self.log("[WARN] Kein Ordner gewählt!")
            self.lbl_status.setText("Bitte Ordner wählen!")
            return
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.input_interval.setEnabled(False)
        self.lbl_status.setText("Überwachung läuft...")

        getter = lambda: self.input_interval.text()
        self.watcher = SyncFolderWatcher(self.sync_path, getter)
        self.watcher.log_signal.connect(self.log_panel.log)
        self.watcher.finished_signal.connect(self.on_watchdog_stopped)
        self.watcher.start()
        self.log("Sync-Watcher gestartet.")

    def on_stop(self):
        if self.watcher:
            self.watcher.stop()
            self.watcher.wait(2000)
            self.watcher = None
            self.log("Sync-Watcher gestoppt.")
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.input_interval.setEnabled(True)
        self.lbl_status.setText("Gestoppt.")

    @QtCore.pyqtSlot()
    def on_watchdog_stopped(self):
        self.on_stop()

def run_gui():
    app = QtWidgets.QApplication(sys.argv)
    win = FluxFrameGUI()
    win.show()
    sys.exit(app.exec_())
