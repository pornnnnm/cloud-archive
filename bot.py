import asyncio
import logging
from datetime import datetime
from typing import Dict, List

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ==================== КОНФИГУРАЦИЯ ====================
BOT_TOKEN = "8628108534:AAEVX1Q-KcZz-F1rY9i22ba5rD4G3VrBONQ"

ADMIN_ID = 8387841712      # куда падают покупки
SUPPORT_ID = 8387841712    # куда падают тикеты

# ==================== ТОВАРЫ ====================
PRODUCTS = {
    "5gb": {
        "id": "5gb",
        "name": "Пакет 5 ГБ",
        "price_label": "100 Stars",
        "price_stars": 100,
        "size": "5 ГБ",
        "emoji": "🎁",
        "payment_link": "https://t.me/+qvZXX4YWZmM5NDky",
        "archive_link": "https://t.me/+archive_5gb_link",   # ← замени на ссылку архива
    },
    "10gb": {
        "id": "10gb",
        "name": "Пакет 10 ГБ",
        "price_label": "250 Stars",
        "price_stars": 250,
        "size": "10 ГБ",
        "emoji": "🎁",
        "payment_link": "https://t.me/+J2sH2y2mQ442YTdi",
        "archive_link": "https://t.me/+archive_10gb_link",  # ← замени
    },
    "20gb": {
        "id": "20gb",
        "name": "Пакет 20 ГБ",
        "price_label": "350 Stars",
        "price_stars": 350,
        "size": "20 ГБ",
        "emoji": "🎁",
        "payment_link": "https://t.me/+6lCju2zxzIAzMTBi",
        "archive_link": "https://t.me/+archive_20gb_link",  # ← замени
    },
}

# ==================== ХРАНИЛИЩЕ ====================
user_purchases: Dict[int, List[Dict]] = {}
pending_purchases: Dict[int, str] = {}   # user_id -> product_id (ожидание подтверждения)

# ==================== FSM ====================
class SupportStates(StatesGroup):
    waiting_for_ticket = State()
    waiting_for_admin_reply = State()

# ==================== ИНИЦИАЛИЗАЦИЯ ====================
logging.basicConfig(level=logging.INFO)
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

# ==================== КЛАВИАТУРЫ ====================
def get_main_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="📦 КАТАЛОГ ПАКЕТОВ", callback_data="catalog"))
    kb.row(InlineKeyboardButton(text="ℹ️ ОПИСАНИЕ И ИНФО", callback_data="info"))
    kb.row(InlineKeyboardButton(text="🆘 ТЕХПОДДЕРЖКА", callback_data="support"))
    kb.row(InlineKeyboardButton(text="🛒 МОИ ПОКУПКИ", callback_data="my_purchases"))
    return kb.as_markup()

def get_catalog_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for pid, p in PRODUCTS.items():
        kb.row(InlineKeyboardButton(
            text=f"{p['emoji']} {p['name']} — {p['price_label']}",
            callback_data=f"buy_{pid}"
        ))
    kb.row(InlineKeyboardButton(text="🔙 НАЗАД", callback_data="back_to_main"))
    return kb.as_markup()

def get_payment_method_keyboard(pid: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="⭐️ Telegram Stars", callback_data=f"pay_stars_{pid}"))
    kb.row(InlineKeyboardButton(text="💎 Криптовалюта", callback_data=f"pay_crypto_{pid}"))
    kb.row(InlineKeyboardButton(text="💳 Оплата картой", callback_data=f"pay_card_{pid}"))
    kb.row(InlineKeyboardButton(text="🔙 НАЗАД К КАТАЛОГУ", callback_data="back_to_catalog"))
    return kb.as_markup()

def get_stars_payment_keyboard(pid: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    p = PRODUCTS[pid]
    kb.row(InlineKeyboardButton(text=f"⭐️ ОПЛАТИТЬ {p['price_label']}", url=p["payment_link"]))
    kb.row(InlineKeyboardButton(text="✅ Я ОПЛАТИЛ", callback_data=f"confirm_stars_{pid}"))
    kb.row(InlineKeyboardButton(text="🔙 НАЗАД", callback_data=f"back_to_methods_{pid}"))
    return kb.as_markup()

def get_manager_payment_keyboard(pid: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🔙 НАЗАД К СПОСОБАМ", callback_data=f"back_to_methods_{pid}"))
    return kb.as_markup()

def get_support_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="✍️ НАПИСАТЬ ТИКЕТ", callback_data="write_ticket"))
    kb.row(InlineKeyboardButton(text="🏠 ГЛАВНОЕ МЕНЮ", callback_data="back_to_main"))
    return kb.as_markup()

