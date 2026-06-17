from typing import Dict
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler

from Calculation import first_funds, get_weekly_investment_plan
from Get_data_portfolio import get_portfolio, get_report_from_email

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class PortfolioBot:
    def __init__(self, token: str):
        self.application = Application.builder().token(token).build()
        self.user_data = {}

        # Регистрируем обработчики
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help))
        self.application.add_handler(CommandHandler("calculate", self.calculate))
        self.application.add_handler(CommandHandler("get_from_email", self.get_from_email))
        self.application.add_handler(CommandHandler("get_report_email", self.get_report_email))

        # Обработчики для кнопок
        self.application.add_handler(MessageHandler(filters.Regex("^(📊 Получить портфолио из email)$"), self.get_from_email))
        self.application.add_handler(MessageHandler(filters.Regex("^(📈 Посмотреть отчет из email)$"), self.get_report_email))

        # Обработчик для текстовых сообщений
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.application.add_handler(CallbackQueryHandler(self.button_handler))

    def get_main_keyboard(self):
        """Создает главную клавиатуру с кнопками"""
        keyboard = [
            [KeyboardButton("📊 Получить портфолио из email")],
            [KeyboardButton("📈 Посмотреть отчет из email")]]

        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    async def start(self, update: Update, context: CallbackContext) -> None:
        """Обработчик команды /start"""
        user = update.effective_user
        welcome_text = f"""
👋 Привет, {user.first_name}!

Я бот-оптимизатор портфеля для фондов УК "Первая" и "ВИМ".

📊 Я помогу:
• Проанализировать текущий портфель
• Рассчитать оптимальное распределение
• Дать рекомендации по еженедельным инвестициям

💡 Нажмите на одну из кнопок ниже, чтобы начать работу!
        """
        await update.message.reply_text(
            welcome_text,
            reply_markup=self.get_main_keyboard()
        )

    async def help(self, update: Update, context: CallbackContext) -> None:
        """Обработчик команды /help"""
        help_text = """
📖 **Доступные команды:**

/start - Начать работу с ботом
/help - Показать эту справку
/calculate - Рассчитать инвестиционный план вручную

💡 **Используйте кнопки ниже для быстрого доступа к функциям!**

📊 **Фонды УК "Первая":**
• 📈 Акции - Фонд топ российских акций
• 🏛️ ОФЗ - Государственные облигации
• 💼 Корпоративные - Корпоративные облигации
• 🛡️ Сберегательный - Сберегательный фонд
        """
        await update.message.reply_text(
            help_text,
            reply_markup=self.get_main_keyboard()
        )

    # Остальные методы (calculate, get_report_email, get_from_email,
    # handle_message, generate_recommendation и т.д.) остаются без изменений

    async def calculate(self, update: Update, context: CallbackContext) -> None:
        """Начать процесс расчета портфеля"""
        user_id = update.effective_user.id
        self.user_data[user_id] = {
            'step': 'waiting_stocks',
            'portfolio': {}
        }

        keyboard = [
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "📊 Давайте рассчитаем ваш инвестиционный план!\n\n"
            "Введите сумму в фонде 📈 **Акции** (руб.):",
            reply_markup=reply_markup
        )


    async def get_report_email(self, update: Update, context: CallbackContext) -> None:

        processing_msg = await update.message.reply_text(
        "📧 Получаю данные из email-отчета...\n"
        "⏳ Это может занять несколько секунд..."
        )

        try:
        # Получаем портфель
            portfolio = get_report_from_email()
            data=portfolio['Дата']
            if portfolio:
            # Удаляем сообщение о обработке
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=processing_msg.message_id
                )

                # Формируем сообщение с портфелем
                str_msg = '\n'.join([f'{k}: {v} руб.' for k, v in portfolio.items() if k!='Дата'])

                str_msg = f"📊 **Текущий портфель:**\n\n{data}\n\n{str_msg}"

                # Отправляем новое сообщение с портфелем
                await update.message.reply_text(str_msg, parse_mode='Markdown')

            else:
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=processing_msg.message_id,
                    text="❌ Не удалось получить данные портфеля из email"
                )

        except NameError as e:
            if "get_portfolio" in str(e):
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=processing_msg.message_id,
                    text="❌ Функция get_portfolio() не определена. Убедитесь, что она импортирована правильно."
                )
            else:
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=processing_msg.message_id,
                    text=f"❌ Ошибка: {str(e)}"
                )
        except Exception as e:
            logger.error(f"Ошибка получения данных из email: {e}", exc_info=True)
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=processing_msg.message_id,
                text=f"❌ Ошибка при получении данных: {str(e)[:200]}"
            )

    async def get_from_email(self, update: Update, context: CallbackContext) -> None:

        processing_msg = await update.message.reply_text(
        "📧 Получаю данные из email-отчета...\n"
        "⏳ Это может занять несколько секунд..."
    )

        try:
            # Пытаемся получить сумму инвестиций из аргументов команды
            weekly_amount = 5000  # Значение по умолчанию
            if context.args and context.args[0].isdigit():
                weekly_amount = float(context.args[0])

            portfolio = get_portfolio()

            # Проверяем, что портфель не пустой и содержит нужные ключи
            required_keys = ['stocks', 'gov_bonds', 'corp_bonds', 'savings']
            if portfolio and all(key in portfolio for key in required_keys):
                # Сохраняем данные пользователя
                user_id = update.effective_user.id
                self.user_data[user_id] = {
                    'portfolio': portfolio,
                    'weekly_investment': weekly_amount
                }

                # Удаляем сообщение о обработке
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=processing_msg.message_id
                )

                await self.generate_recommendation(update, user_id)
            else:
                missing_keys = [key for key in required_keys if key not in portfolio]
                error_msg = f"❌ В портфеле отсутствуют данные по: {', '.join(missing_keys)}" if missing_keys else "❌ Портфель пуст"

                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=processing_msg.message_id,
                    text=f"{error_msg}\n\nПопробуйте ввести данные вручную через /calculate"
                )

        except Exception as e:
            logger.error(f"Ошибка получения данных из email: {e}", exc_info=True)
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=processing_msg.message_id,
                text=f"❌ Ошибка при получении данных: {str(e)[:200]}"
            )

    async def handle_message(self, update: Update, context: CallbackContext) -> None:
        """Обработка текстовых сообщений"""
        user_id = update.effective_user.id
        text = update.message.text

        # Пытаемся разобрать сообщение как полный ввод портфеля
        if await self.try_parse_full_portfolio(update, text):
            return

        # Пошаговый ввод
        if user_id not in self.user_data:
            await update.message.reply_text(
                "Используйте /calculate для начала расчета или /help для справки."
            )
            return

        user_state = self.user_data[user_id]

        try:
            amount = float(text.replace(',', '.').replace(' ', ''))

            steps = {
                'waiting_stocks': ('stocks', '📈 Акции', '🏛️ **ОФЗ**'),
                'waiting_gov_bonds': ('gov_bonds', '🏛️ ОФЗ', '💼 **Корпоративные облигации**'),
                'waiting_corp_bonds': ('corp_bonds', '💼 Корпоративные облигации', '🛡️ **Сберегательный фонд**'),
                'waiting_savings': ('savings', '🛡️ Сберегательный фонд', '💰 **еженедельную сумму инвестиций**')
            }

            if user_state['step'] in steps:
                fund_key, fund_name, next_fund = steps[user_state['step']]
                user_state['portfolio'][fund_key] = amount

                if user_state['step'] == 'waiting_savings':
                    user_state['step'] = 'waiting_investment'
                    await update.message.reply_text(
                        f"Отлично! Теперь введите {next_fund} (руб.):"
                    )
                else:
                    user_state['step'] = list(steps.keys())[list(steps.keys()).index(user_state['step']) + 1]
                    await update.message.reply_text(
                        f"✅ {fund_name}: {amount:,.0f} руб.\n\nВведите сумму в фонде {next_fund} (руб.):"
                    )
            elif user_state['step'] == 'waiting_investment':
                user_state['weekly_investment'] = amount
                await self.generate_recommendation(update, user_id)

        except ValueError:
            await update.message.reply_text("❌ Пожалуйста, введите корректную сумму (только числа):")

    async def try_parse_full_portfolio(self, update: Update, text: str) -> bool:
        """Попытка разобрать полный ввод портфеля одним сообщением"""
        try:
            lines = text.split('\n')
            portfolio = {}
            weekly_investment = None

            for line in lines:
                line = line.strip().lower()
                if 'акци' in line and any(c.isdigit() for c in line):
                    portfolio['stocks'] = float(''.join(c for c in line if c.isdigit() or c == '.'))
                elif 'офз' in line and any(c.isdigit() for c in line):
                    portfolio['gov_bonds'] = float(''.join(c for c in line if c.isdigit() or c == '.'))
                elif 'корп' in line and any(c.isdigit() for c in line):
                    portfolio['corp_bonds'] = float(''.join(c for c in line if c.isdigit() or c == '.'))
                elif 'сбере' in line and any(c.isdigit() for c in line):
                    portfolio['savings'] = float(''.join(c for c in line if c.isdigit() or c == '.'))
                elif 'инвест' in line and any(c.isdigit() for c in line):
                    weekly_investment = float(''.join(c for c in line if c.isdigit() or c == '.'))

            if len(portfolio) >= 4 and weekly_investment is not None:
                user_id = update.effective_user.id
                self.user_data[user_id] = {
                    'portfolio': portfolio,
                    'weekly_investment': weekly_investment
                }
                await self.generate_recommendation(update, user_id)
                return True

        except Exception as e:
            logger.error(f"Ошибка парсинга портфеля: {e}")

        return False

    async def generate_recommendation(self, update: Update, user_id: int) -> None:
        """Генерация и отправка рекомендаций"""
        user_state = self.user_data[user_id]
        portfolio = user_state['portfolio']
        weekly_investment = user_state['weekly_investment']


        try:
            # Показываем сообщение о обработке
            processing_msg = await update.message.reply_text("🔄 Анализирую портфель и макросреду...")

            # Получаем рекомендации
            plan = get_weekly_investment_plan(portfolio, weekly_investment)
            # Формируем ответ
            response = await self.format_recommendation(plan, weekly_investment, portfolio)
            # Удаляем сообщение о обработке и отправляем результат

            await update.message.reply_text(response, parse_mode='Markdown')

            # Очищаем данные пользователя
            del self.user_data[user_id]

        except Exception as e:
            logger.error(f"Ошибка генерации рекомендации: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка при расчете. Пожалуйста, попробуйте еще раз или используйте пошаговый ввод через /calculate"
            )
    async def format_recommendation(self, plan: Dict, weekly_amount: float, portfolio: Dict) -> str:
        """Форматирование рекомендаций в текст"""
        macro = plan['macro_data']
        investment = plan['weekly_investment']

        response = [
            "🎯 **ИНВЕСТИЦИОННЫЙ ПЛАН НА НЕДЕЛЮ**",
            "",
            f"📊 **Макроэкономика:**",
            f"   • Ключевая ставка: {macro['key_rate']}%",
            f"   • Инфляция: {macro['inflation']}%",
            f"   • Реальная ставка: {macro['real_rate']:.1f}%",
            "",
            "💸 **Рекомендуемые инвестиции:**",
        ]

        total_invested = 0
        for fund, amount in investment.items():
            if amount > 0:
                fund_name = first_funds[fund]['display_name']
                response.append(f"   ✅ {fund_name}: {amount:,.0f} руб.")
                total_invested += amount

        if total_invested < weekly_amount:
            response.append(f"   ⚠️ Неиспользовано: {weekly_amount - total_invested:,.0f} руб.")

        response.extend([
            "",
            "📈 **Структура портфеля:**",
        ])

        fund_names = {
            'stocks': '📈 Акции',
            'gov_bonds': '🏛️ ОФЗ',
            'corp_bonds': '💼 Корп. облигации',
            'savings': '🛡️ Сберегательный'
        }

        current = plan['current_allocation']
        target = plan['target_allocation']

        for fund in target.keys():
            current_pct = current.get(fund, 0)
            target_pct = target[fund]
            arrow = "→"
            if current_pct < target_pct:
                arrow = "↗"
            elif current_pct > target_pct:
                arrow = "↘"

            response.append(f"   • {fund_names[fund]}: {current_pct:.1f}% {arrow} {target_pct}%")

        # Стратегическая рекомендация
        response.extend([
            "",
            "💡 **Рекомендация:**",
        ])

        if target['stocks'] > 40:
            response.append("Увеличивайте долю акций - потенциал роста высок 📈")
        elif target['savings'] > 40:
            response.append("Сохраняйте ликвидность - сберегательные инструменты выгодны 🛡️")
        elif target['gov_bonds'] > 50:
            response.append("Фокус на надежность - гос. облигации оптимальны 🏛️")
        else:
            response.append("Сбалансированный подход - продолжайте регулярные инвестиции ⚖️")

        return "\n".join(response)

    async def button_handler(self, update: Update, context: CallbackContext) -> None:
        """Обработчик нажатий на кнопки"""
        query = update.callback_query
        await query.answer()

        if query.data == "cancel":
            user_id = query.from_user.id
            if user_id in self.user_data:
                del self.user_data[user_id]
            await query.edit_message_text("❌ Расчет отменен.")

    def run(self):
        """Запуск бота (версия для Jupyter)"""
        # Создаем новую event loop для Jupyter
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            print("🤖 Бот запущен...")
            self.application.run_polling()
        except KeyboardInterrupt:
            print("\n🛑 Бот остановлен")
        finally:
            loop.close()


