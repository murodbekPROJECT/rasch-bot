from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
import json

from database import get_session, User, Question, DailyTest, Answer, Payment, init_db
from keyboards import main_menu, payment_menu, answer_keyboard, admin_payment_keyboard, contact_keyboard
from rasch import update_theta, theta_to_level, get_wright_map_text
from config import ADMIN_ID, CARD_NUMBER, CARD_OWNER, SINGLE_PRICE, MONTHLY_PRICE, CONTACT_USERNAME

router = Router()
init_db()

class PaymentState(StatesGroup):
    waiting_screenshot = State()
    payment_type = State()

class AdminState(StatesGroup):
    adding_question = State()
    adding_options = State()
    adding_answer = State()
    adding_difficulty = State()

# ============ START ============
@router.message(CommandStart())
async def start(message: Message):
    session = get_session()
    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
    if not user:
        user = User(
            telegram_id=message.from_user.id,
            full_name=message.from_user.full_name,
            username=message.from_user.username
        )
        session.add(user)
        session.commit()
    session.close()

    await message.answer(
        f"🎓 *Rasch Test Botiga xush kelibsiz!*\n\n"
        f"Salom, {message.from_user.first_name}! 👋\n\n"
        f"Bu bot *Rasch modeli* asosida sizning bilim darajangizni aniq o'lchaydi.\n\n"
        f"📝 Har kuni yangi test\n"
        f"📊 Qobiliyat darajangiz (θ) aniqlanadi\n"
        f"🏆 Reyting jadvalida o'z o'rningizni toping\n\n"
        f"Boshlash uchun quyidagi menyudan foydalaning 👇",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )

# ============ BUGUNGI TEST ============
@router.message(F.text == "📝 Bugungi test")
async def daily_test(message: Message):
    session = get_session()
    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()

    # To'lov tekshirish
    now = datetime.now()
    has_access = (
        user.is_subscribed and user.subscription_end and user.subscription_end > now
    ) or user.single_tests_left > 0

    if not has_access:
        await message.answer(
            f"🔒 *Testga kirish uchun to'lov kerak!*\n\n"
            f"💳 Bir martalik: *{SINGLE_PRICE:,} so'm*\n"
            f"👑 Oylik obuna: *{MONTHLY_PRICE:,} so'm*\n\n"
            f"To'lov qilish uchun tugmani bosing 👇",
            parse_mode="Markdown",
            reply_markup=payment_menu()
        )
        session.close()
        return

    # Bugungi testni olish
    today = datetime.now().strftime("%Y-%m-%d")
    daily = session.query(DailyTest).filter_by(date=today, is_active=True).first()

    if not daily:
        await message.answer(
            "📭 Bugun uchun test hali qo'shilmagan.\n"
            "Kechroq tekshiring yoki adminга murojaat qiling.",
            reply_markup=contact_keyboard()
        )
        session.close()
        return

    question_ids = json.loads(daily.question_ids)
    if not question_ids:
        await message.answer("❌ Test savollar topilmadi.")
        session.close()
        return

    # Birinchi savolni yuborish
    question = session.query(Question).filter_by(id=question_ids[0]).first()
    if not question:
        await message.answer("❌ Savol topilmadi.")
        session.close()
        return

    await message.answer(
        f"📝 *1-savol / {len(question_ids)}*\n\n"
        f"*{question.text}*\n\n"
        f"🅰️ {question.option_a}\n"
        f"🅱️ {question.option_b}\n"
        f"🅲 {question.option_c}\n"
        f"🅳 {question.option_d}",
        parse_mode="Markdown",
        reply_markup=answer_keyboard(question.id)
    )
    session.close()

