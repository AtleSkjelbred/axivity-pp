import pandas as pd
import glob
import os
from datetime import datetime
import time
from itertools import groupby
from operator import itemgetter
import argparse
import yaml

import utils.bout
import utils.calc_var
import utils.processing_settings
import utils.df_filter
import utils.other_time as ot
import utils.activity
import utils.transition
import utils.barcode

start_time = time.time()


def main(data_folder, settings):
    outgoing_qc = pd.DataFrame()
    outgoing_df = pd.DataFrame()
    data_path = os.getcwd()

    if settings['ot_run']:
        ot_df = get_ot_df(settings['ot_delimiter'])
    else:
        ot_df = False
    
    if settings['barcode_run']:
        if not os.path.exists(os.path.join(data_path, 'barcode plot')):
            os.makedirs(os.path.join(data_path, 'barcode plot'))

    for csvfile in glob.glob(data_path + '*.csv'):
        df = pd.read_csv(csvfile)
        if settings['id_column'] not in df.columns:
            continue

        new_line = {'subject_id': df[settings['id_column']][0]}
        print(f'--- Processing file: {new_line["subject_id"]} ---', end='\r', flush=True)
        epm, epd = epoch_test(new_line, df, settings['time_column'])
        df = df_filter.filter_dataframe(new_line, df, epm, settings)
        index = get_index(df, settings['time_column'])
        df_filter.filter_days(df, index, settings)
        index = shift_index_keys(index)

        ot_index, ot_qc = ot.other_times(df, new_line['subject_id'], settings['ot_run'], settings['ot_format'], ot_df)
        date_info, ot_date_info = get_date_info(df, index), get_date_info(df, ot_index)

        variables = get_variables(new_line, epm, df, index, date_info, ot_index, ot_date_info, settings)
        calculate_variables.calc_var(df, new_line, index, ot_index, date_info, variables, epm, epd, settings)

        outgoing_qc = pd.concat([pd.DataFrame(ot_qc, index=[0]), outgoing_qc], ignore_index=True)
        outgoing_df = pd.concat([pd.DataFrame(new_line, index=[0]), outgoing_df], ignore_index=True)

        if settings['barcode_run']:
            plot, ot_plot = barcode.gen_plot(df, index, ot_index)
            barcode.plotter(plot, ot_plot, date_info, new_line['subject_id'], data_path)

    if not os.path.exists(os.path.join(data_path, 'results')):
        os.makedirs(os.path.join(data_path, 'results'))
    os.chdir(os.path.join(data_path, 'results'))

    outgoing_qc.to_csv(f'other time qc {str(datetime.now().strftime("%d.%m.%Y %H.%M"))}.csv', index=False)
    outgoing_df.to_csv(f'post process data {str(datetime.now().strftime("%d.%m.%Y %H.%M"))}.csv', index=False)
    end_time = time.time()
    print(f'--- Total run time: {end_time - start_time} sec ---')


def get_ot_df(delim):
    csv_path = [file for file in [f.path for f in os.scandir(os.getcwd()) if f.is_file()] if file.endswith('.csv')]
    ot_df = pd.read_csv(csv_path, delimiter=delim)
    return ot_df


def get_variables(new_line, epm, df, index, date_info, ot_index, ot_date_info, settings) -> dict:
    variables = {}
    if settings['nw_variables']:
        variables['nw'] = non_wear_pct(new_line, df, index, settings)
    if settings['ai_variables']:
        variables['ai'] = activity.get_activities(df, index, date_info, ot_index, ot_date_info,
                                                  settings['ot_variables'], settings['ai_codes'], settings['ai_column'])
    if settings['act_variables']:
        variables['act'] = activity.get_activities(df, index, date_info, ot_index, ot_date_info,
                                                   settings['ot_variables'], settings['act_codes'],
                                                   settings['act_column'])
    if settings['walk_variables']:
        variables['walk'] = activity.get_activities(df, index, date_info, ot_index, ot_date_info,
                                                    settings['ot_variables'], settings['walk_codes'],
                                                    settings['walk_column'])
    if settings['ait_variables']:
        variables['ait'] = transition.get_ait(df, index, date_info, ot_index, ot_date_info, settings['ot_variables'])
    if settings['bout_variables']:
        variables['bout'] = bout.get_bouts(df, index, date_info, ot_index, ot_date_info, epm, settings)
    return variables


def epoch_test(new_line: dict, df: pd.DataFrame, time_column: str) -> tuple[int, int]:
    datetime_object1 = datetime.strptime(df[time_column][10][:19], "%Y-%m-%d %H:%M:%S")
    datetime_object2 = datetime.strptime(df[time_column][11][:19], "%Y-%m-%d %H:%M:%S")
    epm = int(60 / (datetime_object2 - datetime_object1).total_seconds())
    epd = epm * 60 * 24

    new_line.update({'epoch per min': epm,
                     'epoch per day': epd})
    return epm, epd


def get_index(df: pd.DataFrame, time_column: str) -> dict:
    index = [(list(map(itemgetter(1), g))[0]) for k, g in
             groupby(enumerate(df.index[df[time_column].str.contains(' 00:00:')].tolist()), lambda ix: ix[0] - ix[1])]
    index.insert(0, 0)
    index.append(len(df))
    index_dict = {i + 1: [index[i], index[i + 1]] for i in range(len(index) - 1)}
    return index_dict


def shift_index_keys(index: dict) -> dict:
    sorted_keys = sorted(index.keys())
    shifted_dict = {new_key: index[old_key] for new_key, old_key in enumerate(sorted_keys, start=1)}
    return shifted_dict


def get_date_info(df, index):
    info = {day: {
        'day_nr': datetime.strptime(df['timestamp'][val[0]][:10], "%Y-%m-%d").weekday() + 1,
        'day_str': datetime.strptime(df['timestamp'][val[0]][:10], "%Y-%m-%d").strftime('%A'),
        'date': df['timestamp'][val[0]][:10], 'length_epoch': index[day][1] - index[day][0]}
        for day, val in index.items()}
    return info


def non_wear_pct(new_line, df, ind, settings) -> dict:
    temp = {day: {code: (df[settings['nw_column']][start: end].values == code).sum() for code in settings['nw_codes']}
            for day, (start, end) in ind.items()}
    total = {code: round(sum([temp[day][code] for day in ind.keys()]) / sum(e - s for s, e in ind.values()) * 100, 2)
             for code in settings['nw_codes']}
    daily = {day: {code: round(temp[day][code] / (ind[day][1] - ind[day][0]) * 100, 2) for code in settings['nw_codes']}
             for day in ind.keys()}

    for key, value in total.items():
        new_line[f'total_nw_code_{key}'] = value

    return daily


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-folder', type=str, dest='data_folder', help='Path of dataset folder')
    args = parser.parse_args()
    if not args.data_folder:
        if not os.path.exists(os.path.join(os.getcwd(), 'data/')):
            os.makedirs(os.path.join(os.getcwd(), 'data/'))      
        args.data_folder = os.path.join(os.getcwd(), 'data/')

    with open('config.yaml') as f:
        config = yaml.safe_load(f)

    #main(args.data_folder, config)