import asyncio
import logging
import os
import re
from typing import Union

import aiohttp
import yt_dlp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from py_yt import VideosSearch, Playlist

LOGGER = logging.getLogger(__name__)

API_URL = os.environ.get("API_URL", "").rstrip("/")
API_KEY = os.environ.get("API_KEY", "")

DOWNLOAD_DIR = "downloads"


def _env_dir(name: str) -> str:
    value = os.environ.get(name, "").strip()
    return os.path.abspath(os.path.expanduser(value)) if value else ""


AUDIO_DOWNLOAD_PATH = _env_dir("AUDIO_DOWNLOAD_PATH")
VIDEO_DOWNLOAD_PATH = _env_dir("VIDEO_DOWNLOAD_PATH")

AUDIO_EXTENSIONS = ("webm", "m4a", "mp3", "ogg")
VIDEO_EXTENSIONS = ("mp4", "mkv", "webm")


def is_external_path(path) -> bool:
    if not path:
        return False

    full = os.path.abspath(str(path))

    for base in (AUDIO_DOWNLOAD_PATH, VIDEO_DOWNLOAD_PATH):
        if base and (full == base or full.startswith(base + os.sep)):
            return True

    return False


def _find_external(directory: str, video_id: str, extensions, resp=None):
    names = []

    if resp is not None:
        disposition = resp.content_disposition
        if disposition and disposition.filename:
            name = os.path.basename(disposition.filename)
            if name.startswith(video_id + "."):
                names.append(name)

    names.extend(f"{video_id}.{ext}" for ext in extensions)

    for name in names:
        path = os.path.join(directory, name)
        if os.path.isfile(path) and os.path.getsize(path) > 0:
            return path

    return None


def time_to_seconds(time):
    stringt = str(time)
    return sum(
        int(x) * 60 ** i
        for i, x in enumerate(reversed(stringt.split(":")))
    )


async def _download_media(link: str, kind: str, timeout: int) -> str:
    video_id = (
        link.split("v=")[-1].split("&")[0]
        if "v=" in link
        else link
    )

    if not video_id or len(video_id) < 3 or not API_URL:
        return None

    is_audio = kind == "audio"
    external = AUDIO_DOWNLOAD_PATH if is_audio else VIDEO_DOWNLOAD_PATH
    extensions = AUDIO_EXTENSIONS if is_audio else VIDEO_EXTENSIONS

    if external:
        found = _find_external(external, video_id, extensions)
        if found:
            return found

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    extension = "mp3" if is_audio else "mp4"
    file_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.{extension}")

    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        return file_path

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{API_URL}/download",
                params={
                    "url": video_id,
                    "type": kind,
                    "api_key": API_KEY,
                },
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as resp:
                if resp.status != 200:
                    LOGGER.warning(
                        "Media API returned HTTP %s for %s",
                        resp.status,
                        video_id,
                    )
                    return None

                if external:
                    found = _find_external(
                        external, video_id, extensions, resp
                    )
                    if found:
                        return found

                with open(file_path, "wb") as file:
                    async for chunk in resp.content.iter_chunked(131072):
                        file.write(chunk)

        if os.path.isfile(file_path) and os.path.getsize(file_path) > 0:
            return file_path

        return None

    except Exception:
        LOGGER.exception("Media download failed for %s", video_id)

        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
        return None


async def download_song(link: str) -> str:
    return await _download_media(link, "audio", 300)


async def download_video(link: str) -> str:
    return await _download_media(link, "video", 600)


AUTOPLAY_REQUEST_TIMEOUT = 20
AUTOPLAY_MAX_RETRIES = 3
AUTOPLAY_RETRY_DELAY = 1
AUTOPLAY_RETRYABLE_STATUS = (408, 425, 429, 500, 502, 503, 504)


