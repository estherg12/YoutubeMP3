import csv
import io
import os
import runpy
import sys
import unittest
from unittest.mock import MagicMock, mock_open, patch

import main


class TestQuietLogger(unittest.TestCase):
    def setUp(self):
        self.logger = main.QuietLogger()

    def test_debug(self):
        # debug should do nothing without raising exceptions
        self.assertIsNone(self.logger.debug("Debug message"))

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_warning_ignored(self, mock_stdout):
        self.logger.warning("JavaScript runtime not found")
        self.assertEqual(mock_stdout.getvalue(), "")

        self.logger.warning("EJS template notice")
        self.assertEqual(mock_stdout.getvalue(), "")

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_warning_printed(self, mock_stdout):
        self.logger.warning("Some general warning")
        self.assertIn("[Warning] Some general warning", mock_stdout.getvalue())

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_error_printed(self, mock_stdout):
        self.logger.error("Some critical error")
        self.assertIn("[Error] Some critical error", mock_stdout.getvalue())


class TestIsValidYoutubeUrl(unittest.TestCase):
    def test_valid_urls(self):
        valid_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "http://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtube.com/watch?v=dQw4w9WgXcQ",
            "http://youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "http://youtu.be/dQw4w9WgXcQ",
            "https://www.youtube.com/shorts/dQw4w9WgXcQ",
            "https://youtube.com/shorts/dQw4w9WgXcQ",
            "https://www.youtube.com/watch?v=AbC_-12345X",
        ]
        for url in valid_urls:
            with self.subTest(url=url):
                self.assertTrue(main.is_valid_youtube_url(url))

    def test_invalid_urls(self):
        invalid_urls = [
            # No scheme (urlparse scheme is empty, failing scheme check)
            "www.youtube.com/watch?v=dQw4w9WgXcQ",
            "youtube.com/watch?v=dQw4w9WgXcQ",
            "youtu.be/dQw4w9WgXcQ",
            # Unsupported scheme
            "ftp://youtube.com/watch?v=dQw4w9WgXcQ",
            "file:///C:/test.mp4",
            # Invalid domains / SSRF attempts
            "https://notyoutube.com/watch?v=dQw4w9WgXcQ",
            "https://attacker-youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtube.com.attacker.com/watch?v=dQw4w9WgXcQ",
            "https://evil-youtu.be/dQw4w9WgXcQ",
            # Invalid video ID lengths (less than 11 chars)
            "https://www.youtube.com/watch?v=short",
            "https://youtu.be/short",
            # Invalid path formats
            "https://www.youtube.com/feed/trending",
            "https://www.youtube.com/user/channelname",
            "",
            "   ",
            "not a url",
        ]
        for url in invalid_urls:
            with self.subTest(url=url):
                self.assertFalse(main.is_valid_youtube_url(url))

    def test_exception_handling(self):
        # Passing invalid type causing exception internally
        self.assertFalse(main.is_valid_youtube_url(None))


class TestSanitizeFilename(unittest.TestCase):
    def test_standard_filenames(self):
        self.assertEqual(main.sanitize_filename("My Song"), "My Song")
        self.assertEqual(main.sanitize_filename("song_123-track"), "song_123-track")

    def test_strip_dangerous_characters(self):
        dangerous = 'Test / Song \\ : * ? " < > | Name'
        self.assertEqual(main.sanitize_filename(dangerous), "Test  Song         Name")

    def test_strip_slashes_and_basename(self):
        # re.sub removes / and \ first, stripping path separators
        self.assertEqual(main.sanitize_filename("folder/secret_song"), "foldersecret_song")
        self.assertEqual(main.sanitize_filename(r"nested\track"), "nestedtrack")

    def test_strip_trailing_mp3_extension(self):
        self.assertEqual(main.sanitize_filename("song.mp3"), "song")
        self.assertEqual(main.sanitize_filename("song.MP3"), "song")
        self.assertEqual(main.sanitize_filename("song.Mp3"), "song")
        self.assertEqual(main.sanitize_filename("my.mp3.file.mp3"), "my.mp3.file")

    def test_strip_whitespace(self):
        self.assertEqual(main.sanitize_filename("   spaced title   "), "spaced title")
        self.assertEqual(main.sanitize_filename("   song.mp3   "), "song")


