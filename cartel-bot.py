import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command
from aiogram.types import ParseMode
from aiogram.utils import executor

import config # Импортируем файл с настройками (токен бота)

logging.basicConfig(level=logging.INFO)

# Инициализация бота и хранилища состояний
bot = Bot(token=config.TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

WEBAPP_HOST = "68.183.214.201"  # IP-адрес для прослушивания входящих запросов
WEBAPP_PORT = 8080  # Порт для прослушивания входящих запросов
WEBHOOK_URL_PATH = "/webhook"  # Путь, на котором будет доступен бот

# Загрузка ответов из текстового файла
with open("responses.txt", "r", encoding="utf-8") as file:
    responses = {}
    for line in file:
        line = line.strip().split(":")
        keyword = line[0].strip().lower()
        response = line[1].strip()
        responses[keyword] = response.replace(". ", "\n").replace("xxx", "━━━━━━━━━━━━━━━━━━━━\n")

# Команда /start
@dp.message_handler(Command("start"))
async def cmd_start(message: types.Message):
    # Отправляет приветственное сообщение и инструкцию по использованию бота.
    await message.reply("Привет\U0001F44B!\nЯ твой личный помощник в мире напитков.\nОтправь название коктейля, и я расскажу всё о рецептуре его приготовления>")

# Обработчик текстовых сообщений
@dp.message_handler()
async def echo(message: types.Message):
    # Отправляет ответ на запрос пользователя из заранее подготовленных ответов.
    user_text = message.text.lower()

    # Проверяем, есть ли пользовательский текст в списке подготовленных ответов
    if user_text in responses:
        # Если есть, отправляем соответствующий ответ
        response = responses[user_text]
        await bot.send_message(chat_id=message.chat.id, text=response, parse_mode=ParseMode.HTML)
    else:
        # Если нет, отправляем сообщение о том, что ответ не найден
        await bot.send_message(chat_id=message.chat.id, text="Извините, я не могу найти ответ на Ваш запрос.\nПопробуйте в нём что-нибудь поменять.")

def check_connection(dp):
    try:
        # Проверка соединения с Telegram API
        bot.get_me()
        logging.info("Соединение с Telegram API успешно установлено")
    except Exception as e:
        logging.exception("Ошибка при проверке соединения с Telegram API: %s", e)

if __name__ == "__main__":
    # Добавляем LoggingMiddleware для вывода отладочных сообщений
    dp.middleware.setup(LoggingMiddleware())

    # Запускаем проверку соединения с Telegram API перед запуском бота
    check_connection(dp)

    # Запускаем бот в режиме long polling
    executor.start_polling(dp)
