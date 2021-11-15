import pandas as pd
import os
from collections import defaultdict
import tqdm

import requests
import staticmaps
import folium
import json

import typing
from constants import *


def return_seconds(x):
    dt = pd.to_datetime(x)
    return (dt - dt.normalize()).total_seconds()


def save_map(resp, file):
    if resp.status_code != 200:
        return
    with open(file, "wb") as file1:
        file1.write(resp.content)


def add_point(params, lon, lat, marker):
    if 'pt' in params:
        params['pt'] += '~'
    if 'pt' not in params:
        params['pt'] = ''
    params['pt'] += f"{lon},{lat},{marker}"


def make_map_yandex(deltas, speeds, out):
    req = 'https://static-maps.yandex.ru/1.x/'
    params = {}
    params['l'] = 'map'

    for i in deltas:
        add_point(params, i['lon'], i['lat'], 'pm2wtm')

    for i in speeds:
        add_point(params, i['lon'], i['lat'], 'pm2dom')

    resp = requests.get(req, params=params)
    save_map(resp, out)


def make_map_staticmaps(deltas, speeds, out):
    res = staticmaps.Context()

    for i in deltas:
        res.add_object(staticmaps.Marker(staticmaps.create_latlng(i['lat'], i['lon']), color=staticmaps.WHITE, size=12))
    for i in speeds:
        res.add_object(
            staticmaps.Marker(staticmaps.create_latlng(i['lat'], i['lon']), color=staticmaps.ORANGE, size=12))

    try:
        image = res.render_pillow(800, 500)
    except RuntimeError:
        return
    image.save(out)


def is_sharp_change(dv, dt):
    if dv < 20:
        return 0
    if dt > 20:
        return 0
    if dv / dt < 3:
        return 0
    return dv / dt


def tuple2rgb(*rgb):
    rgb = [hex(int(i))[2:] for i in rgb]
    rgb = ['0' * (2 - len(i)) + i for i in rgb]
    return '#' + ''.join(rgb)


def calc_speed_color(speed):
    # RGB
    if 0 <= speed < 40:
        t = 255 - speed * (255 / 40)
        return tuple2rgb(t, 255, t)
    elif 40 <= speed < 80:
        speed -= 40
        # 0 <= speed < 40
        g = 255 - speed * (255 / 40)
        b = speed * (255 / 40)
        return tuple2rgb(0, g, b)
    elif 80 <= speed <= 100:
        speed -= 80
        # 0 <= speed <= 20
        r = 100 + speed * (100 / 20)
        # 100 <= r <= 200
        b = 100 - speed * (100 / 20)
        # 200 >= b >= 100
        return tuple2rgb(r, 0, b)
    else:
        # 100 <= speed
        r = min(speed * 2, 255)
        return tuple2rgb(r, 0, 0)


