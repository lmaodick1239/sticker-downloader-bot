import os
import shutil
import multiprocessing
from typing import List, Tuple
from pathlib import Path
import grequests
import telebot
from config import STICKERS_DIR, TOKEN, URL
from telebot.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from concurrent.futures import ThreadPoolExecutor
import io
from PIL import Image

# This will be executed by both the main process and worker processes,
# giving each worker its own independent TeleBot instance.
bot = telebot.TeleBot(TOKEN, parse_mode=None)
sticker_data = dict()
CONTENT_TYPES = ["text", "audio", "document", "photo", "sticker",
                 "video", "video_note", "voice", "location", "contact", "pinned_message",
                 "animation"
                 ]

task_queue = None

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
        inline_markup = InlineKeyboardMarkup(row_width=2).add(
            InlineKeyboardButton("Download the sticker", callback_data="sticker"),
            InlineKeyboardButton("Download sticker pack", callback_data="pack"),
        )
        sent_msg = bot.send_message(
            message.chat.id,
            "Information about the sticker:\n"
            + f"emoji: {sticker_info.emoji}\n"
            + f"set name: {sticker_info.set_name}",
            reply_markup=inline_markup,
        )
        # Store the sticker info using the bot's message ID so multiple requests don't overwrite each other
        sticker_data[sent_msg.id] = {'file_id': sticker_info.file_id,
                                          'set_name': sticker_info.set_name}


@bot.callback_query_handler(func=lambda call: True)
def callback(call: CallbackQuery) -> None:
    """Handle keyboard buttons.

    :param call: CallbackQuery object.
    """
    chat_id = call.message.chat.id
    message_id = call.message.id
    global sticker_data, task_queue
    
    # Safely pop the data to avoid KeyError if the button is pressed multiple times
    sticker_info = sticker_data.pop(message_id, None)
    
    try:
        bot.edit_message_reply_markup(chat_id, call.message.id, reply_markup=None)
    except Exception:
        pass

    if sticker_info is None:
        bot.send_message(chat_id, "⚠️ No pending sticker found or already processing.")
        return

    bot.send_message(chat_id, "⏳ Your download has been queued. Please wait...")

    if task_queue is not None:
        task_queue.put((chat_id, call.data, sticker_info))
    else:
        # Fallback if queue is not initialized
        if call.data == "sticker":
            sticker(sticker_info, chat_id)
        elif call.data == "pack":
            sticker_pack(sticker_info, chat_id)


def download_worker(queue):
    """Worker process that takes tasks from the queue and executes them."""
    print("Worker process started.")
    while True:
        try:
            task = queue.get()
            if task is None:  # Sentinel value to shut down workers
                break
            
            chat_id, action, sticker_info = task
            print(f"Processing {action} for chat {chat_id}...")
            
            if action == "sticker":
                sticker(sticker_info, chat_id)
            elif action == "pack":
                sticker_pack(sticker_info, chat_id)
                
            bot.send_message(chat_id, "✅ Your sticker task has been completed!")
                
        except Exception as e:
            print(f"Error in worker process: {e}")
            try:
                bot.send_message(chat_id, "⚠️ An error occurred while processing your sticker.")
            except Exception:
                pass
        finally:
            queue.task_done()


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
        print(f"Saving image...{name}")
        save_image(image.content, name, path_to_folder)
    # Folder archiving
    shutil.make_archive(base_name=path_to_folder, format="zip", root_dir=path_to_folder)
    with open(path_to_folder + ".zip", "rb") as archive:
        bot.send_document(chat_id, archive)
    # Delete tar file and folder
    delete_folder_file(path_to_folder)
    
    
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

    print(f"Found {len(webp_files)} images. Starting conversion...")
    
    # Process files in parallel using all available CPU threads
    with ThreadPoolExecutor() as executor:
        executor.map(convert_image, webp_files)
    # After conversion, delete original .webp files
    with ThreadPoolExecutor() as executor:
        executor.submit(delete_webp_files, path)
    print("Mass conversion completed!")

def sticker_pack(sticker_info: dict, chat_id: int) -> None:
    """Handle the "pack" button.
    Create a folder, asynchronous download of stickers, create archive file of folder.
    Send to user archive file and delete archive and folder.

    :param sticker_info: A dictionary with data sticker.
    :param chat_id: A user's id.
    """
    bot.send_message(chat_id, "Please wait a moment😛")
    set_name = sticker_info["set_name"]
    path_to_folder = create_folder(set_name, chat_id)
    sticker_list = bot.get_sticker_set(set_name).stickers
    tasks = []
    for sticker_obj in sticker_list:
        file_path = bot.get_file(sticker_obj.file_id).file_path
        file_name = file_path.split("/")[1]
        tasks.append((file_path, file_name))
    images = download_stickers(tasks)
    for name, image in images:
        save_image(image.content, name, path_to_folder)
    batch_convert(Path(path_to_folder))
        
    # Folder archiving
    shutil.make_archive(base_name=path_to_folder, format="zip", root_dir=path_to_folder)
    with open(path_to_folder + ".zip", "rb") as archive:
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


import uuid

def create_folder(set_name: str, chat_id: int) -> str:
    """Create folder for stickers.

    :param chat_id: A user's id.
    :return: Path to folder.
    """
    unique_id = uuid.uuid4().hex[:6]
    path = os.path.join(STICKERS_DIR, f"{set_name}_{chat_id}_{unique_id}")
    if not os.path.exists(path):
        os.makedirs(path)
    return path


def delete_folder_file(path: str) -> None:
    """Deleting archive file and folder with stickers.

    :param path: Path to folder.
    """
    # Delete archive file
    os.remove(path + ".zip")
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
