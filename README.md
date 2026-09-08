# Local YouTube to MP3 Converter

A secure, offline-first Python utility to download and convert YouTube audio streams directly into high-quality `.mp3` files using `yt-dlp` and `FFmpeg`.

Supports both **interactive manual mode** (prompting link-by-link) and **batch automated conversion** from `.csv` files with custom track names and regional delimiter auto-detection.

---

## Features

- **High-Quality Audio Extraction:** Pulls the best available audio stream and encodes it into 192 kbps `.mp3`.
- **Security & Validation:**
  - Strict regex domain and URL parsing against YouTube schemas (blocks SSRF and malicious network calls).
  - Sanitization of user-provided filenames to prevent directory traversal (`../`) and illegal OS characters.
  - Native Python invocation without shell command injection vulnerabilities.
  - For security reasons, when batching a CSV, no file bigger than 15MB will be downloaded.
- **CSV Batch Mode:**
  - Automated delimiter sniffer supporting standard commas (`,`), semicolons (`;`, standard in European/Spanish Excel exports), and tabs (`\t`).
  - Supports UTF-8 encoding with BOM (`utf-8-sig`) for accented characters.
  - Fault-tolerant processing: skips broken links and continues the remaining queue.
- **Custom or Automatic Naming:** Specify a track name or leave it empty to inherit the official video title.

---

## Prerequisites

### 1. Python
Python 3.10 or newer is required.

### 2. FFmpeg
FFmpeg is required to process and transcode audio streams to `.mp3`.

- **Windows:**
  ```winget install Gyan.FFmpeg```
- **macOS:**
  ```brew install ffmpeg```
- **Linux:**
  ```sudo apt update && sudo apt install ffmpeg```

### 3. JavaScript Runtime (Recomended)
To prevent format throttling and silence ```yt-dlp``` JS runtime notices, install **Deno**:
- **Windows**: ```winget install DenoLand.Deno```
- **macOS**: ```brew install deno```
- **Linux**: ```curl -fsSL https://deno.land/install.sh | sh```

---

## Installation

### 1. Clone the repository
```
git clone [https://github.com/](https://github.com/)<your-username>/YoutubeMP3.git
cd YoutubeMP3
```

### 2. Create and activate a virtual enviroment
* **Windows**:
```
py -m venv .venv
.venv\Scripts\activate
```

* **macOS / Linux**:
```
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies
```pip install yt-dlp```

---

## Usage
Run the main application: ```python main.py```
You will be greeted by the terminal menu:
```
YouTube to MP3 Converter (STOP or enter an invalid URL to exit)

Select an option:
1. Process a CSV file (batch download
2. Manual mode (enter links one by one)
3. Exit
```

### Option 1: CSV Batch Download
Provide the path to your .csv file. The script expects two columns:

| URL | Desired Name of the File |
| :---: | :---: |
| https://youtu.be/5SZYz7lZRRI?si=pC51OQ6ZNkgqYi32 | My Favourite Song |

Both comma-separated (,) and semicolon-separated (;) formats are supported automatically.

### Option 2: Manual Code
Enter YouTube links interactively. You can specify a custom name per link or press Enter to use the original YouTube title.
To exit manual mode, type STOP or enter an invalid URL.
All converted files are automatically saved inside the local ```downloads/``` directory.

---

## Project Structure
YoutubeMP3/

├── downloads/ 

├── .gitignore  

├── main.py  

└── README.md   


## Recommended .gitignore
Ensure your ```.gitignore``` includes:
```
.venv/
__pycache__/
*.py[cod]
downloads/
*.mp3
*.m4a
*.webm
.idea/
.vscode/
```
