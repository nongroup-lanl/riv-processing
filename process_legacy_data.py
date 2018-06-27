"""
Script to compare results with Ucayali classifications and channel masks
"""

import os
import rasterio
import numpy as np
from scipy.io import loadmat


IMAGERY_PATH = '/Users/rmsare/data/Ucayali/images/'
MASK_PATH = '/Users/rmsare/data/Ucayali/masks/'


def get_raster_profile(directory):
    region_name = directory.split('/')[-1]
    filename = os.path.join(directory, 'base_' + region_name + '_1.tif')
    with rasterio.open(filename) as r:
        profile = r.profile
        profile.update(count=1)
    return profile

def read_data(filename, shape):
    struct = loadmat(filename)
    data = np.array(struct['cmap'])
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
    
    files = os.listdir(directory)
    files = [f for f in files if '.mat' in f and f[0] == 'C']
    for f in files:
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
