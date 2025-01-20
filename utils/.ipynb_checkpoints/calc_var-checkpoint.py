import transition
import activity
import bout


def calculate_variables(df, new_line, index, ot_index, date_info, variables, epm, epd, settings):
    temp = {'ai': ['ai_codes', 'ai_column'], 'act': ['act_codes', 'act_column'], 'walk': ['walk_codes', 'walk_column']}
    chosen_var = {key: {'codes': settings[codes], 'column': settings[column]}
                  for key, (codes, column) in temp.items() if key in variables}
    code_name = settings['code_name']
    bout_codes = settings['bout_codes']

    wk_wknd = weekday_distribution(new_line, index, date_info, epm)
    if settings['average_variables']:
        average_variables(new_line, variables, index, wk_wknd, epm, epd, code_name, chosen_var, bout_codes)
    if settings['week_wknd_variables']:
        wk_wknd_variables(new_line, variables, index, date_info, wk_wknd, epm, epd, code_name, chosen_var, bout_codes)

    if settings['daily_variables']:
        daily_variables(new_line, variables, date_info, code_name)
    if settings['ot_variables']:
        other_time_variables(new_line, df, ot_index, code_name, chosen_var, bout_codes, settings, epm)

    return


def weekday_distribution(new_line, index, date_info, epm) -> dict:
    wk_wknd = {'wk': [val[1] - val[0] for key, val in index.items() if date_info[key]['day_nr'] not in [6, 7]],
               'wknd': [val[1] - val[0] for key, val in index.items() if date_info[key]['day_nr'] in [6, 7]]}
    for key, val in wk_wknd.items():
        wk_wknd[key] = sum(val) / (epm * 60 * 24)
    wk_wknd['total'] = wk_wknd['wk'] + wk_wknd['wknd']

    new_line[f'total_days'] = round(wk_wknd['total'], 2)
    new_line[f'wk_days'] = round(wk_wknd['wk'], 2)
    new_line[f'wknd_days'] = round(wk_wknd['wknd'], 2)
    return wk_wknd


def average_variables(new_line, var, index, wk_wknd, epm, epd, code_name, chosen_var, bout_codes):

    for key, dic in chosen_var.items():
        temp = {code: [var[key][day][code]['total'] for day in index.keys()] for code in dic['codes']}
        act_avg = {code: sum(temp[code]) / (wk_wknd['total']) for code in dic['codes']}
        for code, value in act_avg.items():
            new_line[f'avg_{code_name[code]}_min'] = round(value / epm, 2)
            new_line[f'avg_{code_name[code]}_pct'] = round(value / epd * 100, 2)

    if 'ait' in var.keys():
        temp = sum(var['ait'][day]['total'] for day in index.keys()) / wk_wknd['total']
        new_line[f'avg_ait'] = round(temp, 2)

    if 'bout' in var.keys():
        temp = {code: [var['bout'][day]['total'][code] for day in index.keys()] for code in bout_codes}
        for code, lists in temp.items():
            temp[code] = [round(sum(x) / wk_wknd['total'], 2) for x in zip(*lists)]
        for code, values in temp.items():
            for nr, val in enumerate(values):
                new_line[f'avg_{code_name[code]}_bout_c{nr + 1}'] = val


