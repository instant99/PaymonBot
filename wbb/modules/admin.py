"""
MIT License

Copyright (c) 2021 TheHamkerCat

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import asyncio

from pyrogram import filters
from pyrogram.types import CallbackQuery, ChatPermissions, Message

from wbb import BOT_ID, SUDOERS, app
from wbb.core.decorators.errors import capture_err
from wbb.core.keyboard import ikb
from wbb.utils.dbfunctions import (add_warn, get_warn, int_to_alpha,
                                   remove_warns, save_filter)
from wbb.utils.functions import (extract_user, extract_user_and_reason,
                                 time_converter)

__MODULE__ = "Admin"
__HELP__ = """/ban - Забанить пользователя
/dban - Удалить сообщение на которое вы ответили, и забанить пользователя
/tban - Забанить пользователя на определенное время
/unban - Разбанить пользователя
/warn - Выдать предупреждение пользователю
/dwarn - Удалить сообщение на которое вы ответили, и выдать предупреждение
/rmwarns - Удалить все предупреждения пользователя
/warns - Посмотреть список предупреждений
/kick - Кикнуть пользователя
/dkick - Кикнуть пользователя и удалить его сообщение
/purge - Очистить сообщения
/del - Удалить сообщение
/promote - Повысить пользователя
/fullpromote - Повысить пользователя и дать ему все права
/demote - Понизить пользователя
/pin - Закрепить сообщение
/mute - Выдать мут пользователю
/tmute - Выдать мут на определенное время
/unmute - Снять мут
/ban_ghosts - Забанить удаленные аккаунты
/report | @admins | @admin - Отправить репорт админам."""


async def member_permissions(chat_id: int, user_id: int):
    perms = []
    try:
        member = await app.get_chat_member(chat_id, user_id)
    except Exception:
        return []
    if member.can_post_messages:
        perms.append("can_post_messages")
    if member.can_edit_messages:
        perms.append("can_edit_messages")
    if member.can_delete_messages:
        perms.append("can_delete_messages")
    if member.can_restrict_members:
        perms.append("can_restrict_members")
    if member.can_promote_members:
        perms.append("can_promote_members")
    if member.can_change_info:
        perms.append("can_change_info")
    if member.can_invite_users:
        perms.append("can_invite_users")
    if member.can_pin_messages:
        perms.append("can_pin_messages")
    if member.can_manage_voice_chats:
        perms.append("can_manage_voice_chats")
    return perms


from wbb.core.decorators.permissions import adminsOnly


async def list_admins(chat_id: int):
    return [
        member.user.id
        async for member in app.iter_chat_members(
            chat_id, filter="administrators"
        )
    ]


async def current_chat_permissions(chat_id):
    perms = []
    perm = (await app.get_chat(chat_id)).permissions
    if perm.can_send_messages:
        perms.append("can_send_messages")
    if perm.can_send_media_messages:
        perms.append("can_send_media_messages")
    if perm.can_send_other_messages:
        perms.append("can_send_other_messages")
    if perm.can_add_web_page_previews:
        perms.append("can_add_web_page_previews")
    if perm.can_change_info:
        perms.append("can_change_info")
    if perm.can_invite_users:
        perms.append("can_invite_users")
    if perm.can_pin_messages:
        perms.append("can_pin_messages")

    return perms


# Get List Of Members In A Chat


async def list_members(group_id):
    return [member.user.id async for member in app.iter_chat_members(group_id)]


# Purge Messages


@app.on_message(filters.command("purge") & ~filters.edited & ~filters.private)
@adminsOnly("can_delete_messages")
async def purgeFunc(_, message: Message):
    await message.delete()

    if not message.reply_to_message:
        return await message.reply_text("Ответьте на сообщение от которого хотите очистить чат.")

    chat_id = message.chat.id
    message_ids = []

    for message_id in range(
        message.reply_to_message.message_id,
        message.message_id,
    ):
        message_ids.append(message_id)

        # Max message deletion limit is 100
        if len(message_ids) == 100:
            await app.delete_messages(
                chat_id=chat_id,
                message_ids=message_ids,
                revoke=True,  # For both sides
            )

            # To delete more than 100 messages, start again
            message_ids = []

    # Delete if any messages left
    if message_ids:
        await app.delete_messages(
            chat_id=chat_id,
            message_ids=message_ids,
            revoke=True,
        )


# Kick members


@app.on_message(
    filters.command(["kick", "dkick"]) & ~filters.edited & ~filters.private
)
@adminsOnly("can_restrict_members")
async def kickFunc(_, message: Message):
    user_id, reason = await extract_user_and_reason(message)
    if not user_id:
        return await message.reply_text("Я не могу найти этого пользователя.")
    if user_id == BOT_ID:
        return await message.reply_text(
            "Вместо того, чтобы пытаться кикнуть меня, ты мог бы тратить своё время лучше. Это просто скучно.."
        )
    if user_id in SUDOERS:
        return await message.reply_text("Ты хочешь кикнуть того кто выше тебя по правам?")
    if user_id in (await list_admins(message.chat.id)):
        return await message.reply_text(
            "Я не могу кикнуть админа, ты это знаешь, я тоже."
        )
    mention = (await app.get_users(user_id)).mention
    msg = f"""