class TestDownloadAsMp3(unittest.TestCase):
    @patch("main.os.makedirs")
    @patch("main.yt_dlp.YoutubeDL")
    def test_download_default_title(self, mock_ydl_class, mock_makedirs):
        mock_ydl_instance = MagicMock()
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = {"title": "Sample Title"}
        mock_ydl_instance.prepare_filename.return_value = os.path.join("downloads", "Sample Title.webm")

        result = main.download_as_mp3("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

        mock_makedirs.assert_called_once_with("downloads", exist_ok=True)
        mock_ydl_class.assert_called_once()
        opts = mock_ydl_class.call_args[0][0]
        self.assertIn("%(title)s.%(ext)s", opts["outtmpl"])
        self.assertEqual(opts["postprocessors"][0]["preferredcodec"], "mp3")

        mock_ydl_instance.extract_info.assert_called_once_with("https://www.youtube.com/watch?v=dQw4w9WgXcQ", download=True)
        mock_ydl_instance.prepare_filename.assert_called_once_with({"title": "Sample Title"})
        self.assertEqual(result, os.path.join("downloads", "Sample Title.mp3"))

    @patch("main.os.makedirs")
    @patch("main.yt_dlp.YoutubeDL")
    def test_download_custom_name_and_custom_output_dir(self, mock_ydl_class, mock_makedirs):
        mock_ydl_instance = MagicMock()
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = {"title": "Sample Title"}
        mock_ydl_instance.prepare_filename.return_value = os.path.join("custom_dir", "My Safe Song.webm")

        result = main.download_as_mp3(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            custom_name="My Safe / Song.mp3",
            output_dir="custom_dir"
        )

        mock_makedirs.assert_called_once_with("custom_dir", exist_ok=True)
        opts = mock_ydl_class.call_args[0][0]
        self.assertIn("My Safe  Song.%(ext)s", opts["outtmpl"])
        self.assertEqual(result, os.path.join("custom_dir", "My Safe Song.mp3"))

    @patch("main.os.makedirs")
    @patch("main.yt_dlp.YoutubeDL")
    def test_download_exception_propagation(self, mock_ydl_class, mock_makedirs):
        mock_ydl_instance = MagicMock()
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.side_effect = Exception("Network download error")

        with self.assertRaises(Exception) as context:
            main.download_as_mp3("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

        self.assertIn("Network download error", str(context.exception))


class TestProcessCsvBatch(unittest.TestCase):
    @patch("builtins.input", return_value="non_existent.csv")
    @patch("main.os.path.exists", return_value=False)
    @patch("sys.stdout", new_callable=io.StringIO)
    def test_file_not_found(self, mock_stdout, mock_exists, mock_input):
        main.process_csv_batch()
        self.assertIn("Error: file not found at non_existent.csv", mock_stdout.getvalue())

    @patch("builtins.input", return_value='"empty.csv"')
    @patch("main.os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open, read_data="")
    @patch("sys.stdout", new_callable=io.StringIO)
    def test_empty_csv(self, mock_stdout, mock_open_file, mock_exists, mock_input):
        main.process_csv_batch()
        self.assertIn("The provided CSV file is empty.", mock_stdout.getvalue())

    @patch("builtins.input", return_value="valid.csv")
    @patch("main.os.path.exists", return_value=True)
    @patch("main.download_as_mp3")
    @patch("sys.stdout", new_callable=io.StringIO)
    def test_csv_processing_with_header_valid_invalid_and_error_rows(self, mock_stdout, mock_download, mock_exists, mock_input):
        csv_content = (
            "URL,Custom Title\n"  # Header row (should be skipped)
            "\n"  # Empty row (should be skipped)
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ,Song One\n"  # Valid row
            "https://invalid-url.com/watch?v=12345,Invalid Song\n"  # Invalid URL row
            "https://youtu.be/dQw4w9WgXcQ,\n"  # Valid URL, no custom name
            "https://www.youtube.com/watch?v=AbCdEfGhIjK,Failing Download\n"  # Valid URL that fails
        )

        mock_download.side_effect = [
            "downloads/Song One.mp3",
            "downloads/Video Title.mp3",
            Exception("Download failed for video"),
        ]

        with patch("builtins.open", mock_open(read_data=csv_content)):
            main.process_csv_batch()

        output = mock_stdout.getvalue()
        self.assertIn("Processing URL: https://www.youtube.com/watch?v=dQw4w9WgXcQ", output)
        self.assertIn("Success: downloads/Song One.mp3", output)
        self.assertIn("[Skipped] Invalid YouTube URL: 'https://invalid-url.com/watch?v=12345'", output)
        self.assertIn("Downloading: Default Video Title...", output)
        self.assertIn("Failed: Download failed for video", output)
        self.assertIn("Processing complete.", output)

        self.assertEqual(mock_download.call_count, 3)

    @patch("builtins.input", return_value="corrupt.csv")
    @patch("main.os.path.exists", return_value=True)
    @patch("builtins.open", side_effect=PermissionError("Permission denied"))
    @patch("sys.stdout", new_callable=io.StringIO)
    def test_csv_file_open_exception(self, mock_stdout, mock_open_file, mock_exists, mock_input):
        main.process_csv_batch()
        self.assertIn("Error processing CSV file: Permission denied", mock_stdout.getvalue())


class TestProcessManualLoop(unittest.TestCase):
    @patch("builtins.input", side_effect=["STOP"])
    @patch("sys.stdout", new_callable=io.StringIO)
    def test_stop_command(self, mock_stdout, mock_input):
        main.process_manual_loop()
        self.assertIn("Stopping program... Goodbye!", mock_stdout.getvalue())

    @patch("builtins.input", side_effect=[""])
    @patch("sys.stdout", new_callable=io.StringIO)
    def test_empty_input_stops(self, mock_stdout, mock_input):
        main.process_manual_loop()
        self.assertIn("Stopping program... Goodbye!", mock_stdout.getvalue())

    @patch("builtins.input", side_effect=["https://invalid-url.com"])
    @patch("sys.stdout", new_callable=io.StringIO)
    def test_invalid_url_stops(self, mock_stdout, mock_input):
        main.process_manual_loop()
        self.assertIn("Invalid YouTube URL. Please try again.", mock_stdout.getvalue())

    @patch("builtins.input", side_effect=[
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "My Song",
        "stop"
    ])
    @patch("main.download_as_mp3", return_value="downloads/My Song.mp3")
    @patch("sys.stdout", new_callable=io.StringIO)
    def test_successful_download_and_then_stop(self, mock_stdout, mock_download, mock_input):
        main.process_manual_loop()
        output = mock_stdout.getvalue()
        self.assertIn("Success! Audio saved as: downloads/My Song.mp3", output)
        mock_download.assert_called_once_with("https://www.youtube.com/watch?v=dQw4w9WgXcQ", custom_name="My Song")

    @patch("builtins.input", side_effect=[
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "My Song",
        "stop"
    ])
    @patch("main.download_as_mp3", side_effect=ValueError("Invalid custom filename"))
    @patch("sys.stdout", new_callable=io.StringIO)
    def test_download_value_error(self, mock_stdout, mock_download, mock_input):
        main.process_manual_loop()
        output = mock_stdout.getvalue()
        self.assertIn("Input Error: Invalid custom filename", output)

    @patch("builtins.input", side_effect=[
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "My Song",
        "stop"
    ])
    @patch("main.download_as_mp3", side_effect=Exception("Extraction error"))
    @patch("sys.stdout", new_callable=io.StringIO)
    def test_download_general_exception(self, mock_stdout, mock_download, mock_input):
        main.process_manual_loop()
        output = mock_stdout.getvalue()
        self.assertIn("Download Error: Extraction error", output)


class TestMainInteractiveMenu(unittest.TestCase):
    @patch("builtins.input", side_effect=["1", "non_existent.csv", "3"])
    @patch("sys.stdout", new_callable=io.StringIO)
    def test_menu_option_csv(self, mock_stdout, mock_input):
        runpy.run_path(os.path.abspath(main.__file__), run_name="__main__")
        output = mock_stdout.getvalue()
        self.assertIn("1. Process a CSV file", output)
        self.assertIn("Error: file not found at non_existent.csv", output)
        self.assertIn("Stopping program... Goodbye!", output)

    @patch("builtins.input", side_effect=["2", "STOP", "3"])
    @patch("sys.stdout", new_callable=io.StringIO)
    def test_menu_option_manual(self, mock_stdout, mock_input):
        runpy.run_path(os.path.abspath(main.__file__), run_name="__main__")
        output = mock_stdout.getvalue()
        self.assertIn("2. Manual mode", output)
        self.assertIn("Manual Mode (type STOP or enter an invalid URL to exit)", output)
        self.assertIn("Stopping program... Goodbye!", output)

    @patch("builtins.input", side_effect=["invalid", "exit"])
    @patch("sys.stdout", new_callable=io.StringIO)
    def test_menu_invalid_option_then_exit(self, mock_stdout, mock_input):
        runpy.run_path(os.path.abspath(main.__file__), run_name="__main__")
        output = mock_stdout.getvalue()
        self.assertIn("Invalid choice. Please choose 1, 2, or 3.", output)
        self.assertIn("Stopping program... Goodbye!", output)


if __name__ == "__main__":
    unittest.main()
