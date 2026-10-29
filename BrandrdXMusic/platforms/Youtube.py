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

API_URL = os.environ.get(
    "API_URL",
    "https://api.shrutibots.in",
).rstrip("/")

API_KEY = os.environ.get("API_KEY", "").strip()

DOWNLOAD_DIR = "downloads"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def _env_dir(name: str) -> str:
    value = os.environ.get(name, "").strip()
    return (
        os.path.abspath(os.path.expanduser(value))
        if value
        else ""
    )


AUDIO_DOWNLOAD_PATH = _env_dir("AUDIO_DOWNLOAD_PATH")
VIDEO_DOWNLOAD_PATH = _env_dir("VIDEO_DOWNLOAD_PATH")

AUDIO_EXTENSIONS = ("webm", "m4a", "mp3", "ogg")
VIDEO_EXTENSIONS = ("mp4", "mkv", "webm")


# ============================================================
# Helpers
# ============================================================

def _extract_video_id(link: str) -> str:
    link = str(link or "").strip()

    if re.fullmatch(r"[A-Za-z0-9_-]{11}", link):
        return link

    match = re.search(
        r"(?:youtube\.com/watch\?.*?v=|youtu\.be/|"
        r"youtube\.com/shorts/|youtube\.com/embed/)"
        r"([A-Za-z0-9_-]{11})",
        link,
    )

    return match.group(1) if match else ""


def _find_external(
    directory: str,
    video_id: str,
    extensions,
    resp=None,
):
    if not directory or not os.path.isdir(directory):
        return None

    names = []

    if resp is not None:
        disposition = getattr(
            resp,
            "content_disposition",
            None,
        )

        if disposition and disposition.filename:
            name = os.path.basename(disposition.filename)

            if name.startswith(video_id + "."):
                names.append(name)

    names.extend(
        f"{video_id}.{ext}"
        for ext in extensions
    )

    for name in names:
        path = os.path.join(directory, name)

        if (
            os.path.isfile(path)
            and os.path.getsize(path) > 0
        ):
            return path

    return None


def is_external_path(path) -> bool:
    if not path:
        return False

    full = os.path.abspath(str(path))

    for base in (
        AUDIO_DOWNLOAD_PATH,
        VIDEO_DOWNLOAD_PATH,
    ):
        if base:
            try:
                if os.path.commonpath([full, base]) == base:
                    return True
            except ValueError:
                continue

    return False


def time_to_seconds(time):
    stringt = str(time or "0")

    return sum(
        int(x) * 60 ** i
        for i, x in enumerate(
            reversed(stringt.split(":"))
        )
    )


def _existing_download(video_id: str, extensions):
    for ext in extensions:
        path = os.path.join(
            DOWNLOAD_DIR,
            f"{video_id}.{ext}",
        )

        if (
            os.path.isfile(path)
            and os.path.getsize(path) > 0
        ):
            return path

    return None


# ============================================================
# yt-dlp Fallback
# ============================================================

def _yt_dlp_fallback(video_id: str, kind: str):
    url = f"https://www.youtube.com/watch?v={video_id}"

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    options = {
        "format": (
            "bestaudio/best"
            if kind == "audio"
            else "best[ext=mp4]/best"
        ),
        "outtmpl": os.path.join(
            DOWNLOAD_DIR,
            "%(id)s.%(ext)s",
        ),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "retries": 3,
        "fragment_retries": 3,
        "socket_timeout": 30,
        "overwrites": False,
    }

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(
                url,
                download=True,
            )

            if not info:
                LOGGER.error(
                    "yt-dlp returned no information for %s",
                    video_id,
                )
                return None

            filepath = info.get("filepath")

            if filepath and os.path.isfile(filepath):
                if os.path.getsize(filepath) > 0:
                    return filepath

            # Try yt-dlp's expected output filename.
            try:
                filepath = ydl.prepare_filename(info)

                if (
                    os.path.isfile(filepath)
                    and os.path.getsize(filepath) > 0
                ):
                    return filepath
            except Exception:
                LOGGER.debug(
                    "Could not resolve output filename for %s",
                    video_id,
                    exc_info=True,
                )

        # Find the actual extension if it differs from expected.
        for name in os.listdir(DOWNLOAD_DIR):
            if name.startswith(video_id + "."):
                path = os.path.join(DOWNLOAD_DIR, name)

                if (
                    os.path.isfile(path)
                    and os.path.getsize(path) > 0
                    and not path.endswith(".part")
                ):
                    return path

    except Exception:
        LOGGER.exception(
            "yt-dlp fallback failed for %s (%s)",
            video_id,
            kind,
        )

    return None


