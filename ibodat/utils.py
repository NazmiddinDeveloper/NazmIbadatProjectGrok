from datetime import datetime, time


def get_prayer_zones(start_str, end_str):
    """
    Namoz vaqtini 3 ga bo'ladi:
    - green : birinchi 2/3
    - yellow: o'rta 1/6 ... 5/6
    - red   : oxirgi 1/3
    """
    fmt = "%H:%M"
    start = datetime.strptime(start_str, fmt)
    end   = datetime.strptime(end_str,   fmt)

    total  = (end - start).seconds
    third  = total // 3

    green_end  = start.timestamp() + third * 2
    yellow_end = start.timestamp() + third * 2 + third // 2

    green_end_t  = datetime.fromtimestamp(green_end).strftime(fmt)
    yellow_end_t = datetime.fromtimestamp(yellow_end).strftime(fmt)

    return {
        'green':  {'from': start_str,    'to': green_end_t},
        'yellow': {'from': green_end_t,  'to': yellow_end_t},
        'red':    {'from': yellow_end_t, 'to': end_str},
    }


def get_done_status(done_at_str, zones):
    """
    Bajarilgan vaqtga qarab status qaytaradi
    """
    if not done_at_str:
        return 'missed'

    fmt  = "%H:%M"
    done = datetime.strptime(done_at_str[:5], fmt)
    g_end = datetime.strptime(zones['green']['to'],  fmt)
    y_end = datetime.strptime(zones['yellow']['to'], fmt)

    if done <= g_end:
        return 'on_time'
    elif done <= y_end:
        return 'late'
    else:
        return 'qaza'