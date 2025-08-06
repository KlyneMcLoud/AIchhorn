import sys
import subprocess
from pathlib import Path
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout,
    QLabel, QLineEdit, QFileDialog, QHBoxLayout,
    QTreeWidget, QTreeWidgetItem, QAbstractItemView,
    QToolButton, QMenu, QAction, QSizePolicy, QStyle
)
from PyQt5.QtCore import Qt

from fluxframe.watchdog import SyncFolderWatcher
from fluxframe import storage

class FilterMenu(QMenu):
    """Dropdown-Menü mit Rechtsklick-Single-Select-Unterstützung."""
    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            action = self.actionAt(event.pos())
            if action:
                for act in self.actions():
                    act.setChecked(False)
                action.setChecked(True)
                parent = self.parentWidget()
                parent.selected_extensions = {'' if action.text() == '[no ext]' else action.text()}
                parent.populate_tree()
                return
        super().mousePressEvent(event)

class FluxFrameGUI(QWidget):
    """
    GUI zum Überwachen von Ordnern und Auswählen gefilterter Dateien im Baum.
    """
    def __init__(self):
        super().__init__()
        self.watcher = None
        self.root_path = None
        self.selected_extensions = set()
        self.filter_actions = {}
        self.icons = {}
        self.setup_ui()
        self.init_icons()

    def setup_ui(self):
        self.setWindowTitle("Flux Folder Watcher")
        self.resize(700, 500)

        # Pfad- und Steuer-Buttons
        self.folder_input = QLineEdit(self)
        self.folder_input.setPlaceholderText("Zu überwachenden Ordner auswählen…")
        browse_btn = QPushButton("Durchsuchen")
        browse_btn.clicked.connect(self.on_browse)
        self.start_btn = QPushButton("Start")
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)
        self.parse_btn = QPushButton("Parse")
        self.parse_btn.setEnabled(False)
        self.start_btn.clicked.connect(self.on_start)
        self.stop_btn.clicked.connect(self.on_stop)
        self.parse_btn.clicked.connect(self.on_parse)

        path_layout = QHBoxLayout()
        path_layout.addWidget(self.folder_input)
        path_layout.addWidget(browse_btn)
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addWidget(self.parse_btn)

        # Filter-Dropdown
        self.filter_btn = QToolButton(self)
        self.filter_btn.setText("Filter Extensions")
        self.filter_btn.setPopupMode(QToolButton.InstantPopup)
        self.filter_menu = FilterMenu(self)
        self.filter_btn.setMenu(self.filter_menu)
        filter_layout = QHBoxLayout()
        filter_layout.addStretch()
        filter_layout.addWidget(self.filter_btn)

        # Dateibaum
        self.tree = QTreeWidget(self)
        self.tree.setHeaderLabels(["Name"])
        self.tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tree.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Log
        self.log_label = QLabel(self)
        self.log_label.setFixedHeight(30)
        self.log_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.addLayout(path_layout)
        layout.addLayout(btn_layout)
        layout.addLayout(filter_layout)
        layout.addWidget(self.tree)
        layout.addWidget(self.log_label)

    def init_icons(self):
        style = QApplication.style()
        self.icons['folder'] = style.standardIcon(QStyle.SP_DirIcon)
        self.icons['file'] = style.standardIcon(QStyle.SP_FileIcon)

    def on_browse(self):
        selected = QFileDialog.getExistingDirectory(self, "Ordner auswählen", str(Path.home()))
        if selected:
            self.folder_input.setText(selected)

    def on_start(self):
        path = self.folder_input.text().strip()
        if not path:
            return self.log("Kein Pfad angegeben")
        if self.watcher:
            return self.log("Watcher läuft bereits")
        self.root_path = Path(path)
        self.watcher = SyncFolderWatcher(path)
        self.watcher.update_signal.connect(self.handle_update)
        self.watcher.start()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.parse_btn.setEnabled(True)
        self.log(f"Überwachung gestartet: {path}")
        self.populate_filters()
        self.populate_tree()

    def on_stop(self):
        if not self.watcher:
            return
        self.watcher.stop()
        self.watcher = None
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.parse_btn.setEnabled(False)
        self.log("Überwachung gestoppt")

    def on_parse(self):
        items = self.tree.selectedItems()
        if not items:
            return self.log("Keine Datei ausgewählt zum Parsen")
        script_path = Path(__file__).parent.parent / 'parse_io' / 'parse_content_io.py'
        for item in items:
            entry = item.data(0, Qt.UserRole)
            if not entry:
                continue
            file_path = Path(entry['path']) / entry['name']
            try:
                subprocess.run([sys.executable, str(script_path), str(file_path)], check=True)
                self.log(f"Parsed: {file_path}")
            except subprocess.CalledProcessError as e:
                self.log(f"Parse-Fehler: {file_path}")

    def handle_update(self, message):
        self.log(message)
        self.populate_filters()
        self.populate_tree()

    def populate_filters(self):
        self.filter_menu.clear()
        self.filter_actions.clear()
        entries = storage.get_entries()
        exts = sorted({e['extension'] or '' for e in entries})
        self.selected_extensions = set(exts)
        for ext in exts:
            label = ext or '[no ext]'
            act = QAction(label, self)
            act.setCheckable(True)
            act.setChecked(True)
            act.toggled.connect(self.on_filter_toggled)
            self.filter_menu.addAction(act)
            self.filter_actions[label] = act

    def on_filter_toggled(self, checked):
        action = self.sender()
        ext = '' if action.text() == '[no ext]' else action.text()
        if checked:
            self.selected_extensions.add(ext)
        else:
            self.selected_extensions.discard(ext)
        self.populate_tree()

    def get_filtered_entries(self):
        result = []
        for e in storage.get_entries():
            try:
                Path(e['path']).relative_to(self.root_path)
            except Exception:
                continue
            if not e['extension'] or e['extension'] in self.selected_extensions:
                result.append(e)
        return result

    def build_tree_structure(self, entries):
        tree = {}
        for e in entries:
            try:
                rel = Path(e['path']).relative_to(self.root_path)
            except Exception:
                continue
            node = tree
            for part in rel.parts:
                node = node.setdefault(part, {})
            node.setdefault(e['name'], {})['_entry'] = e
        return tree

    def populate_tree(self):
        self.tree.clear()
        if not self.root_path:
            return
        entries = self.get_filtered_entries()
        tree_dict = self.build_tree_structure(entries)
        first_dirs = sorted([p.name for p in self.root_path.iterdir() if p.is_dir()])
        first_files = sorted([e['name'] for e in entries if Path(e['path']) == self.root_path])
        first = first_dirs + first_files
        for name in first:
            is_dir = (self.root_path / name).is_dir()
            item = QTreeWidgetItem(self.tree, [name])
            item.setIcon(0, self.icons['folder'] if is_dir else self.icons['file'])
            subtree = tree_dict.get(name)
            if subtree:
                self._add_items(item, subtree)
        self.tree.expandToDepth(1)

    def _add_items(self, parent, subtree):
        for name, branch in sorted(subtree.items()):
            if name == '_entry':
                continue
            item = QTreeWidgetItem(parent, [name])
            is_file = '_entry' in branch and len(branch) == 1
            item.setIcon(0, self.icons['file' if is_file else 'folder'])
            if is_file:
                item.setData(0, Qt.UserRole, branch['_entry'])
            self._add_items(item, branch)

    def log(self, message):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_label.setText(f"{ts} — {message}")


def run_gui():
    app = QApplication(sys.argv)
    win = FluxFrameGUI()
    win.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    run_gui()