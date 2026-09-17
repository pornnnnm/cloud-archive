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
ADMIN_ID = 8931562459

# ==================== КРИПТО-АДРЕСА ====================
CRYPTO_ADDRESSES = {
    "USDT (TON)": "UQBdDAigocyBfvdbAtigQNGHbHK70vYS-1JSInDfPPLMKaCk",
    "USDT (TRC20)": "TAhBvPrJxpN9y52N6hu73pUAvh1eULbxBU",
    "GRAM": "UQBdDAigocyBfvdbAtigQNGHbHK70vYS-1JSInDfPPLMKaCk"
}

# ==================== ТОВАРЫ ====================
PRODUCTS = {
    "5gb": {
        "id": "5gb",
        "name": "Пакет 5 ГБ",
        "price_label": "100 Stars",
        "price_stars": 100,
        "price_crypto": "1.8$ / 1.22 GRAM",
        "price_usdt": "1.8$",
        "price_gram": "1.22 GRAM",
        "size": "5 ГБ",
        "emoji": "🎁",
        "payment_link": "https://t.me/+qvZXX4YWZmM5NDky",
    },
    "10gb": {
        "id": "10gb",
        "name": "Пакет 10 ГБ",
        "price_label": "250 Stars",
        "price_stars": 250,
        "price_crypto": "4.5$ / 3 GRAM",
        "price_usdt": "4.5$",
        "price_gram": "3 GRAM",
        "size": "10 ГБ",
        "emoji": "🎁",
        "payment_link": "https://t.me/+J2sH2y2mQ442YTdi",
    },
    "20gb": {
        "id": "20gb",
        "name": "Пакет 20 ГБ",
        "price_label": "350 Stars",
        "price_stars": 350,
        "price_crypto": "7.2$ / 4.86 GRAM",
        "price_usdt": "7.2$",
        "price_gram": "4.86 GRAM",
        "size": "20 ГБ",
        "emoji": "🎁",
        "payment_link": "https://t.me/+6lCju2zxzIAzMTBi",
    },
}

# ==================== ХРАНИЛИЩЕ ДАННЫХ ====================
user_purchases: Dict[int, List[Dict]] = {}

# ==================== FSM ====================
class SupportStates(StatesGroup):
    waiting_for_ticket = State()
    waiting_for_admin_reply = State()

class PaymentStates(StatesGroup):
    waiting_for_method = State()
    waiting_for_crypto_confirm = State()

# ==================== ИНИЦИАЛИЗАЦИЯ ====================
logging.basicConfig(level=logging.INFO)
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

# ==================== КЛАВИАТУРЫ ====================
def get_main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📦 КАТАЛОГ ПАКЕТОВ", callback_data="catalog"))
    builder.row(InlineKeyboardButton(text="ℹ️ ОПИСАНИЕ И ИНФО", callback_data="info"))
    builder.row(InlineKeyboardButton(text="🆘 ТЕХПОДДЕРЖКА", callback_data="support"))
    builder.row(InlineKeyboardButton(text="🛒 МОИ ПОКУПКИ", callback_data="my_purchases"))
    return builder.as_markup()

def get_catalog_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for product_id, product in PRODUCTS.items():
        builder.row(
            InlineKeyboardButton(
                text=f"{product['emoji']} {product['name']} — {product['price_label']}",
                callback_data=f"buy_{product_id}"
            )
        )
    builder.row(InlineKeyboardButton(text="🔙 НАЗАД", callback_data="back_to_main"))
    return builder.as_markup()

def get_payment_method_keyboard(product_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⭐️ Telegram Stars", callback_data=f"pay_stars_{product_id}")
    )
    builder.row(
        InlineKeyboardButton(text="💎 Криптовалюта", callback_data=f"pay_crypto_{product_id}")
    )
    builder.row(
        InlineKeyboardButton(text="💳 Оплата картой", callback_data=f"pay_card_{product_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 НАЗАД К КАТАЛОГУ", callback_data="back_to_catalog")
    )
    return builder.as_markup()