**Kicked User:** {mention}
**Kicked By:** {message.from_user.mention if message.from_user else 'Anon'}
**Причина:** {reason or 'Причина не указана.'}"""
    if message.command[0][0] == "d":
        await message.reply_to_message.delete()
    await message.chat.kick_member(user_id)
    await message.reply_text(msg)
    await asyncio.sleep(1)
    await message.chat.unban_member(user_id)


# Ban members


@app.on_message(
    filters.command(["ban", "dban", "tban"])
    & ~filters.edited
    & ~filters.private
)
@adminsOnly("can_restrict_members")
async def banFunc(_, message: Message):
    user_id, reason = await extract_user_and_reason(message, sender_chat=True)

    if not user_id:
        return await message.reply_text("Я не могу найти этого пользователя.")
    if user_id == BOT_ID:
        return await message.reply_text(
            "Нет, я не сделаю этого! Проси создателя чата сделать это."
        )
    if user_id in SUDOERS:
        return await message.reply_text(
            "Хах, давай сначала сделаем ему <code>/demote</code>."
        )
    if user_id in (await list_admins(message.chat.id)):
        return await message.reply_text(
            "Я не могу забанить админа, ты знаешь правила, я тоже."
        )

    try:
        mention = (await app.get_users(user_id)).mention
    except IndexError:
        mention = (
            message.reply_to_message.sender_chat.title
            if message.reply_to_message
            else "Anon"
        )

    msg = (
        f"**Забаненнен:** {mention}\n"
        f"**Забанил админ:** {message.from_user.mention if message.from_user else 'Anon'}\n"
    )
    if message.command[0][0] == "d":
        await message.reply_to_message.delete()
    if message.command[0] == "tban":
        split = reason.split(None, 1)
        time_value = split[0]
        temp_reason = split[1] if len(split) > 1 else ""
        temp_ban = await time_converter(message, time_value)
        msg += f"**Banned For:** {time_value}\n"
        if temp_reason:
            msg += f"**Причина:** {temp_reason}"
        try:
            if len(time_value[:-1]) < 3:
                await message.chat.kick_member(user_id, until_date=temp_ban)
                await message.reply_text(msg)
            else:
                await message.reply_text("Вы не можете использовать число более 99")
        except AttributeError:
            pass
        return
    if reason:
        msg += f"**Причина:** {reason}"
    await message.chat.kick_member(user_id)
    await message.reply_text(msg)


# Unban members


@app.on_message(filters.command("unban") & ~filters.edited & ~filters.private)
@adminsOnly("can_restrict_members")
async def unbanFunc(_, message: Message):
    # we don't need reasons for unban, also, we
    # don't need to get "text_mention" entity, because
    # normal users won't get text_mention if the the user
    # they want to unban is not in the group.
    if len(message.command) == 2:
        user = message.text.split(None, 1)[1]
    elif len(message.command) == 1 and message.reply_to_message:
        user = message.reply_to_message.from_user.id
    else:
        return await message.reply_text(
            "Укажите имя пользователя или ответьте на сообщение пользователя, чтобы снять бан."
        )
    await message.chat.unban_member(user)
    umention = (await app.get_users(user)).mention
    await message.reply_text(f"Разбанен! {umention}")


# Delete messages


@app.on_message(filters.command("del") & ~filters.edited & ~filters.private)
@adminsOnly("can_delete_messages")
async def deleteFunc(_, message: Message):
    if not message.reply_to_message:
        return await message.reply_text("Ответьте на сообщение которое хотите удалить")
    await message.reply_to_message.delete()
    await message.delete()


# Promote Members


@app.on_message(
    filters.command(["promote", "fullpromote"])
    & ~filters.edited
    & ~filters.private
)
@adminsOnly("can_promote_members")
async def promoteFunc(_, message: Message):
    user_id = await extract_user(message)
    umention = (await app.get_users(user_id)).mention
    if not user_id:
        return await message.reply_text("Я не могу найти этого пользователя.")
    bot = await app.get_chat_member(message.chat.id, BOT_ID)
    if user_id == BOT_ID:
        return await message.reply_text("Я не могу повысить себя.")
    if not bot.can_promote_members:
        return await message.reply_text("У меня недостаточно прав")
    if message.command[0][0] == "f":
        await message.chat.promote_member(
            user_id=user_id,
            can_change_info=bot.can_change_info,
            can_invite_users=bot.can_invite_users,
            can_delete_messages=bot.can_delete_messages,
            can_restrict_members=bot.can_restrict_members,
            can_pin_messages=bot.can_pin_messages,
            can_promote_members=bot.can_promote_members,
            can_manage_chat=bot.can_manage_chat,
            can_manage_voice_chats=bot.can_manage_voice_chats,
        )
        return await message.reply_text(f"Выданы полные права! {umention}")

    await message.chat.promote_member(
        user_id=user_id,
        can_change_info=False,
        can_invite_users=bot.can_invite_users,
        can_delete_messages=bot.can_delete_messages,
        can_restrict_members=False,
        can_pin_messages=False,
        can_promote_members=False,
        can_manage_chat=bot.can_manage_chat,
        can_manage_voice_chats=bot.can_manage_voice_chats,
    )
    await message.reply_text(f"Пользователь {umention} был повышен в правах")


# Demote Member


@app.on_message(filters.command("demote") & ~filters.edited & ~filters.private)
@adminsOnly("can_promote_members")
async def demote(_, message: Message):
    user_id = await extract_user(message)
    if not user_id:
        return await message.reply_text("Я не могу найти этого пользователя.")
    if user_id == BOT_ID:
        return await message.reply_text("Я не могу позинить в правах себя.")
    if user_id in SUDOERS:
        return await message.reply_text(
            "Может сначала я сниму тебя?"
        )
    await message.chat.promote_member(
        user_id=user_id,
        can_change_info=False,
        can_invite_users=False,
        can_delete_messages=False,
        can_restrict_members=False,
        can_pin_messages=False,
        can_promote_members=False,
        can_manage_chat=False,
        can_manage_voice_chats=False,
    )
    umention = (await app.get_users(user_id)).mention
    await message.reply_text(f"Пользователь {umention} был понижен в правах")


# Pin Messages


@app.on_message(filters.command(["pin","unpin"]) & ~filters.edited & ~filters.private)
@adminsOnly("can_pin_messages")
async def pin(_, message: Message):
    if not message.reply_to_message:
        return await message.reply_text("Ответьте на сообщение что бы закрепить/открепить его.")
    r = message.reply_to_message
    if message.command[0] == "unpin":
        await r.unpin()
        return await message.reply_text(f"Сообщение {r.link} было откреплено.")
    if message.command[1] != "loud":
        await r.pin(disable_notification=True)
    else:
        await r.pin(disable_notification=False)
    await message.reply(
        f"**[Сообщение]({r.link}) было закреплено.**",
        disable_web_page_preview=True,
    )
    msg = "Пожалуйста, проверьте закрепленное сообщение: ~ " + f"[Проверить, {r.link}]"
    filter_ = dict(type="text", data=msg)
    await save_filter(message.chat.id, "~pinned", filter_)


# Mute members


@app.on_message(
    filters.command(["mute", "tmute"]) & ~filters.edited & ~filters.private
)
@adminsOnly("can_restrict_members")
async def mute(_, message: Message):
    user_id, reason = await extract_user_and_reason(message)
    if not user_id:
        return await message.reply_text("Я не могу найти этого пользователя.")
    if user_id == BOT_ID:
        return await message.reply_text("Я не могу выдать мут себе")
    if user_id in SUDOERS:
        return await message.reply_text(
            "Если вы думаете, что можете заткнуть админа, вы сильно ошибаетесь!"
        )
    if user_id in (await list_admins(message.chat.id)):
        return await message.reply_text(
            "Я не могу выдать мут админу, ты это знаешь, я тоже."
        )
    mention = (await app.get_users(user_id)).mention
    keyboard = ikb({"⚠   Снять мут   ⚠": f"unmute_{user_id}"})
    msg = (
        f"**Muted User:** {mention}\n"
        f"**Muted By:** {message.from_user.mention if message.from_user else 'Anon'}\n"
    )
    if message.command[0] == "tmute":
        split = reason.split(None, 1)
        time_value = split[0]
        temp_reason = split[1] if len(split) > 1 else ""
        temp_mute = await time_converter(message, time_value)
        msg += f"**Выдан мут на:** {time_value}\n"
        if temp_reason:
            msg += f"**Причина:** {temp_reason}"
        try:
            if len(time_value[:-1]) < 3:
                await message.chat.restrict_member(
                    user_id,
                    permissions=ChatPermissions(),
                    until_date=temp_mute,
                )
                await message.reply_text(msg, reply_markup=keyboard)
            else:
                await message.reply_text("Вы не можете использовать число больше 99")
        except AttributeError:
            pass
        return
    if reason:
        msg += f"**Причина:** {reason}"
    await message.chat.restrict_member(user_id, permissions=ChatPermissions())
    await message.reply_text(msg, reply_markup=keyboard)


# Unmute members


@app.on_message(filters.command("unmute") & ~filters.edited & ~filters.private)
@adminsOnly("can_restrict_members")
async def unmute(_, message: Message):
    user_id = await extract_user(message)
    if not user_id:
        return await message.reply_text("Я не могу найти этого пользователя.")
    await message.chat.unban_member(user_id)
    umention = (await app.get_users(user_id)).mention
    await message.reply_text(f"Мут снят! {umention}")


# Ban deleted accounts


@app.on_message(filters.command("ban_ghosts") & ~filters.private)
@adminsOnly("can_restrict_members")
async def ban_deleted_accounts(_, message: Message):
    chat_id = message.chat.id
    deleted_users = []
    async for i in app.iter_chat_members(chat_id):
        if i.user.is_deleted:
            deleted_users.append(i.user.id)
    if deleted_users:
        banned_users = 0
        for deleted_user in deleted_users:
            try:
                await message.chat.kick_member(deleted_user)
            except Exception:
                pass
            banned_users += 1
        await message.reply_text(f"Забанено {banned_users} удаленных аккаунтов")
    else:
        await message.reply_text("В чате не найдены удаленные аккаунты")


@app.on_message(
    filters.command(["warn", "dwarn"]) & ~filters.edited & ~filters.private
)
@adminsOnly("can_restrict_members")
async def warn_user(_, message: Message):
    user_id, reason = await extract_user_and_reason(message)
    chat_id = message.chat.id
    if not user_id:
        return await message.reply_text("Я не могу найти этого пользователя.")
    if user_id == BOT_ID:
        return await message.reply_text(
            "Хаха невозможно дать предупреждение самой себе."
        )
    if user_id in SUDOERS:
        return await message.reply_text(
            "Ты серьёзно? Ты не можешь дать предупреждение админу."
        )
    if user_id in (await list_admins(chat_id)):
        return await message.reply_text(
            "Я не могу выдать предупреждение админу, ты знаешь правила, я тоже."
        )
    if user_id not in (await list_members(chat_id)):
        return await message.reply_text("Этого пользователя здесь нет.")
    user, warns = await asyncio.gather(
        app.get_users(user_id),
        get_warn(chat_id, await int_to_alpha(user_id)),
    )
    mention = user.mention
    keyboard = ikb({"⚠  Снять преждупреждение  ⚠": f"unwarn_{user_id}"})
    warns = warns["warns"] if warns else 0
    if message.command[0][0] == "d":
        await message.reply_to_message.delete()
    if warns >= 2:
        await message.chat.kick_member(user_id)
        await message.reply_text(
            f"Количество предупреждений у {mention} превышено, выдан бан."
        )
        await remove_warns(chat_id, await int_to_alpha(user_id))
    else:
        warn = {"warns": warns + 1}
        msg = f"""
