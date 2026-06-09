import os
import shutil
from typing import List, Tuple

import grequests
import telebot
from config import STICKERS_DIR, TOKEN, URL
from telebot.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message


bot = telebot.TeleBot(TOKEN, parse_mode=None)
sticker_data = dict()
CONTENT_TYPES = ["text", "audio", "document", "photo", "sticker",
                 "video", "video_note", "voice", "location", "contact", "pinned_message",
                 "animation"
                 ]

@bot.message_handler(commands=["start"])
def start(message: Message) -> None:
    """Send to user welcome message.

    :param message: Object Message.
    """
    bot.send_message(
        message.chat.id,
        f"Hi! I'm bot - @{bot.get_me().username}.\n"
        + "Have a good day!!\n"
        + "I'll help you download stickers!\n"
        + "Send me a sticker and I'll download it for you.",
    )


@bot.message_handler(content_types=CONTENT_TYPES)
def message(message: Message) -> None:
    """Send to user warning message or sticker information and a inline keyboard.

    :param message: Object Message.
    """
    global sticker_data
    if not message.content_type == 'sticker':
        bot.send_message(message.chat.id, "The bot works only with stickers.‼")

    else:
        sticker_info = message.sticker
        sticker_data[message.chat.id] = {'file_id': sticker_info.file_id,
                                          'set_name': sticker_info.set_name}
        inline_markup = InlineKeyboardMarkup(row_width=2).add(
        from pathlib import Path
        from concurrent.futures import ThreadPoolExecutor
        from PIL import Image
            InlineKeyboardButton("Download the sticker", callback_data="sticker"),
            InlineKeyboardButton("Download sticker pack", callback_data="pack"),
        )
        bot.send_message(
            message.chat.id,
            "Information about the sticker:\n"
            + f"emoji: {sticker_info.emoji}\n"
            + f"set name: {sticker_info.set_name}",
            reply_markup=inline_markup,
        )


@bot.callback_query_handler(func=lambda call: True)
def callback(call: CallbackQuery) -> None:
    """Handle keyboard buttons.

    :param call: CallbackQuery object.
    """
    chat_id = call.message.chat.id
    sticker_info = sticker_data.pop(chat_id)
    bot.edit_message_reply_markup(chat_id, call.message.id, reply_markup=None)
    if call.data == "sticker":
        sticker(sticker_info, chat_id)
    elif call.data == "pack":
        sticker_pack(sticker_info, chat_id)


def sticker(sticker_info: dict, chat_id: int) -> None:
    """Handle the "sticker" button.
    Create a folder, download sticker, create archive file of folder.
    Send to user archive file and delete archive and folder.

    :param sticker_info: A dictionary with data sticker.
    :param chat_id: A user's id.
    """
    path_to_folder = create_folder(sticker_info['set_name'], chat_id)
    file_id = sticker_info["file_id"]
    file_path = bot.get_file(file_id).file_path
    file_name = file_path.split("/")[1]
    images = download_stickers([(file_path, file_name)])
    for name, image in images:
        save_image(image.content, name, path_to_folder)
    # Folder archiving
    shutil.make_archive(base_name=path_to_folder, format="tar", root_dir=path_to_folder)
    with open(path_to_folder + ".tar", "rb") as archive:
        bot.send_document(chat_id, archive)
    # Delete tar file and folder
    delete_folder_file(path_to_folder)
<<<<<<< HEAD
    
    
def convert_image(webp_path):
    # Define output path with .png extension
    png_path = webp_path.with_suffix('.png')
    
    # Convert and save
    with Image.open(webp_path) as img:
        img.save(png_path, 'PNG')
    print(f"Successfully converted: {webp_path.name}")
        
def delete_webp_files(path: str) -> None:
    """Delete .webp files from folder.

    :param path: Path to folder.
    """
    for file in Path(path).glob("*.webp"):
        try:
            file.unlink()
            print(f"Deleted: {file.name}")
        except Exception as e:
            print(f"Error deleting {file.name}: {e}")
        
def batch_convert(path: str) -> None:
    # Target all .webp files in current working directory
    webp_files = list(path.glob("*.webp"))
    
    if not webp_files:
        print("No .webp files found in this directory.")
        return

            bot.polling(none_stop=True)
    Send to user archive file and delete archive and folder.

    :param sticker_info: A dictionary with data sticker.
    :param chat_id: A user's id.
    """
    bot.send_message(chat_id, "Please wait a moment😛")
    set_name = sticker_info["set_name"]
    path_to_folder = create_folder(set_name, chat_id)
    sticker_list = bot.get_sticker_set(set_name).stickers
    tasks = []
    for sticker in sticker_list:
        file_path = bot.get_file(sticker.file_id).file_path
        file_name = file_path.split("/")[1]
        tasks.append((file_path, file_name))
    images = download_stickers(tasks)
    for name, image in images:
        save_image(image.content, name, path_to_folder)
    # Folder archiving
    shutil.make_archive(base_name=path_to_folder, format="tar", root_dir=path_to_folder)
    with open(path_to_folder + ".tar", "rb") as archive:
        bot.send_document(chat_id, archive)
    # Delete tar file and folder
    delete_folder_file(path_to_folder)


def download_stickers(tasks: List[Tuple]) -> List[Tuple]:
    """Asynchronous download of stickers from Telegram server.

    :param tasks: List of tuples with image name and path.
    :return: List of tuples image name and response
    """
    file_names = [task[1] for task in tasks]
    gen = (grequests.get(URL.format(TOKEN=TOKEN, file_path=task[0])) for task in tasks)
    response = grequests.map(gen)
    return list(zip(file_names, response))


def create_folder(set_name: str, chat_id: int) -> str:
    """Create folder for stickers.

    :param chat_id: A user's id.
    :return: Path to folder.
    """
    path = os.path.join(STICKERS_DIR, set_name + f'_{chat_id}')
    if not os.path.exists(path):
        os.mkdir(path)
    return path


def delete_folder_file(path: str) -> None:
    """Deleting archive file and folder with stickers.

    :param path: Path to folder.
    """
    # Delete archive file
    os.remove(path + ".tar")
    # Delete folder
    shutil.rmtree(path)


def save_image(image: bytes, image_name: str, path: str) -> None:
    """Save image to a user's folder.

    :param image: Bytes of image.
    :param image_name: A image name.
    :param path: A location to save the image.
    """
    with open(f"{path}/{image_name}", "wb") as img:
        img.write(image)


if __name__ == "__main__":
<<<<<<< HEAD
    task_queue = multiprocessing.JoinableQueue()

    # Spawn a pool of worker processes
    num_workers = os.cpu_count() or 4  # Use number of CPU cores or default to 4
    processes = []
    for _ in range(num_workers):
        p = multiprocessing.Process(target=download_worker, args=(task_queue,))
        p.daemon = True # Allows processes to exit when the main script stops
        p.start()
        processes.append(p)

    print("Bot is polling...")
    try:
        bot.polling(none_stop=True)
    except KeyboardInterrupt:
        print("Stopping...")
=======
    bot.polling(none_stop=True)
>>>>>>> parent of f7ea542 (blows your whole shit up with AI slop)
