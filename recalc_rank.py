import pandas as pd
from constants import *
from collections import defaultdict
from math import *

def get_rank1(score1):
    """
    Возвращает K-ранг

    :param score1: K-rate водителя
    :return: K-ранг (индекс в массиве)
    """
    for i in range(len(K_RANKS) - 1, -1, -1):
        if K_RANKS[i] < score1:
            return i
    assert False


def get_rank2(score2):
    """
    Возвращает V-ранг

    :param score2: V-rate водителя
    :return: V-ранг (индекс в массиве)
    """
    for i in range(len(V_RANKS) - 1, -1, -1):
        if V_RANKS[i] < score2:
            return i
    assert False


def recalc(_new_df: pd.DataFrame):
    """
    Добавляет ранги водителям

    :param _new_df: Данные, в которые надо посчитать ранги
    :return: _new_df с добавленными столбцами K_rank, V_rank
    """
    new_df = _new_df.copy()

    last_info = defaultdict(lambda: [0, 0, 0, 0])  # last K/V rate, last K/V rank
    cnts = defaultdict(int)

    res = []
    for order in new_df.itertuples():
        res.append([])
        driver = order.driver_id

        now_k_rank = get_rank1(order.K_rate)
        now_v_rank = get_rank2(order.V_rate)
        last_k_rank = int(last_info[driver][2])
        last_v_rank = int(last_info[driver][3])
        if now_k_rank < last_k_rank:
            res[-1].append(now_k_rank)
        elif now_k_rank == last_k_rank:
            res[-1].append(now_k_rank)
        else:
            need = (K_RANKS[now_k_rank] - K_RANKS[now_k_rank - 1]) // 2
            if order.K_rate >= need:
                res[-1].append(now_k_rank)
            else:
                res[-1].append(last_k_rank)

        cnts[driver] += 1

        if now_v_rank < last_v_rank:
            res[-1].append(now_v_rank)
        elif now_v_rank == last_v_rank:
            res[-1].append(now_v_rank)
        else:
            need = (V_RANKS[now_v_rank] - V_RANKS[now_v_rank - 1]) // 2
            if order.V_rate >= need:
                res[-1].append(now_v_rank)
            else:
                res[-1].append(last_v_rank)

        last_info[driver] = [order.K_rate, order.V_rate, res[-1][0], res[-1][1]]

    return new_df.join(pd.DataFrame(res, columns=['K_rank', 'V_rank']))


df2 = pd.read_csv('final/new_tab.csv')
df2 = df2.drop('K_rate', axis=1).rename(columns={'new_K_rate': 'K_rate'})
df2['K_rate'] = df2['K_rate'].fillna(0)
df2['V_rate'] = df2['V_rate'].fillna(0)
recalc(df2).to_csv('drivers_with_ranks.csv')
