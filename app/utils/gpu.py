import subprocess, sys

def get_cuda_device_name():
    try:
        import torch
        if torch.cuda.is_available():
            return torch.cuda.get_device_name(0)
    except Exception:
        pass
    return None

def detect_k80_or_kepler(name: str) -> bool:
    if not name:
        return False
    name_l = name.lower()
    return ("k80" in name_l) or ("tesla k80" in name_l) or ("kepler" in name_l)

def suggest_torch_command(device_name: str) -> str:
    if detect_k80_or_kepler(device_name):
        return "pip install torch==1.13.1+cu117 torchvision==0.14.1+cu117 torchaudio==0.13.1 -f https://download.pytorch.org/whl/cu117"
    return "pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118"

def ensure_spacy_model():
    try:
        import spacy
        try:
            spacy.load("en_core_web_sm")
            return True
        except Exception:
            pass
        subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"], check=False)
        try:
            spacy.load("en_core_web_sm")
            return True
        except Exception:
            return False
    except Exception:
        return False