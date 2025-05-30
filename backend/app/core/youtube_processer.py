# from youtube_transcript_api import YouTubeTranscriptApi
from pytube import YouTube
from pytube.exceptions import PytubeError, VideoUnavailable
from urllib.parse import urlparse, parse_qs
import re
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

class YouTubeProcessor:
    @staticmethod
    def validate_youtube_url(url: str) -> None:
        """More permissive YouTube URL validation"""
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
        """More flexible video ID extraction"""
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

            # Fallback
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
    def get_transcript(video_id: str) -> Optional[str]:
        """Fetch transcript with fallback logic"""
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

            # Try English transcripts
            for transcript in transcript_list:
                if transcript.language_code == 'en':
                    try:
                        return " ".join([t.text for t in transcript.fetch()])
                    except Exception:
                        continue

            # Fallback: try any available transcript
            for transcript in transcript_list:
                try:
                    return " ".join([t.text for t in transcript.fetch()])
                except Exception:
                    continue

            return None

        except Exception as e:
            logger.warning(f"Transcript error for {video_id}: {str(e)}")
            return None

    @staticmethod
    def get_video_metadata(video_url: str) -> Dict[str, str]:
        """Get metadata with fallback and error handling"""
        try:
            yt = YouTube(video_url)

            title = yt.title or "No title available"
            description = yt.description or "No description available"

            return {
                'title': title,
                'description': description,
                'author': yt.author or "Unknown Author",
                'length': yt.length,
                'views': yt.views,
                'retrieved_successfully': True
            }

        except VideoUnavailable:
            return {
                'retrieved_successfully': False,
                'error': "Video is unavailable"
            }
        except Exception as e:
            logger.error(f"Metadata error: {str(e)}")
            return {
                'retrieved_successfully': False,
                'error': str(e)
            }
