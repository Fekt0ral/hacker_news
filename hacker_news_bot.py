import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from aiogram import BaseMiddleware
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
from dotenv import load_dotenv
import asyncio
import logging

#Доделать: 1.Выбор между источниками новостей 2.Добавить жанры: IT, политика, экономика 
# 3.Удалять сообщение, заменяя его, чтобы не спамить 4.Сделать настройку сообщений по таймеру

#Логирование для поиска и обработки ошибок
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

#Токен бота в ТГ
load_dotenv()
TOKEN = os.getenv("TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

#Inline-кнопка вызова новостей
def inline_top_button():
    inline_button = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Топ новости", callback_data="top_news")]
    ])

    return inline_button

#Inline-кнопка стартового меню
def inline_start_button():
    inline_button = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", callback_data="start")]
    ])

    return inline_button

#Стартовое сообщение
async def send_start_message(message: types.Message):
    await message.answer(
        text="Привет! Я бот Hacker News. Нажми кнопку ниже, чтобы получить топ-10 новостей!", 
        reply_markup=inline_top_button()
    )

#Функция сбора топ-10 новостей с сайта Hacker News
async def get_top_news():
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get('https://hacker-news.firebaseio.com/v0/topstories.json', timeout=5) as resp:
                top_news_ids = (await resp.json())[:10]

            articles = []
            for news_id in top_news_ids:
                try:
                    async with session.get(f'https://hacker-news.firebaseio.com/v0/item/{news_id}.json', timeout=5) as resp:
                        item = await resp.json()
                        articles.append((item['title'], item.get('url', f"https://news.ycombinator.com/item?id={item['id']}")))
                except aiohttp.ClientError as e:
                    logger.error(f"Ошибка при получении новости {news_id}: {e}")
                    continue
            return articles
        except aiohttp.ClientError as e:
            logger.error(f"Ошибка при получении списка новостей: {e}")
            return []
        
#Приветственное сообщение
@dp.message(CommandStart())
async def start_handler(message: types.Message):
    await send_start_message(message)

#Обработка остальных сообщений
@dp.message()
async def debug_messages(message: types.Message):
    logger.info(f"Получено сообщение: {message.text}")
    await message.answer("Сообщение получено, но команда не распознана.\nНажми кнопку ниже!", reply_markup=inline_top_button())

#Кнопка 'топ новости'
@dp.callback_query(lambda c: c.data == "top_news")
async def process_callback(callback_query: types.CallbackQuery):
    news = await get_top_news()

    if not news:
        await callback_query.message.answer("Не удалось получить новости. Попробуйте позже.",
                                            reply_markup=inline_start_button()
                                            )
        return
    
    text = "\n\n".join(
        [f"{i+1}. {title} — {url}" for i, (title, url) in enumerate(news)]
    )
    
    await callback_query.message.answer(text, reply_markup=inline_start_button())
    await callback_query.answer()

#Кнопка 'назад'
@dp.callback_query(lambda c: c.data == "start")
async def back_to_start(callback_query: types.CallbackQuery):
    await send_start_message(callback_query.message)
    await callback_query.answer()

#Ловит ошибки и отправляет логи
class ErrorLoggingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        try:
            return await handler(event, data)
        except Exception as e:
            logger.error(f"Ошибка при обработке обновления: {e}", exc_info=True)
            return

#Запуск бота
async def main():
    dp.update.middleware(ErrorLoggingMiddleware())
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())