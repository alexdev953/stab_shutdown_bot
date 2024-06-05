import asyncio
from datetime import datetime, time
from Config import config_data as config
import aiohttp
from aiogram import types, executor, Bot, Dispatcher, filters, exceptions
from aiogram.types.inline_keyboard import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.types.reply_keyboard import ReplyKeyboardMarkup, KeyboardButton
from web_utils import data_parser
from Logger import logger
from db import DataBase

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}
db = DataBase()

BOT_TOKEN, CHAT_ID, API_URL = config.get_start_values()

bot = Bot(token=BOT_TOKEN, parse_mode=types.ParseMode.HTML)

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

dp = Dispatcher(bot=bot, loop=loop)

status_emoji = {True: '✅',
                False: '❌',
                None: "🤷🏻"}

firs_key = ReplyKeyboardMarkup(resize_keyboard=True,
                               one_time_keyboard=True,
                               row_width=1,
                               ).row(KeyboardButton('Стан 💡'))


async def get_energy():
    data = db.get_json()
    if data.get('data'):
        logger.debug('Get data from DB!')
        return data, data.get('actual')
    if data.get('next_day'):
        logger.debug('Get last actual from DB!')
        return get_last_actual_db()
    else:
        actual_data = await get_energy_val()
        if actual_data.get('actual_date') == datetime.now().strftime('%d.%m.%Y'):
            return actual_data, actual_data.get('actual')
        else:
            return get_last_actual_db()


def get_last_actual_db():
    last_actual = db.get_last_actual()
    return last_actual, last_actual.get('actual')


async def get_energy_val() -> dict:
    async with aiohttp.ClientSession(conn_timeout=5, headers=HEADERS) as session:
        try:
            async with session.get(API_URL, ssl=False) as resp:
                if resp.ok:
                    text_parser = data_parser(await resp.text())
                    db.save_json(text_parser)
                else:
                    logger.warn(resp.status, await resp.json())
                    text_parser = {'data': None}
        except aiohttp.client.ClientError as e:
            logger.error(f'Error: {e}')
            text_parser = {'data': None}
    logger.debug(text_parser)
    return text_parser


async def make_inline_keyboard(data: dict, hour: str, group: str = ''):
    keyboard = InlineKeyboardMarkup()
    width = []
    if data.get('data'):
        for groups, hours in data.get('data').items():
            status_pow = hours.get(hour)
            width.append(InlineKeyboardButton(text=f'{groups} {status_emoji.get(status_pow)}',
                                              callback_data=f'grp@{groups}'))
            if len(width) == 2:
                keyboard.row(*width)
                width = []

    if group:
        keyboard.add(InlineKeyboardButton(text='🔄 Оновити групу 🔄',
                                          callback_data=group))
    else:
        keyboard.add(InlineKeyboardButton(text='🔄 ОНОВИТИ 🔄',
                                          callback_data='upd'))
    keyboard.add(InlineKeyboardButton(text='🏙️ Дізнатися групу 🏙️',
                                      url="https://oblenergo.cv.ua/shutdowns2/"))
    return keyboard


async def create_keyboard(data: dict, group: str = '') -> tuple[bool, types.inline_keyboard.InlineKeyboardMarkup]:
    hour = datetime.now().strftime('%H')
    keyboard = await make_inline_keyboard(data, str(hour), group)
    status = True if data.get('data') else False
    return status, keyboard


async def group_detailed(group: str, data: dict):
    detailed = []
    row = []
    now_time = datetime.now()
    for k, v in data.get('data').get(group).items():
        time_json = time(hour=int(k))
        time_str = await format_time(now_time, time_json, int(k))
        row.append(f"{time_str}{status_emoji.get(v)}")
        if len(row) == 4:
            detailed.append('|'.join(row))
            row = []
    detailed_str = '\n\n'.join(detailed)
    finally_msg = (f"🏙️<b><u>Група {group}</u></b>\n\n{detailed_str}\n\n"
                   f"✅- <code>Заживлені</code> ❌- <code>Відключені</code>\n🤷🏻- <code>Можливо заживлені</code>"
                   f"\n\n<b>Станом на:</b> <code>{data.get('actual')}</code>")
    return finally_msg


async def format_time(time_now: datetime, time_str: time, json_time: int) -> str:
    if time_now.hour == json_time:
        time_form = f"<b><u>{time_now.strftime('%H:%M')}</u></b>"
    else:
        time_form = f"<code>{time_str.strftime('%H:%M')}</code>"
    return time_form


async def actual_msg(status: bool, date: str) -> str:
    if status:
        date = datetime.now().strftime("%d.%m.%y %H:%M") if not date else date
        return f'Станом на <code>{date}</code>\n\n' \
               f'✅- <code>Заживлені</code> ❌- <code>Відключені</code>\n🤷🏻- <code>Можливо заживлені</code>\n\n' \
               f'<b>Оберіть групу для детального перегляду</b>\n👇👇👇👇'
    else:
        return 'Актуальні дані зараз відсутні😢😢😢\nСпробуйте пізніше⏱️'


async def actual_info(message: types.Message):
    energy, date = await get_energy()
    data_status, keyboard = await create_keyboard(energy)
    msg = await actual_msg(data_status, date)
    await message.answer(msg, reply_markup=keyboard)


async def create_short_keyboard(group: str):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(text="🔽 Всі групи 🔽",
                                      callback_data='groups'))
    keyboard.add(InlineKeyboardButton(text='🔄 Оновити групу 🔄',
                                      callback_data=f'grp@{group}'))
    keyboard.add(InlineKeyboardButton(text='🏙️ Дізнатися групу 🏙️',
                                      url="https://oblenergo.cv.ua/shutdowns2/"))
    return keyboard


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
    energy, date = await get_energy()
    keyboard = await create_short_keyboard(group)
    msg = await group_detailed(group, energy)
    try:
        await query.message.edit_text(text=msg, reply_markup=keyboard)
    except exceptions.MessageNotModified as edit_error:
        logger.error(f'Message not edit: {edit_error}')
    except exceptions.MessageToEditNotFound:
        logger.error(f"MessageToEditNotFound:\n{query.as_json()}")
        await query.message.answer(text=msg, reply_markup=keyboard)
    finally:
        await query.answer(f'✅Оновленно 🏙️Група: {group}', cache_time=3)


@dp.callback_query_handler(lambda message: db.check_user(message.from_user),
                           text_startswith=['upd'])
async def take_update(query: types.CallbackQuery):
    energy, date = await get_energy()
    data_status, keyboard = await create_keyboard(data=energy)
    msg = await actual_msg(data_status, date)
    try:
        await query.message.delete()
    except exceptions.MessageCantBeDeleted:
        await query.message.edit_text('👇👇👇👇')
    except exceptions.MessageToDeleteNotFound as del_error:
        logger.error(f"{del_error}:\n{query.as_json()}")
    finally:
        await asyncio.sleep(0.3)
        await query.message.answer(text=msg, reply_markup=keyboard)
        await query.answer('Дані оновлено ✅', cache_time=3)


@dp.callback_query_handler(lambda message: db.check_user(message.from_user),
                           text_startswith=['groups'])
async def get_groups(query: types.CallbackQuery):
    energy, date = await get_energy()
    callback_group = query.message.reply_markup.to_python().get('inline_keyboard')[-2][0].get('callback_data')
    data_status, keyboard = await create_keyboard(energy, group=callback_group)
    await query.message.edit_reply_markup(reply_markup=keyboard)
    await query.answer('🔽 Всі групи 🔽', cache_time=3)


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
