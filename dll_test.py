import os
import ctypes

# Wichtig: CUDA-Pfad temporär zum DLL-Suchpfad hinzufügen (ab Python 3.8)
os.add_dll_directory("C:\\bin\\dev\\CUDA\\bin")
os.add_dll_directory("C:\\bin\\dev\\llama\\llama.cpp\\build\\bin\\Release")

try:
    ctypes.WinDLL("C:\\bin\\dev\\llama\\llama.cpp\\build\\bin\\Release\\ggml-cuda.dll")
    print("✅ DLL erfolgreich geladen.")
except OSError as e:
    print("❌ Fehler beim Laden der DLL:")
    print(e)