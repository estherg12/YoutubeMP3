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

    def warning(self, msg):
        # Ignore JavaScript runtime notice
        if "JavaScript runtime" in msg or "EJS" in msg:
            return
        print(f"[Warning] {msg}")

    def error(self, msg):
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

    # Determine base template based on wether a valid custom name was provided
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


if __name__ == "__main__":
    print("YouTube to MP3 Converter (STOP or enter an invalid URL to exit)\n")

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
            saved_file = download_as_mp3(user_url, custom_name=user_filename)
            print(f"Success! Audio saved as: {saved_file}")
        except ValueError as err:
            print(f"Input Error: {err}")
        except Exception as err:
            print(f"Download Error: {err}")