# ============ JAVOB BERISH ============
@router.callback_query(F.data.startswith("ans_"))
async def process_answer(callback: CallbackQuery):
    _, question_id, selected = callback.data.split("_")
    question_id = int(question_id)

    session = get_session()
    user = session.query(User).filter_by(telegram_id=callback.from_user.id).first()
    question = session.query(Question).filter_by(id=question_id).first()

    if not question:
        await callback.answer("Savol topilmadi!")
        session.close()
        return

    # Javobni saqlash
    is_correct = selected == question.correct
    answer = Answer(
        user_id=user.id,
        question_id=question_id,
        selected=selected,
        is_correct=is_correct
    )
    session.add(answer)

    # Theta yangilash
    all_answers = session.query(Answer).filter_by(user_id=user.id).all()
    answer_data = [(a.is_correct, a.question.difficulty) for a in all_answers if a.question]
    user.theta = update_theta(user.theta, answer_data)
    session.commit()

    result_text = "✅ To'g'ri!" if is_correct else f"❌ Noto'g'ri! To'g'ri javob: *{question.correct.upper()}*"

    await callback.message.edit_text(
        f"📝 *{question.text}*\n\n"
        f"Siz tanladingiz: *{selected.upper()}*\n"
        f"{result_text}\n\n"
        f"📊 Sizning θ: *{user.theta}* ({theta_to_level(user.theta)})",
        parse_mode="Markdown"
    )

    # Keyingi savolni tekshirish
    today = datetime.now().strftime("%Y-%m-%d")
    daily = session.query(DailyTest).filter_by(date=today, is_active=True).first()
    if daily:
        question_ids = json.loads(daily.question_ids)
        current_idx = question_ids.index(question_id) if question_id in question_ids else -1
        if current_idx >= 0 and current_idx + 1 < len(question_ids):
            next_q = session.query(Question).filter_by(id=question_ids[current_idx + 1]).first()
            if next_q:
                await callback.message.answer(
                    f"📝 *{current_idx + 2}-savol / {len(question_ids)}*\n\n"
                    f"*{next_q.text}*\n\n"
                    f"🅰️ {next_q.option_a}\n"
                    f"🅱️ {next_q.option_b}\n"
                    f"🅲 {next_q.option_c}\n"
                    f"🅳 {next_q.option_d}",
                    parse_mode="Markdown",
                    reply_markup=answer_keyboard(next_q.id)
                )
        else:
            # Test tugadi
            if user.single_tests_left > 0:
                user.single_tests_left -= 1
                session.commit()
            await callback.message.answer(
                f"🎉 *Test yakunlandi!*\n\n"
                f"📊 Sizning qobiliyat darajangiz (θ): *{user.theta}*\n"
                f"🎖️ Daraja: *{theta_to_level(user.theta)}*\n\n"
                f"Ertaga yangi test sizni kutadi! 💪",
                parse_mode="Markdown",
                reply_markup=main_menu()
            )

    session.close()
    await callback.answer()

# ============ NATIJALAR ============
@router.message(F.text == "📊 Mening natijalarim")
async def my_results(message: Message):
    session = get_session()
    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
    answers = session.query(Answer).filter_by(user_id=user.id).all()

    total = len(answers)
    correct = sum(1 for a in answers if a.is_correct)
    accuracy = round(correct / total * 100, 1) if total > 0 else 0

    sub_status = "✅ Faol" if (user.is_subscribed and user.subscription_end and user.subscription_end > datetime.now()) else "❌ Yo'q"

    await message.answer(
        f"📊 *Sizning statistikangiz*\n\n"
        f"👤 Ism: {user.full_name}\n"
        f"🧠 Qobiliyat (θ): *{user.theta}*\n"
        f"🎖️ Daraja: *{theta_to_level(user.theta)}*\n\n"
        f"📝 Jami savollar: {total}\n"
        f"✅ To'g'ri javoblar: {correct}\n"
        f"🎯 Aniqlik: {accuracy}%\n\n"
        f"💳 Bir martalik testlar: {user.single_tests_left}\n"
        f"👑 Obuna: {sub_status}",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )
    session.close()

