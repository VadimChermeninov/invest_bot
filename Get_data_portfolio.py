import imaplib
import email
import logging
from environs import Env

logger = logging.getLogger(__name__)

env = Env()  # Создаем экземпляр класса Env
env.read_env()

App_password=env('App_password')
def get_html_with_app_password(your_email='trkvoshka@gmail.com', app_password=App_password,
                               sender_email='broker_rep@sberbank.ru'):
    """
    Функция с явной передачей пароля приложения
    """
    imap = None
    try:
        # Убираем пробелы из пароля
        app_password = app_password.replace(' ', '')

        imap = imaplib.IMAP4_SSL("imap.gmail.com")
        imap.login(your_email, app_password)
        imap.select("INBOX")

        # Ищем последнее письмо с HTML вложением
        result, data = imap.search(None, f'(FROM "{sender_email}")')

        if not data[0]:
            logger.warning("Писем от отправителя не найдено")
            return None

        # Проверяем последнее письмо
        email_id = data[0].split()[-1]
        result, data = imap.fetch(email_id, '(RFC822)')
        msg = email.message_from_bytes(data[0][1])

        for part in msg.walk():
            filename = part.get_filename()
            if filename and filename.lower().endswith('.html'):
                html_content = part.get_payload(decode=True)
                if html_content:
                    return html_content.decode('utf-8', errors='ignore')

        logger.warning("HTML вложение не найдено")
        return None

    except Exception as e:
        logger.error(f"Ошибка в get_html_with_app_password: {e}")
        return None
    finally:
        if imap:
            try:
                imap.close()
                imap.logout()
            except:
                pass


from bs4 import BeautifulSoup as BS


def get_data_html(html):
    """Парсит HTML и возвращает словарь с данными"""
    try:
        if html is None:
            logger.error("html is None")
            return {}

        soup = BS(html, 'html.parser')

        # Проверяем наличие h3
        h3 = soup.find('h3')
        if h3 is None:
            logger.error("h3 tag not found")
            return {}


        tables = soup.find_all('table')
        if len(tables) < 3:
            logger.error(f"Недостаточно таблиц: {len(tables)}")
            return {}

        table = tables[2]
        rows = table.find_all('tr')

        dct = {}
        for row in rows:
            cols = row.find_all('td')
            if len(cols) == 18:
                dct[cols[0].text.strip()] = cols[6].text.strip().replace(' ', '')

        # Удаляем первые два элемента
        for key in list(dct)[:2]:
            dct.pop(key)

        titles = {
            'БПИФ Индекс МосБиржи УК ВИМ': 'stocks',
            'Фонд Государственные облигации': 'gov_bonds',
            'Фонд Корпоративные облигации': 'corp_bonds',
            'Фонд Сберегательный': 'savings'
        }

        result = {}
        for key, value in titles.items():
            if key in dct and dct[key]:
                try:
                    result[value] = round(float(dct[key]))
                except ValueError:
                    logger.warning(f"Не удалось преобразовать {key}: {dct[key]}")
                    result[value] = 0
            else:
                logger.warning(f"Ключ {key} не найден в данных")
                result[value] = 0

        return result

    except Exception as e:
        logger.error(f"Ошибка в get_data_html: {e}")
        return {}


def get_portfolio():
    """Возвращает данные портфеля. Всегда возвращает словарь, даже при ошибке"""
    try:
        html = get_html_with_app_password()
        if html is None:
            logger.error("Не удалось получить HTML письмо")
            return {}

        portfolio = get_data_html(html)
        if not portfolio:
            logger.warning("Парсинг HTML вернул пустой словарь")
            return {}

        return portfolio

    except Exception as e:
        logger.error(f"Ошибка в get_portfolio: {e}")
        return {}


def get_report_from_email():

    html=get_html_with_app_password()

    """Возвращает отчет с датой"""
    try:
        if html is None:
            logger.error("html is None in get_report_email")
            return {}

        soup = BS(html, 'html.parser')
        h3 = soup.find('h3')
        if h3 is None:
            return {}

        data = h3.text.split(',')[-1].strip()
        portfolio = get_data_html(html)
        portfolio['Дата'] = data.capitalize()
        return portfolio

    except Exception as e:
        logger.error(f"Ошибка в get_report_email: {e}")
        return {}