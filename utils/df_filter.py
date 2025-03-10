import pandas as pd
from itertools import groupby
from operator import itemgetter


def filter_dataframe(new_line, df, epm, settings):
    if not settings['nw_ends'] and not settings['bug_ends']:
        return df
    df = non_wear_ends(new_line, df, epm, settings)

    df = filter_predictions(df, settings)

    return df


def non_wear_ends(new_line, df, epm, settings) -> pd.DataFrame:
    start_len = len(df)
    if settings['nw_column'] in df.columns and settings['nw_ends']:
        df = remove_inactive_ends(df, settings['nw_column'], 4, epm * settings['nw_ends_min'], settings['nw_ends_pct'])
    if settings['bug_ends']:
        df = remove_inactive_ends(df, 'label', 8, epm * settings['bug_ends_min'], settings['bug_ends_pct'])
        df = remove_inactive_ends(df, 'label', 7, epm * settings['bug_ends_min'], settings['bug_ends_pct'])
    end_len = len(df)

    new_line['epochs_removed'] = (start_len - end_len)

    return df


def remove_inactive_ends(df, column, code, length, threshold) -> pd.DataFrame:
    for i in reversed(range(len(df))):
        if df[column][i] != code:
            if (df[column][i - length: i] == code).sum() < length * threshold:
                df = df.iloc[:i + 1]
                break

    for i in range(len(df)):
        if df[column][i] != code:
            if (df[column][i:i + length] == code).sum() < length * threshold:
                df = df.iloc[i:]
                break
    df.reset_index(drop=True, inplace=True)
    return df


def filter_predictions(df: pd.DataFrame, settings: dict) -> pd.DataFrame:

    if settings['remove_stairs']:
        for i in df.index[df[settings['act_column']].isin([4, 5])].tolist():
            df.at[i, settings['act_column']] = 1
            if settings['walk_column'] in df.columns:
                df.at[i, settings['walk_column']] = 104

    if settings['remove_bending']:
        for i in df.index[df[settings['act_column']] == 10].tolist():
            df.at[i, settings['act_column']] = 6

    if settings['remove_shuffling']:
        for i in df.index[df[settings['act_column']] == 3].tolist():
            try:
                if df[settings['act_column']][i - 1] == 1 and df[settings['act_column']][i + 1] == 1:
                    df.at[i, settings['act_column']] = 1
                else:
                    df.at[i, settings['act_column']] = 6
            except KeyError:
                df.at[i, settings['act_column']] = 6

    if settings['merge_cyc_codes']:
        df[settings['act_column']] = df[settings['act_column']].replace([13, 14, 130, 140], 13)

    if settings['adjust_cyc_interval']:
        df = cycling_interval(df, settings)

    if settings['ai_variables'] or settings['ait_variables']:
        df[settings['ai_column']] = ['I' if i == 7 or i == 8 else 'A' for i in df[settings['act_column']]]

    return df


def cycling_interval(df, settings) -> pd.DataFrame:
    temp = [ind for ind, item in enumerate(df[settings['act_column']]) if item == 13]
    lens = [len(list(map(itemgetter(1), g))) for k, g in groupby(enumerate(temp), lambda ix: ix[0] - ix[1])]
    starts = [(list(map(itemgetter(1), g))[0]) for k, g in groupby(enumerate(temp), lambda ix: ix[0] - ix[1])]

    for start, length in zip(starts, lens):
        if length <= settings['min_cyc_epochs']:
            try:
                df.loc[start:start + length - 1, settings['act_column']] = df[settings['act_column']][start - 1]
            except KeyError:
                df.loc[start:start + length - 1, settings['act_column']] = df[settings['act_column']][start + 1]
    return df


def filter_days(df, index, settings, epd):
    if not settings['nw_days'] and not settings['bug_days']:
        return df
    print(index, epd)
    conditions = []
    if settings['nw_days']:
        conditions.append((settings['nw_column'], 4, settings['nw_days_pct']))
    if settings['bug_days']:
        if settings['bug_lying']:
            conditions.append((settings['act_column'], 8, settings['bug_days_pct']))
        if settings['bug_sitting']:
            conditions.append((settings['act_column'], 7, settings['bug_days_pct']))
        if settings['bug_standing']:
            conditions.append((settings['act_column'], 6, settings['bug_days_pct']))

    keys_to_delete = set()
    for day, (start, end) in index.items():
        if settings['remove_partial_days']:
            if index[day][1] - index[day][0] < epd:
                keys_to_delete.add(day)
        for con in conditions:
            if (df[con[0]][start:end].values == con[1]).sum() > ((end - start) * con[2]):
                keys_to_delete.add(day)
                break

    for day in keys_to_delete:
        del index[day]

    return df
