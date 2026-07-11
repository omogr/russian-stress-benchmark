import os
import zipfile
from pathlib import Path
import urllib.request

#DATA_URL = "https://github.com/omogr/russian-stress-benchmark/releases/download/v1.0.0/accent_engine.zip"

DATA_URL = [
    "https://github.com/omogr/russian-stress-benchmark/releases/download/v1.0.0/wiktionary_enhancer.zip",
    "https://github.com/omogr/russian-stress-benchmark/releases/download/v1.0.0/accent_engine.zip"
]    
DATA_DIR = Path(__file__).parent / "data"

def ensure_data():
    if DATA_DIR.exists():
        return
        
    zip_path = DATA_DIR.with_suffix(".zip")
    
    for url in DATA_URL:
        DATA_DIR.mkdir(exist_ok=True)
        print("Downloading dictionaries...", url[-20:])
        urllib.request.urlretrieve(url, zip_path)
        
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(DATA_DIR)
        zip_path.unlink()

# В начале работы скрипта
ensure_data()