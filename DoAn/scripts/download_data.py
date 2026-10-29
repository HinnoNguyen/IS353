import os
import sys
import tarfile
import urllib.request
from pathlib import Path
import zstandard

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
URL = "https://datasets.ldbcouncil.org/snb-interactive-v1/social_network-sf0.1-CsvComposite-LongDateFormatter.tar.zst"
ARCHIVE_PATH = DATA_DIR / "social_network-sf0.1-CsvComposite-LongDateFormatter.tar.zst"

def download_file(url, target_path):
    print(f"Downloading from: {url}")
    target_path.parent.mkdir(parents=True, exist_ok=True)
    
    def reporthook(block_num, block_size, total_size):
        downloaded = block_num * block_size
        if total_size > 0:
            percent = downloaded * 100 / total_size
            mb = downloaded / (1024 * 1024)
            total_mb = total_size / (1024 * 1024)
            sys.stdout.write(f"\rDownloading: {mb:.1f} MB / {total_mb:.1f} MB ({percent:.1f}%)")
        else:
            mb = downloaded / (1024 * 1024)
            sys.stdout.write(f"\rDownloading: {mb:.1f} MB")
        sys.stdout.flush()

    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as response, open(target_path, "wb") as out_file:
        total_size = int(response.headers.get("Content-Length", 0))
        block_size = 1024 * 1024 # 1 MB
        downloaded = 0
        while True:
            buffer = response.read(block_size)
            if not buffer:
                break
            downloaded += len(buffer)
            out_file.write(buffer)
            if total_size > 0:
                percent = downloaded * 100 / total_size
                sys.stdout.write(f"\rDownloading: {downloaded / (1024*1024):.1f} MB / {total_size / (1024*1024):.1f} MB ({percent:.1f}%)")
            else:
                sys.stdout.write(f"\rDownloading: {downloaded / (1024*1024):.1f} MB")
            sys.stdout.flush()
    print("\nDownload complete.")

def extract_archive(archive_path, extract_dir):
    print(f"Extracting {archive_path.name} to {extract_dir}...")
    with open(archive_path, "rb") as f:
        dctx = zstandard.ZstdDecompressor()
        with dctx.stream_reader(f) as r:
            with tarfile.open(fileobj=r, mode="r|") as t:
                # Python 3.12+ safe filter
                if hasattr(tarfile, "data_filter"):
                    t.extractall(extract_dir, filter="data")
                else:
                    t.extractall(extract_dir)
    print("Extraction complete.")

def main():
    if not ARCHIVE_PATH.exists():
        download_file(URL, ARCHIVE_PATH)
    else:
        print(f"Archive {ARCHIVE_PATH} already exists, skipping download.")
        
    extract_archive(ARCHIVE_PATH, DATA_DIR)
    
    # Kiểm tra cấu trúc
    target_dir = DATA_DIR / "social_network-sf0.1-CsvComposite-LongDateFormatter"
    static_dir = target_dir / "static"
    dynamic_dir = target_dir / "dynamic"
    print(f"Checking folders:")
    print(f"  Target dir exists: {target_dir.exists()}")
    print(f"  Static dir exists: {static_dir.exists()} ({len(list(static_dir.glob('*.csv')))} csv files)")
    print(f"  Dynamic dir exists: {dynamic_dir.exists()} ({len(list(dynamic_dir.glob('*.csv')))} csv files)")

if __name__ == "__main__":
    main()

