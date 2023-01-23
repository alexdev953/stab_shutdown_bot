import asyncio
from datetime import datetime, time
from Config import Config
import aiohttp
from aiogram import types, executor, Bot, Dispatcher, filters
from aiogram.types.inline_keyboard import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.types.reply_keyboard import ReplyKeyboardMarkup, KeyboardButton

from Logger import logger

config = Config()

BOT_TOKEN, CHAT_ID, API_URL = config.get_start_values()

bot = Bot(token=BOT_TOKEN, parse_mode=types.ParseMode.HTML)

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

dp = Dispatcher(bot=bot, loop=loop)

status_emoji = {True: '✅',
                False: '❌'}


async def get_energy_val() -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(API_URL, ssl=False) as resp:
            if resp.ok:
                json_resp = await resp.json()
            else:
                logger.warn(resp.status, await resp.json())
                json_resp = {'data': None}
    logger.debug(json_resp)
    return json_resp


async def make_inline_keyboard(data: dict):
    keyboard = InlineKeyboardMarkup()
    width = []
    for k, v in data.items():
        width.append(InlineKeyboardButton(text=f'{k} {status_emoji.get(v)}',
                                          callback_data=f'grp@{k}'))
        if len(width) == 2:
            keyboard.row(*width)
            width = []
    keyboard.add(InlineKeyboardButton(text='ОНОВИТИ 🔄',
                                      callback_data='upd'))
    keyboard.add(InlineKeyboardButton(text='Дізнатися групу 🏙️',
                                      url="https://oblenergo.cv.ua/shutdowns2/"))
    return keyboard


async def create_keyboard(data=None):
    hour = datetime.now().hour
    energy_val = await get_energy_val() if not data else data
    if energy_val.get('data'):
        keyboard = await make_inline_keyboard(energy_val.get('data').get(str(hour)))
        return keyboard


async def group_detailed(group: str, data: dict):
    detailed = []
    row = []
    for k, v in data.get('data').items():
        time_str = time(hour=int(k)).strftime('%H:%M')
        time_str = f"<b><u>{time_str}</u></b>" if datetime.now().hour == int(k) else f"<pre>{time_str}</pre>"
        row.append(f"{time_str}{status_emoji.get(v.get(group))}")
        if len(row) == 4:
            detailed.append('|'.join(row))
            row = []
    detailed_str = '\n\n'.join(detailed)
    finally_msg = f"<b><u>Група {group}</u></b>\n\n{detailed_str}"
    return finally_msg


async def actual_msg(keyboard) -> str:
    if keyboard:
        return f'Станом на <code>{datetime.now().strftime("%d.%m.%y %H:%M")}</code>\n' \
               f'<b>Оберіть групу для детального перегляду</b>\n👇👇👇👇'
    else:
        return 'Актуальні дані зараз відсутні 😢\nСпробуйте пізніше'


async def actual_info(message: types.Message):
    keyboard = await create_keyboard()
    msg = await actual_msg(keyboard)
    await message.answer(msg, reply_markup=keyboard)


@dp.message_handler(commands=['start'])
async def take_start(message: types.Message):
    about_bot = await bot.get_me()
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True,
                                   one_time_keyboard=True,
                                   row_width=1,
                                   ).row(KeyboardButton('Стан 💡'))
    await message.answer(
        f"Привіт, {message.from_user.first_name}!\nЯ - <b>{about_bot.first_name}</b>",
        reply_markup=keyboard)


@dp.message_handler(filters.Text(equals='Стан 💡'))
async def take_now(message: types.Message):
    await actual_info(message)


@dp.message_handler(filters.Command(['now'], ignore_case=True))
async def take_now_cmd(message: types.Message):
    await actual_info(message)


@dp.callback_query_handler(text_startswith=['grp'])
async def take_group(query: types.CallbackQuery):
    await query.answer('Шукаю світло 🔭')
    group = query.data.split('@')[1]
    energy = await get_energy_val()
    keyboard = await create_keyboard(energy)
    msg = await group_detailed(group, energy) if energy.get('data') else await actual_msg(keyboard)
    await query.message.edit_text(text=msg)
    await query.message.edit_reply_markup(reply_markup=keyboard)


@dp.callback_query_handler(text_startswith=['upd'])
async def take_update(query: types.CallbackQuery):
    await query.answer('Оновлюю дані 🔄')
    keyboard = await create_keyboard()
    msg = await actual_msg(keyboard)
    await query.message.edit_text(msg)
    if keyboard:
        await query.message.edit_reply_markup(keyboard)
    else:
        await query.message.delete_reply_markup()


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