def wk_wknd_variables(new_line, var, index, date_info, wk_wknd, epm, epd, code_name, chosen_var, bout_codes):

    for key, dic in chosen_var.items():
        temp = {'wk': {}, 'wknd': {}}
        for day in index.keys():
            target = 'wknd' if date_info[day]['day_nr'] in [6, 7] else 'wk'
            for code in dic['codes']:
                temp[target].setdefault(code, []).append(var[key][day][code]['total'])

        for key2, dic2 in temp.items():
            for code2, inner_list in dic2.items():
                new_line[f'avg_{key2}_{code_name[code2]}_min'] = round(sum(inner_list) / wk_wknd[key2] / epm, 2)
                new_line[f'avg_{key2}_{code_name[code2]}_pct'] = round(sum(inner_list) / wk_wknd[key2] / epd * 100, 2)

    if 'ait' in var.keys():
        temp = {'wk': [], 'wknd': []}
        for day in index.keys():
            temp['wknd' if date_info[day]['day_nr'] in [6, 7] else 'wk'].append(var['ait'][day]['total'])

        for key, value in temp.items():
            try:
                new_line[f'avg_{key}_ait'] = round(sum(value) / wk_wknd[key], 2)
            except ZeroDivisionError:
                continue

    if 'bout' in var.keys():
        bouts_ave = {}
        for day in index.keys():
            target_dict = bouts_ave.setdefault('wknd' if date_info[day]['day_nr'] in [6, 7] else 'wk', {})
            for code in bout_codes:
                target_dict.setdefault(code, []).append(var['bout'][day]['total'][code])

        for key, values in bouts_ave.items():
            for code, lists in values.items():
                bouts_ave[key][code] = [round(sum(x) / wk_wknd[key], 2) for x in zip(*lists)]

        for key in bouts_ave.keys():
            for code, values in bouts_ave[key].items():
                for nr, val in enumerate(values):
                    new_line[f'avg_{key}_{code_name[code]}_bout_c{nr + 1}'] = val


def daily_variables(new_line, var, date_info, code_name):

    for day, info in date_info.items():
        new_line[f'day{day}_nr'] = day
        new_line[f'day{day}_date'] = info['date']
        new_line[f'day{day}_wkday_nr'] = info['day_nr']
        new_line[f'day{day}_wkday_str'] = info['day_str']
        new_line[f'day{day}_length_min'] = info['length_epoch']
        new_line[f'day{day}_length_pct'] = round(info['length_epoch'] / 1440 * 100, 2)

        if 'nw' in var.keys():
            for key, value in var['nw'][day].items():
                new_line[f'day{day}_nw_code_{key}'] = value

        if 'act' in var.keys():
            for code, values in var['act'][day].items():
                new_line[f'day{day}_total_{code_name[code]}'] = values['total']
                new_line[f'day{day}_normal_{code_name[code]}'] = values['normal']
                new_line[f'day{day}_other_{code_name[code]}'] = values['ot']

        if 'walk' in var.keys():
            for code, values in var['walk'][day].items():
                new_line[f'day{day}_total_{code_name[code]}'] = values['total']
                new_line[f'day{day}_normal_{code_name[code]}'] = values['normal']
                new_line[f'day{day}_other_{code_name[code]}'] = values['ot']

        if 'ait' in var.keys():
            new_line[f'day{day}_total_ait'] = var['ait'][day]['total']
            new_line[f'day{day}_normal_ait'] = var['ait'][day]['normal']
            new_line[f'day{day}_other_ait'] = var['ait'][day]['ot']

        if 'bout' in var.keys():
            for key in ['total', 'normal', 'other']:
                for code, values in var['bout'][day][key].items():
                    for nr, val in enumerate(values):
                        new_line[f'day{day}_{code_name[code]}_{key}_bouts_c{nr + 1}'] = val


def other_time_variables(new_line, df, wrk_index, code_name, chosen_var, bout_codes, settings, epm):

    for shift, (start, end) in wrk_index.items():
        length = end - start
        new_line[f'ot{shift}_length'] = length

        if settings['ait_variables']:
            new_line[f'ot{shift}_ait'] = transition.calculate_transitions(df, start, end)

        for key, dic in chosen_var.items():
            for code in dic['codes']:
                count = activity.count_codes(df, start, end, dic['column'], code)
                new_line[f'ot{shift}_{code_name[code]}_min'] = count
                new_line[f'ot{shift}_{code_name[code]}_pct'] = round(count / length * 100, 3)

        if settings['bout_variables']:
            bouts = bout.count_bouts(df, start, end, epm, settings)
            for code in bout_codes:
                for cat, val in enumerate(bouts[code]):
                    new_line[f'ot{shift}_{code_name[code]}_bout_c{cat + 1}'] = val
