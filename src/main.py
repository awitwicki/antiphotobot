from datetime import datetime
import os
import logging
import sys
import uuid
import hashlib

from aiogram import Bot, types, executor
from aiogram.dispatcher import Dispatcher
from aiogram.types import ParseMode
from aiogram.dispatcher.filters import Filter
from minio import Minio
from minio.error import S3Error

logging.basicConfig(stream=sys.stdout, level=logging.WARNING)

from classifier import PhotoСlassifier

logging.warning("Starting application...")

input_path = 'input'
images_path = 'images'
photos_path = 'photos'

bot_token = os.getenv('TELEGRAM_TOKEN', '')
whitelist_chats_val = os.getenv('ANTIPHOTOSBOT_ALLOWED_CHATS', '')
minio_endpoint = os.getenv('MINIO_ENDPOINT')
minio_access_key = os.getenv('MINIO_ACCESS_KEY')
minio_secret_key = os.getenv('MINIO_SECRET_KEY')

anti_photos_bot_bucket_name = 'antiphotosbot-bucket'

minio_client = Minio(
    endpoint="antiphotosbot-minio:9000",
    access_key=minio_access_key,
    secret_key=minio_secret_key,
    secure=False
)

# Create folder if not exists
if not os.path.exists(input_path):
    os.makedirs(input_path)

# Create bucket if not exists
try:
    minio_client.make_bucket(anti_photos_bot_bucket_name)
except S3Error as err:
    if err.code != "BucketAlreadyOwnedByYou":
        logging.exception("Error creating bucket:", err)
        exit(1)
    logging.warning("Bucket already exists")

def is_image_in_bucket_exists(bucket_name: str, object_name: str) -> bool:
    try:
        # Check if the object exists in the bucket
        minio_client.stat_object(bucket_name, object_name)
        logging.info('Object exists in bucket')
        return True
    except S3Error as err:
        if err.code == "NoSuchKey":
            logging.info('Object does not exists in bucket')
            return False
        else:
            logging.exception(f"Error checking object: {bucket_name}:{object_name}", err)
            logging.info('Object does not exists in bucket')
            return False


# Upload file to minio
def upload_file_to_minio(file_path: str, bucket_name: str, object_name: str):
    try:
        minio_client.fput_object(bucket_name, object_name, file_path)
        logging.info(f"File {file_path} uploaded to bucket {bucket_name} as {object_name}")
    except S3Error as err:
        logging.exception("Error uploading file:", err)


whitelist_chats: list = None if whitelist_chats_val == '' else [int(chat) for chat in whitelist_chats_val.split(',')]

bot: Bot = Bot(token=bot_token)
dp: Dispatcher = Dispatcher(bot)
photo_classifier: PhotoСlassifier = PhotoСlassifier()

def calculate_hash(f):
    hash_md5 = hashlib.md5()
    for chunk in iter(lambda: f.read(4096), b""):
        hash_md5.update(chunk)
    return hash_md5.hexdigest()


def build_file_name(file):
    file_hash = calculate_hash(file)
    return f"{file_hash}.jpg"


class ignore_old_messages(Filter):
    async def check(self, message: types.Message):
        return (datetime.now() - message.date).seconds < 30


class white_list_chats(Filter):
    async def check(self, message: types.Message):
        if whitelist_chats:
            return message.chat.id in whitelist_chats
        return True


async def download_file(message: types.Document, path: str) -> str:
    photo_name = f'data/images/{uuid.uuid1()}.jpg'
    file_info = await bot.get_file(message.photo[-2].file_id)
    await bot.download_file(file_info.file_path, photo_name)
    return photo_name


async def check_image_for_is_photo(message) -> bool:   
    file_info = await bot.get_file(message.photo[-1].file_id)
    photo_file = await bot.download_file(file_info.file_path)

    im_name = build_file_name(photo_file)
    logging.info(f'im_name: {im_name}')

    # Check if image already exists
    if_classified_image_exists = is_image_in_bucket_exists(anti_photos_bot_bucket_name, f'{images_path}/{im_name}')
    if_classified_photo_exists = is_image_in_bucket_exists(anti_photos_bot_bucket_name, f'{photos_path}/{im_name}')

    if not (if_classified_image_exists or if_classified_photo_exists):
        # Save the photo to disk with hash as filename
        photo_name = f'{input_path}/{im_name}'
        photo_file.seek(0)

        logging.info(f'Save image to disk: {photo_name}')

        with open(photo_name, "wb") as f:
            f.write(photo_file.read())

        logging.info(f'Image saved: {photo_name}')

        # Predict photo
        is_photo = photo_classifier.is_photo(photo_name)
        
        # Move photo to direct folder
        if is_photo:
            new_photo_name = photo_name.replace(input_path, photos_path)
        else:
            new_photo_name = photo_name.replace(input_path, images_path)
        upload_file_to_minio(photo_name, anti_photos_bot_bucket_name, new_photo_name)
        os.remove(photo_name)
    else:
        is_photo = if_classified_photo_exists
        
    return is_photo


@dp.message_handler(white_list_chats(), ignore_old_messages(), commands=['start'])
async def google(message: types.Message):
    reply_text = "Привіт, додай мене в свій чат і я слідкуватиму щоб захистити групу від фото монітора\nЯ навчу людей робити скріншоти."
    await bot.send_message(message.chat.id, text=reply_text, reply_to_message_id=message.message_id, parse_mode=ParseMode.MARKDOWN)


@dp.message_handler(white_list_chats(), ignore_old_messages(), content_types=types.ContentType.PHOTO)
async def photo_handle(message: types.Document):
    logging.debug(f'Photo message received file_id:{message.photo[-1].file_id}')
    # Check photo size
    image_height = message.photo[-1].height
    image_width = message.photo[-1].width

    # Ignore small images
    if image_height < 100 or image_width < 100:
        logging.debug(f'Ignore small image: {image_height}x{image_width}')
        return

    # Ignore not square-like images
    if image_width / image_height > 2 or image_height / image_width > 2:
        logging.debug(f'Ignore not square-like image: {image_height}x{image_width}')
        return

    # TODO
    # Crop center rectangle

    # Check_image_for_is_photo
    logging.debug('Check image for is photo (run AI)')
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
