import asyncio

from pyrogram.enums import ChatMemberStatus, ChatMembersFilter
from pyrogram.errors import FloodWait, UserAlreadyParticipant

from BrandrdXMusic import app

_REQUESTED_CHATS = set()


async def safe_reply(message, text):
    try:
        await message.reply_text(text)
        return True

    except FloodWait as exc:
        await asyncio.sleep(exc.value + 1)

        try:
            await message.reply_text(text)
            return True
        except Exception:
            return False

    except Exception:
        return False


async def notify_owner(message):
    chat_id = message.chat.id

    try:
        async for member in app.get_chat_members(
            chat_id,
            filter=ChatMembersFilter.ADMINISTRATORS,
        ):
            if member.status == ChatMemberStatus.OWNER:
                try:
                    await app.send_message(
                        member.user.id,
                        (
                            "⚠️ **Admin Request**\n\n"
                            f"Group: **{message.chat.title or 'Unknown'}**\n"
                            f"Group ID: `{chat_id}`\n\n"
                            "Please make the BrandedXMusic bot an "
                            "Admin with Invite Users permission. 🎵"
                        ),
                    )
                    return True

                except Exception:
                    return False

    except Exception:
        return False

    return False


async def invite_assistant(message):
    chat_id = message.chat.id

    try:
        from BrandrdXMusic.core.call import Hotty
        from BrandrdXMusic.utils.database import group_assistant

        # Get the assistant selected for this group.
        assistant = await group_assistant(Hotty, chat_id)

        # Match the selected PyTgCalls client to its Pyrogram client.
        assistant_clients = {
            id(Hotty.one): Hotty.userbot1,
            id(Hotty.two): Hotty.userbot2,
            id(Hotty.three): Hotty.userbot3,
            id(Hotty.four): Hotty.userbot4,
            id(Hotty.five): Hotty.userbot5,
        }

        assistant_client = assistant_clients.get(id(assistant))

        if assistant_client is None:
            await safe_reply(
                message,
                "❌ Could not identify the selected assistant account.",
            )
            return False

        assistant_user = await assistant_client.get_me()

        # Check whether the assistant is already in the group.
        try:
            member = await app.get_chat_member(
                chat_id,
                assistant_user.id,
            )

            if member.status not in (
                ChatMemberStatus.LEFT,
                ChatMemberStatus.BANNED,
            ):
                return True

        except Exception:
            pass

        # Main bot invites the selected assistant.
        await app.add_chat_members(
            chat_id,
            assistant_user.id,
        )

        return True

    except UserAlreadyParticipant:
        return True

    except FloodWait as exc:
        await asyncio.sleep(exc.value + 1)

        try:
            from BrandrdXMusic.core.call import Hotty
            from BrandrdXMusic.utils.database import group_assistant

            assistant = await group_assistant(Hotty, chat_id)

            assistant_clients = {
                id(Hotty.one): Hotty.userbot1,
                id(Hotty.two): Hotty.userbot2,
                id(Hotty.three): Hotty.userbot3,
                id(Hotty.four): Hotty.userbot4,
                id(Hotty.five): Hotty.userbot5,
            }

            assistant_client = assistant_clients.get(id(assistant))

            if not assistant_client:
                return False

            assistant_user = await assistant_client.get_me()

            await app.add_chat_members(
                chat_id,
                assistant_user.id,
            )

            return True

        except UserAlreadyParticipant:
            return True
        except Exception:
            await safe_reply(
                message,
                "❌ Assistant invite failed. Please try again later.",
            )
            return False

    except Exception:
        await safe_reply(
            message,
            (
                "❌ **Assistant Joining Failed**\n\n"
                "Please make sure I have Admin permission with "
                "Invite Users enabled."
            ),
        )
        return False


async def check_admin_and_request(message):
    chat_id = message.chat.id

    try:
        bot = await app.get_me()

        member = await app.get_chat_member(
            chat_id,
            bot.id,
        )

        if member.status not in (
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER,
        ):
            if chat_id not in _REQUESTED_CHATS:
                group_text = (
                    "⚠️ **Admin Permission Required**\n\n"
                    "Mujhe music play karne ke liye Admin banayein. 🎵\n\n"
                    "Please enable Invite Users permission "
                    "and try again."
                )

                sent = await safe_reply(message, group_text)

                await notify_owner(message)

                if sent:
                    _REQUESTED_CHATS.add(chat_id)

            return False

        _REQUESTED_CHATS.discard(chat_id)

    except FloodWait as exc:
        await asyncio.sleep(exc.value + 1)
        return False

    except Exception:
        await safe_reply(
            message,
            (
                "⚠️ I couldn't verify my Admin status.\n\n"
                "Please check my group permissions."
            ),
        )
        return False

    # Automatically invite the selected assistant.
    joined = await invite_assistant(message)

    if not joined:
        return False

    return True
