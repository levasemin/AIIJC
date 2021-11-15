import pandas as pd
from constants import *
import os
from collections import deque, defaultdict
import tqdm


def restore_columns(df: pd.DataFrame, need: str = 'id_driver') -> pd.DataFrame:
    """
    Calculates count/count_of_speeding/avg_speed in every last 7 days and overall

    :param df: Tracks
    :type df: pd.DataFrame
    :param need: Needed column
    :type need: str

    :return: Restored dataframe
    """
    history = defaultdict(lambda: deque())
    sums = defaultdict(int)
    sums_time = defaultdict(int)
    add_columns = defaultdict(list)

    all_sums = defaultdict(int)
    all_sums_time = defaultdict(int)
    all_cnts = defaultdict(int)
    for i in tqdm.tqdm(df.itertuples(), total=df.shape[0]):
        now_id = eval(f'i.{need}')
        dist = calc_distance(i.from_latitude, i.from_longitude, i.to_latitude, i.to_longitude) + i.arrived_distance
        history[now_id].append([i.dt_15_min, dist, i.duration + i.arrived_duration])
        sums[now_id] += dist
        all_sums[now_id] += dist
        sums_time[now_id] += i.duration + i.arrived_duration
        all_sums_time[now_id] += i.duration + i.arrived_duration
        all_cnts[now_id] += 1
        while (i.dt_15_min - history[now_id][0][0]).total_seconds() > WEEK_SECONDS:
            sums[now_id] -= history[now_id][0][1]
            sums_time[now_id] -= history[now_id][0][2]
            history[now_id].popleft()
        add_columns['order_ids'].append(i.id_order)
        add_columns['last_total_dist'].append(sums[now_id])
        add_columns['last_total_time'].append(sums_time[now_id])
        add_columns['last_total_cnt'].append(len(history[now_id]))
        add_columns['total_dist'].append(all_sums[now_id])
        add_columns['total_time'].append(all_sums_time[now_id])
        add_columns['total_cnt'].append(all_cnts[now_id])
    add_columns = pd.DataFrame(add_columns)
    add_columns = df.merge(add_columns, right_on='order_ids', left_on='id_order')
    add_columns = add_columns.drop('order_ids', axis=1)
    return add_columns


def main():
    df1 = pd.read_csv(os.path.join(COMMON_PATH, 'df_ride_data.csv'))
    df2 = pd.read_csv(os.path.join(COMMON_PATH, 'df_ride_data_part2.csv'))
    df2.index += df1.index.max()
    df2 = pd.concat([df1, df2])
    df2.dt_15_min = pd.to_datetime(df2.dt_15_min)
    df2.sort_values(by='dt_15_min', inplace=True)
    restore_columns(df2, 'id_client').to_csv('merged_data_client.csv')


if __name__ == '__main__':
    main()
