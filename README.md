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
