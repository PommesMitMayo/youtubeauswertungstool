import sys
import csv
import matplotlib.pyplot as plt
import itertools
import glob
import datetime
import pathlib
import os
import shutil
import gc
from wordcloud import WordCloud


def create_dict(file_name):
    print('Loading results from .csv')
    results = []
    try:
        with open(file_name, newline='') as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                results.append(dict(row))
    except FileNotFoundError:
        print('No file found. Add the path to the survey results csv as first parameter.')
        sys.exit()
    print('Total results: ' + str(len(results)))

    print('Filtering results without parental approval and duplicates')
    result_dict = {}
    for result in results:
        timestamp = result.pop('Timestamp') if 'Timestamp' in result else result.pop('Zeitstempel')
        if 'keine' not in result.get(get_key('1', results[0])):
            valid = True
            for key, valid_result in result_dict.items():
                if result == valid_result:
                    valid = False
            if valid:
                result_dict[timestamp] = result
    print('Total valid results: ' + str(len(result_dict)))

    return result_dict


def get_key(question_id, dict):
    for key in dict:
        if question_id == key.split('.')[0]:
            return key
    print('Question with ID ' + question_id + ' not found.')
    sys.exit()


def generate_data_sets(x, y, results):
    print('Generating data sets')
    data_sets = {}
    x_vals = {}
    y_vals = {}
    for result in results:
        for x_val in result[x].split(';'):
            x_val = x_val.split(' ')[0] if x == '25. Alter' else x_val
            if x_val not in data_sets:
                x_vals[x_val] = 0
                data_sets[x_val] = {}
            x_has_at_least_one_y = False
            for y_val in result[y].split(';'):
                y_val = y_val.split(' ')[0] if y == '25. Alter' else y_val
                if y_val and y_val not in y_vals:
                    y_vals[y_val] = 0
                if x_val and y_val:
                    x_has_at_least_one_y = True
                    if y_val not in data_sets[x_val]:
                        data_sets[x_val][y_val] = 0
                    data_sets[x_val][y_val] += 1
                    y_vals[y_val] += 1
            if x_has_at_least_one_y: x_vals[x_val] += 1

    return {k: v for k, v in data_sets.items() if v}, x_vals, y_vals


def get_x_locations(data_sets, use_max_percentage):
    maximums = [max(list(data_sets[key].values())) for key in list(data_sets)]
    step = 100 if use_max_percentage else max(maximums)
    return list(range(0, len(maximums) * step, step))


def custom_sort_value(val):
    switcher = {
        'immer': 12,
        'mehrmals t??glich': 11,
        't??glich': 10,
        'mehrmals die Woche': 8,
        'h??ufig': 7,
        'einmal die Woche': 5,
        'manchmal': 4,
        'seltener': 3,
        'selten': 2,
        'nie': 1,
        'wei?? nicht': 0,
    }
    return switcher.get(val, val)


def calculate_normalized(data_sets, xs_occurrence, use_max_percentage):
    if use_max_percentage:
        maximum = max([max(list(data_sets[key].values())) / xs_occurrence[key] for key in list(data_sets)])
        for data_set_key in data_sets:
            for y_key in data_sets[data_set_key]:
                y_percentage = data_sets[data_set_key][y_key] / xs_occurrence[data_set_key]
                data_sets[data_set_key][y_key] = (
                    data_sets[data_set_key][y_key], 100 * y_percentage / maximum)
    else:
        maximum = max([max(list(data_sets[key].values())) for key in list(data_sets)])
        for data_set_key in data_sets:
            data_set_max = max(list(data_sets[data_set_key].values()))
            for y_key in data_sets[data_set_key]:
                data_sets[data_set_key][y_key] = (
                    data_sets[data_set_key][y_key], data_sets[data_set_key][y_key] * maximum / data_set_max)


