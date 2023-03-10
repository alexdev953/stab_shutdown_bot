import asyncio
from datetime import datetime

import aiogram
import aioschedule
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InputMediaPhoto

from Config import Config
from Logger import logger

config = Config()

BOT_TOKEN, CHAT_ID, API_URL = config.get_start_values()

bot = Bot(token=BOT_TOKEN, parse_mode=types.ParseMode.HTML)

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

dp = Dispatcher(bot=bot, loop=loop)


@dp.message_handler(commands=['start'])
async def take_start(message: types.Message):
    about_bot = await bot.get_me()
    await message.answer(
        f"Привіт, {message.from_user.first_name}!\nЯ - <b>{about_bot['first_name']}</b>")


@dp.message_handler(commands=['now'])
async def take_now(message: types.Message):
    photo_url, actual_msg = await prepare_data()
    await send_message(photo=photo_url, actual_time=actual_msg, chat_id=message.from_user.id)


async def edit_message(photo: str, actual_time):
    status, message_id = config.read_from_config()
    await bot.edit_message_media(chat_id=CHAT_ID, message_id=message_id, media=InputMediaPhoto(photo))
    await bot.edit_message_caption(chat_id=CHAT_ID, message_id=message_id, caption=actual_time)


async def send_message(photo: str, actual_time, chat_id=None):
    chat_id = chat_id if chat_id else CHAT_ID
    response_msg = await bot.send_photo(chat_id=chat_id, caption=actual_time, photo=photo)
    return response_msg.message_id


async def prepare_data() -> tuple[str, str]:
    unix_timestamp = int(datetime.now().timestamp() * 1000)
    photo_url = f'http://oblenergo.cv.ua/shutdowns/GPV.png?ver={unix_timestamp}'
    actual_msg = f'Станом на {datetime.now().strftime("%d.%m.%y %H:%M")}'
    return photo_url, actual_msg


async def job():
    photo_url, actual_msg = await prepare_data()
    try:
        await edit_message(photo=photo_url, actual_time=actual_msg)
    except Exception as e:
        logger.exception(e)
        if isinstance(e, aiogram.exceptions.MessageToEditNotFound):
            msg_id = await send_message(photo=photo_url, actual_time=actual_msg)
            config.write_to_config(msg_id)


async def scheduler():
    """
    Планувальник на кожен день
    :return:
    """
    # aioschedule.every().hour.do(job)
    aioschedule.every(10).minutes.do(job)
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)


if __name__ == '__main__':
    loop.create_task(scheduler())
    executor.start_polling(dp, skip_updates=True)
