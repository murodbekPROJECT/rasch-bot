from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from config import CONTACT_USERNAME

def main_menu(is_subscribed: bool = False) -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="📝 Bugungi test"), KeyboardButton(text="📊 Mening natijalarim")],
        [KeyboardButton(text="🏆 Reyting"), KeyboardButton(text="💳 To'lov")],
        [KeyboardButton(text="📚 Majburiy bo'lim")],
        [KeyboardButton(text="ℹ️ Bot haqida")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def payment_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Bir martalik — 7,000 so'm", callback_data="pay_single")],
        [InlineKeyboardButton(text="👑 Oylik — 20,000 so'm", callback_data="pay_monthly")],
        [InlineKeyboardButton(text=f"📞 Murojaat: {CONTACT_USERNAME}", url=f"https://t.me/{CONTACT_USERNAME.replace('@', '')}")]
    ])

def answer_keyboard(question_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="A", callback_data=f"ans_{question_id}_a"),
            InlineKeyboardButton(text="B", callback_data=f"ans_{question_id}_b"),
        ],
        [
            InlineKeyboardButton(text="C", callback_data=f"ans_{question_id}_c"),
            InlineKeyboardButton(text="D", callback_data=f"ans_{question_id}_d"),
        ]
    ])

def admin_payment_keyboard(payment_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_{payment_id}"),
            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_{payment_id}")
        ]
    ])

def contact_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📞 {CONTACT_USERNAME}", url=f"https://t.me/{CONTACT_USERNAME.replace('@', '')}")]
    ])

def majburiy_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Tarix", callback_data="maj_subject_1")],
        [InlineKeyboardButton(text=f"📞 Murojaat: {CONTACT_USERNAME}", url=f"https://t.me/{CONTACT_USERNAME.replace('@', '')}")]
    ])

def sinf_menu(subject_id: int) -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for sinf in range(6, 12):
        row.append(InlineKeyboardButton(text=f"{sinf}-sinf", callback_data=f"maj_sinf_{subject_id}_{sinf}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="📋 Umumiy (aralash)", callback_data=f"maj_sinf_{subject_id}_0")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def majburiy_answer_keyboard(question_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="A", callback_data=f"mans_{question_id}_a"),
            InlineKeyboardButton(text="B", callback_data=f"mans_{question_id}_b"),
        ],
        [
            InlineKeyboardButton(text="C", callback_data=f"mans_{question_id}_c"),
            InlineKeyboardButton(text="D", callback_data=f"mans_{question_id}_d"),
        ]
    ])

def admin_majburiy_payment_keyboard(payment_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"mapprove_{payment_id}"),
            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"mreject_{payment_id}")
        ]
    ])