# ============================================================
# Download Media
# ============================================================

async def _download_media(
    link: str,
    kind: str,
    timeout: int,
) -> str:
    video_id = _extract_video_id(link)

    if not video_id:
        LOGGER.error(
            "Invalid YouTube URL or video ID: %s",
            link,
        )
        return None

    is_audio = kind == "audio"

    external = (
        AUDIO_DOWNLOAD_PATH
        if is_audio
        else VIDEO_DOWNLOAD_PATH
    )

    extensions = (
        AUDIO_EXTENSIONS
        if is_audio
        else VIDEO_EXTENSIONS
    )

    # First check configured external download directory.
    if external:
        found = _find_external(
            external,
            video_id,
            extensions,
        )

        if found:
            return found

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    # Reuse an existing non-empty file.
    existing = _existing_download(
        video_id,
        extensions,
    )

    if existing:
        return existing

    # --------------------------------------------------------
    # Try configured API
    # --------------------------------------------------------

    if API_KEY and API_KEY != "YOUR_API_KEY":
        temp_path = os.path.join(
            DOWNLOAD_DIR,
            f"{video_id}.{ 'mp3' if is_audio else 'mp4' }.part",
        )

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{API_URL}/download",
                    params={
                        "url": video_id,
                        "type": kind,
                        "api_key": API_KEY,
                    },
                    timeout=aiohttp.ClientTimeout(
                        total=timeout
                    ),
                ) as resp:

                    content_type = resp.headers.get(
                        "Content-Type",
                        "",
                    ).lower()

                    if resp.status == 200:
                        # Avoid saving a JSON/text error response
                        # as an MP3 or MP4 file.
                        invalid_types = (
                            "application/json",
                            "text/",
                            "application/xml",
                        )

                        if not any(
                            item in content_type
                            for item in invalid_types
                        ):
                            with open(temp_path, "wb") as file:
                                async for chunk in (
                                    resp.content.iter_chunked(
                                        131072
                                    )
                                ):
                                    file.write(chunk)

                            if (
                                os.path.isfile(temp_path)
                                and os.path.getsize(temp_path) > 0
                            ):
                                final_path = temp_path[:-4]
                                os.replace(
                                    temp_path,
                                    final_path,
                                )
                                return final_path

                    LOGGER.warning(
                        "Download API failed for %s: "
                        "HTTP %s, content-type=%s",
                        video_id,
                        resp.status,
                        content_type,
                    )

        except Exception:
            LOGGER.exception(
                "Download API error for %s",
                video_id,
            )

        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    LOGGER.warning(
                        "Could not remove temporary file: %s",
                        temp_path,
                    )

    else:
        LOGGER.warning(
            "API_KEY is missing or invalid; "
            "trying yt-dlp fallback for %s",
            video_id,
        )

    # --------------------------------------------------------
    # Fallback to yt-dlp
    # --------------------------------------------------------

    try:
        filepath = await asyncio.wait_for(
            asyncio.to_thread(
                _yt_dlp_fallback,
                video_id,
                kind,
            ),
            timeout=timeout,
        )

        if (
            filepath
            and os.path.isfile(filepath)
            and os.path.getsize(filepath) > 0
        ):
            return filepath

    except asyncio.TimeoutError:
        LOGGER.error(
            "Download timed out for %s (%s)",
            video_id,
            kind,
        )

    except Exception:
        LOGGER.exception(
            "Download fallback error for %s",
            video_id,
        )

    LOGGER.error(
        "All download methods failed for %s (%s)",
        video_id,
        kind,
    )

    return None