def get_back_button() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🔙 НАЗАД", callback_data="back_to_main"))
    return kb.as_markup()

def get_admin_reply_keyboard(user_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="✍️ ОТВЕТИТЬ", callback_data=f"reply_to_{user_id}"))
    return kb.as_markup()

# ==================== /start и /menu ====================
@dp.message(Command("start"))
async def cmd_start(message: Message):
    text = (
        "🌟 ДОБРО ПОЖАЛОВАТЬ В CLOUD STORE!\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📁 Премиум Архивы Контента\n\n"
        "🔥 Что мы предлагаем:\n"
        "• Эксклюзивная коллекция — только лучший и проверенный контент.\n"
        "• Разовая оплата — доступ навсегда.\n"
        "• Мгновенная выдача — ссылка приходит сразу после оплаты.\n"
        "• Круглосуточная поддержка.\n\n"
        "👇 Выбери нужный раздел:"
    )
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="📦 ОТКРЫТЬ КАТАЛОГ", callback_data="catalog"))
    kb.row(
        InlineKeyboardButton(text="ℹ️ ОПИСАНИЕ И ИНФО", callback_data="info"),
        InlineKeyboardButton(text="🆘 ТЕХПОДДЕРЖКА", callback_data="support"),
    )
    kb.row(InlineKeyboardButton(text="🛒 МОИ ПОКУПКИ", callback_data="my_purchases"))
    await message.answer(text, reply_markup=kb.as_markup())

@dp.message(Command("menu"))
async def cmd_menu(message: Message):
    await message.answer("🏠 ГЛАВНОЕ МЕНЮ:", reply_markup=get_main_menu())

# ==================== ОБЩИЕ ХЕНДЛЕРЫ ====================
@dp.callback_query(F.data == "back_to_main")
async def back_to_main(cb: CallbackQuery):
    await cb.message.edit_text("🏠 ГЛАВНОЕ МЕНЮ:", reply_markup=get_main_menu())
    await cb.answer()

@dp.callback_query(F.data == "back_to_catalog")
async def back_to_catalog(cb: CallbackQuery):
    await cb.message.edit_text(
        "📦 КАТАЛОГ ПАКЕТОВ\n\nВыбери тариф:",
        reply_markup=get_catalog_menu(),
    )
    await cb.answer()

@dp.callback_query(F.data == "catalog")
async def show_catalog(cb: CallbackQuery):
    await cb.message.edit_text(
        "📦 КАТАЛОГ ПАКЕТОВ\n\nВыбери тариф:",
        reply_markup=get_catalog_menu(),
    )
    await cb.answer()

@dp.callback_query(F.data.startswith("back_to_methods_"))
async def back_to_methods(cb: CallbackQuery):
    pid = cb.data.split("_")[3]
    p = PRODUCTS.get(pid)
    if not p:
        await cb.answer("Товар не найден")
        return
    await cb.message.edit_text(
        f"💳 ВЫБЕРИ СПОСОБ ОПЛАТЫ\n\n"
        f"Товар: {p['emoji']} {p['name']}\n"
        f"Цена: {p['price_label']}\n\n"
        f"Выбери способ оплаты:",
        reply_markup=get_payment_method_keyboard(pid),
    )
    await cb.answer()

# ==================== ИНФО ====================
@dp.callback_query(F.data == "info")
async def show_info(cb: CallbackQuery):
    text = (
        "📦 ПОДРОБНАЯ ИНФОРМАЦИЯ\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Мы открываем доступ к защищенным приватным папкам на быстрых серверах.\n\n"
        "🔥 Плюсы нашего сервиса:\n"
        "• Файлы хранятся вечно и не удаляются.\n"
        "• Регулярное добавление нового материала.\n"
        "• Никаких ежемесячных списаний — покупка разовая.\n"
        "• Полная конфиденциальность.\n\n"
        "💰 Наш прайс-лист:\n"
        "➕ Пакет 5 ГБ — 100 ⭐️ Stars\n"
        "➕ Пакет 10 ГБ — 250 ⭐️ Stars\n"
        "➕ Пакет 20 ГБ — 350 ⭐️ Stars"
    )
    await cb.message.edit_text(text, reply_markup=get_back_button())
    await cb.answer()

