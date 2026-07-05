import os
import zipfile
import time

def create_local_backup():
    source_dir = r"c:\Users\msand\JARVIS-MOBILE-AI"
    # Save it to the Desktop so it's easy to find and copy to the phone
    output_filename = r"c:\Users\msand\Desktop\JARVIS_FULL_BACKUP.zip"
    
    # Folders we DO NOT want to zip (Windows-specific or unnecessary bloat)
    exclude_dirs = {'.git', 'jarvis-env', 'venv', '__pycache__', '.idea', '.vscode'}
    
    print(f"Creating full offline backup of JARVIS at: {output_filename}")
    print("This will include ALL your secret API keys, your voice profile, and your memories.")
    print("Packing files... Please wait.")
    
    with zipfile.ZipFile(output_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            # Modify dirs in-place to skip excluded directories entirely
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                file_path = os.path.join(root, file)
                # Ensure we don't accidentally zip the output file itself if it was in the same dir
                if file_path == output_filename:
                    continue
                    
                # Create a relative path so the zip structure is clean
                arcname = os.path.relpath(file_path, source_dir)
                zipf.write(file_path, arcname)

    print(f"\n✅ Backup Complete!")
    print(f"File saved to: {output_filename}")
    print(f"File size: {os.path.getsize(output_filename) / (1024*1024):.2f} MB")

if __name__ == "__main__":
    create_local_backup()
