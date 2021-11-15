from math import pi as PI, sin, cos, atan2, sqrt


def calc_distance(lat1, lon1, lat2, lon2):
    """
    Считает между координатами

    :param lat1: Широта1
    :param lon1: Долгота1
    :param lat2: Широта2
    :param lon2: Долгота2
    :return: Расстояние между координатами в метрах
    """
    R = 6371e3  # metres
    φ1 = lat1 * PI / 180  # φ, λ in radians
    φ2 = lat2 * PI / 180
    Δφ = (lat2 - lat1) * PI / 180
    Δλ = (lon2 - lon1) * PI / 180

    a = sin(Δφ / 2) * sin(Δφ / 2) + \
        cos(φ1) * cos(φ2) * \
        sin(Δλ / 2) * sin(Δλ / 2)
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    d = R * c  # in metres

    return d


COMMON_PATH = 'final'  # Не забудьте изменить пути! Don't forget to change paths!
TRACKS_COLUMNS = ['dt', 'lat_', 'lon_', 'order_id', 'driver_id']  # Необходимые столбцы для маркеров
WEEK_SECONDS = 7 * 24 * 60 * 60  # Количество секунд в неделе
ONE_STEP = 20_000  # Шаг для маркеров
K_RANKS = [-1000, 0.09, 0.148, 0.19, 1000]  # Границы для K-rank
V_RANKS = [-1000, 0.197, 0.37, 0.667, 1000]  # Границы для V-rank
