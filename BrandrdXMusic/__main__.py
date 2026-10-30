import asyncio
import importlib
import importlib.util
import logging
import pkgutil

import config
from pyrogram import idle
from pytgcalls.exceptions import NoActiveGroupCall

from BrandrdXMusic import LOGGER, app, userbot
from BrandrdXMusic.core.call import Hotty
from BrandrdXMusic.misc import sudo
from BrandrdXMusic.plugins import ALL_MODULES
from BrandrdXMusic.utils.database import get_banned_users, get_gbanned
from BrandrdXMusic.plugins.admins.callback import markup_timer
from config import BANNED_USERS


# --------------------------------------------- #
# LOAD BRANDRDXMUSIC + BRANDRDKING PLUGINS
# --------------------------------------------- #

def load_brandrdking_modules():
    loaded = 0

    # Supports either folder location:
    # BrandrdXMusic/BrandrdKing/
    # BrandrdKing/ (repository root)

    package_names = [
        "BrandrdXMusic.BrandrdKing",
        "BrandrdKing",
    ]

    for package_name in package_names:
        try:
            spec = importlib.util.find_spec(package_name)
        except (ImportError, ModuleNotFoundError, ValueError):
            spec = None

        if spec is None or not spec.submodule_search_locations:
            continue

        try:
            package = importlib.import_module(package_name)
        except Exception:
            LOGGER("BrandrdKing").exception(
                "Could not import package %s", package_name
            )
            continue

        for module in pkgutil.iter_modules(
            package.__path__, prefix=package.__name__ + "."
        ):
            if module.ispkg:
                continue

            try:
                importlib.import_module(module.name)
                loaded += 1

            except Exception:
                LOGGER("BrandrdKing").exception(
                    "Failed to load module: %s", module.name
                )

        # Avoid importing the same package twice.
        break

    if not loaded:
        LOGGER("BrandrdKing").warning(
            "No BrandrdKing modules loaded. Check the folder path."
        )


# --------------------------------------------- #
# BOT INITIALIZATION
# --------------------------------------------- #

async def init():
    if not any(
        [
            config.STRING1,
            config.STRING2,
            config.STRING3,
            config.STRING4,
            config.STRING5,
        ]
    ):
        LOGGER("BrandrdXMusic").error(
            "Assistant client variables not defined, exiting..."
        )
        return

    await sudo()

    try:
        users = await get_gbanned()
        for user_id in users:
            BANNED_USERS.add(user_id)

        users = await get_banned_users()
        for user_id in users:
            BANNED_USERS.add(user_id)

    except Exception:
        LOGGER("BrandrdXMusic").exception(
            "Could not load banned users."
        )

    await app.start()

    # Load existing music bot plugins.
    for all_module in ALL_MODULES:
        try:
            importlib.import_module(
                "BrandrdXMusic.plugins" + all_module
            )
        except Exception:
            LOGGER("BrandrdXMusic.plugins").exception(
                "Failed to load plugin: %s", all_module
            )

    LOGGER("BrandrdXMusic.plugins").info(
        "Successfully imported music bot modules."
    )

    # Load BrandrdKing commands.
    load_brandrdking_modules()

    await userbot.start()
    await Hotty.start()

    try:
        await Hotty.stream_call(
            "https://graph.org/file/e999c40cb700e7c684b75.mp4"
        )

    except NoActiveGroupCall:
        LOGGER("BrandrdXMusic").error(
            "Please turn on the videochat of your log group/channel."
        )
        await Hotty.stop()
        await userbot.stop()
        await app.stop()
        return

        except Exception as e:
            LOGGER("BrandrdXMusic").warning(
                "Initial VC connection failed: %s", e
            )

    await Hotty.decorators()
    # Start Stream Markup Timer
    timer_task = asyncio.create_task(markup_timer())

    LOGGER("BrandrdXMusic").info(
    "ᴅʀᴏᴘ ʏᴏᴜʀ ɢɪʀʟꜰʀɪᴇɴᴅ'ꜱ ɴᴜᴍʙᴇʀ ᴀᴛ @BRANDED_PAID_CC ᴊᴏɪɴ @BRANDRD_BOT , @BRANDEDKING8 ꜰᴏʀ ᴀɴʏ ɪꜱꜱᴜᴇꜱ"
            )

    try:
        await idle()
    finally:
        timer_task.cancel()

        try:
            await timer_task
        except asyncio.CancelledError:
            pass
            
        await Hotty.stop()
        await userbot.stop()
        await app.stop()

        LOGGER("BrandrdXMusic").info(
            "Stopping BrandrdXMusic bot..."
        )


if __name__ == "__main__":
    logging.getLogger("telethon.crypto.aes").setLevel(logging.WARNING)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(init())
