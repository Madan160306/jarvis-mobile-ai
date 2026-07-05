import os
import sys
import requests

MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")

MODELS = {
    "llama-3.2-1b-q4_k_m.gguf": "https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf",
    "Llama-3.2-3B-Instruct-Q4_K_M.gguf": "https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf",
    "vision/MobileNetSSD_deploy.prototxt.txt": "https://raw.githubusercontent.com/nikmart/pi-object-detection/master/MobileNetSSD_deploy.prototxt.txt",
    "vision/MobileNetSSD_deploy.caffemodel": "https://github.com/nikmart/pi-object-detection/raw/master/MobileNetSSD_deploy.caffemodel",
}

def download_file(url, filepath):
    expected_sizes = {
        "3B": 1.9 * 1024 * 1024 * 1024,
        "1b": 700 * 1024 * 1024,
        "MobileNetSSD": 10 * 1024
    }
    
    current_size = 0
    if os.path.exists(filepath):
        current_size = os.path.getsize(filepath)
        
        # Check if already fully downloaded
        is_complete = False
        if "3B" in filepath and current_size > expected_sizes["3B"]:
            is_complete = True
        elif "1b" in filepath and current_size > expected_sizes["1b"]:
            is_complete = True
        elif "MobileNetSSD" in filepath and current_size > expected_sizes["MobileNetSSD"]:
            is_complete = True
            
        if is_complete:
            print(f"[OK] {os.path.basename(filepath)} already exists and is complete ({current_size / (1024*1024):.1f} MB).")
            return

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    headers = {}
    if current_size > 0:
        headers['Range'] = f'bytes={current_size}-'
        print(f"[FETCH] Resuming {os.path.basename(filepath)} from {current_size / (1024*1024):.1f} MB...")
    else:
        print(f"[FETCH] Downloading {os.path.basename(filepath)}...")
        
    try:
        response = requests.get(url, headers=headers, stream=True, allow_redirects=True, timeout=60)
        
        # 416 means range not satisfiable (already fully downloaded)
        if response.status_code == 416:
            print(f"[OK] {os.path.basename(filepath)} already fully downloaded based on server response.")
            return
            
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        # If resuming (206), total size is current + remaining
        if response.status_code == 206:
            total_size += current_size
        elif response.status_code == 200:
            # If server ignored range header, start over
            current_size = 0
            
        block_size = 1024 * 1024  # 1 MB
        
        downloaded = current_size
        mode = 'ab' if current_size > 0 else 'wb'
        
        with open(filepath, mode) as out_file:
            for chunk in response.iter_content(chunk_size=block_size):
                if chunk:
                    out_file.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = int(downloaded * 100 / total_size)
                        sys.stdout.write(f"\rDownloading... {percent}% ({downloaded / (1024*1024):.1f}/{total_size / (1024*1024):.1f} MB)")
                    else:
                        sys.stdout.write(f"\rDownloading... {downloaded / (1024*1024):.1f} MB")
                    sys.stdout.flush()
        print()
        print(f"[DONE] Downloaded {os.path.basename(filepath)} successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to download {os.path.basename(filepath)}: {e}")

if __name__ == "__main__":
    os.makedirs(MODELS_DIR, exist_ok=True)
    import time
    for filename, url in MODELS.items():
        filepath = os.path.join(MODELS_DIR, filename)
        
        retries = 20
        for attempt in range(retries):
            try:
                download_file(url, filepath)
                # Check size again to ensure it didn't fail silently
                if os.path.exists(filepath):
                    size = os.path.getsize(filepath)
                    if "3B" in filepath and size > 1.9 * 1024**3:
                        break
                    elif "1b" in filepath and size > 700 * 1024**2:
                        break
                    elif "MobileNetSSD" in filepath and size > 10 * 1024:
                        break
                print(f"Retry {attempt+1}/{retries} - waiting 5 seconds before retrying...")
                time.sleep(5)
            except Exception as e:
                print(f"Retry {attempt+1}/{retries} after error: {e}")
                time.sleep(5)
