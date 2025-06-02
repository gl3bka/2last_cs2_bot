import asyncio
import os
import uuid
import logging
import json
import traceback
from dotenv import load_dotenv
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from yookassa import Payment, Configuration
from db import init_db, save_payment, mark_paid, get_user_by_payment

load_dotenv()

# === Настройки ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")
CHANNEL_ID = os.getenv("CHANNEL_ID")
JOIN_LINK = os.getenv("JOIN_LINK")

Configuration.account_id = YOOKASSA_SHOP_ID
Configuration.secret_key = YOOKASSA_SECRET_KEY

# === Telegram ===
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# === Telegram: Команда /start
@dp.message(CommandStart())
async def start(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 1 мес = 100₽", callback_data="pay_1m")]
    ])
    await message.answer("Подпишитесь на канал за 100₽ в месяц:", reply_markup=kb)

# === Telegram: Кнопка оплаты
@dp.callback_query(lambda c: c.data == "pay_1m")
async def pay_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    payment_id = str(uuid.uuid4())
    print(f"💳 Сгенерирован и сохранён payment_id: {payment_id}")
    payment = Payment.create({
        "amount": {"value": "100.00", "currency": "RUB"},
        "confirmation": {
            "type": "redirect",
            "return_url": "https://t.me/your_bot"
        },
        "capture": True,
        "description": f"Подписка на канал",
        "metadata": {"payment_id": payment_id}
    }, uuid.uuid4())

    save_payment(payment_id, user_id)
    await bot.send_message(user_id, f"🔗 Оплатите по ссылке:\n{payment.confirmation.confirmation_url}")

# === Telegram: Автоодобрение заявки в канал
@dp.chat_join_request()
async def join_request(event: types.ChatJoinRequest):
    if str(event.chat.id) == CHANNEL_ID:
        await bot.approve_chat_join_request(event.chat.id, event.from_user.id)
        await bot.send_message(event.from_user.id, "✅ Вы были добавлены в канал!")

# === Webhook: Обработка уведомлений от ЮKassa
async def yookassa_webhook(request):
    try:
        data = await request.json()
        try:
            # Логируем всё в файл
            with open("webhook_debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n\n")
        except Exception as e:
            print(f"Ошибка записи в файл webhook_debug.log: {e}")



        print(">>> Webhook получен")
        print(json.dumps(data, indent=2, ensure_ascii=False))

        # Читаем поля
        event_type = data.get("event")
        obj = data.get("object", {})
        status = obj.get("status")
        metadata = obj.get("metadata", {})
        payment_id = metadata.get("payment_id")

        print(f"🔍 Event: {event_type}")
        print(f"🔍 Status: {status}")
        print(f"🔍 Payment ID: {payment_id}")

        if event_type == "payment.succeeded" and status == "succeeded" and payment_id:
            user_id = get_user_by_payment(payment_id)
            print(f"🔍 Найден user_id: {user_id}")

            if user_id:
                mark_paid(payment_id)
                await bot.send_message(user_id, f"✅ Оплата подтверждена!\nВот ссылка на канал: {JOIN_LINK}")
                print(f"📤 Сообщение отправлено пользователю {user_id}")
            else:
                print(f"⚠️ Пользователь с payment_id {payment_id} не найден в базе")

        return web.Response(status=200)

    except Exception as e:
        print("❌ Ошибка в обработке webhook:", e)
        traceback.print_exc()
        return web.Response(status=500)

# === Запуск всего
from aiohttp import web

async def main():
    logging.basicConfig(level=logging.INFO)
    init_db()

    app = web.Application()
    app.router.add_post("/webhook", yookassa_webhook)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 443)  # если с HTTPS, иначе 80
    await site.start()

    bot_task = asyncio.create_task(dp.start_polling(bot))

    while True:
        await asyncio.sleep(3600)




if __name__ == "__main__":
    asyncio.run(main())