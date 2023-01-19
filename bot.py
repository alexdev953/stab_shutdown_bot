import asyncio
import configparser
from datetime import datetime, time

import aiohttp
from aiogram import types, executor, Bot, Dispatcher, filters
from aiogram.types.inline_keyboard import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.types.reply_keyboard import ReplyKeyboardMarkup, KeyboardButton

from Logger import logger


def load_config() -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    config.read('config.ini')
    return config


def write_to_config(value: str):
    config = load_config()
    config['Telegram']['message_id'] = str(value)
    with open('config.ini', 'w') as configfile:
        config.write(configfile)


def read_from_config() -> tuple[bool, int]:
    config = load_config()
    message_id = config['Telegram'].getint('message_id')
    if message_id == 0:
        return False, 0
    return True, message_id


def get_start_values() -> tuple[str, str, str]:
    config = load_config()
    bot_token = config['Telegram']['bot_token']
    chat_id = config['Telegram']['chat_id']
    api_url = config['Web']['url_api']
    return bot_token, chat_id, api_url


BOT_TOKEN, CHAT_ID, API_URL = get_start_values()

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
    keyboard.add(InlineKeyboardButton(text='ОНОВИТИ 🔄', callback_data='upd'))
    return keyboard


async def create_keyboard():
    hour = datetime.now().hour
    energy_val = await get_energy_val()
    if energy_val.get('data'):
        keyboard = await make_inline_keyboard(energy_val.get('data').get(str(hour)))
        return keyboard


async def group_detailed(group: str, data: dict):
    detailed = []
    row = []
    for k, v in data.get('data').items():
        time_str = time(hour=int(k)).strftime('%H:%M')
        row.append(f"{time_str}{status_emoji.get(v.get(group))}")
        if len(row) == 4:
            detailed.append('|'.join(row))
            row = []
    detailed_str = '\n\n'.join(detailed)
    finally_msg = f"<b><u>Група {group}</u></b>\n\n<pre>{detailed_str}</pre>"
    return finally_msg


async def actual_msg(keyboard) -> str:
    if keyboard:
        return f'Станом на <code>{datetime.now().strftime("%d.%m.%y %H:%M")}</code>\n'\
           f'<b>Оберіть групу для детального перегляду</b>\n👇👇👇👇'
    else:
        return 'Немає актуальних данних на сьогодні'


@dp.message_handler(commands=['start'])
async def take_start(message: types.Message):
    about_bot = await bot.get_me()
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True,
                                   one_time_keyboard=True,
                                   row_width=1,
                                   ).row(KeyboardButton('Стан 💡'))
    await message.answer(
        f"Привіт, {message.from_user.first_name}!\nЯ - <b>{about_bot['first_name']}</b>",
        reply_markup=keyboard)


@dp.message_handler(filters.Text(equals='Стан 💡'))
async def take_now(message: types.Message):
    keyboard = await create_keyboard()
    msg = await actual_msg(keyboard)
    await message.answer(msg, reply_markup=keyboard)


@dp.callback_query_handler(text_startswith=['grp'])
async def take_group(query: types.CallbackQuery):
    await query.answer('Шукаю світло 🔭')
    group = query.data.split('@')[1]
    energy = await get_energy_val()
    msg = await group_detailed(group, energy)
    keyboard = query.message.reply_markup
    await query.message.edit_text(text=msg, reply_markup=keyboard)


@dp.callback_query_handler(text_startswith=['upd'])
async def take_update(query: types.CallbackQuery):
    await query.answer('Оновлюю дані')
    keyboard = await create_keyboard()
    msg = await actual_msg(keyboard)
    await query.message.edit_text(msg)
    await query.message.edit_reply_markup(keyboard)


@dp.errors_handler()
async def send_admin(update: types.Update, error):
    """
    Take error in bot and send to admin and user
    """
    if not isinstance(error, asyncio.exceptions.TimeoutError):
        logger.exception(error)
        admin_list = [379210271]
        name_error = f'{error}'.replace('<', '').replace('>', '')
        message_to_admin = f"""Сталася помилка в боті:\n{name_error}"""
        for admins in admin_list:
            await bot.send_message(admins, message_to_admin)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