# ==================== ПОДДЕРЖКА ====================
@dp.callback_query(F.data == "support")
async def show_support(cb: CallbackQuery):
    text = (
        "🆘 ТЕХПОДДЕРЖКА CLOUD STORE\n\n"
        "Возникли трудности со скачиванием, оплатой или есть предложение?\n\n"
        "Опиши свой вопрос — саппорт ответит в течение 15–30 минут."
    )
    await cb.message.edit_text(text, reply_markup=get_support_keyboard())
    await cb.answer()

@dp.callback_query(F.data == "write_ticket")
async def write_ticket(cb: CallbackQuery, state: FSMContext):
    await cb.message.edit_text("✍️ Опиши свой вопрос одним сообщением:")
    await state.set_state(SupportStates.waiting_for_ticket)
    await cb.answer()

@dp.message(SupportStates.waiting_for_ticket)
async def process_ticket(msg: Message, state: FSMContext):
    user_id = msg.from_user.id
    text = (
        f"📩 НОВЫЙ ТИКЕТ!\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 {msg.from_user.full_name}\n"
        f"🔗 @{msg.from_user.username or 'без username'}\n"
        f"🆔 {user_id}\n\n"
        f"📝 {msg.text}"
    )
    await bot.send_message(SUPPORT_ID, text, reply_markup=get_admin_reply_keyboard(user_id))
    await msg.answer("✅ Тикет отправлен! Саппорт ответит скоро.", reply_markup=get_back_button())
    await state.clear()

@dp.callback_query(F.data.startswith("reply_to_"))
async def admin_reply(cb: CallbackQuery, state: FSMContext):
    uid = int(cb.data.split("_")[2])
    await state.update_data(reply_user_id=uid)
    await state.set_state(SupportStates.waiting_for_admin_reply)
    await cb.message.edit_text(f"✍️ Напиши ответ пользователю (ID: {uid}):")
    await cb.answer()

@dp.message(SupportStates.waiting_for_admin_reply)
async def send_reply(msg: Message, state: FSMContext):
    data = await state.get_data()
    uid = data.get("reply_user_id")
    if not uid:
        await msg.answer("❌ Ошибка: нет ID.")
        await state.clear()
        return
    try:
        await bot.send_message(uid, f"📩 ОТВЕТ ОТ ПОДДЕРЖКИ\n\n{msg.text}")
        await msg.answer(f"✅ Отправлено пользователю ({uid})", reply_markup=get_main_menu())
    except Exception as e:
        await msg.answer(f"❌ Не удалось: {e}", reply_markup=get_main_menu())
    await state.clear()

@dp.message()
async def user_reply(msg: Message, state: FSMContext):
    if msg.from_user.id in (ADMIN_ID, SUPPORT_ID):
        return
    if await state.get_state():
        return
    text = (
        f"💬 СООБЩЕНИЕ В ПОДДЕРЖКУ\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 {msg.from_user.full_name}\n"
        f"🔗 @{msg.from_user.username or 'без username'}\n"
        f"🆔 {msg.from_user.id}\n\n"
        f"📝 {msg.text}"
    )
    await bot.send_message(SUPPORT_ID, text, reply_markup=get_admin_reply_keyboard(msg.from_user.id))
    await msg.answer("✅ Сообщение отправлено в поддержку!")

# ==================== МОИ ПОКУПКИ ====================
@dp.callback_query(F.data == "my_purchases")
async def my_purchases(cb: CallbackQuery):
    purchases = user_purchases.get(cb.from_user.id, [])
    if not purchases:
        await cb.message.edit_text(
            "🛒 МОИ ПОКУПКИ\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "У тебя пока нет покупок.",
            reply_markup=get_back_button(),
        )
        await cb.answer()
        return
    text = "🛒 МОИ ПОКУПКИ\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    for i, p in enumerate(purchases, 1):
        text += (
            f"{i}. {p['emoji']} {p['name']}\n"
            f"   📅 {p['date']}\n"
            f"   💰 {p['price']}\n\n"
        )
    await cb.message.edit_text(text, reply_markup=get_back_button())
    await cb.answer()

# ==================== ПОКУПКА ====================
@dp.callback_query(F.data.startswith("buy_"))
async def select_product(cb: CallbackQuery):
    pid = cb.data.split("_")[1]
    p = PRODUCTS.get(pid)
    if not p:
        await cb.answer("Товар не найден")
        return
    await cb.message.edit_text(
        f"💳 ВЫБЕРИ СПОСОБ ОПЛАТЫ\n\n"
        f"Товар: {p['emoji']} {p['name']}\n"
        f"Цена: {p['price_label']}\n\n"
        f"Выбери способ оплаты:",
        reply_markup=get_payment_method_keyboard(pid),
    )
    await cb.answer()

