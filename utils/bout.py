def get_bouts(df, index, date_info, wrk_index, wrk_date_info, epm, settings):
    temp = {}
    for day, (start, end) in index.items():
        temp[day] = {}
        temp[day]['total'] = count_bouts(df, start, end, epm, settings)
        if settings['ot_run'] and wrk_index:
            temp[day]['other'] = get_wrk_bouts(df, index, date_info, wrk_index, wrk_date_info, day, epm, settings)
            temp[day]['normal'] = {key: [a - b for a, b in zip(temp[day]['total'][key], temp[day]['other'][key])]
                                   for key in temp[day]['total']}

    return temp


def get_wrk_bouts(df, index, date_info, wrk_index, wrk_date_info, day, epm, settings):
    from utils.activity import find_key_for_value
    key1 = find_key_for_value(wrk_date_info, date_info[day]['date'])
    key2 = find_key_for_value(wrk_date_info, date_info[day - 1]['date']) if day != 1 else None

    codes = settings['bout_codes']
    i_cat = settings['i_cat']

    if key1:
        temp1 = count_bouts(df, wrk_index[key1][0], min(wrk_index[key1][1], index[day][1]), epm, settings)
    else:
        temp1 = {key: [0 for _ in range(len(i_cat))] for key in codes}

    if key2 and wrk_index[key2][1] > index[day][0]:
        temp2 = count_bouts(df, index[day][0], wrk_index[key2][1], epm, settings)
    else:
        temp2 = {key: [0 for _ in range(len(i_cat))] for key in codes}

    return {key: [a + b for a, b in zip(temp1[key], temp2[key])] for key in temp1}


def count_bouts(df, start, end, epm, settings):
    column = settings['act_column']
    codes = settings['bout_codes']
    max_noise = settings['noise_threshold']
    cut = settings['length_treshold']

    temp = {key: [] for key in codes}
    selected_values = df[column].iloc[start:end]
    
    if df[column][start] in codes:
        current_code = df[column][start]
        jump = 0
    else:
        jump = skip(df, start, codes, column)
        current_code = df[column][start + jump]
    length, noise = 0, 0
    
    for i, value in selected_values.items():
        if jump > 0:
            jump -= 1
            continue

        if value != current_code:
            epoch_gap = find_next(df, current_code, i, column)
            if ((length / epm) < cut and epoch_gap < 2) or \
            ((length / epm) > cut and epoch_gap < 3 and noise / length < max_noise):
                noise, length = noise + 1, length + 1
            else:
                temp[current_code].append(length - 1 if df[column][i - 1] != current_code else length)
                length = 2 if df[column][i - 1] != current_code else 1
                noise = 0
                try:
                    current_code = value if value in codes else df[column][i + skip(df, i, codes, column)]
                except KeyError:
                    print('TEST', i, value, start, end, df['timestamp'][start], df['timestamp'][7791])
                    break
        else:
            length += 1
    temp[current_code].append(length)
    return get_bout_categories(temp, epm, settings['i_cat'], settings['a_cat'])


def skip(df, index, codes, column) -> int:
    count = 1
    try:
        while df[column][index + count] not in codes:
            count += 1
        return count
    except KeyError:
        return count


def find_next(df, code, index, column) -> int:
    count = 1
    try:
        while df[column][index + count] != code:
            count += 1
        return count
    except KeyError:
        return count


def get_bout_categories(bout_dict, epm, i_cat, a_cat) -> dict[dict[list]]:
    bouts = {code: [sum(map(lambda item: (a_cat if code not in [7, 8] else i_cat)[i][0] / (60 / epm) <= item <=
                                         (a_cat if code not in [7, 8] else i_cat)[i][1] / (60 / epm),
                            bout_dict[code]))
                    for i in list(a_cat.keys())]
             for code in bout_dict.keys()}
    return bouts