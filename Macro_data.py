import requests
from bs4 import BeautifulSoup as BS
from datetime import datetime
from typing import Dict

def get_current_macro_data() -> Dict:

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

        url = 'https://www.cbr.ru/key-indicators/'
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Проверяем статус ответа

        soup = BS(response.text, 'html.parser')


        target_of_inflation, inflation, key_rate=[float(i.text.split('%')[0].replace(",", ".")) for i in soup.find('div', class_='key-indicators_intro row').find_all('div', class_='value')]


        return {
            'key_rate': key_rate,      # Ключевая ставка ЦБ РФ
            'inflation': inflation,      # Инфляция
            'real_rate': key_rate-inflation,      # Реальная ставка (ключевая - инфляция)
             'update_date': datetime.now().strftime("%Y-%m-%d")
        }
    except Exception as e:
        print(f"Ошибка парсинга ЦБ: {e}")