def plot_charts(results, x_axis_id, y_axis_id):
    key_x_axis = get_key(x_axis_id, results[0])
    key_y_axis = get_key(y_axis_id, results[0])
    data_sets, xs_occurrence, unsorted_ys = generate_data_sets(key_x_axis, key_y_axis, results)
    calculate_normalized(data_sets, xs_occurrence, True)
    x_locations = get_x_locations(data_sets, True)

    xs = sorted(list(data_sets), key=custom_sort_value)
    for sort_y in [False, True]:
        if sort_y:
            ys = sorted(list(unsorted_ys), key=lambda y: unsorted_ys[y])
        else:
            ys = sorted(list(unsorted_ys), key=custom_sort_value)
        bin_edges = list(range(len(ys)))

        px = 1 / plt.rcParams['figure.dpi']
        fig, ax = plt.subplots(figsize=(1366 * px, 768 * px))
        fig.canvas.manager.set_window_title(
            '_'.join([x_axis_id, y_axis_id, 'sorted_by_occurrence' if sort_y else 'custom_sorted']))

        for x_location, data_set_key in zip(x_locations, xs):
            binned_data = [data_sets[data_set_key][y][1] if y in data_sets[data_set_key] else 0 for y in ys]
            binned_data_text = [
                str(round(100 * data_sets[data_set_key][y][0] / xs_occurrence[data_set_key], 1)) + '% (' + str(
                    data_sets[data_set_key][y][0]) + '/' + str(xs_occurrence[data_set_key]) + ')' if y in data_sets[
                    data_set_key] else '' for y in ys]
            lefts = [x_location - 0.5 * bd for bd in binned_data]
            bars = ax.barh(bin_edges, binned_data, left=lefts, height=1)
            for bar in bars:
                ax.text(bar.get_x() + bar.get_width() / 2,
                        bar.get_y() + .5,
                        binned_data_text.pop(0),
                        ha='center',
                        va='center',
                        weight='bold')

        ax.set_xticks(x_locations)
        ax.set_xticklabels(xs, wrap=True)

        ax.set_yticks(bin_edges)
        ax.set_yticklabels(ys, wrap=True)

        ax.set_xlabel(key_x_axis, wrap=True)
        ax.set_ylabel(key_y_axis, wrap=True)

        plt.tight_layout()
        created_file_name = '_'.join(
            [x_axis_id, y_axis_id, 'sorted_by_occurrence' if sort_y else 'custom_sorted']) + '.png'
        plt.savefig(created_file_name)
        print('Saved as ' + created_file_name)
        fig.clf()
        plt.close()
        del bin_edges, binned_data, binned_data_text
    del data_sets
    gc.collect()


def print_all_words(csv_file, question_id):
    results = list(create_dict(csv_file).values())
    question_key = get_key(question_id, results[0])
    text = ' '.join([word for words in [result[question_key].split(';') for result in results] for word in words])
    word_cloud = WordCloud(width=1920, height=1080).generate(text)

    fig = plt.figure()
    fig.set_size_inches(16, 9)
    fig.canvas.manager.set_window_title('_'.join(['wc', question_id]))

    plt.imshow(word_cloud, interpolation='bilinear')
    plt.axis("off")
    plt.tight_layout(pad=0)
    plt.savefig('_'.join(['wc', question_id]) + '.png')


def filter_csv(csv_file):
    results = create_dict(csv_file)
    with open('filtered_' + csv_file, 'x', newline='') as filtered_csvfile:
        fieldnames = ['Timestamp'] + list(list(results.values())[0].keys())
        writer = csv.DictWriter(filtered_csvfile, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for timestamp, result in results.items():
            writer.writerow({'Timestamp': timestamp, **result})


if __name__ == '__main__':
    operation = input('Choose operation (plot|word_cloud|plot_all) --> ')

    if operation == 'plot':
        x_axis_id = input('Choose X-Axis question identifier --> ')
        y_axis_id = input('Choose Y-Axis question identifier --> ')
        plot_charts(list(create_dict(sys.argv[1]).values()), x_axis_id, y_axis_id)

    if operation == 'word_cloud':
        identifier = input('Choose question identifier --> ')
        print_all_words(sys.argv[1], identifier)

    if operation == 'plot_all':
        results = list(create_dict(sys.argv[1]).values())
        all_questions = list(results[0].keys())
        all_keys = list(map(lambda question: question.split('.')[0], all_questions))
        for x, y in itertools.product(all_keys, all_keys):
            plot_charts(results, x, y)
        dirname = str(datetime.datetime.now()).split('.')[0]
        this_path = pathlib.Path().absolute()
        target_dir = os.path.join(this_path, dirname)
        os.mkdir(target_dir)
        for dir_or_file in os.listdir(this_path):
            if dir_or_file.endswith('.png'):
                shutil.move(os.path.join(this_path, dir_or_file), target_dir)
        shutil.make_archive(target_dir, 'zip', target_dir)
        shutil.rmtree(target_dir)

    if operation == 'filter':
        filter_csv(sys.argv[1])
