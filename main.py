import csv
import os
import re
from urllib.parse import urlparse
import yt_dlp

# Security: Restrict allowed domains and URL format
YOUTUBE_REGEX = re.compile(
    r"^(https?://)?(www\.)?(youtube\.com/(watch\?v=|shorts/)|youtu\.be/)[a-zA-Z0-9_-]{11}"
)

class QuietLogger:
    """Filter out non-fatal warnings while keeping errors visible."""
    def debug(self, msg):
        pass

    @staticmethod
    def warning(msg):
        # Ignore JavaScript runtime notice
        if "JavaScript runtime" in msg or "EJS" in msg:
            return
        print(f"[Warning] {msg}")

    @staticmethod
    def error(msg):
        print(f"[Error] {msg}")


def is_valid_youtube_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        # Prevent SSRF / internal network queries
        if parsed.scheme not in ("http", "https"):
            return False

        hostname = parsed.hostname or ""
        if not (hostname.endswith("youtube.com") or hostname == "youtu.be"):
            return False

        return bool(YOUTUBE_REGEX.match(url))

    except Exception:
        return False

def sanitize_filename(name: str) -> str:
    # Strip dangerous filesystem characters: \ / : * ? " < > |
    cleaned = re.sub(r'[\\/:*?"<>|]', '', name).strip()

    # Strip any directory traversal attempts or trailing extensions
    cleaned = os.path.basename(cleaned)
    if cleaned.lower().endswith(".mp3"):
        cleaned = cleaned[:-4].strip()
    return cleaned

def download_as_mp3(url: str, custom_name: str | None = None, output_dir: str = "downloads") -> str:
    os.makedirs(output_dir, exist_ok=True)

    # Determine base template based on whether a valid custom name was provided
    safe_name = sanitize_filename(custom_name) if custom_name else ""
    if safe_name:
        filename_template = f"{safe_name}.%(ext)s"
    else:
        filename_template = "%(title)s.%(ext)s"

    out_template = os.path.join(output_dir, filename_template)

    # yt-dlp configuration: Extract the best audio and convert via ffmpeg
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": out_template,
        "ffmpeg_location": r"C:\ffmpeg-9.0.1-essentials_build\bin",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "logger": QuietLogger(),
        "quiet": False,
        "no_warnings": True,
        "restrictfilenames": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["default"]
            }
        },
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        # yt-dlp changes the extension to .mp3 post-conversion
        base_name, _ = os.path.splitext(filename)
        return f"{base_name}.mp3"

def process_csv_batch():
    raw_path = input("Enter path to CSV file: ").strip().strip('"'). strip("'")

    if not os.path.exists(raw_path):
        print(f"Error: file not found at {raw_path}\n")
        return

    try:
        with open(raw_path, mode="r", encoding="utf-8-sig") as csv_file:
            reader = csv.reader(csv_file)
            rows = list(reader)

            if not rows:
                print("The provided CSV file is empty.\n")
                return

            print(f"\nProcessing {len(rows)} rows from CSV...\n")

            for index, row in enumerate(rows, start=1):
                if not row:
                    continue

                url = row[0].strip()
                if index == 1 and not is_valid_youtube_url(url) and any(header_word in url.lower() for header_word in ["url", "link", "youtube"]):
                    continue

                custom_name = row[1].strip() if len(row) > 1 else ""

                print(f"[{index}/{len(rows)}] Processing URL: {url}")

                if not is_valid_youtube_url(url):
                    print(f"  [Skipped] Invalid YouTube URL: '{url}'\n")
                    continue

                try:
                    print(f"  Downloading: {custom_name or 'Default Video Title'}...")
                    saved_path = download_as_mp3(url, custom_name=custom_name)
                    print(f"  Success: {saved_path}\n")

                except Exception as e:
                    print(f"  Failed: {e}\n")

            print(f"\nProcessing complete. Total rows: {len(rows)}\n")

    except Exception as e:
        print(f"Error processing CSV file: {e}\n")

def process_manual_loop():
    print("\n Manual Mode (type STOP or enter an invalid URL to exit)\n")

    while True:
        user_url = input("Enter YouTube URL: ").strip()

        # Stop condition: STOP
        if user_url.upper() == "STOP" or not user_url:
            print("Stopping program... Goodbye!")
            break

        # Stop condition: invalid URL
        if not is_valid_youtube_url(user_url):
            print("Invalid YouTube URL. Please try again.")
            break

        user_filename = input("Enter custom name (leave blank to use video title): ").strip()

        try:
            print("Downloading and converting...")
            saved_file = download_as_mp3(user_url, custom_name=user_filename)
            print(f"Success! Audio saved as: {saved_file}")
        except ValueError as err:
            print(f"Input Error: {err}")
        except Exception as err:
            print(f"Download Error: {err}")


if __name__ == "__main__":
    print("YouTube to MP3 Converter (STOP or enter an invalid URL to exit)\n")

    while True:
        print("Select an option:")
        print("1. Process a CSV file (batch download")
        print("2. Manual mode (enter links one by one)")
        print("3. Exit")

        choice = input("Enter your choice: ").strip()

        if choice == "1":
            process_csv_batch()
        elif choice == "2":
            process_manual_loop()
        elif choice in ("3", "STOP", "stop", "exit"):
            print("Stopping program... Goodbye!")
            break
        else:
            print("Invalid choice. Please choose 1, 2, or 3.\n")