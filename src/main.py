from datetime import datetime
import os
import uuid
import hashlib

from aiogram import Bot, types, executor
from aiogram.dispatcher import Dispatcher
from aiogram.types import ParseMode
from aiogram.dispatcher.filters import Filter

from classifier import PhotoСlassifier

input_path = '../data/input/'
images_path = '../data/images/'
photos_path = '../data/photos/'

bot_token = os.getenv('ANTIPHOTOSBOT_TELEGRAM_TOKEN', '')
whitelist_chats = os.getenv('KARMABOT_ALLOWED_CHATS', '')

whitelist_chats: list = None if whitelist_chats == '' else [int(chat) for chat in whitelist_chats.split(',')]

bot: Bot = Bot(token=bot_token)
dp: Dispatcher = Dispatcher(bot)
photoСlassifier: PhotoСlassifier = PhotoСlassifier()

# TODO rework to "message.photo[-1].file_unique_id"
def calculate_hash(file_path: str):
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def build_file_name(file_path: str):
    file_hash = calculate_hash(file_path)
    return f"{file_hash}.jpg"

class ignore_old_messages(Filter):
    async def check(self, message: types.Message):
        return (datetime.now() - message.date).seconds < 30


class white_list_chats(Filter):
    async def check(self, message: types.Message):
        if whitelist_chats:
            return message.chat.id in whitelist_chats
        return True


async def download_file(file_id: str) -> str:
    photo_name = f'../data/input/{uuid.uuid1()}_uid1.jpg'
    file_info = await bot.get_file(file_id)
    await bot.download_file(file_info.file_path, photo_name)
    return photo_name


async def check_image_for_is_photo(message) -> bool:
    print(message.photo)

    # Download the photo
    photo_name = await download_file(message.photo[-1].file_id)

    # Get new name with image hash
    im_name = build_file_name(photo_name)

    # Check if image already exists
    if_classified_image_exists = os.path.exists(f'{images_path}/{im_name}')
    if_classified_photo_exists = os.path.exists(f'{photos_path}/{im_name}')

    # print(f'exists in {images_path}{im_name}: {if_classified_image_exists}')
    # print(f'exists in {photos_path}{im_name}: {if_classified_photo_exists}')

    if not if_classified_image_exists and not if_classified_photo_exists:
        # Predict photo
        is_photo = photoСlassifier.is_photo(photo_name)

        # Move photo to direct folder
        if is_photo:
            new_photo_path = photos_path
        else:
            new_photo_path = images_path

        new_photo_name = new_photo_path + im_name

        os.rename(photo_name, new_photo_name)
        print('photo was not in database')
    else:
        print('photo already in database')
        is_photo = if_classified_photo_exists
        # os.remove(photo_name)

    return is_photo

@dp.message_handler(white_list_chats(), ignore_old_messages(), commands=['start'])
async def google(message: types.Message):
    reply_text = "Привіт, додай мене в свій чат і я слідкуватиму щоб захистити групу від фото монітора\nЯ навчу людей робити скріншоти."
    await bot.send_message(message.chat.id, text=reply_text, reply_to_message_id=message.message_id, parse_mode=ParseMode.MARKDOWN)


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

    is_photo = await check_image_for_is_photo(message)

    if is_photo:
        # Send warn
        chat_id = message.chat.id

        advice_reply = 'Фото монітора в чаті, бережіть очі!\nБудь ласка, робіть скріншоти, а не фотографії монітора!\n\n#фотомонітора'
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="Щоб зробити скріншот потрібно тільки...", url="https://github.com/awitwicki/antiphotobot/blob/main/info.md"))

        await bot.send_message(chat_id, text=advice_reply, reply_to_message_id=message.message_id, reply_markup=keyboard)


if __name__ == '__main__':
    dp.bind_filter(white_list_chats)
    dp.bind_filter(ignore_old_messages)
    executor.start_polling(dp)