async def get_autoplay(
    video_id: str,
    timeout: int = AUTOPLAY_REQUEST_TIMEOUT,
    retries: int = AUTOPLAY_MAX_RETRIES,
    seed_id: str = None,
) -> list:
    video_id = (
        video_id.split("v=")[-1].split("&")[0]
        if "v=" in video_id
        else video_id
    )

    if not video_id or len(video_id) < 3 or not API_URL:
        return []

    params = {"video_id": video_id, "api_key": API_KEY}

    if seed_id and seed_id != video_id:
        params["seed_id"] = seed_id

    for attempt in range(retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{API_URL}/autoplay",
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("tracks", [])

                    if (
                        resp.status in AUTOPLAY_RETRYABLE_STATUS
                        and attempt + 1 < retries
                    ):
                        await asyncio.sleep(AUTOPLAY_RETRY_DELAY)
                        continue

                    LOGGER.warning(
                        "Autoplay API returned HTTP %s", resp.status
                    )
                    return []

        except (asyncio.TimeoutError, aiohttp.ClientError):
            if attempt + 1 < retries:
                await asyncio.sleep(AUTOPLAY_RETRY_DELAY)
                continue
            LOGGER.exception("Autoplay request failed")
            return []

        except Exception:
            LOGGER.exception("Unexpected autoplay error")
            return []

    return []


class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.status = "https://www.youtube.com/oembed?url="
        self.listbase = "https://youtube.com/playlist?list="
        self.reg = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    async def exists(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        return bool(re.search(self.regex, link))

    async def url(self, message_1: Message) -> Union[str, None]:
        messages = [message_1]

        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)

        for message in messages:
            if message.entities:
                text = message.text or message.caption or ""

                for entity in message.entities:
                    if entity.type == MessageEntityType.URL:
                        return text[
                            entity.offset:entity.offset + entity.length
                        ]

            if message.caption_entities:
                for entity in message.caption_entities:
                    if entity.type == MessageEntityType.TEXT_LINK:
                        return entity.url

        return None

    async def details(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link

        if "&" in link:
            link = link.split("&")[0]

        results = VideosSearch(link, limit=1)
        result_list = (await results.next()).get("result", [])

        if not result_list:
            raise ValueError("YouTube video details not found")

        result = result_list[0]

        title = result["title"]
        duration_min = result.get("duration")
        thumbnail = result["thumbnails"][0]["url"].split("?")[0]
        vidid = result["id"]
        duration_sec = int(time_to_seconds(duration_min)) if duration_min else 0

        return title, duration_min, duration_sec, thumbnail, vidid

    async def title(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]

        results = VideosSearch(link, limit=1)
        result_list = (await results.next()).get("result", [])
        return result_list[0]["title"] if result_list else None

    async def duration(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]

        results = VideosSearch(link, limit=1)
        result_list = (await results.next()).get("result", [])
        return result_list[0].get("duration") if result_list else None

    async def thumbnail(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]

        results = VideosSearch(link, limit=1)
        result_list = (await results.next()).get("result", [])

        if not result_list:
            return None

        return result_list[0]["thumbnails"][0]["url"].split("?")[0]

    async def video(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]

        try:
            downloaded_file = await download_video(link)

            if downloaded_file:
                return 1, downloaded_file

            return 0, "Video download failed"

        except Exception as exc:
            LOGGER.exception("YouTube video download failed")
            return 0, f"Video download error: {exc}"

    async def playlist(
        self, link, limit, user_id, videoid: Union[bool, str] = None
    ):
        if videoid:
            link = self.listbase + link
        if "&" in link:
            link = link.split("&")[0]

        try:
            plist = await Playlist.get(link)
        except Exception:
            LOGGER.exception("YouTube playlist lookup failed")
            return []

        videos = plist.get("videos") or []
        ids = []

        for data in videos[:limit]:
            if not data:
                continue

            vid = data.get("id")
            if vid:
                ids.append(vid)

        return ids

    async def track(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]

        results = VideosSearch(link, limit=1)
        result_list = (await results.next()).get("result", [])

        if not result_list:
            raise ValueError("YouTube track not found")

        result = result_list[0]

        track_details = {
            "title": result["title"],
            "link": result["link"],
            "vidid": result["id"],
            "duration_min": result.get("duration"),
            "thumb": result["thumbnails"][0]["url"].split("?")[0],
        }

        return track_details, result["id"]

    async def formats(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]

        def get_formats():
            with yt_dlp.YoutubeDL({
                "quiet": True,
                "no_warnings": True,
            }) as ydl:
                info = ydl.extract_info(link, download=False)
                formats_available = []

                for fmt in info.get("formats", []):
                    try:
                        if "dash" not in str(fmt.get("format", "")).lower():
                            formats_available.append({
                                "format": fmt.get("format"),
                                "filesize": fmt.get("filesize"),
                                "format_id": fmt.get("format_id"),
                                "ext": fmt.get("ext"),
                                "format_note": fmt.get("format_note"),
                                "yturl": link,
                            })
                    except Exception:
                        continue

                return formats_available

        return await asyncio.to_thread(get_formats), link

    async def slider(self, link: str, query_type: int, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]

        results = VideosSearch(link, limit=10)
        result_list = (await results.next()).get("result", [])

        if query_type >= len(result_list):
            raise IndexError("YouTube result index out of range")

        result = result_list[query_type]

        return (
            result["title"],
            result.get("duration"),
            result["thumbnails"][0]["url"].split("?")[0],
            result["id"],
        )

    async def download(
        self,
        link: str,
        mystic,
        video: Union[bool, str] = None,
        videoid: Union[bool, str] = None,
        songaudio: Union[bool, str] = None,
        songvideo: Union[bool, str] = None,
        format_id: Union[bool, str] = None,
        title: Union[bool, str] = None,
    ):
        if videoid:
            link = self.base + link

        if "&" in link:
            link = link.split("&")[0]

        # Keep the existing video download path unchanged.
        if video:
            try:
                file_path = await download_video(link)
                return (file_path, True) if file_path else (None, False)
            except Exception:
                LOGGER.exception("YouTube video download failed")
                return None, False

        # Resolve an audio-only URL without saving the song locally.
        def resolve_audio_url():
            options = {
                "quiet": True,
                "no_warnings": True,
                "noplaylist": True,
                "format": "bestaudio[protocol^=http]/bestaudio/best",
            }

            # No cookies or cookie-file options are used here.
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(link, download=False)

                if info and info.get("url"):
                    return info["url"]

                return None

        try:
            stream_url = await asyncio.to_thread(resolve_audio_url)

            if stream_url:
                # False means the queue should retain the video ID,
                # not this temporary URL.
                return stream_url, False

            LOGGER.warning("YouTube returned no audio stream URL")
            return None, False

        except Exception:
            LOGGER.exception("YouTube audio URL resolution failed")
            return None, False


YouTube = YouTubeAPI()
