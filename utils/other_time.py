from datetime import datetime


def other_times(df, subject_id, ot_run, ot_format, ot_df):
    if not ot_run or ot_format not in [1, 2]:
        return False, False

    ot_qc = {'SID': subject_id}
    index_other_df = ot_df.index[(ot_df['ID']) == subject_id].tolist()

    if len(index_other_df) != 1:
        ot_qc.update({
            'ID_occurrences': len(index_other_df),
            'file_start': datetime.strptime(df['timestamp'].iloc[0][:15], "%Y-%m-%d %H:%M"),
            'file_end': datetime.strptime(df['timestamp'].iloc[-1][:15], "%Y-%m-%d %H:%M")})
        return False, ot_qc

    ind = int(index_other_df[0])
    ot_qc['ot_index'] = ind
    ot_qc['ID_occurrences'] = int(len(index_other_df))

    ot_datetime = import_other_times(ot_df, ind, ot_qc, ot_format)

    if not ot_datetime:
        ot_qc['no_data'] = True
        return False, ot_qc
    ot_qc['no_data'] = False
    ot_index = get_index(df, ot_datetime, ot_qc)
    find_bugs(ot_datetime, ot_index, df, ot_qc)
    ot_index = shift_index_keys(ot_index)

    return ot_index, ot_qc


def import_other_times(ot_df, ot_index, ot_qc, format_type):
    ot_datetime = {}
    invalid_plot, incomplete_plot = False, False
    origo = 3 if format_type == 1 else 5
    increment = 5 if format_type == 1 else 12

    for day in range(1, 99):
        end_index = origo + 4 if format_type == 1 else origo + 10
        row = ot_df.iloc[ot_index, origo:end_index]

        if row.isna().all():
            break
        elif row.notna().all():
            try:
                if format_type == 1:
                    s_date, s_time, e_date, e_time = row
                    start = datetime.strptime(f'{s_date} {s_time}', '%d.%m.%Y %H:%M')
                    end = datetime.strptime(f'{e_date} {e_time}', '%d.%m.%Y %H:%M')
                else:
                    s_day, s_month, s_year, e_day, e_month, e_year, s_hour, s_min, e_hour, e_min = row
                    start = datetime(2000 + int(s_year), int(s_month), int(s_day), int(s_hour), int(s_min))
                    end = datetime(2000 + int(e_year), int(e_month), int(e_day), int(e_hour), int(e_min))
                ot_datetime[day] = [start.strftime('%Y-%m-%d %H:%M'), end.strftime('%Y-%m-%d %H:%M')]
            except ValueError:
                invalid_plot = True
        else:
            incomplete_plot = True

        origo += increment

    ot_qc.update({'invalid_plot': invalid_plot,
                  'incomplete_plot': incomplete_plot})
    return ot_datetime


def import_other_times_1(ot_df, ot_index, ot_qc):
    ot_datetime = {}
    invalid_plot = False
    incomplete_plot = False
    origo = 3

    for day in range(1, 99):
        row = ot_df.iloc[ot_index, origo:origo + 4]
        s_date, s_time, e_date, e_time = row
        if row.isna().all():
            break
        elif row.notna().all():
            try:
                start = datetime.strptime(f'{s_date} {s_time}', '%d.%m.%Y %H:%M')
                end = datetime.strptime(f'{e_date} {e_time}', '%d.%m.%Y %H:%M')
                ot_datetime[day] = [start.strftime('%Y-%m-%d %H:%M'), end.strftime('%Y-%m-%d %H:%M')]
            except ValueError:
                invalid_plot = True
        else:
            incomplete_plot = True

        origo += 5

    ot_qc['invalid_plot'] = invalid_plot
    ot_qc['incomplete_plot'] = incomplete_plot
    return ot_datetime


def import_other_times_2(ot_df, ot_index, ot_qc):
    ot_datetime = {}
    invalid_plot = False
    incomplete_plot = False
    origo = 5
    for day in range(1, 99):
        row = ot_df.iloc[ot_index, origo:origo + 10]
        s_day, s_month, s_year, e_day, e_month, e_year, s_hour, s_min, e_hour, e_min = row

        if row.isna().all():
            break
        elif row.notna().all():
            try:
                start = datetime(2000 + int(s_year), int(s_month), int(s_day), int(s_hour), int(s_min))
                end = datetime(2000 + int(e_year), int(e_month), int(e_day), int(e_hour), int(e_min))
                ot_datetime[day] = [start.strftime('%Y-%m-%d %H:%M'), end.strftime('%Y-%m-%d %H:%M')]
            except ValueError:
                invalid_plot = True
        else:
            incomplete_plot = True

        origo += 12
    ot_qc['invalid_plot'] = invalid_plot
    ot_qc['incomplete_plot'] = incomplete_plot
    return ot_datetime


def get_index(df, ot_datetime, ot_qc):
    ot_index = {}
    date_not_in_data = False

    for day, (start, end) in ot_datetime.items():
        start_index = df.index[df['timestamp'].str.contains(start)].tolist()
        end_index = df.index[df['timestamp'].str.contains(end)].tolist()
        ot_index[day] = [start_index, end_index]

    if len(ot_index[1][0]) == 0:
        ot_index[1][0] = [0]
    if len(ot_index[sorted(list(ot_index.keys()))[-1]][1]) == 0:
        ot_index[sorted(list(ot_index.keys()))[-1]][1] = [len(df) - 1]

    keys = []
    for key, (start, end) in ot_index.items():
        if len(start) == 0 or len(end) == 0:
            keys.append(key)
            date_not_in_data = True
        else:
            ot_index[key][0] = ot_index[key][0][0]
            ot_index[key][1] = ot_index[key][1][0]

    for key in keys:
        del ot_index[key]

    ot_qc['date_not_in_data'] = date_not_in_data
    return ot_index


def find_bugs(ot_datetime, ot_index, df, ot_qc):
    is_zero, is_minus = False, False
    count = 0
    start_time = datetime.strptime(df['timestamp'].iloc[0][:15], "%Y-%m-%d %H:%M")
    end_time = datetime.strptime(df['timestamp'].iloc[-1][:15], "%Y-%m-%d %H:%M")

    for key, (start, end) in ot_index.items():
        if end - start == 0:
            is_zero = True
        elif (end - start) < 0:
            is_minus = True

    ot_qc.update({
        'has_zero': is_zero,
        'has_minus': is_minus,
        'file_start': start_time,
        'file_end': end_time})

    for key, (start, end) in ot_index.items():
        ot_qc[f'time_period_{key}'] = int(end - start)

    for day, value in ot_datetime.items():
        for val in value:
            check = datetime.strptime(val, "%Y-%m-%d %H:%M")
            if start_time <= check <= end_time:
                continue
            else:
                count += 1
                ot_qc[f'out {count}'] = val
    return


def shift_index_keys(index):
    sorted_keys = sorted(index.keys())
    shifted_dict = {new_key: index[old_key] for new_key, old_key in enumerate(sorted_keys, start=1)}
    return shifted_dict
