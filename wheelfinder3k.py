# wheelfinder3000.py
# Prüft dein System und empfiehlt passende PyTorch Wheels (manuell oder via pip)

import platform
import sys
from urllib.parse import quote


def get_python_tag():
    version = sys.version_info
    return f"cp{version.major}{version.minor}"


def get_platform_tag():
    arch = platform.architecture()[0]
    if arch == "64bit":
        return "win_amd64"
    else:
        return "win32"


def show_system_info():
    print("\n📋 System-Check:")
    print(f"  Python-Version   : {platform.python_version()}  [{get_python_tag()}]")
    print(f"  Plattform         : {platform.system()} {platform.release()} [{get_platform_tag()}]")
    print(f"  Architekturstufe : {platform.architecture()[0]}")


def get_download_url(pkg_name, version, cuda_tag="cu118"):
    base_url = "https://download.pytorch.org/whl"
    py_tag = get_python_tag()
    plat_tag = get_platform_tag()
    filename = f"{pkg_name}-{version}%2B{cuda_tag}-{py_tag}-{py_tag}-{plat_tag}.whl"
    return f"{base_url}/{cuda_tag}/{filename}"


def print_manual_links():
    print("\n🔗 Empfohlene Download-Links (manuell):")
    print("  torch       :", get_download_url("torch", "2.3.0"))
    print("  torchvision :", get_download_url("torchvision", "0.18.0"))
    print("  torchaudio  :", get_download_url("torchaudio", "2.3.0"))


def print_pip_command():
    print("\n🐍 Empfohlener pip-Befehl:")
    print("(nur wenn Wheels kompatibel sind, sonst manuell laden!)\n")
    print("pip install torch==2.3.0 torchvision==0.18.0 torchaudio==2.3.0 --index-url https://pypi.org/simple --extra-index-url https://download.pytorch.org/whl/cu118")


def check_cuda_gpu():
    try:
        import torch
        print("\n🧠 torch gefunden:")
        print("  Version       :", torch.__version__)
        print("  CUDA verfügbar :", torch.cuda.is_available())
    except ImportError:
        print("\n⚠️  torch ist noch nicht installiert.")


if __name__ == "__main__":
    print("\n=== 🛠️  WHEELFINDER 3000 ===")
    show_system_info()
    print_manual_links()
    print_pip_command()
    check_cuda_gpu()
    print("\nFertig.")
