import logging
import os
from collections import deque
from io import BytesIO

import numpy as np
import requests
from PIL import Image
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

TOKEN = "719194908:AAHYi7_L0m-tFL7CFTLV_uCXxNlARlYa2Pk"
PORT = int(os.environ.get('PORT', '8443'))


def colors_roughly_equal(color1, color2, threshold=5):
    return np.all(np.abs(color1 - color2) <= threshold)


def dfs_inplace(matrix, color, i, j):
    h, w = matrix.shape[0:2]
    queue = deque([(i, j)])
    while len(queue):
        i, j = queue.popleft()

        if matrix[i, j, -1] == 0 or not colors_roughly_equal(matrix[i, j], color):
            continue
        else:
            matrix[i, j, -1] = 0
        queue.append((min(i + 1, h - 1), j))
        queue.append((max(0, i - 1), j))
        queue.append((i, min(j + 1, w - 1)))
        queue.append((i, max(j - 1, 0)))


def process_image(bot, update):
    print("Received image from {}".format(update.message.chat_id))
    img_document = update.message.document
    print(img_document)
    if not img_document['mime_type'].startswith('image'):
        return
    img_file_id = img_document['file_id']
    file = bot.getFile(img_file_id)
    img_url = file.file_path
    response = requests.get(img_url)
    img = Image.open(BytesIO(response.content))
    img = img.convert('RGBA')
    pixels = np.array(img)
    bg_value = np.copy(pixels[0, 0]).astype('int32')
    h, w = pixels.shape[0:2]
    print("starting dfs")
    dfs_inplace(pixels, bg_value, 0, 0)
    if pixels[-1, -1, -1] != 0:
        dfs_inplace(pixels, bg_value, h - 1, w - 1)

    img = Image.fromarray(pixels)
    img.thumbnail((512, 512), Image.ANTIALIAS)  # inplace

    image_file = BytesIO()
    img.save(image_file, format='PNG', quality=95)
    image_file.seek(0)  # important, set pointer to beginning after writing image
    print("ready to send")
    bot.send_document(chat_id=update.message.chat_id, document=image_file)


def start(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Just send me image document")


updater = Updater(token=TOKEN)
dispatcher = updater.dispatcher
start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)
image_handler = MessageHandler(Filters.document, process_image)
dispatcher.add_handler(image_handler)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

updater.start_webhook(
    listen="0.0.0.0",
    port=PORT,
    url_path=TOKEN
)

updater.bot.set_webhook(
    "https://image-thumbnail-bot.herokuapp.com/" + TOKEN
)

updater.idle()