async def download_song(link: str) -> str:
    return await _download_media(
        link,
        "audio",
        300,
    )


async def download_video(link: str) -> str:
    return await _download_media(
        link,
        "video",
        600,
    )


# ============================================================
# Autoplay API
# ============================================================

AUTOPLAY_REQUEST_TIMEOUT = 20
AUTOPLAY_MAX_RETRIES = 3
AUTOPLAY_RETRY_DELAY = 1

AUTOPLAY_RETRYABLE_STATUS = (
    408,
    425,
    429,
    500,
    502,
    503,
    504,
)


async def get_autoplay(
    video_id: str,
    timeout: int = AUTOPLAY_REQUEST_TIMEOUT,
    retries: int = AUTOPLAY_MAX_RETRIES,
    seed_id: str = None,
) -> list:
    video_id = _extract_video_id(video_id)

    if not video_id:
        return []

    params = {
        "video_id": video_id,
        "api_key": API_KEY,
    }

    if seed_id and seed_id != video_id:
        params["seed_id"] = seed_id

    for attempt in range(1, retries + 1):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{API_URL}/autoplay",
                    params=params,
                    timeout=aiohttp.ClientTimeout(
                        total=timeout
                    ),
                ) as resp:

                    if resp.status == 200:
                        data = await resp.json()

                        if isinstance(data, dict):
                            tracks = data.get("tracks", [])

                            return (
                                tracks
                                if isinstance(tracks, list)
                                else []
                            )

                        return []

                    LOGGER.warning(
                        "Autoplay API returned HTTP %s",
                        resp.status,
                    )

                    if (
                        resp.status not in AUTOPLAY_RETRYABLE_STATUS
                        or attempt == retries
                    ):
                        return []

        except (
            asyncio.TimeoutError,
            aiohttp.ClientError,
        ):
            LOGGER.warning(
                "Autoplay API request failed "
                "(attempt %s/%s)",
                attempt,
                retries,
                exc_info=True,
            )

            if attempt == retries:
                return []

        except Exception:
            LOGGER.exception(
                "Unexpected autoplay API error"
            )
            return []

        await asyncio.sleep(AUTOPLAY_RETRY_DELAY)

    return []


# ============================================================
# YouTube API
# ============================================================

