import csv
import os
import re
from urllib.parse import urlparse
import yt_dlp

# Security: Restrict allowed domains and URL format
YOUTUBE_REGEX = re.compile(
    r"^(https?://)?(www\.)?(youtube\.com/(watch\?v=|shorts/)|youtu\.be/)[a-zA-Z0-9_-]{11}"
)

# Reject any audio whose resulting MP3 would be bigger than this
MAX_MP3_SIZE_MB = 15
MAX_MP3_SIZE_BYTES = MAX_MP3_SIZE_MB * 1024 * 1024
MP3_BITRATE_KBPS = 192


class FileTooLargeError(Exception):
    """Raised when the resulting MP3 would exceed MAX_MP3_SIZE_MB."""


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

def estimated_mp3_size(duration_seconds: float | None) -> int | None:
    """Estimate the MP3 size in bytes from its duration and the target bitrate."""
    if not duration_seconds or duration_seconds <= 0:
        return None
    return int(duration_seconds * MP3_BITRATE_KBPS * 1000 / 8)


def format_size(num_bytes: float) -> str:
    return f"{num_bytes / (1024 * 1024):.1f} MB"


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
                "preferredquality": str(MP3_BITRATE_KBPS),
            }
        ],
        "logger": QuietLogger(),
        "no_warnings": True,
        "restrictfilenames": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "ios", "web"]
            }
        },
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        # Inspect the video first so oversized audio is never downloaded
        probe = ydl.extract_info(url, download=False)
        estimated = estimated_mp3_size(probe.get("duration"))
        if estimated and estimated > MAX_MP3_SIZE_BYTES:
            raise FileTooLargeError(
                f"Too large: ~{format_size(estimated)} (limit {MAX_MP3_SIZE_MB} MB)"
            )

        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        # yt-dlp changes the extension to .mp3 post-conversion
        base_name, _ = os.path.splitext(filename)
        mp3_path = f"{base_name}.mp3"

        # The estimate can be off, so enforce the limit on the real file too
        if os.path.exists(mp3_path):
            actual_size = os.path.getsize(mp3_path)
            if actual_size > MAX_MP3_SIZE_BYTES:
                os.remove(mp3_path)
                raise FileTooLargeError(
                    f"Too large: {format_size(actual_size)} "
                    f"(limit {MAX_MP3_SIZE_MB} MB), file deleted"
                )

        return mp3_path

def print_failed_rows_table(failed_rows: list[dict]) -> None:
    """Print a table with the CSV rows that could not be downloaded."""
    if not failed_rows:
        print("All rows were downloaded successfully.\n")
        return

    def one_line(value: str, fallback: str = "") -> str:
        # Error messages can span several lines, which would break the table
        return " ".join(str(value).split()) or fallback

    headers = ("Row", "URL", "Name", "Reason")
    table = [
        (
            str(item["row"]),
            one_line(item["url"], "(empty)"),
            one_line(item["name"], "(no custom name)"),
            one_line(item["reason"], "Unknown error"),
        )
        for item in failed_rows
    ]

    # Size each column to its widest value, capped so the table stays readable
    max_widths = (5, 60, 40, 60)
    widths = [
        min(max(len(headers[col]), *(len(row[col]) for row in table)), max_widths[col])
        for col in range(len(headers))
    ]

    def format_row(values) -> str:
        cells = []
        for col, value in enumerate(values):
            width = widths[col]
            if len(value) > width:
                value = value[: width - 3] + "..."
            cells.append(value.ljust(width))
        return "| " + " | ".join(cells) + " |"

    separator = "+" + "+".join("-" * (width + 2) for width in widths) + "+"

    print(f"{len(failed_rows)} row(s) failed and were NOT downloaded:\n")
    print(separator)
    print(format_row(headers))
    print(separator)
    for row in table:
        print(format_row(row))
    print(separator)
    print("\nFix or re-run these rows to try again.\n")


def process_csv_batch():
    raw_path = input("Enter path to CSV file: ").strip().strip('"'). strip("'")

    if not os.path.exists(raw_path):
        print(f"Error: file not found at {raw_path}\n")
        return

    try:
        with open(raw_path, mode="r", encoding="utf-8-sig") as csv_file:
            sample = csv_file.read(2048)
            csv_file.seek(0)
            delimiter = ","

            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=[",", ";", "\t"])
                delimiter = dialect.delimiter
            except Exception:
                if ";" in sample:
                    delimiter = ";"

            reader = csv.reader(csv_file, delimiter=delimiter)
            rows = [row for row in reader if any(field.strip() for field in row)]

            if not rows:
                print("The provided CSV file is empty.\n")
                return

            print(f"\nProcessing {len(rows)} rows from CSV...\n")

            failed_rows = []
            succeeded = 0

            for index, row in enumerate(rows, start=1):
                if not row:
                    continue

                url = row[0].strip() if len(row) > 0 else ""
                if index == 1 and not is_valid_youtube_url(url) and any(header_word in url.lower() for header_word in ["url", "link", "youtube"]):
                    continue

                custom_name = row[1].strip() if len(row) > 1 else ""

                print(f"[{index}/{len(rows)}] Processing URL: {url}")

                if not is_valid_youtube_url(url):
                    print(f"  [Skipped] Invalid YouTube URL: '{url}'\n")
                    failed_rows.append({
                        "row": index,
                        "url": url,
                        "name": custom_name,
                        "reason": "Invalid YouTube URL",
                    })
                    continue

                try:
                    display_name = custom_name if custom_name else "Default Video Title"
                    print(f"  Downloading: {display_name}...")
                    saved_path = download_as_mp3(url, custom_name=custom_name)
                    print(f"  Success: {saved_path}\n")
                    succeeded += 1

                except FileTooLargeError as e:
                    print(f"  [Skipped] {e}\n")
                    failed_rows.append({
                        "row": index,
                        "url": url,
                        "name": custom_name,
                        "reason": str(e),
                    })

                except Exception as e:
                    print(f"  Failed: {e}\n")
                    failed_rows.append({
                        "row": index,
                        "url": url,
                        "name": custom_name,
                        "reason": str(e).strip() or e.__class__.__name__,
                    })

            print(f"\nProcessing complete. Total rows: {len(rows)} | "
                  f"Downloaded: {succeeded} | Failed: {len(failed_rows)}\n")
            print_failed_rows_table(failed_rows)

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
        except FileTooLargeError as err:
            print(f"Skipped: {err}")
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