# ============ REYTING ============
@router.message(F.text == "🏆 Reyting")
async def leaderboard(message: Message):
    session = get_session()
    top_users = session.query(User).order_by(User.theta.desc()).limit(10).all()

    text = "🏆 *TOP-10 Reyting*\n\n"
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

    for i, u in enumerate(top_users):
        marker = "👉 " if u.telegram_id == message.from_user.id else ""
        text += f"{medals[i]} {marker}{u.full_name}: θ = *{u.theta}* ({theta_to_level(u.theta)})\n"

    session.close()
    await message.answer(text, parse_mode="Markdown", reply_markup=main_menu())

# ============ TO'LOV ============
@router.message(F.text == "💳 To'lov")
async def payment(message: Message):
    await message.answer(
        f"💳 *To'lov tizimi*\n\n"
        f"📌 Bir martalik test: *{SINGLE_PRICE:,} so'm*\n"
        f"👑 Oylik obuna: *{MONTHLY_PRICE:,} so'm*\n\n"
        f"Kerakli rejimni tanlang 👇",
        parse_mode="Markdown",
        reply_markup=payment_menu()
    )

@router.callback_query(F.data.in_(["pay_single", "pay_monthly"]))
async def payment_type(callback: CallbackQuery, state: FSMContext):
    ptype = "single" if callback.data == "pay_single" else "monthly"
    amount = SINGLE_PRICE if ptype == "single" else MONTHLY_PRICE

    await state.update_data(payment_type=ptype, amount=amount)
    await state.set_state(PaymentState.waiting_screenshot)

    await callback.message.answer(
        f"💳 *To'lov ma'lumotlari*\n\n"
        f"💰 Summa: *{amount:,} so'm*\n"
        f"🏦 Karta: `{CARD_NUMBER}`\n"
        f"👤 Karta egasi: *{CARD_OWNER}*\n\n"
        f"✅ Pul o'tkazgandan keyin *chek (screenshot)* rasmini yuboring 👇",
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(PaymentState.waiting_screenshot, F.photo)
async def receive_screenshot(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    ptype = data.get("payment_type", "single")
    amount = data.get("amount", SINGLE_PRICE)

    session = get_session()
    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()

    payment = Payment(
        user_id=user.id,
        amount=amount,
        payment_type=ptype,
        screenshot_file_id=message.photo[-1].file_id
    )
    session.add(payment)
    session.commit()
    payment_id = payment.id
    session.close()

    # Adminga xabar yuborish
    await bot.send_photo(
        ADMIN_ID,
        photo=message.photo[-1].file_id,
        caption=(
            f"💳 *Yangi to'lov so'rovi!*\n\n"
            f"👤 Foydalanuvchi: {message.from_user.full_name}\n"
            f"🆔 ID: `{message.from_user.id}`\n"
            f"💰 Summa: *{amount:,} so'm*\n"
            f"📦 Tur: *{'Bir martalik' if ptype == 'single' else 'Oylik obuna'}*\n"
            f"🔢 To'lov ID: #{payment_id}"
        ),
        parse_mode="Markdown",
        reply_markup=admin_payment_keyboard(payment_id)
    )

    await message.answer(
        "✅ *Chekingiz yuborildi!*\n\n"
        "Admin tekshirib, tez orada tasdiqlaydi.\n"
        "Odatda 5-30 daqiqa ichida 😊",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )
    await state.clear()

# ============ ADMIN: TO'LOV TASDIQLASH ============
@router.callback_query(F.data.startswith("approve_"))
async def approve_payment(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Ruxsat yo'q!")
        return

    payment_id = int(callback.data.split("_")[1])
    session = get_session()
    payment = session.query(Payment).filter_by(id=payment_id).first()

    if not payment:
        await callback.answer("To'lov topilmadi!")
        session.close()
        return

    payment.status = "approved"
    user = payment.user

    if payment.payment_type == "monthly":
        user.is_subscribed = True
        user.subscription_end = datetime.now() + timedelta(days=30)
    else:
        user.single_tests_left += 1

    session.commit()

    # Foydalanuvchiga xabar
    await bot.send_message(
        user.telegram_id,
        f"✅ *To'lovingiz tasdiqlandi!*\n\n"
        f"{'👑 Oylik obuna faollashtirildi (30 kun)' if payment.payment_type == 'monthly' else '📝 1 ta test huquqi qo\'shildi'}\n\n"
        f"Testni boshlashingiz mumkin! 🎉",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )

    await callback.message.edit_caption(
        callback.message.caption + "\n\n✅ *TASDIQLANDI*",
        parse_mode="Markdown"
    )
    await callback.answer("✅ Tasdiqlandi!")
    session.close()

@router.callback_query(F.data.startswith("reject_"))
async def reject_payment(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Ruxsat yo'q!")
        return

    payment_id = int(callback.data.split("_")[1])
    session = get_session()
    payment = session.query(Payment).filter_by(id=payment_id).first()

    if payment:
        payment.status = "rejected"
        session.commit()
        await bot.send_message(
            payment.user.telegram_id,
            f"❌ *To'lovingiz rad etildi.*\n\n"
            f"Murojaat uchun: {CONTACT_USERNAME}",
            parse_mode="Markdown",
            reply_markup=contact_keyboard()
        )

    await callback.message.edit_caption(
        callback.message.caption + "\n\n❌ *RAD ETILDI*",
        parse_mode="Markdown"
    )
    await callback.answer("❌ Rad etildi!")
    session.close()

# ============ ADMIN: SAVOL QO'SHISH ============
@router.message(Command("addquestion"))
async def add_question_start(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("📝 Savol matnini kiriting:")
    await state.set_state(AdminState.adding_question)

@router.message(AdminState.adding_question)
async def add_question_text(message: Message, state: FSMContext):
    await state.update_data(question_text=message.text)
    await message.answer("🅰️ A variantini kiriting:")
    await state.set_state(AdminState.adding_options)

temp_options = {}

@router.message(AdminState.adding_options)
async def add_options(message: Message, state: FSMContext):
    data = await state.get_data()
    uid = message.from_user.id
    if uid not in temp_options:
        temp_options[uid] = []
    temp_options[uid].append(message.text)

    labels = ["B", "C", "D"]
    idx = len(temp_options[uid]) - 1
    if idx < 3:
        await message.answer(f"{'🅱️' if idx==0 else '🅲' if idx==1 else '🅳'} {labels[idx]} variantini kiriting:")
    else:
        await message.answer("✅ To'g'ri javobni kiriting (a/b/c/d):")
        await state.set_state(AdminState.adding_answer)

@router.message(AdminState.adding_answer)
async def add_correct(message: Message, state: FSMContext):
    if message.text.lower() not in ["a", "b", "c", "d"]:
        await message.answer("❌ Faqat a, b, c yoki d kiriting!")
        return
    await state.update_data(correct=message.text.lower())
    await message.answer("📊 Savol qiyinlik darajasini kiriting (-3 dan +3 gacha, masalan: 0.5):")
    await state.set_state(AdminState.adding_difficulty)

@router.message(AdminState.adding_difficulty)
async def add_difficulty(message: Message, state: FSMContext):
    try:
        difficulty = float(message.text)
        difficulty = max(-4.0, min(4.0, difficulty))
    except ValueError:
        await message.answer("❌ Raqam kiriting! Masalan: 0.5")
        return

    data = await state.get_data()
    uid = message.from_user.id
    options = temp_options.get(uid, ["", "", "", ""])

    session = get_session()
    q = Question(
        text=data["question_text"],
        option_a=options[0] if len(options) > 0 else "",
        option_b=options[1] if len(options) > 1 else "",
        option_c=options[2] if len(options) > 2 else "",
        option_d=options[3] if len(options) > 3 else "",
        correct=data["correct"],
        difficulty=difficulty
    )
    session.add(q)
    session.commit()
    q_id = q.id
    session.close()

    if uid in temp_options:
        del temp_options[uid]

    await message.answer(
        f"✅ *Savol qo'shildi!*\n"
        f"🆔 ID: #{q_id}\n"
        f"📊 Qiyinlik: {difficulty}\n\n"
        f"Bugungi testga qo'shish: /setdaily",
        parse_mode="Markdown"
    )
    await state.clear()

# ============ ADMIN: KUNLIK TEST ============
@router.message(Command("setdaily"))
async def set_daily(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    session = get_session()
    questions = session.query(Question).all()
    if not questions:
        await message.answer("❌ Hech qanday savol yo'q. Avval /addquestion bilan savol qo'shing.")
        session.close()
        return

    q_list = "\n".join([f"#{q.id} — {q.text[:40]}... (b={q.difficulty})" for q in questions[-10:]])
    await message.answer(
        f"📋 *So'nggi savollar:*\n\n{q_list}\n\n"
        f"Savol ID larini kiriting (vergul bilan): masalan `1,2,3`",
        parse_mode="Markdown"
    )

@router.message(Command("confirmdaily"))
async def confirm_daily(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    parts = message.text.replace("/confirmdaily", "").strip()
    try:
        ids = [int(x.strip()) for x in parts.split(",") if x.strip()]
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Masalan: /confirmdaily 1,2,3")
        return

    today = datetime.now().strftime("%Y-%m-%d")
    session = get_session()
    existing = session.query(DailyTest).filter_by(date=today).first()
    if existing:
        existing.question_ids = json.dumps(ids)
        existing.is_active = True
    else:
        daily = DailyTest(date=today, question_ids=json.dumps(ids))
        session.add(daily)
    session.commit()
    session.close()

    await message.answer(f"✅ Bugungi test ({today}) — {len(ids)} ta savol bilan faollashtirildi!")

# ============ BOT HAQIDA ============
@router.message(F.text == "ℹ️ Bot haqida")
async def about(message: Message):
    await message.answer(
        f"ℹ️ *Rasch Test Bot haqida*\n\n"
        f"Bu bot *Rasch psixometrik modeli* asosida ishlaydi.\n\n"
        f"📌 Rasch modeli:\n"
        f"• Har bir savolning qiyinlik darajasi (b) mavjud\n"
        f"• Har bir foydalanuvchining qobiliyati (θ) hisoblanadi\n"
        f"• To'g'ri javob ehtimoli: P = e^(θ-b) / (1 + e^(θ-b))\n\n"
        f"📊 Daraja shkalasi:\n"
        f"• θ ≥ 2.0 → 🏆 Ekspert\n"
        f"• θ ≥ 1.0 → ⭐⭐⭐ Yuqori\n"
        f"• θ ≥ 0.0 → ⭐⭐ O'rta-yuqori\n"
        f"• θ ≥ -1.0 → ⭐ O'rta\n"
        f"• θ < -1.0 → 📚 Boshlang'ich\n\n"
        f"📞 Murojaat: {CONTACT_USERNAME}",
        parse_mode="Markdown",
        reply_markup=contact_keyboard()
    )

# ============ ADMIN PANEL ============
@router.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    session = get_session()
    total_users = session.query(User).count()
    total_questions = session.query(Question).count()
    pending_payments = session.query(Payment).filter_by(status="pending").count()
    session.close()

    await message.answer(
        f"👨‍💼 *Admin Panel*\n\n"
        f"👥 Foydalanuvchilar: {total_users}\n"
        f"📝 Savollar: {total_questions}\n"
        f"⏳ Kutilayotgan to'lovlar: {pending_payments}\n\n"
        f"*Buyruqlar:*\n"
        f"/addquestion — Yangi savol qo'shish\n"
        f"/setdaily — Bugungi testni ko'rish\n"
        f"/confirmdaily 1,2,3 — Test belgilash\n"
        f"/stats — To'liq statistika",
        parse_mode="Markdown"
    )

@router.message(Command("stats"))
async def admin_stats(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    session = get_session()
    users = session.query(User).all()
    thetas = [u.theta for u in users]
    questions = session.query(Question).all()
    q_data = [(f"#{q.id}", q.difficulty) for q in questions]

    text = get_wright_map_text(thetas, q_data)
    session.close()

    await message.answer(f"```\n{text}\n```", parse_mode="Markdown")
