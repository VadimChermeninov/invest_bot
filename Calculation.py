from Macro_data import get_current_macro_data
import requests
from bs4 import BeautifulSoup as BS
from datetime import datetime
from typing import Dict



first_funds = {
            'stocks': {
                'name': 'ВИМ Индекс Мосбиржи',
                'ticker': 'ВИМ Мосбиржа',
                'risk': 'высокий',
                'display_name': '📈 Акции'
            },
            'gov_bonds': {
                'name': 'УК Первая - Государственные облигации', 
                'ticker': 'ПЕРВАЯ_ОФЗ',
                'risk': 'низкий',
                'display_name': '🏛️ ОФЗ'
            },
            'corp_bonds': {
                'name': 'УК Первая - Корпоративные облигации',
                'ticker': 'ПЕРВАЯ_КОРП',
                'risk': 'средний',
                'display_name': '💼 Корп. облигации'
            },
            'savings': {
                'name': 'УК Первая - Сберегательный фонд',
                'ticker': 'ПЕРВАЯ_СБЕР',
                'risk': 'минимальный',
                'display_name': '🛡️ Сберегательный'
            }
        }
        
indicators = {}


def calculate_fund_scores(macro_data: Dict) -> Dict:
        key_rate = macro_data['key_rate']
        inflation = macro_data['inflation']
        real_rate = key_rate - inflation

        scores = {}

    # БАЗОВЫЕ ОЦЕНКИ ДЛЯ СТАВКИ 8%
    # Настраиваем базовые значения так, чтобы при ставке ~8% получить нужное распределение
        base_scores = {
        'stocks': 100,      # Целевая доля 100%
        'gov_bonds': 0,   # Целевая доля 0%
        'corp_bonds': 0,  # Целевая доля 0%
        'savings':  0      # Целевая доля 0%
    }

        scores = base_scores.copy()

    # АКЦИИ - модификации от базового значения
        if key_rate > 14:
            scores['stocks'] -= 15
        elif key_rate > 11:
            scores['stocks'] -= 10
        elif key_rate > 8:
            scores['stocks'] -= 5
        elif key_rate < 6:
            scores['stocks'] += 15
        elif key_rate < 8:
            scores['stocks'] += 10

    # ГОСУДАРСТВЕННЫЕ ОБЛИГАЦИИ
        if real_rate > 5:
            scores['gov_bonds'] += 15
        elif real_rate > 3:
            scores['gov_bonds'] += 10
        elif real_rate < 1:
            scores['gov_bonds'] -= 10

        if key_rate > 12:
            scores['gov_bonds'] += 10

    # КОРПОРАТИВНЫЕ ОБЛИГАЦИИ
        if real_rate > 4:
            scores['corp_bonds'] += 8
        elif real_rate > 2:
            scores['corp_bonds'] += 5
        elif real_rate < 0:
            scores['corp_bonds'] -= 5

    # СБЕРЕГАТЕЛЬНЫЙ ФОНД
        if real_rate > 6:
            scores['savings'] += 5
        elif real_rate > 4:
            scores['savings'] += 2
        elif real_rate < 2:
            scores['savings'] -= 3

    # Нормализуем scores, чтобы сумма была равна 100%
        total = sum(scores.values())
        for fund in scores:
            scores[fund] = round((scores[fund] / total) * 100)

    # Корректируем возможные ошибки округления
        diff = 100 - sum(scores.values())
        if diff != 0:
        # Добавляем разницу к акциям (основному активу)
            scores['stocks'] += diff

        return scores

def calculate_target_allocation(scores: Dict) -> Dict:
   
    total_score = sum(scores.values())

    allocation = {}
    for fund, score in scores.items():
        allocation[fund] = round((score / total_score) * 100, 1)

    return allocation

def get_weekly_investment_plan(current_portfolio: Dict[str, float],
                                   weekly_amount: float) -> Dict:

    macro_data = get_current_macro_data()
    scores = calculate_fund_scores(macro_data)
    target_allocation = calculate_target_allocation(scores)

    total_current = sum(current_portfolio.values())
    current_allocation = {}
    if total_current > 0:
        for fund in first_funds.keys():
            current_value = current_portfolio.get(fund, 0)
            current_allocation[fund] = (current_value / total_current) * 100
    else:
        current_allocation = {fund: 0 for fund in first_funds.keys()}

        # Рассчитываем целевые суммы после инвестирования
    future_total = total_current + weekly_amount
    target_amounts = {}
    for fund in first_funds.keys():
        target_amounts[fund] = (target_allocation[fund] / 100) * future_total

        # Определяем сколько инвестировать в каждый фонд на этой неделе
    weekly_investment = {}

    for fund in first_funds.keys():
        current_amount = current_portfolio.get(fund, 0)
        target_amount = target_amounts[fund]
        shortage = target_amount - current_amount

        if shortage > 0:
            fund_share = max(0, shortage) / sum(max(0, target_amounts[f] - current_portfolio.get(f, 0))
                                                    for f in first_funds.keys())
            weekly_investment[fund] = min(weekly_amount * fund_share, shortage)
        else:
            weekly_investment[fund] = 0

        # Корректируем распределение
    total_planned = sum(weekly_investment.values())
    if total_planned < weekly_amount:
        remaining = weekly_amount - total_planned
        for fund in first_funds.keys():
            if weekly_investment[fund] > 0:
                additional = remaining * (target_allocation[fund] / 100)
                weekly_investment[fund] += additional

        # Округляем до целых рублей
    for fund in weekly_investment:
        weekly_investment[fund] = round(weekly_investment[fund])

        # Гарантируем, что сумма равна weekly_amount
    final_total = sum(weekly_investment.values())
    if final_total != weekly_amount:
        diff = weekly_amount - final_total
        largest_fund = max(weekly_investment.items(), key=lambda x: x[1])[0]
        weekly_investment[largest_fund] += diff

    return {
            'weekly_investment': weekly_investment,
            'target_allocation': target_allocation,
            'current_allocation': current_allocation,
            'scores': scores,
            'macro_data': macro_data,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M")
        }