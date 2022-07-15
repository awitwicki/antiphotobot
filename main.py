from datetime import datetime
import os
import uuid

from aiogram import Bot, types, executor
from aiogram.dispatcher import Dispatcher
from aiogram.types import ParseMode
# from aiogram.types.message import Message
from aiogram.dispatcher.filters import Filter

from classifier import PhotoСlassifier

bot_token = os.getenv('ANTIPHOTOSBOT_TELEGRAM_TOKEN')
whitelist_chats = os.getenv('KARMABOT_ALLOWED_CHATS', '')

whitelist_chats: list = None if whitelist_chats == '' else [int(chat) for chat in whitelist_chats.split(',')]


bot: Bot = Bot(token=bot_token)
dp: Dispatcher = Dispatcher(bot)
photoСlassifier: PhotoСlassifier = PhotoСlassifier()


class ignore_old_messages(Filter):
    async def check(self, message: types.Message):
        return (datetime.now() - message.date).seconds < 30


class white_list_chats(Filter):
    async def check(self, message: types.Message):
        if whitelist_chats:
            return message.chat.id in whitelist_chats
        return True


async def download_file(message: types.Document) -> str:
    photo_name = f'data/images/{uuid.uuid1()}.jpg'
    file_info = await bot.get_file(message.photo[-2].file_id)
    await bot.download_file(file_info.file_path, photo_name)
    return photo_name


@dp.message_handler(white_list_chats(), ignore_old_messages(), commands=['start'])
async def google(message: types.Message):
    reply_text = "Привіт, додай мене в свій чат і я слідкуватиму щоб захистити групу від фото монітора\nЯ навчу людей робити скріншоти."
    msg = await bot.send_message(message.chat.id, text=reply_text, reply_to_message_id=message.message_id, parse_mode=ParseMode.MARKDOWN)


@dp.message_handler(white_list_chats(), ignore_old_messages(), content_types=types.ContentType.PHOTO)
async def photo_handle(message: types.Document):
    # Check photo size
    image_height = message.photo[-1].height
    image_width = message.photo[-1].width

    # Ignore small images
    if image_height < 100 or image_width < 100:
        return

    # Ignore not square-like images
    if image_width / image_height > 2 or image_height / image_width > 2:
        return

    # TODO
    # Crop center rectangle

    # Download photo
    photo_name = await download_file(message)

    # Predict photo
    is_photo = photoСlassifier.is_photo(photo_name)
    if is_photo:
        # Move photo to direct folder
        new_photo_name = photo_name.replace('data/images/', 'data/photos/')
        os.rename(photo_name, new_photo_name)

        # Send warn
        chat_id = message.chat.id

        advice_reply = 'Фото монітора в чаті, бережіть очі!\nБудь ласка, робіть скріншоти, а не фотографії монітора!\n\n#фотомонітора'
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="Щоб зробити скріншот потрібно тільки...", url="https://github.com/awitwicki/antiphotobot/blob/main/info.md"))

        msg = await bot.send_message(chat_id, text=advice_reply, reply_to_message_id=message.message_id, reply_markup=keyboard)


if __name__ == '__main__':
    dp.bind_filter(white_list_chats)
    dp.bind_filter(ignore_old_messages)
    executor.start_polling(dp, on_startup=print(f"Bot is started."))
