import os
os.environ["LLAMA_CPP_LIB"] = "C:\\bin\\dev\\llama\\llama.cpp\\build\\bin\\Release\\llama.dll"
os.add_dll_directory("C:\\bin\\dev\\CUDA\\bin")
os.add_dll_directory("C:\\bin\\dev\\llama\\llama.cpp\\build\\bin\\Release")

import ctypes
ctypes.WinDLL("C:\\bin\\dev\\llama\\llama.cpp\\build\\bin\\Release\\ggml-cuda.dll")
ctypes.WinDLL("C:\\bin\\dev\\llama\\llama.cpp\\build\\bin\\Release\\llama.dll")

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QLabel, QSplitter
)
from PyQt5.QtCore import Qt
import sys

from llama_cpp import Llama

# Initialisierung des LLaMA-Modells mit den relevanten Parametern
llm = Llama(
    model_path="C:\\usr\\dev\\llmodels\\mistral-7b-openorca.Q4_K_M.gguf",  # Pfad zum Modell
    n_ctx=4096,              # Kontextgröße
    n_gpu_layers=-1,         # alle Layer auf GPU
    n_threads=6,             # Anzahl CPU-Threads
    use_mlock=True           # Speicherschutz gegen Auslagerung
)

class AIchhorn(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()  # Benutzeroberfläche aufbauen

    def init_ui(self):
        self.setWindowTitle("AIchhorn CommandCenter")
        self.resize(1000, 600)

        main_layout = QHBoxLayout(self)  # Hauptlayout horizontal

        splitter = QSplitter(Qt.Horizontal)  # Trennleiste für Chat und Log
        main_layout.addWidget(splitter)

        # --- Chatpanel ---
        chat_widget = QWidget()
        chat_layout = QVBoxLayout(chat_widget)

        self.output_area = QTextEdit()  # Ausgabe-Feld für Chat
        self.output_area.setReadOnly(True)

        self.input_line = QLineEdit()  # Eingabezeile
        self.input_line.returnPressed.connect(self.handle_input)  # Enter-Taste = senden

        self.send_button = QPushButton("Senden")  # Button zum Senden
        self.send_button.clicked.connect(self.handle_input)

        input_layout = QHBoxLayout()  # Layout für Eingabefeld + Button
        input_layout.addWidget(self.input_line)
        input_layout.addWidget(self.send_button)

        chat_layout.addWidget(QLabel("Chat:"))
        chat_layout.addWidget(self.output_area)
        chat_layout.addLayout(input_layout)

        splitter.addWidget(chat_widget)  # Chatbereich zum Splitter hinzufügen

        # --- Logpanel ---
        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)

        self.log_area = QTextEdit()  # Bereich für Log/Fehler
        self.log_area.setReadOnly(True)

        log_layout.addWidget(QLabel("Log & Fehlerausgabe:"))
        log_layout.addWidget(self.log_area)

        splitter.addWidget(log_widget)
        splitter.setSizes([700, 300])  # Anfangsverhältnis zwischen Chat und Log

    def handle_input(self):
        user_input = self.input_line.text().strip()
        if not user_input:
            return  # keine leeren Eingaben verarbeiten

        self.output_area.append(f"Du: {user_input}")
        self.input_line.clear()

        try:
            # Anfrage an das LLaMA-Modell senden
            response = llm(user_input, max_tokens=128)
            answer = response["choices"][0]["text"].strip()
            self.output_area.append(f"LLaMA: {answer}\n")
        except Exception as e:
            # Fehlerausgabe in das Logpanel
            self.log_area.append(f"Fehler: {str(e)}\n")

# Einstiegspunkt der Anwendung
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = AIchhorn()
    window.show()
    sys.exit(app.exec_())