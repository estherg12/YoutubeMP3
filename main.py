import os
import re
from urllib.parse import urlparse
import yt_dlp

# Security: Restrict allowed domains and URL format
YOUTUBE_REGEX = re.compile(
    r"^(https?://)?(www\.)?(youtube\.com/(watch\?v=|shorts/)|youtu\.be/)[a-zA-Z0-9_-]{11}"
)


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
    if not is_valid_youtube_url(url):
        raise ValueError("Invalid YouTube URL provided.")

    os.makedirs(output_dir, exist_ok=True)

    # Determine base template based on wether a valid custom name was provided
    safe_name = sanitize_filename(custom_name) if custom_name else ""
    if safe_name:
        out_template = os.path.join(output_dir, f"{safe_name}.%(ext)s")
    else:
        out_template = os.path.join(output_dir, "%(title)s.%(ext)s")

    # yt-dlp configuration: Extract the best audio and convert via ffmpeg
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(output_dir, "%(title)s.%(ext)s"),
        "ffmpeg_location": r"C:\ffmpeg-9.0.1-essentials_build\bin",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "quiet": False,
        "no_warnings": False,
        "restrictfilenames": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        # yt-dlp changes the extension to .mp3 post-conversion
        base_name, _ = os.path.splitext(filename)
        return f"{base_name}.mp3"


if __name__ == "__main__":
    user_url = input("Enter YouTube URL: ").strip()
    user_filename = input("Enter custom name (leave blank to use video title): ").strip()

    try:
        saved_file = download_as_mp3(user_url, custom_name=user_filename)
        print(f"Success! Audio saved as: {saved_file}")
    except ValueError as err:
        print(f"Input Error: {err}")
    except Exception as err:
        print(f"Download Error: {err}")