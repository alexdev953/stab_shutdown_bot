import asyncio
from datetime import datetime, time
from Config import Config
import aiohttp
from aiogram import types, executor, Bot, Dispatcher, filters, exceptions
from aiogram.types.inline_keyboard import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.types.reply_keyboard import ReplyKeyboardMarkup, KeyboardButton

from Logger import logger
from db import DataBase

db = DataBase()

config = Config()

BOT_TOKEN, CHAT_ID, API_URL = config.get_start_values()

bot = Bot(token=BOT_TOKEN, parse_mode=types.ParseMode.HTML)

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

dp = Dispatcher(bot=bot, loop=loop)

status_emoji = {True: '✅',
                False: '❌'}

firs_key = ReplyKeyboardMarkup(resize_keyboard=True,
                               one_time_keyboard=True,
                               row_width=1,
                               ).row(KeyboardButton('Стан 💡'))


async def get_energy_val() -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(API_URL, ssl=False) as resp:
            if resp.ok:
                json_resp = await resp.json()
                # json_resp = {'data': None}
            else:
                logger.warn(resp.status, await resp.json())
                json_resp = {'data': None}
    logger.debug(json_resp)
    return json_resp


async def make_inline_keyboard(data: dict, hour: str):
    keyboard = InlineKeyboardMarkup()
    width = []
    if data.get('data'):
        for k, v in data.get('data').get(hour).items():
            width.append(InlineKeyboardButton(text=f'{k} {status_emoji.get(v)}',
                                              callback_data=f'grp@{k}'))
            if len(width) == 2:
                keyboard.row(*width)
                width = []
    keyboard.add(InlineKeyboardButton(text='🔄 ОНОВИТИ 🔄',
                                      callback_data='upd'))
    keyboard.add(InlineKeyboardButton(text='🏙️ Дізнатися групу 🏙️',
                                      url="https://oblenergo.cv.ua/shutdowns2/"))
    return keyboard


async def create_keyboard(data: dict) -> tuple[bool, types.inline_keyboard.InlineKeyboardMarkup]:
    hour = datetime.now().hour
    keyboard = await make_inline_keyboard(data, str(hour))
    status = True if data.get('data') else False
    return status, keyboard


async def group_detailed(group: str, data: dict):
    detailed = []
    row = []
    for k, v in data.get('data').items():
        time_str = time(hour=int(k)).strftime('%H:%M')
        time_str = f"<b><u>{time_str}</u></b>" if datetime.now().hour == int(k) else f"<code>{time_str}</code>"
        row.append(f"{time_str}{status_emoji.get(v.get(group))}")
        if len(row) == 4:
            detailed.append('|'.join(row))
            row = []
    detailed_str = '\n\n'.join(detailed)
    finally_msg = f"🏙️<b><u>Група {group}</u></b>\n\n{detailed_str}"
    return finally_msg


async def actual_msg(status: bool) -> str:
    if status:
        return f'Станом на <code>{datetime.now().strftime("%d.%m.%y %H:%M")}</code>\n' \
               f'<b>Оберіть групу для детального перегляду</b>\n👇👇👇👇'
    else:
        return 'Актуальні дані зараз відсутні😢😢😢\nСпробуйте пізніше⏱️'


async def actual_info(message: types.Message):
    energy = await get_energy_val()
    data_status, keyboard = await create_keyboard(energy)
    msg = await actual_msg(data_status)
    await message.answer(msg, reply_markup=keyboard)


@dp.message_handler(lambda message: db.check_user(message.from_user),
                    commands=['start'])
async def take_start(message: types.Message):
    about_bot = await bot.get_me()
    await message.answer(
        f"Привіт, {message.from_user.first_name}!\nЯ - <b>{about_bot.first_name}</b>",
        reply_markup=firs_key)


@dp.message_handler(lambda message: db.check_user(message.from_user),
                    filters.Text(equals='Стан 💡'))
async def take_now(message: types.Message):
    await actual_info(message)


@dp.message_handler(lambda message: db.check_user(message.from_user),
                    filters.Command('now', ignore_case=True))
async def take_now_cmd(message: types.Message):
    await actual_info(message)


@dp.callback_query_handler(lambda message: db.check_user(message.from_user),
                           text_startswith=['grp'])
async def take_group(query: types.CallbackQuery):
    group = query.data.split('@')[1]
    energy = await get_energy_val()
    data_status, keyboard = await create_keyboard(energy)
    msg = await group_detailed(group, energy) if data_status else await actual_msg(data_status)
    try:
        await query.message.edit_text(text=msg, reply_markup=keyboard)
    except exceptions.MessageNotModified:
        pass


@dp.callback_query_handler(lambda message: db.check_user(message.from_user),
                           text_startswith=['upd'])
async def take_update(query: types.CallbackQuery):
    energy = await get_energy_val()
    data_status, keyboard = await create_keyboard(data=energy)
    msg = await actual_msg(data_status)
    try:
        # raise exceptions.MessageCantBeDeleted(query.as_json())
        await query.message.delete()
    except exceptions.MessageCantBeDeleted:
        await query.message.edit_text('👇👇👇👇')
    finally:
        await asyncio.sleep(0.3)
        await query.message.answer(text=msg, reply_markup=keyboard)


@dp.message_handler(lambda message: db.check_user(message.from_user),
                    filters.Text)
async def get_all_msg(message: types.Message):
    logger.info(message.as_json())
    await message.reply(
        'Нажаль я ще не все вмію',
        reply_markup=firs_key)


@dp.my_chat_member_handler()
async def member_catch(update: types.ChatMemberUpdated):
    user_id = update.from_user.id
    member_status = update.new_chat_member.status
    if member_status == types.ChatMemberStatus.KICKED or member_status == types.ChatMemberStatus.MEMBER:
        db.chat_member(user_id, update.new_chat_member.status)


@dp.errors_handler()
async def send_admin(update: types.Update, error):
    """
    Take error in bot and send to admin and user
    """
    if not isinstance(error, asyncio.exceptions.TimeoutError):
        logger.exception(error)
        logger.error(update.as_json())
        admin_list = [379210271]
        name_error = f'{error}'.replace('<', '').replace('>', '')
        message_to_admin = f"""Сталася помилка в боті:\n{name_error}"""
        for admins in admin_list:
            await bot.send_message(admins, message_to_admin)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