# ==================== ⭐️ ОПЛАТА ЗВЁЗДАМИ ====================
@dp.callback_query(F.data.startswith("pay_stars_"))
async def pay_stars(cb: CallbackQuery):
    pid = cb.data.split("_")[2]
    p = PRODUCTS.get(pid)
    if not p:
        await cb.answer("Товар не найден")
        return

    pending_purchases[cb.from_user.id] = pid

    text = (
        f"⭐️ ОПЛАТА ЗВЁЗДАМИ\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Товар: {p['emoji']} {p['name']}\n"
        f"Стоимость: {p['price_label']}\n\n"
        f"📌 Как оплатить:\n"
        f"1. Нажми «⭐️ ОПЛАТИТЬ {p['price_label']}».\n"
        f"2. Оплати звёзды Telegram.\n"
        f"3. Вернись сюда и нажми «✅ Я ОПЛАТИЛ».\n"
        f"4. Получи ссылку на архив в этом чате."
    )
    await cb.message.edit_text(text, reply_markup=get_stars_payment_keyboard(pid))
    await cb.answer()

@dp.callback_query(F.data.startswith("confirm_stars_"))
async def confirm_stars(cb: CallbackQuery):
    pid = cb.data.split("_")[2]
    p = PRODUCTS.get(pid)
    if not p:
        await cb.answer("Товар не найден")
        return

    uid = cb.from_user.id
    pending_purchases.pop(uid, None)

    purchase = {
        "product_id": pid,
        "name": p["name"],
        "price": p["price_label"],
        "emoji": p["emoji"],
        "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
    }
    user_purchases.setdefault(uid, []).append(purchase)

    # Уведомление админу
    await bot.send_message(
        ADMIN_ID,
        f"🛒 НОВАЯ ПОКУПКА (STARS)!\n\n"
        f"👤 {cb.from_user.full_name}\n"
        f"🔗 @{cb.from_user.username or '—'}\n"
        f"🆔 {uid}\n"
        f"📦 {p['name']}\n"
        f"💰 {p['price_label']}\n"
        f"📅 {purchase['date']}",
    )

    # Пользователю — ссылка на архив
    await cb.message.edit_text(
        f"✅ ОПЛАТА ПОДТВЕРЖДЕНА!\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎉 Ты приобрёл {p['emoji']} {p['name']}!\n"
        f"💳 Оплачено: {p['price_label']}\n\n"
        f"🔗 Ссылка на архив:\n{p['archive_link']}\n\n"
        f"📌 Она также сохранена в «МОИ ПОКУПКИ».\n\n"
        f"Спасибо за покупку! ❤️",
        reply_markup=get_main_menu(),
    )
    await cb.answer("✅ Покупка подтверждена!")

# ==================== 💎 КРИПТА (менеджер) ====================
@dp.callback_query(F.data.startswith("pay_crypto_"))
async def pay_crypto(cb: CallbackQuery):
    pid = cb.data.split("_")[2]
    p = PRODUCTS.get(pid)
    if not p:
        await cb.answer("Товар не найден")
        return
    text = (
        f"💎 ОПЛАТА КРИПТОВАЛЮТОЙ\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Товар: {p['emoji']} {p['name']}\n\n"
        f"📌 Для оплаты криптовалютой напишите менеджеру — @oplataoi.\n"
        f"Просьба указать размер и банк."
    )
    await cb.message.edit_text(text, reply_markup=get_manager_payment_keyboard(pid))
    await cb.answer()

# ==================== 💳 КАРТА (менеджер) ====================
@dp.callback_query(F.data.startswith("pay_card_"))
async def pay_card(cb: CallbackQuery):
    pid = cb.data.split("_")[2]
    p = PRODUCTS.get(pid)
    if not p:
        await cb.answer("Товар не найден")
        return
    text = (
        f"💳 ОПЛАТА КАРТОЙ\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Товар: {p['emoji']} {p['name']}\n\n"
        f"📌 Для оплаты картой напишите менеджеру — @oplataoi.\n"
        f"Просьба указать размер и банк."
    )
    await cb.message.edit_text(text, reply_markup=get_manager_payment_keyboard(pid))
    await cb.answer()

# ==================== ЗАПУСК ====================
async def main():
    logging.info("Бот CLOUD Store запускается...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