def get_stars_payment_keyboard(product_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    product = PRODUCTS[product_id]
    builder.row(
        InlineKeyboardButton(text="⭐️ ОПЛАТИТЬ ЗВЁЗДАМИ", url=product["payment_link"])
    )
    builder.row(
        InlineKeyboardButton(text="🔙 НАЗАД К СПОСОБАМ", callback_data=f"back_to_methods_{product_id}")
    )
    return builder.as_markup()

def get_crypto_payment_keyboard(product_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Я ОПЛАТИЛ КРИПТОЙ", callback_data=f"confirm_crypto_{product_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 НАЗАД К СПОСОБАМ", callback_data=f"back_to_methods_{product_id}")
    )
    return builder.as_markup()

def get_card_payment_keyboard(product_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔙 НАЗАД К СПОСОБАМ", callback_data=f"back_to_methods_{product_id}")
    )
    return builder.as_markup()

def get_support_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✍️ НАПИСАТЬ ТИКЕТ", callback_data="write_ticket"))
    builder.row(InlineKeyboardButton(text="🏠 ГЛАВНОЕ МЕНЮ", callback_data="back_to_main"))
    return builder.as_markup()

def get_back_button() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 НАЗАД", callback_data="back_to_main"))
    return builder.as_markup()

def get_admin_reply_keyboard(user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✍️ ОТВЕТИТЬ", callback_data=f"reply_to_{user_id}")
    )
    return builder.as_markup()

# ==================== ОБРАБОТЧИКИ КОМАНД ====================
@dp.message(Command("start"))
async def cmd_start(message: Message):
    welcome_text = (
        "🌟 ДОБРО ПОЖАЛОВАТЬ В CLOUD STORE!\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📁 Премиум Архивы Контента\n\n"
        "🔥 Что мы предлагаем:\n"
        "• Эксклюзивная коллекция — только лучший и проверенный контент.\n"
        "• Разовая оплата — доступ навсегда, без скрытых списаний.\n"
        "• Мгновенная выдача — ссылка приходит сразу после оплаты.\n"
        "• Круглосуточная поддержка — поможем в любой ситуации.\n\n"
        "👇 Выбери нужный раздел:"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📦 ОТКРЫТЬ КАТАЛОГ", callback_data="catalog")
    )
    builder.row(
        InlineKeyboardButton(text="ℹ️ ОПИСАНИЕ И ИНФО", callback_data="info"),
        InlineKeyboardButton(text="🆘 ТЕХПОДДЕРЖКА", callback_data="support")
    )
    builder.row(
        InlineKeyboardButton(text="🛒 МОИ ПОКУПКИ", callback_data="my_purchases")
    )
    
    await message.answer(welcome_text, reply_markup=builder.as_markup())

@dp.message(Command("menu"))
async def cmd_menu(message: Message):
    await message.answer(
        "🏠 ГЛАВНОЕ МЕНЮ CLOUD STORE\n\n"
        "Ты вернулся на главную. Выбери интересующий раздел ниже:",
        reply_markup=get_main_menu()
    )

# ==================== ОБРАБОТЧИКИ КНОПОК ====================
@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    await callback.message.edit_text(
        "🏠 ГЛАВНОЕ МЕНЮ CLOUD STORE\n\n"
        "Ты вернулся на главную. Выбери интересующий раздел ниже:",
        reply_markup=get_main_menu()
    )
    await callback.answer()

@dp.callback_query(F.data == "back_to_catalog")
async def back_to_catalog(callback: CallbackQuery):
    await callback.message.edit_text(
        "📦 КАТАЛОГ ПАКЕТОВ\n\n"
        "Выбери подходящий тариф и нажми на кнопку для покупки:",
        reply_markup=get_catalog_menu()
    )
    await callback.answer()

@dp.callback_query(F.data == "catalog")
async def show_catalog(callback: CallbackQuery):
    await callback.message.edit_text(
        "📦 КАТАЛОГ ПАКЕТОВ\n\n"
        "Выбери подходящий тариф и нажми на кнопку для покупки:",
        reply_markup=get_catalog_menu()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("back_to_methods_"))
async def back_to_payment_methods(callback: CallbackQuery):
    product_id = callback.data.split("_")[3]
    product = PRODUCTS.get(product_id)
    
    if not product:
        await callback.answer("Товар не найден!")
        return
    
    await callback.message.edit_text(
        f"💳 ВЫБЕРИ СПОСОБ ОПЛАТЫ\n\n"
        f"Товар: {product['emoji']} {product['name']}\n"
        f"Цена: {product['price_label']} / {product['price_crypto']}\n\n"
        f"Выбери способ оплаты:",
        reply_markup=get_payment_method_keyboard(product_id)
    )
    await callback.answer()

@dp.callback_query(F.data == "info")
async def show_info(callback: CallbackQuery):
    info_text = (
        "📦 ПОДРОБНАЯ ИНФОРМАЦИЯ\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Мы открываем доступ к защищенным приватным папкам "
        "на быстрых серверах.\n\n"
        "🔥 Плюсы нашего сервиса:\n"
        "• Файлы хранятся вечно и не удаляются.\n"
        "• Регулярное добавление нового материала.\n"
        "• Никаких ежемесячных списаний — покупка разовая.\n"
        "• Полная конфиденциальность.\n\n"
        "💰 Наш прайс-лист:\n"
        "➕ Пакет 5 ГБ — 100 ⭐️ Stars / 1.8$ / 1.22 GRAM\n"
        "➕ Пакет 10 ГБ — 250 ⭐️ Stars / 4.5$ / 3 GRAM\n"
        "➕ Пакет 20 ГБ — 350 ⭐️ Stars / 7.2$ / 4.86 GRAM"
    )
    await callback.message.edit_text(info_text, reply_markup=get_back_button())
    await callback.answer()

# ==================== ПОДДЕРЖКА ====================
@dp.callback_query(F.data == "support")
async def show_support(callback: CallbackQuery):
    support_text = (
        "🆘 ТЕХПОДДЕРЖКА CLOUD STORE\n\n"
        "Возникли трудности со скачиванием, оплатой или есть предложение?\n\n"
        "Опиши свой вопрос подробно, и наш саппорт ответит тебе прямо сюда в течение 15-30 минут."
    )
    await callback.message.edit_text(support_text, reply_markup=get_support_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "write_ticket")
async def write_ticket(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "✍️ НАПИСАТЬ ТИКЕТ\n\n"
        "Опиши свою проблему или вопрос максимально подробно.\n"
        "Наш саппорт ответит тебе в ближайшее время.\n\n"
        "Отправь сообщение с описанием:"
    )
    await state.set_state(SupportStates.waiting_for_ticket)
    await callback.answer()

@dp.message(SupportStates.waiting_for_ticket)
async def process_ticket(message: Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username or "без username"
    full_name = message.from_user.full_name
    
    ticket_text = (
        f"📩 НОВЫЙ ТИКЕТ!\n\n"
        f"👤 От: {full_name} (@{username})\n"
        f"🆔 ID: {user_id}\n"
        f"📝 Сообщение:\n{message.text}"
    )
    
    await bot.send_message(ADMIN_ID, ticket_text, reply_markup=get_admin_reply_keyboard(user_id))
    await state.update_data(user_id=user_id)
    
    await message.answer(
        "✅ Ваш тикет отправлен! Саппорт ответит вам в ближайшее время.",
        reply_markup=get_back_button()
    )
    await state.clear()

@dp.callback_query(F.data.startswith("reply_to_"))
async def admin_reply_to_user(callback: CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split("_")[2])
    
    await state.update_data(reply_user_id=user_id)
    await state.set_state(SupportStates.waiting_for_admin_reply)
    
    await callback.message.edit_text(
        f"✍️ ОТВЕТ ПОЛЬЗОВАТЕЛЮ (ID: {user_id})\n\n"
        "Напиши текст ответа. Он будет отправлен пользователю."
    )
    await callback.answer()

@dp.message(SupportStates.waiting_for_admin_reply)
async def send_admin_reply_to_user(message: Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get("reply_user_id")
    
    if not user_id:
        await message.answer("❌ Ошибка: не найден ID пользователя.")
        await state.clear()
        return
    
    await bot.send_message(
        user_id,
        f"📩 ОТВЕТ ОТ ПОДДЕРЖКИ\n\n{message.text}"
    )
    
    await message.answer(
        f"✅ Ответ отправлен пользователю (ID: {user_id})",
        reply_markup=get_main_menu()
    )
    await state.clear()

@dp.message()
async def user_reply_to_support(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    if user_id == ADMIN_ID:
        return
    
    current_state = await state.get_state()
    if current_state:
        return
    
    admin_text = (
        f"💬 НОВОЕ СООБЩЕНИЕ В ТИКЕТЕ\n\n"
        f"👤 От: {message.from_user.full_name} (@{message.from_user.username})\n"
        f"🆔 ID: {user_id}\n"
        f"📝 Сообщение:\n{message.text}"
    )
    
    await bot.send_message(ADMIN_ID, admin_text, reply_markup=get_admin_reply_keyboard(user_id))
    await message.answer("✅ Сообщение отправлено в поддержку!")

# ==================== МОИ ПОКУПКИ ====================
@dp.callback_query(F.data == "my_purchases")
async def show_my_purchases(callback: CallbackQuery):
    user_id = callback.from_user.id
    purchases = user_purchases.get(user_id, [])
    
    if not purchases:
        await callback.message.edit_text(
            "🛒 МОИ ПОКУПКИ\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "У тебя пока нет покупок.\n"
            "Перейди в каталог и выбери подходящий пакет!",
            reply_markup=get_back_button()
        )
        await callback.answer()
        return
    
    purchases_text = "🛒 МОИ ПОКУПКИ\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    for i, purchase in enumerate(purchases, 1):
        purchases_text += (
            f"{i}. {purchase['emoji']} {purchase['name']}\n"
            f"   📅 {purchase['date']}\n"
            f"   💰 {purchase['price']}\n"
        )
    
    await callback.message.edit_text(purchases_text, reply_markup=get_back_button())
    await callback.answer()

# ==================== ПОКУПКА ТОВАРА ====================
@dp.callback_query(F.data.startswith("buy_"))
async def select_product(callback: CallbackQuery):
    product_id = callback.data.split("_")[1]
    product = PRODUCTS.get(product_id)
    
    if not product:
        await callback.answer("Товар не найден!")
        return
    
    await callback.message.edit_text(
        f"💳 ВЫБЕРИ СПОСОБ ОПЛАТЫ\n\n"
        f"Товар: {product['emoji']} {product['name']}\n"
        f"Цена: {product['price_label']} / {product['price_crypto']}\n\n"
        f"Выбери способ оплаты:",
        reply_markup=get_payment_method_keyboard(product_id)
    )
    await callback.answer()

# ==================== ОПЛАТА ЗВЁЗДАМИ (АВТОМАТИЧЕСКАЯ) ====================
@dp.callback_query(F.data.startswith("pay_stars_"))
async def pay_with_stars(callback: CallbackQuery):
    product_id = callback.data.split("_")[2]
    product = PRODUCTS.get(product_id)
    user_id = callback.from_user.id
    
    if not product:
        await callback.answer("Товар не найден!")
        return
    
    purchase = {
        "product_id": product_id,
        "name": product["name"],
        "price": f"{product['price_label']}",
        "emoji": product["emoji"],
        "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "method": "⭐️ Telegram Stars",
    }
    
    if user_id not in user_purchases:
        user_purchases[user_id] = []
    user_purchases[user_id].append(purchase)
    
    await bot.send_message(
        ADMIN_ID,
        f"🛒 ОПЛАТА ЗВЁЗДАМИ ПРОШЛА УСПЕШНО!\n\n"
        f"👤 Пользователь: {callback.from_user.full_name} (@{callback.from_user.username})\n"
        f"🆔 ID: {user_id}\n"
        f"📦 Товар: {product['name']}\n"
        f"💰 Оплата: {product['price_label']}\n"
        f"📅 Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    )
    
    await callback.message.edit_text(
        f"✅ ОПЛАТА ЗВЁЗДАМИ ПРОШЛА УСПЕШНО!\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎉 Ты приобрёл {product['emoji']} {product['name']}!\n"
        f"💳 Оплачено: {product['price_label']}\n\n"
        f"🔗 Ссылка на архив уже отправлена тебе в чат!\n\n"
        f"📌 Если ссылка не пришла — напиши в поддержку: /support\n\n"
        f"Спасибо за покупку! ❤️",
        reply_markup=get_main_menu()
    )
    
    await callback.answer("✅ Покупка подтверждена!")

# ==================== ОПЛАТА КРИПТОВАЛЮТОЙ ====================
@dp.callback_query(F.data.startswith("pay_crypto_"))
async def pay_with_crypto(callback: CallbackQuery):
    product_id = callback.data.split("_")[2]
    product = PRODUCTS.get(product_id)
    
    if not product:
        await callback.answer("Товар не найден!")
        return
    
    crypto_text = (
        f"💎 ОПЛАТА КРИПТОВАЛЮТОЙ\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Товар: {product['emoji']} {product['name']}\n"
        f"Стоимость: {product['price_crypto']}\n\n"
        f"📌 Отправь оплату на один из адресов:\n\n"
        f"🟣 USDT (TON):\n`{CRYPTO_ADDRESSES['USDT (TON)']}`\n\n"
        f"🔵 USDT (TRC20):\n`{CRYPTO_ADDRESSES['USDT (TRC20)']}`\n\n"
        f"🟢 GRAM:\n`{CRYPTO_ADDRESSES['GRAM']}`\n\n"
        f"⚠️ После оплаты нажми «Я ОПЛАТИЛ КРИПТОЙ» для получения архива!\n\n"
        f"💬 По вопросам крипто-оплаты пиши менеджеру — @oplataoi.\n"
        f"Просьба указать размер и банк."
    )
    
    await callback.message.edit_text(
        crypto_text,
        reply_markup=get_crypto_payment_keyboard(product_id),
        parse_mode="Markdown"
    )
    await callback.answer()

# ==================== ОПЛАТА КАРТОЙ ====================
@dp.callback_query(F.data.startswith("pay_card_"))
async def pay_with_card(callback: CallbackQuery):
    product_id = callback.data.split("_")[2]
    product = PRODUCTS.get(product_id)
    
    if not product:
        await callback.answer("Товар не найден!")
        return
    
    card_text = (
        f"💳 ОПЛАТА КАРТОЙ\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Товар: {product['emoji']} {product['name']}\n"
        f"Стоимость: {product['price_label']} / {product['price_crypto']}\n\n"
        f"📌 Для оплаты картой напишите менеджеру — @oplataoi.\n"
        f"Просьба указать размер и банк."
    )
    
    await callback.message.edit_text(
        card_text,
        reply_markup=get_card_payment_keyboard(product_id)
    )
    await callback.answer()

# ==================== ПОДТВЕРЖДЕНИЕ КРИПТО-ОПЛАТЫ (СКРИНШОТ) ====================
@dp.callback_query(F.data.startswith("confirm_crypto_"))
async def confirm_crypto_payment(callback: CallbackQuery, state: FSMContext):
    product_id = callback.data.split("_")[2]
    product = PRODUCTS.get(product_id)
    user_id = callback.from_user.id
    
    if not product:
        await callback.answer("Товар не найден!")
        return
    
    await state.update_data(
        product_id=product_id,
        product_name=product["name"],
        product_emoji=product["emoji"],
        product_price=product["price_crypto"]
    )
    
    await callback.message.edit_text(
        f"📸 ОТПРАВЬ СКРИНШОТ ОПЛАТЫ\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Товар: {product['emoji']} {product['name']}\n"
        f"Сумма: {product['price_crypto']}\n\n"
        f"✅ Чтобы подтвердить оплату и получить доступ к архиву:\n"
        f"1. Отправь скриншот перевода в этот чат.\n"
        f"2. Наш саппорт проверит оплату в течение 15-30 минут.\n"
        f"3. После проверки ты получишь ссылку на архив!\n\n"
        f"📌 Скриншот должен быть чётким, с видимой суммой и адресом получателя.",
        reply_markup=get_back_button()
    )
    
    await state.set_state(PaymentStates.waiting_for_crypto_confirm)
    await callback.answer()

@dp.message(PaymentStates.waiting_for_crypto_confirm)
async def process_crypto_screenshot(message: Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username or "без username"
    full_name = message.from_user.full_name
    
    data = await state.get_data()
    product_id = data.get("product_id")
    product_name = data.get("product_name", "Товар")
    product_emoji = data.get("product_emoji", "📦")
    product_price = data.get("product_price", "0")
    
    if not message.photo:
        await message.answer(
            "❌ Пожалуйста, отправь скриншот в виде фото (изображение).\n\n"
            "Если у тебя проблемы с отправкой, напиши в поддержку: /support"
        )
        return
    
    photo = message.photo[-1]
    file_id = photo.file_id
    
    purchase = {
        "product_id": product_id,
        "name": product_name,
        "price": product_price,
        "emoji": product_emoji,
        "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "method": "💎 Crypto (скриншот отправлен)",
    }
    
    if user_id not in user_purchases:
        user_purchases[user_id] = []
    user_purchases[user_id].append(purchase)
    
    admin_text = (
        f"📸 НОВЫЙ СКРИНШОТ ОПЛАТЫ!\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 Пользователь: {full_name} (@{username})\n"
        f"🆔 ID: {user_id}\n"
        f"📦 Товар: {product_emoji} {product_name}\n"
        f"💰 Сумма: {product_price}\n"
        f"📅 Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
        f"📌 Проверь оплату и выдай доступ пользователю!"
    )
    
    await bot.send_photo(
        ADMIN_ID,
        photo=file_id,
        caption=admin_text,
        reply_markup=get_admin_reply_keyboard(user_id)
    )
    
    await message.answer(
        f"✅ СКРИНШОТ ПРИНЯТ!\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📸 Ваш скриншот оплаты успешно получен!\n\n"
        f"⏳ Ожидайте! С вами свяжется саппорт в течение 15-30 минут.\n\n"
        f"🔗 После проверки вы получите ссылку на архив в этом чате.\n\n"
        f"💬 Если у вас есть вопросы — напишите в поддержку: /support\n\n"
        f"Спасибо за покупку! ❤️",
        reply_markup=get_main_menu()
    )
    
    await state.clear()

# ==================== ЗАПУСК ====================
async def main():
    logging.info("Бот CLOUD Store запускается...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())