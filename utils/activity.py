def count_codes(df, start, end, column, code):
    return (df[column][start:end].values == code).sum()


def get_activities(df, index, date_info, ot_index, wrk_date_info, run_ot, codes, column):
    temp = {}
    
    for day, (start, end) in index.items():
        temp[day] = {}

        for code in codes:
            temp[day][code] = {'total': count_codes(df, start, end, column, code)}
            if run_ot and ot_index:
                temp[day][code]['ot'] = get_wrk_act(df, index, date_info, ot_index, wrk_date_info, day,
                                                    column, code)
                temp[day][code]['normal'] = temp[day][code]['total'] - temp[day][code]['ot']

    return temp


def get_wrk_act(df, index, date_info, wrk_index, wrk_date_info, day, column, code):
    key1 = find_key_for_value(wrk_date_info, date_info[day]['date'])
    key2 = find_key_for_value(wrk_date_info, date_info[day - 1]['date']) if day != 1 else None

    temp = 0
    if key1:
        temp += count_codes(df, wrk_index[key1][0], min(wrk_index[key1][1], index[day][1]), column, code)
    if key2 and wrk_index[key2][1] > index[day][0]:
        temp += count_codes(df, index[day][0], wrk_index[key2][1], column, code)
    return temp


def find_key_for_value(nested_dict, target_value, current_key=None):
    for key, value in nested_dict.items():
        if isinstance(value, dict):
            nested_key = find_key_for_value(value, target_value, key)
            if nested_key is not None:
                return nested_key
        elif value == target_value:
            return current_key if current_key is not None else key
    return None