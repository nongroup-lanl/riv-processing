"""
Script to compare results with Ucayali classifications and channel masks
"""

import os
import rasterio
import numpy as np
from scipy.io import loadmat


IMAGERY_PATH = '/Users/rmsare/data/Ucayali/images/'
MASK_PATH = '/Users/rmsare/data/Ucayali/masks/'
STRUCT_FIELD_NAME = 'cmap'


def get_raster_profile(directory):
    files = os.listdir(directory)
    available_tif_files = [f for f in files if '.tif' in f]
    in_file = available_tif_files[0]
    filename = os.path.join(directory, in_file)
    with rasterio.open(filename) as r:
        profile = r.profile
        profile.update(count=1)
    return profile


def read_data(filename, shape):
    struct = loadmat(filename)
    data = np.array(struct[STRUCT_FIELD_NAME])
    data = data.reshape(shape, order='F')
    return data


def save_file_as_tiff(in_filename, profile, shape):
    out_filename = in_filename.replace('mat', 'tif')
    data = read_data(in_filename, shape)
    with rasterio.open(out_filename, 'w', **profile) as out:
        out.write(data.astype(profile['dtype']), 1)


def process_directory(directory):
    profile = get_raster_profile(directory)
    shape = (profile['height'], profile['width'])

    all_files = os.listdir(directory)
    in_files = [f for f in all_files if '.mat' in f and f[0] == 'C']
    done_files = [f for f in all_files if '.tif' in f and f[0] == 'C']
    done_files = [f.replace('tif', 'mat') for f in done_files]
    in_files = list(set(in_files) - set(done_files))

    for f in in_files:
        filename = os.path.join(directory, f)
        save_file_as_tiff(filename, profile, shape)


def main():
    directories = ['R3', 'R4', 'R5', 'R6']
    for directory in directories:
        print('Processing {}...'.format(directory))
        directory = os.path.join(IMAGERY_PATH, directory)
        process_directory(directory)


if __name__ == "__main__":
    main()