**Выдано предупреждение:** {mention}
**Выдал наказание:** {message.from_user.mention if message.from_user else 'Anon'}
**Причина:** {reason or 'Причина не указана.'}
**Список варнов:** {warns + 1}/3"""
        await message.reply_text(msg, reply_markup=keyboard)
        await add_warn(chat_id, await int_to_alpha(user_id), warn)


@app.on_callback_query(filters.regex("unwarn_"))
async def remove_warning(_, cq: CallbackQuery):
    from_user = cq.from_user
    chat_id = cq.message.chat.id
    permissions = await member_permissions(chat_id, from_user.id)
    permission = "can_restrict_members"
    if permission not in permissions:
        return await cq.answer(
            "У вас недостаточно прав для выполнения этого действия.\n"
            + f"Нужные права: {permission}",
            show_alert=True,
        )
    user_id = cq.data.split("_")[1]
    warns = await get_warn(chat_id, await int_to_alpha(user_id))
    if warns:
        warns = warns["warns"]
    if not warns or warns == 0:
        return await cq.answer("У пользователя нет предупреждений.")
    warn = {"warns": warns - 1}
    await add_warn(chat_id, await int_to_alpha(user_id), warn)
    text = cq.message.text.markdown
    text = f"~~{text}~~\n\n"
    text += f"__Предупреждение снял {from_user.mention}__"
    await cq.message.edit(text)


# Rmwarns


@app.on_message(
    filters.command("rmwarns") & ~filters.edited & ~filters.private
)
@adminsOnly("can_restrict_members")
async def remove_warnings(_, message: Message):
    if not message.reply_to_message:
        return await message.reply_text(
            "Ответьте на сообщение, чтобы удалить предупреждения пользователя."
        )
    user_id = message.reply_to_message.from_user.id
    mention = message.reply_to_message.from_user.mention
    chat_id = message.chat.id
    warns = await get_warn(chat_id, await int_to_alpha(user_id))
    if warns:
        warns = warns["warns"]
    if warns == 0 or not warns:
        await message.reply_text(f"{mention} have no warnings.")
    else:
        await remove_warns(chat_id, await int_to_alpha(user_id))
        await message.reply_text(f"Removed warnings of {mention}.")


# Warns


@app.on_message(filters.command("warns") & ~filters.edited & ~filters.private)
@capture_err
async def check_warns(_, message: Message):
    user_id = await extract_user(message)
    if not user_id:
        return await message.reply_text("Я не могу найти этого пользователя.")
    warns = await get_warn(message.chat.id, await int_to_alpha(user_id))
    mention = (await app.get_users(user_id)).mention
    if warns:
        warns = warns["warns"]
    else:
        return await message.reply_text(f"{mention} не имеет предупреждение.")
    return await message.reply_text(f"{mention} имеет {warns}/3 предупреждений.")


# Report


@app.on_message(
    (
        filters.command("report")
        | filters.command(["admins", "admin"], prefixes="@")
    )
    & ~filters.edited
    & ~filters.private
)
@capture_err
async def report_user(_, message):
    if not message.reply_to_message:
        return await message.reply_text(
            "Ответьте на сообщение, чтобы сообщить об этом пользователе админам."
        )

    if message.reply_to_message.from_user.id == message.from_user.id:
        return await message.reply_text("Зачем вы хотите пожаловаться на себя ?")

    list_of_admins = await list_admins(message.chat.id)
    if message.reply_to_message.from_user.id in list_of_admins:
        return await message.reply_text(
            "Знаете ли вы, что пользователь, которому вы отвечаете, является администратором ?"
        )

    user_mention = message.reply_to_message.from_user.mention
    text = f"Reported {user_mention} to admins!"
    admin_data = await app.get_chat_members(
        chat_id=message.chat.id, filter="administrators"
    )  # will it giv floods ?
    for admin in admin_data:
        if admin.user.is_bot or admin.user.is_deleted:
            # return bots or deleted admins
            continue
        text += f"[\u2063](tg://user?id={admin.user.id})"

    await message.reply_to_message.reply_text(text)