class MapMaker:
    """
    Класс, создающий карты

    MapMaker(data) сразу вызывает фунцию load_data(tracks)
    """

    def __init__(self, tracks):
        self.tracks = pd.DataFrame()
        self.speeds = defaultdict(list)
        self.deltas = defaultdict(list)
        self.have_data = False
        self.all_ids = set()
        self.load_data(tracks)

    def load_data(self, tracks: pd.DataFrame) -> None:
        """Функция загружает данные из tracks

        :param tracks: Содержит в себе треки. Должны быть все столбцы из TRACKS_COLUMNS
        :type tracks: pd.DataFrame

        :returns:
            Nothing
        """
        # Датафрейм tracks должен содержать столбцы из TRACKS_COLUMNS
        self.tracks = tracks.copy()
        self.speeds = defaultdict(list)
        self.deltas = defaultdict(list)
        self.all_ids = set()
        self.have_data = False

        for i in TRACKS_COLUMNS:
            if i not in self.tracks.columns:
                print(f'Error, no column {i}')
                return
        self.tracks.dt = pd.to_datetime(self.tracks.dt)
        self.tracks.sort_values(by='dt', inplace=True)
        print('Applying return_seconds')
        self.tracks['dt'] = self.tracks['dt'].apply(return_seconds).astype(int)

        last = defaultdict(list)
        for i in tqdm.tqdm(self.tracks.itertuples()):
            now_id = i.order_id
            self.all_ids.add(now_id)
            last[now_id].append((i.dt, i.lat_, i.lon_))

        print('Getting speeds')
        for i in last:
            now = last[i]
            for j in range(1, len(now)):
                dt = now[j][0] - now[j - 1][0]
                if dt < 1:
                    continue
                lat1, lat2 = now[j - 1][1], now[j][1]
                lon1, lon2 = now[j - 1][2], now[j][2]
                self.speeds[i].append({'speed': calc_distance(lat1, lon1, lat2, lon2) / dt * 3.6, 'dt': dt,
                                       'lat1': lat1, 'lon1': lon1, 'lat2': lat2, 'lon2': lon2})

        print('Grouping')
        for i in self.speeds:
            sp = self.speeds[i]
            for j in range(1, len(sp)):
                self.deltas[i].append(
                    {'dv': abs(sp[j]['speed'] - sp[j - 1]['speed']), 'dt': sp[j]['dt'] + sp[j - 1]['dt'],
                     'lat1': sp[j - 1]['lat1'], 'lon1': sp[j - 1]['lon1'],
                     'lat2': sp[j]['lat1'], 'lon2': sp[j]['lon1'],
                     'lat3': sp[j]['lat2'], 'lon3': sp[j]['lon2'],
                     'v1': sp[j - 1]['speed'], 'v2': sp[j]['speed'],
                     't1': sp[j - 1]['dt'], 't2': sp[j]['dt']})
        self.have_data = True

    def make_figure(self, order_id, out_dir, max_boost=2, max_speed=80, map_type='staticmaps'):
        if not self.have_data:
            print("Data was not loaded or loaded with wrong format")
            return
        speeds = self.speeds[order_id]
        deltas = self.deltas[order_id]
        deltas = [{'lon': i['lon1'], 'lat': i['lat1']} for i in deltas if i['dv'] / i['dt'] > max_boost]
        speeds = [{'lon': i['lon1'], 'lat': i['lat1']} for i in speeds if i['speed'] > max_speed]

        if map_type == 'yandex':
            make_map_yandex(deltas, speeds, out_dir)
        elif map_type == 'staticmaps':
            make_map_staticmaps(deltas, speeds, out_dir)
        else:
            assert False

    def make_folium_map(self, order_id: str, out_dir: str, out_res: str = 'csv', save: bool = True,
                        save_maps: bool = False) -> None:
        """Функция сохраняет folium-карту в json и html в out_dir/order_id

        :param order_id: Номер заказа
        :type order_id: str
        :param out_dir: Путь для сохранения
        :type out_dir: str
        :param out_res: Тип файла-результата
        :type out_res: str
        :param save: Сохранять ли результат
        :type save: bool
        :param save_maps: Сохранять ли карты
        :type save_maps: bool

        :returns:
            Nothing
        """
        if not self.have_data:
            print("Data was not loaded or loaded with wrong format")
            return
        print(f'Start making map for {order_id}')

        if save_maps:
            need_tracks = self.tracks[self.tracks.order_id == order_id]
            if need_tracks.shape[0] == 0:
                print(f'No tracks for {order_id}')
                return

        if order_id not in self.all_ids:
            print(f'No tracks for {order_id}')
            return

        data = dict()
        data['order_id'] = order_id
        data['speedings'] = list()
        data['big_speed_changes'] = list()

        if save_maps:
            need_tracks = need_tracks[['order_id', 'dt', 'lat_', 'lon_']]
            m = folium.Map(need_tracks[['lat_', 'lon_']].to_numpy().tolist()[0], zoom_start=15, control_scale=True)
            folium.PolyLine(need_tracks[['lat_', 'lon_']].to_numpy().tolist(),
                            color='blue', weigth=2.5, opacity=1).add_to(m)

        speeds = [{'lon1': i['lon1'], 'lat1': i['lat1'], 'speed': i['speed'],
                   'lon2': i['lon2'], 'lat2': i['lat2'], 'dt': i['dt'], 'dist': i['dt'] * i['speed']}
                  for i in self.speeds[order_id]]
        deltas = [{'lon1': i['lon1'], 'lat1': i['lat1'],
                   'lon2': i['lon2'], 'lat2': i['lat2'],
                   'lon3': i['lon3'], 'lat3': i['lat3'],
                   'change': is_sharp_change(i['dv'], i['dt']), 'dt': i['dt'],
                   'v1': i['v1'], 'v2': i['v2'], 't1': i['t1'], 't2': i['t2']
                   } for i in self.deltas[order_id]]
        deltas = [i for i in deltas if i['change']]

        for i in speeds:
            if save_maps:
                folium.PolyLine([[i['lat1'], i['lon1']], [i['lat2'], i['lon2']]],
                                color=calc_speed_color(i['speed']), weigth=2.5, opacity=1,
                                tooltip=f'Скорость {round(i["speed"], 1)} км/ч').add_to(m)
            data['speedings'].append({'lon1': i['lon1'], 'lat1': i['lat1'], 'lon2': i['lon2'], 'lat2': i['lat2'],
                                      'dist': i['dist'], 'time': i['dt'], 'speed': i['speed']})

        for i in deltas:
            if save_maps:
                folium.Marker(location=[i['lat2'], i['lon2']],
                              tooltip=f'Скорость изменена в {round(i["change"], 1)} раз за {i["dt"]} c',
                              icon=folium.Icon(color='orange', icon='None', prefix='af')).add_to(m)
            data['big_speed_changes'].append({'lon1': i['lon1'], 'lat1': i['lat1'],
                                              'lon2': i['lon2'], 'lat2': i['lat2'],
                                              'lon3': i['lon3'], 'lat3': i['lat3'],
                                              'v1': i['v1'], 'v2': i['v2'],
                                              't1': i['t1'], 't2': i['t2']})

        if save:
            res_dir = os.path.join(out_dir, order_id)
            if not os.path.isdir(res_dir):
                os.makedirs(res_dir)
            if save_maps:
                m.save(os.path.join(res_dir, f'{order_id}.html'))

        if out_res == 'json':
            if save:
                res_dir = os.path.join(out_dir, order_id)
                if not os.path.isdir(res_dir):
                    os.makedirs(res_dir)
                with open(os.path.join(res_dir, f'{order_id}.json'), 'w') as file:
                    json.dump(data, file, sort_keys=True, indent=4)
            return data
        elif out_res == 'csv':
            res = pd.Series()
            res['order_id'] = data['order_id']
            res['cnt_sharp'] = len(data['big_speed_changes'])
            res['sum_fast'] = sum(i['speed'] * i['time'] for i in data['speedings'] if i['speed'] > 60)
            res['all_path'] = sum(i['speed'] * i['time'] for i in data['speedings'])

            t = sum(i['time'] for i in data['speedings'])
            res['avg_speed'] = sum(i['speed'] * i['time'] for i in data['speedings']) / (1 if t == 0 else t)
            if save:
                res_dir = os.path.join(out_dir, order_id)
                if not os.path.isdir(res_dir):
                    os.makedirs(res_dir)
                res.to_csv(os.path.join(res_dir, f'{order_id}.csv'))
            return res

    def make_folium_maps(self, order_ids: typing.Iterable[str], out_dir: str,
                         out_res: str = 'csv', save_all: bool = False, out_filename: str = 'stats.csv',
                         save_maps: bool = False):
        """Сохраняет folium-карту в our_dir/order_id для всех order_id в order_ids

        :param order_ids: Номера заказов
        :type order_ids: Iterable[str]
        :param out_dir: Путь для сохранения
        :type out_dir: str
        :param out_res: Тип файла-результата
        :type out_res: str
        :param save_all: Сохранять ли промежуточные
        :type save_all: bool
        :param out_filename: Название файла для результата
        :type out_filename: str
        :param save_maps: Сохранять ли карты
        :type save_maps: bool

        :returns:
            Nothing
        """
        res = pd.DataFrame()
        for i in tqdm.tqdm(order_ids):
            res = res.append(self.make_folium_map(i, out_dir, out_res, save_all), ignore_index=True)
        if not os.path.isdir(out_dir):
            os.makedirs(out_dir)
        res.to_csv(os.path.join(os.path.join(out_dir, out_filename)))

    def make_all_folium_maps(self, out_dir: str, out_res: str = 'csv',
                             save_all: bool = False, out_filename: str = 'stats.csv',
                             save_maps: bool = False):
        """Сохраняет folium-карту в our_dir/order_id для всех order_id в последних треках

        :param out_dir: Путь для сохранения
        :type out_dir: str
        :param out_res: Тип файла-результата
        :type out_res: str
        :param save_all: Сохранять ли промежуточные
        :type save_all: bool
        :param out_filename: Название файла для результата
        :type out_filename: str
        :param save_maps: Сохранять ли карты
        :type save_maps: bool

        :returns:
            Nothing
        """
        if self.have_data:
            self.make_folium_maps(self.tracks.order_id.unique(), out_dir, out_res, save_all, out_filename)


def main():
    tracks = pd.read_csv(os.path.join(COMMON_PATH, 'df_track.csv'))
    need_ids = pd.read_csv(os.path.join(COMMON_PATH, 'train_v4.csv')).id_order.unique()

    # map sample
    map = MapMaker(tracks)
    map.make_folium_map(tracks.order_id.unique()[2], out_dir='maps12', save_maps=True)
    return # end of map sample
    for step in tqdm.tqdm(range(0, len(need_ids), ONE_STEP), total=len(need_ids) / ONE_STEP):
        nt = tracks[tracks.order_id.isin(need_ids[step:step + ONE_STEP])]
        maps = MapMaker(nt)
        maps.make_all_folium_maps('maps11', out_filename=f'stats_{step}.csv')

    res = pd.DataFrame()
    for step in range(0, len(need_ids), ONE_STEP):
        res = pd.concat([res, pd.read_csv(os.path.join('maps11', f'stats_{step}.csv'))])
    res.to_csv(os.path.join('maps11', 'stats_all.csv'))


if __name__ == '__main__':
    main()
