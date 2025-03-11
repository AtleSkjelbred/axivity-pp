from itertools import groupby
from operator import itemgetter


def calculate_transitions(df, start, end):
    return len([list(map(itemgetter(1), g))[0] for k, g in groupby(enumerate([index for index, item in enumerate(
        df['ai_column'][start: end]) if item == 'A']), lambda ix: ix[0] - ix[1])])


def get_ait(df, index, date_info, ot_index, ot_date_info, run_ot):
    ait = {}
    
    for day, value in index.items():
        ait[day] = {}
        
        ait[day] = {'total': calculate_transitions(df, value[0], value[1])}
        if run_ot and ot_index:
            ait[day]['ot'] = get_wrk_ait(df, index, date_info, ot_index, ot_date_info, day)

            # noinspection PyTypeChecker
            ait[day].setdefault('ot', '.')

            if ait[day]['ot'] != '.':
                ait[day]['normal'] = ait[day]['total'] - ait[day]['ot']
            else:
                ait[day]['normal'] = ait[day]['total']
    return ait


def get_wrk_ait(df, index, date_info, ot_index, ot_date_info, day):
    from utils.activity import find_key_for_value
    key1 = find_key_for_value(ot_date_info, date_info[day]['date'])
    key2 = find_key_for_value(ot_date_info, date_info[day - 1]['date']) if day != 1 else None

    temp = 0
    if key1:
        temp += calculate_transitions(df, ot_index[key1][0], min(ot_index[key1][1], index[day][1]))
    if key2 and ot_index[key2][1] > index[day][0]:
        temp += calculate_transitions(df, index[day][0], ot_index[key2][1])

    return temp
