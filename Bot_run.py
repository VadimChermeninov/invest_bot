
import logging
from Bot import PortfolioBot

from environs import Env

env = Env()  # Создаем экземпляр класса Env
env.read_env()



BOT_TOKEN = env('BOT_TOKEN')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = PortfolioBot(BOT_TOKEN)

bot.run()