from youtube_transcript_api import YouTubeTranscriptApi  # type: ignore
import yt_dlp  # type: ignore
import re
import logging
from faster_whisper import WhisperModel # type: ignore
import whisper # type: ignore
from urllib.parse import urlparse, parse_qs
from typing import Optional, Dict, Tuple
import tempfile
import os

logger = logging.getLogger(__name__)

class YouTubeProcessor:
    @staticmethod
    def validate_youtube_url(url: str) -> None:
        patterns = [
            r'^(https?://)?(www\.)?youtube\.com/watch\?v=[\w-]{11}',
            r'^(https?://)?youtu\.be/[\w-]{11}',
            r'^(https?://)?(www\.)?youtube\.com/embed/[\w-]{11}',
            r'^(https?://)?(www\.)?youtube\.com/shorts/[\w-]{11}',
            r'^(https?://)?(www\.)?youtube\.com/live/[\w-]{11}',
            r'^(https?://)?(www\.)?youtube\.com/v/[\w-]{11}'
        ]
        if not any(re.search(pattern, url) for pattern in patterns):
            raise ValueError(
                "Please provide a valid YouTube URL in one of these formats:\n"
                "- https://www.youtube.com/watch?v=VIDEO_ID\n"
                "- https://youtu.be/VIDEO_ID\n"
                "- https://www.youtube.com/embed/VIDEO_ID\n"
                "- https://www.youtube.com/shorts/VIDEO_ID"
            )

    @staticmethod
    def extract_video_id(url: str) -> str:
        try:
            YouTubeProcessor.validate_youtube_url(url)

            if "youtu.be" in url:
                return url.split("/")[-1].split("?")[0]
            if "/shorts/" in url:
                return url.split("/shorts/")[1].split("?")[0]
            if "/live/" in url:
                return url.split("/live/")[1].split("?")[0]
            if "v=" in url:
                query = urlparse(url).query
                params = parse_qs(query)
                return params["v"][0][:11]
            if "embed/" in url:
                return url.split("embed/")[1].split("?")[0]

            patterns = [
                r'(?:v=|\/)([\w-]{11})',
                r'\.be\/([\w-]{11})',
                r'\/shorts\/([\w-]{11})',
                r'\/live\/([\w-]{11})'
            ]
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    return match.group(1)

            raise ValueError("Could not extract video ID")

        except Exception as e:
            logger.error(f"URL validation failed: {str(e)}")
            raise ValueError("Invalid YouTube URL. Please check the URL format.")

    @staticmethod
    def _download_audio(video_id: str) -> str:
        # Step 1: Check video duration first
        ydl_opts_info = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
                info = ydl.extract_info(f'https://www.youtube.com/watch?v={video_id}', download=False)
                if info.get('duration', 0) > 600:  # 10 minutes
                    raise ValueError("Video too long (>10 min)")
        except Exception as e:
            logger.error(f"Failed to fetch video info: {str(e)}")
            raise ValueError("Could not fetch video information")

        # Step 2: Proceed to audio download
        ydl_opts_download = {
            'format': 'bestaudio[abr<=64]',  # Limit to 64 kbps
            'outtmpl': os.path.join(tempfile.gettempdir(), f'%(id)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '64',  # Lower quality
            }]
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts_download) as ydl:
                info = ydl.extract_info(f'https://www.youtube.com/watch?v={video_id}', download=True)
                return ydl.prepare_filename(info).replace('.webm', '.mp3').replace('.m4a', '.mp3')
        except Exception as e:
            logger.error(f"Failed to download audio: {str(e)}")
            raise ValueError("Could not download video audio")

    @staticmethod
    def _transcribe_audio(audio_path: str) -> str:
        try:
            model = WhisperModel("tiny", device="cpu", compute_type="int8")
            segments, _ = model.transcribe(audio_path)
            transcript = " ".join([segment.text for segment in segments])
            return transcript
        except Exception as e:
            logger.error(f"Transcription failed: {str(e)}")
            raise ValueError("Could not transcribe audio")
        finally:
            try:
                os.remove(audio_path)
            except:
                pass

    @staticmethod
    def get_transcript(video_id: str, video_url: str = None) -> Tuple[Optional[str], Optional[str]]:
        """Fetch transcript with fallback to speech-to-text"""
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

            for transcript in transcript_list:
                if transcript.language_code == 'en':
                    try:
                        return (" ".join([t.text for t in transcript.fetch()]), None)
                    except Exception as e:
                        logger.warning(f"Failed to fetch English transcript: {str(e)}")
                        continue

            for transcript in transcript_list:
                try:
                    return (" ".join([t.text for t in transcript.fetch()]), None)
                except Exception as e:
                    logger.warning(f"Failed to fetch transcript: {str(e)}")
                    continue

            if not video_url:
                return None, "No transcript and no video URL provided for fallback"

            logger.info(f"No transcript available. Attempting speech-to-text for {video_id}")
            audio_path = YouTubeProcessor._download_audio(video_id)
            transcript = YouTubeProcessor._transcribe_audio(audio_path)
            return transcript, None

        except Exception as e:
            error_msg = str(e)
            if "Subtitles are disabled" in error_msg:
                if not video_url:
                    return None, "Subtitles disabled and no video URL for fallback"
                try:
                    audio_path = YouTubeProcessor._download_audio(video_id)
                    transcript = YouTubeProcessor._transcribe_audio(audio_path)
                    return transcript, None
                except Exception as se:
                    return None, f"Failed fallback speech-to-text: {str(se)}"
            logger.warning(f"Transcript error: {error_msg}")
            return None, error_msg

    @staticmethod
    def get_transcript_with_fallback(video_id: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Try to get transcript, fallback to audio transcription if not available
        Returns: (transcript, error_message)
        """
        try:
            transcript, error = YouTubeProcessor.get_transcript(video_id)
            if transcript:
                return transcript, None

            logger.info(f"No transcript available, attempting audio transcription for {video_id}")
            audio_path = YouTubeProcessor._download_audio(video_id)
            transcript = YouTubeProcessor._transcribe_audio(audio_path)

            if len(transcript.strip()) < 50:
                return None, "Transcribed content too short (video may have no speech)"

            return transcript, None

        except Exception as e:
            logger.error(f"Transcript with fallback failed: {str(e)}")
            return None, str(e)

    @staticmethod
    def get_video_metadata(video_url: str) -> Dict[str, str]:
        """Get metadata with yt-dlp"""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'extract_flat': True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)

                if not info:
                    return {
                        'retrieved_successfully': False,
                        'error': "Could not retrieve video information"
                    }

                return {
                    'title': info.get('title', 'No title available'),
                    'description': info.get('description', 'No description available'),
                    'author': info.get('uploader', 'Unknown Author'),
                    'length': info.get('duration', 0),
                    'views': info.get('view_count', 0),
                    'retrieved_successfully': True
                }

        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e).lower()
            if 'private' in error_msg:
                detail = "Video is private"
            elif 'age restricted' in error_msg:
                detail = "Age-restricted video"
            elif 'unavailable' in error_msg:
                detail = "Video unavailable in your region"
            elif 'removed' in error_msg or 'terminated' in error_msg:
                detail = "Video has been removed"
            else:
                detail = f"Video metadata error: {str(e)}"

            return {
                'retrieved_successfully': False,
                'error': detail
            }
        except Exception as e:
            logger.error(f"Metadata error: {str(e)}")
            return {
                'retrieved_successfully': False,
                'error': str(e)
            }
