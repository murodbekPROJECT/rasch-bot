@router.message(CommandStart())
async def start(message: Message):
    try:
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
    except Exception as e:
        await message.answer(f"❌ Xato: {str(e)}")
        return

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
