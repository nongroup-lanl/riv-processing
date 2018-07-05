"""
Parse filenames to make list of LANDSAT images in directory
"""

import os

from datetime import datetime


def parse_filename(filename):
    strings = filename.split('_')
    print(strings)
    platform = strings[1]
    month, day, year = strings[2:5]
    path = int(strings[5][0:3])
    row = int(strings[5][3:7])
    in_date = datetime.strptime('{} {} {}'.format(month, day, year), 
                                '%b %d %Y')
    out_date = in_date.strftime('%Y-%m-%d')
    return path, row, out_date

def process_directory(directory):
    out_filename = os.path.join(directory, 'imagelist.txt')

    files = os.listdir(directory)
    files = [f for f in files if 'an1.tif' in f and f[0] == 'C']

    with open(out_filename, 'w') as out:
        for f in files:
            path, row, date = parse_filename(f)
            out.write('{} {} {}\n'.format(path, row, date))

if __name__ == "__main__":
    base_directory = '/Users/rmsare/data/cleaned/Ucayali/images/'
    directories = os.listdir(base_directory)
    directories = [d for d in directories if d[0] != '.']
    for d in directories:
        process_directory(base_directory + d)
