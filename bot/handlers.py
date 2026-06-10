from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
import json
import re

from database import get_session, User, Question, DailyTest, Answer, Payment, init_db
from keyboards import main_menu, payment_menu, answer_keyboard, admin_payment_keyboard, contact_keyboard
from rasch import update_theta, theta_to_level, get_wright_map_text, calculate_z_score, calculate_t_score, t_score_to_grade
from config import ADMIN_ID, CARD_NUMBER, CARD_OWNER, SINGLE_PRICE, MONTHLY_PRICE, CONTACT_USERNAME

router = Router()
init_db()

# ============ STATES ============
class PaymentState(StatesGroup):
    waiting_screenshot = State()
    payment_type = State()

class AdminState(StatesGroup):
    adding_question = State()
    adding_options = State()
    adding_answer = State()
    adding_difficulty = State()

class PDFState(StatesGroup):
    waiting_answers = State()

temp_options = {}

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
        f"📈 Z-ball va T-ball hisoblanadi\n"
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

    # Obuna muddati avtomatik tekshirish
    now = datetime.now()
    if user.is_subscribed and user.subscription_end and user.subscription_end < now:
        user.is_subscribed = False
        session.commit()

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

    today = datetime.now().strftime("%Y-%m-%d")
    daily = session.query(DailyTest).filter_by(date=today, is_active=True).first()

    if not daily:
        await message.answer(
            "📭 Bugun uchun test hali qo'shilmagan.\n"
            "Kechroq tekshiring yoki murojaat qiling.",
            reply_markup=contact_keyboard()
        )
        session.close()
        return

    question_ids = json.loads(daily.question_ids)
    if not question_ids:
        await message.answer("❌ Test savollar topilmadi.")
        session.close()
        return

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

    is_correct = selected == question.correct
    answer = Answer(
        user_id=user.id,
        question_id=question_id,
        selected=selected,
        is_correct=is_correct
    )
    session.add(answer)

    all_answers = session.query(Answer).filter_by(user_id=user.id).all()
    answer_data = [(a.is_correct, a.question.difficulty) for a in all_answers if a.question]
    user.theta = update_theta(user.theta, answer_data)

    # Z va T ball hisoblash
    all_users = session.query(User).all()
    all_thetas = [u.theta for u in all_users]
    z = calculate_z_score(user.theta, all_thetas)
    t = calculate_t_score(z)
    grade = t_score_to_grade(t)

    session.commit()

    result_text = "✅ To'g'ri!" if is_correct else f"❌ Noto'g'ri! To'g'ri javob: *{question.correct.upper()}*"

    await callback.message.edit_text(
        f"📝 *{question.text}*\n\n"
        f"Siz tanladingiz: *{selected.upper()}*\n"
        f"{result_text}\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📊 θ (Qobiliyat): *{user.theta}*\n"
        f"📈 Z-ball: *{z}*\n"
        f"🎯 T-ball: *{t}*\n"
        f"🎖️ Daraja: *{grade}*",
        parse_mode="Markdown"
    )

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
            if user.single_tests_left > 0:
                user.single_tests_left -= 1
                session.commit()
            await callback.message.answer(
                f"🎉 *Test yakunlandi!*\n\n"
                f"📊 θ (Qobiliyat): *{user.theta}*\n"
                f"📈 Z-ball: *{z}*\n"
                f"🎯 T-ball: *{t}*\n"
                f"🎖️ Yakuniy daraja: *{grade}*\n\n"
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

    all_users = session.query(User).all()
    all_thetas = [u.theta for u in all_users]
    z = calculate_z_score(user.theta, all_thetas)
    t = calculate_t_score(z)
    grade = t_score_to_grade(t)

    now = datetime.now()
    if user.is_subscribed and user.subscription_end and user.subscription_end > now:
        sub_status = f"✅ Faol ({user.subscription_end.strftime('%d.%m.%Y')} gacha)"
    else:
        sub_status = "❌ Yo'q"

    await message.answer(
        f"📊 *Sizning statistikangiz*\n\n"
        f"👤 Ism: {user.full_name}\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🧠 θ (Qobiliyat): *{user.theta}*\n"
        f"📈 Z-ball: *{z}*\n"
        f"🎯 T-ball: *{t}*\n"
        f"🎖️ Daraja: *{grade}*\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📝 Jami savollar: {total}\n"
        f"✅ To'g'ri javoblar: {correct}\n"
        f"🎯 Aniqlik: {accuracy}%\n\n"
        f"━━━━━━━━━━━━━━━\n"
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
    all_thetas = [u.theta for u in session.query(User).all()]

    text = "🏆 *TOP-10 Reyting*\n\n"
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

    for i, u in enumerate(top_users):
        z = calculate_z_score(u.theta, all_thetas)
        t = calculate_t_score(z)
        grade = t_score_to_grade(t)
        marker = "👉 " if u.telegram_id == message.from_user.id else ""
        text += f"{medals[i]} {marker}{u.full_name}\n"
        text += f"   θ={u.theta} | T={t} | {grade}\n\n"

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

    pay = Payment(
        user_id=user.id,
        amount=amount,
        payment_type=ptype,
        screenshot_file_id=message.photo[-1].file_id
    )
    session.add(pay)
    session.commit()
    payment_id = pay.id
    session.close()

    await bot.send_photo(
        ADMIN_ID,
        photo=message.photo[-1].file_id,
        caption=(
            f"💳 *Yangi to'lov so'rovi!*\n\n"
            f"👤 Foydalanuvchi: {message.from_user.full_name}\n"
            f"🆔 ID: `{message.from_user.id}`\n"
            f"💰 Summa: *{amount:,} so'm*\n"
            "📦 Tur: *" + ("Bir martalik" if ptype == "single" else "Oylik obuna") + "*\n"
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
    pay = session.query(Payment).filter_by(id=payment_id).first()

    if not pay:
        await callback.answer("To'lov topilmadi!")
        session.close()
        return

    pay.status = "approved"
    user = pay.user

    if pay.payment_type == "monthly":
        user.is_subscribed = True
        user.subscription_end = datetime.now() + timedelta(days=30)
        access_text = "👑 Oylik obuna faollashtirildi (30 kun)"
    else:
        user.single_tests_left += 1
        access_text = "📝 1 ta test huquqi qo'shildi"

    session.commit()

    await bot.send_message(
        user.telegram_id,
        f"✅ *To'lovingiz tasdiqlandi!*\n\n"
        f"{access_text}\n\n"
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
    pay = session.query(Payment).filter_by(id=payment_id).first()

    if pay:
        pay.status = "rejected"
        session.commit()
        await bot.send_message(
            pay.user.telegram_id,
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

# ============ ADMIN: PDF DAN SAVOLLAR YUKLASH ============
@router.message(F.document)
async def receive_pdf(message: Message, state: FSMContext, bot: Bot):
    if message.from_user.id != ADMIN_ID:
        return
    if not message.document.file_name.endswith('.pdf'):
        return

    await message.answer("⏳ PDF yuklanmoqda, savollar chiqarilmoqda...")

    file = await bot.get_file(message.document.file_id)
    file_path = f"/tmp/{message.document.file_name}"
    await bot.download_file(file.file_path, file_path)

    try:
        import pdfplumber
        questions_data = []
        with pdfplumber.open(file_path) as pdf:
            full_text = ""
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"

        lines = full_text.split('\n')
        current_q = None
        options = []
        q_number = 0

        for line in lines:
            line = line.strip()
            if not line:
                continue

            q_match = re.match(r'^(\d+)[.)]\s+(.+)', line)
            if q_match:
                if current_q and len(options) >= 4:
                    questions_data.append({
                        'number': q_number,
                        'text': current_q,
                        'options': options[:4]
                    })
                q_number = int(q_match.group(1))
                current_q = q_match.group(2)
                options = []
            elif re.match(r'^[AaBbCcDd][.)]\s+', line):
                options.append(re.sub(r'^[AaBbCcDd][.)]\s+', '', line))

        if current_q and len(options) >= 4:
            questions_data.append({
                'number': q_number,
                'text': current_q,
                'options': options[:4]
            })

        if not questions_data:
            await message.answer(
                "❌ PDF dan savollar topilmadi!\n\n"
                "PDF quyidagi formatda bo'lishi kerak:\n"
                "```\n1. Savol matni\nA) Variant\nB) Variant\nC) Variant\nD) Variant\n```",
                parse_mode="Markdown"
            )
            return

        await state.update_data(questions_data=questions_data)
        await state.set_state(PDFState.waiting_answers)

        preview = f"✅ *{len(questions_data)} ta savol topildi!*\n\n"
        for q in questions_data[:3]:
            preview += f"*{q['number']}. {q['text'][:50]}*\n"
            for i, opt in enumerate(q['options']):
                preview += f"  {'ABCD'[i]}) {opt[:30]}\n"
            preview += "\n"

        if len(questions_data) > 3:
            preview += f"... va yana {len(questions_data)-3} ta savol\n\n"

        preview += (
            "📝 *Endi to'g'ri javoblarni yuboring:*\n"
            "Format: `1-A, 2-C, 3-B, 4-D, 5-A`"
        )

        await message.answer(preview, parse_mode="Markdown")

    except ImportError:
        await message.answer(
            "❌ `pdfplumber` o'rnatilmagan!\n\nCMD da:\n`pip install pdfplumber`",
            parse_mode="Markdown"
        )
    except Exception as e:
        await message.answer(f"❌ Xato: {str(e)}")

@router.message(PDFState.waiting_answers)
async def receive_answers(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return

    data = await state.get_data()
    questions_data = data.get('questions_data', [])

    answers_map = {}
    pairs = re.findall(r'(\d+)[-–]\s*([AaBbCcDd])', message.text)
    for num, ans in pairs:
        answers_map[int(num)] = ans.lower()

    if not answers_map:
        await message.answer(
            "❌ Format noto'g'ri!\n\nTo'g'ri format: `1-A, 2-C, 3-B`",
            parse_mode="Markdown"
        )
        return

    session = get_session()
    saved = 0
    missing = []
    saved_ids = []

    for q_data in questions_data:
        num = q_data['number']
        correct = answers_map.get(num)
        if not correct:
            missing.append(num)
            continue

        q = Question(
            text=q_data['text'],
            option_a=q_data['options'][0] if len(q_data['options']) > 0 else "",
            option_b=q_data['options'][1] if len(q_data['options']) > 1 else "",
            option_c=q_data['options'][2] if len(q_data['options']) > 2 else "",
            option_d=q_data['options'][3] if len(q_data['options']) > 3 else "",
            correct=correct,
            difficulty=0.0
        )
        session.add(q)
        session.flush()
        saved_ids.append(q.id)
        saved += 1

    session.commit()
    session.close()

    result = f"✅ *{saved} ta savol bazaga saqlandi!*\n"
    if missing:
        result += f"⚠️ Javobi yo'q savollar: {missing}\n"
    result += f"\nBugungi test uchun:\n`/confirmdaily {','.join(map(str, saved_ids))}`"

    await message.answer(result, parse_mode="Markdown")
    await state.clear()

# ============ ADMIN: SAVOL QO'SHISH (QO'LDA) ============
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

@router.message(AdminState.adding_options)
async def add_options(message: Message, state: FSMContext):
    uid = message.from_user.id
    if uid not in temp_options:
        temp_options[uid] = []
    temp_options[uid].append(message.text)

    idx = len(temp_options[uid]) - 1
    if idx == 0:
        await message.answer("🅱️ B variantini kiriting:")
    elif idx == 1:
        await message.answer("🅲 C variantini kiriting:")
    elif idx == 2:
        await message.answer("🅳 D variantini kiriting:")
    else:
        await message.answer("✅ To'g'ri javobni kiriting (a/b/c/d):")
        await state.set_state(AdminState.adding_answer)

@router.message(AdminState.adding_answer)
async def add_correct(message: Message, state: FSMContext):
    if message.text.lower() not in ["a", "b", "c", "d"]:
        await message.answer("❌ Faqat a, b, c yoki d kiriting!")
        return
    await state.update_data(correct=message.text.lower())
    await message.answer("📊 Qiyinlik darajasi (-3 dan +3): masalan 0.5")
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
        f"Bugungi testga qo'shish: `/confirmdaily {q_id}`",
        parse_mode="Markdown"
    )
    await state.clear()

# ============ ADMIN: JAVOBLARNI KO'RISH ============
@router.message(Command("answers"))
async def show_answers(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    session = get_session()
    questions = session.query(Question).all()
    if not questions:
        await message.answer("❌ Savollar yo'q.")
        session.close()
        return

    text = "📋 *Savollar va to'g'ri javoblar:*\n\n"
    for q in questions[-20:]:
        text += f"#{q.id} {q.text[:40]}...\n✅ {q.correct.upper()} | b={q.difficulty}\n\n"
    session.close()
    await message.answer(text, parse_mode="Markdown")

# ============ ADMIN: SAVOL O'CHIRISH ============
@router.message(Command("delquestion"))
async def del_question(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.replace("/delquestion", "").strip()
    try:
        qid = int(parts)
    except:
        await message.answer("❌ Masalan: /delquestion 5")
        return
    session = get_session()
    q = session.query(Question).filter_by(id=qid).first()
    if q:
        session.delete(q)
        session.commit()
        await message.answer(f"✅ #{qid} savol o'chirildi!")
    else:
        await message.answer(f"❌ #{qid} savol topilmadi!")
    session.close()

# ============ ADMIN: KUNLIK TEST BELGILASH ============
@router.message(Command("setdaily"))
async def set_daily(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    session = get_session()
    questions = session.query(Question).all()
    if not questions:
        await message.answer("❌ Savollar yo'q. /addquestion yoki PDF yuboring.")
        session.close()
        return

    q_list = "\n".join([f"#{q.id} — {q.text[:40]}..." for q in questions[-15:]])
    await message.answer(
        f"📋 *So'nggi savollar:*\n\n{q_list}\n\n"
        f"Savol ID larini kiriting:\n`/confirmdaily 1,2,3`",
        parse_mode="Markdown"
    )
    session.close()

@router.message(Command("confirmdaily"))
async def confirm_daily(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    parts = message.text.replace("/confirmdaily", "").strip()
    try:
        ids = [int(x.strip()) for x in parts.split(",") if x.strip()]
    except ValueError:
        await message.answer("❌ Masalan: /confirmdaily 1,2,3")
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

    await message.answer(f"✅ Bugungi test ({today}) — {len(ids)} ta savol faollashtirildi!")

# ============ BOT HAQIDA ============
@router.message(F.text == "ℹ️ Bot haqida")
async def about(message: Message):
    await message.answer(
        f"ℹ️ *Rasch Test Bot*\n\n"
        f"📐 *Formulalar:*\n"
        f"• Z = (θ - μ) / σ\n"
        f"• T = 50 + 10Z\n\n"
        f"📊 *Darajalar:*\n"
        f"• T ≥ 70 → 🏆 A+\n"
        f"• T ≥ 65 → ⭐⭐⭐ A\n"
        f"• T ≥ 60 → ⭐⭐ B+\n"
        f"• T ≥ 55 → ⭐ B\n"
        f"• T ≥ 50 → 🔵 C+\n"
        f"• T ≥ 46 → 🟡 C\n"
        f"• T < 46 → 🔴 C dan quyi\n\n"
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
    pending = session.query(Payment).filter_by(status="pending").count()
    session.close()

    await message.answer(
        f"👨‍💼 *Admin Panel*\n\n"
        f"👥 Foydalanuvchilar: {total_users}\n"
        f"📝 Savollar: {total_questions}\n"
        f"⏳ Kutilayotgan to'lovlar: {pending}\n\n"
        f"*Buyruqlar:*\n"
        f"/addquestion — Qo'lda savol qo'shish\n"
        f"/answers — Savollar va javoblar\n"
        f"/delquestion 5 — Savol o'chirish\n"
        f"/setdaily — Savollar ro'yxati\n"
        f"/confirmdaily 1,2,3 — Test belgilash\n"
        f"/stats — Wright Map statistika\n\n"
        f"📄 *PDF yuborish* — savollarni avtomatik yuklash",
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
    session.close()

    text = get_wright_map_text(thetas, q_data)
    await message.answer(f"```\n{text}\n```", parse_mode="Markdown")