class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.status = "https://www.youtube.com/oembed?url="
        self.listbase = "https://youtube.com/playlist?list="
        self.reg = re.compile(
            r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])"
        )

    async def exists(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):
        if videoid:
            link = self.base + link

        return bool(re.search(self.regex, link))

    async def url(
        self,
        message_1: Message,
    ) -> Union[str, None]:
        messages = [message_1]

        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)

        for message in messages:
            entities = (
                message.entities
                if message.text
                else message.caption_entities
            )

            text = message.text or message.caption or ""

            for entity in entities or []:
                if entity.type == MessageEntityType.URL:
                    return text[
                        entity.offset:
                        entity.offset + entity.length
                    ]

                if entity.type == MessageEntityType.TEXT_LINK:
                    return entity.url

        return None

    async def details(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):
        if videoid:
            link = self.base + link

        if "&" in link:
            link = link.split("&")[0]

        results = VideosSearch(link, limit=1)
        result = (await results.next()).get("result", [])

        if not result:
            raise ValueError(
                f"No YouTube results found for {link}"
            )

        result = result[0]

        title = result["title"]
        duration_min = result.get("duration")
        thumbnail = result["thumbnails"][0]["url"].split("?")[0]
        vidid = result["id"]

        duration_sec = (
            int(time_to_seconds(duration_min))
            if duration_min
            else 0
        )

        return (
            title,
            duration_min,
            duration_sec,
            thumbnail,
            vidid,
        )

    async def title(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):
        details = await self.details(link, videoid)
        return details[0]

    async def duration(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):
        details = await self.details(link, videoid)
        return details[1]

    async def thumbnail(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):
        details = await self.details(link, videoid)
        return details[3]

    async def video(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):
        if videoid:
            link = self.base + link

        try:
            downloaded_file = await download_video(link)

            if downloaded_file:
                return 1, downloaded_file

            return 0, "Video download failed"

        except Exception as e:
            LOGGER.exception("Video download error")
            return 0, f"Video download error: {e}"

    async def playlist(
        self,
        link,
        limit,
        user_id,
        videoid: Union[bool, str] = None,
    ):
        if videoid:
            link = self.listbase + link

        if "&" in link:
            link = link.split("&")[0]

        try:
            plist = await Playlist.get(link)
        except Exception:
            LOGGER.exception("Playlist extraction failed")
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

    async def track(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):
        if videoid:
            link = self.base + link

        if "&" in link:
            link = link.split("&")[0]

        results = VideosSearch(link, limit=1)
        result = (await results.next()).get("result", [])

        if not result:
            raise ValueError(
                f"No YouTube track found for {link}"
            )

        result = result[0]

        title = result["title"]
        duration_min = result.get("duration")
        vidid = result["id"]
        yturl = result.get(
            "link",
            self.base + vidid,
        )
        thumbnail = result["thumbnails"][0]["url"].split("?")[0]

        track_details = {
            "title": title,
            "link": yturl,
            "vidid": vidid,
            "duration_min": duration_min,
            "thumb": thumbnail,
        }

        return track_details, vidid

    async def formats(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):
        if videoid:
            link = self.base + link

        if "&" in link:
            link = link.split("&")[0]

        ytdl_opts = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
        }

        def _get_formats():
            with yt_dlp.YoutubeDL(ytdl_opts) as ydl:
                info = ydl.extract_info(
                    link,
                    download=False,
                )

                formats_available = []

                for fmt in info.get("formats", []):
                    try:
                        if "dash" not in str(
                            fmt.get("format", "")
                        ).lower():
                            formats_available.append(
                                {
                                    "format": fmt.get("format"),
                                    "filesize": fmt.get("filesize"),
                                    "format_id": fmt.get("format_id"),
                                    "ext": fmt.get("ext"),
                                    "format_note": fmt.get("format_note"),
                                    "yturl": link,
                                }
                            )
                    except Exception:
                        continue

                return formats_available

        formats_available = await asyncio.to_thread(
            _get_formats
        )

        return formats_available, link

    async def slider(
        self,
        link: str,
        query_type: int,
        videoid: Union[bool, str] = None,
    ):
        if videoid:
            link = self.base + link

        if "&" in link:
            link = link.split("&")[0]

        search = VideosSearch(link, limit=10)
        results = (await search.next()).get("result", [])

        if not results or query_type >= len(results):
            raise ValueError("No slider results available")

        result = results[query_type]

        title = result["title"]
        duration_min = result.get("duration")
        vidid = result["id"]
        thumbnail = result["thumbnails"][0]["url"].split("?")[0]

        return title, duration_min, thumbnail, vidid

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
    ) -> str:
        if videoid:
            link = self.base + link

        try:
            if video:
                downloaded_file = await download_video(link)
            else:
                downloaded_file = await download_song(link)

            if downloaded_file:
                return downloaded_file, True

            LOGGER.error(
                "YouTube returned an empty file path for %s. "
                "Check API configuration, yt-dlp extraction, "
                "and download logs.",
                _extract_video_id(link) or link,
            )

            return None, False

        except Exception:
            LOGGER.exception(
                "YouTube download failed for %s",
                link,
            )
            return None, False


YouTube = YouTubeAPI()
