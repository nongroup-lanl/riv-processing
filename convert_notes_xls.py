"""
Convert field notes in Excel file to polyline format
"""

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point


COLUMNS = ['Waypoint/location', 'lat', 'lon', 
           'ele', 'time', 'name', 
           'driving direction', 'bank L/R', 'original perma ID',
           'original notes']
RENAMED_COLUMNS = ['WP', 'lat', 'lon', 
                   'elev', 'timestamp', 'name',
                   'direction', 'bank', 'permafrost',
                   'notes']


def process_file(filename):
    gdf = load_field_notes(filename)
    gdf = delete_nodata_points(gdf)
    gdf = standardize_uncertain_observations(gdf)
    
    upriver, downriver = separate_by_driving_direction(gdf)
    left, right = separate_by_bank(upriver)
    left.to_file('split/KY18_permafrost_upriver_left.shp')
    right.to_file('split/KY18_permafrost_upriver_right.shp')

    left, right = separate_by_bank(downriver)
    left.to_file('split/KY18_permafrost_downriver_left.shp')
    right.to_file('split/KY18_permafrost_downriver_right.shp')


def load_field_notes(filename):
    df = pd.read_excel(filename)
    df = df[COLUMNS]
    df.columns = RENAMED_COLUMNS
    points = [Point(xy) for xy in zip(df.lon, df.lat)]
    gdf = gpd.GeoDataFrame(geometry=points, data=df)
    return gdf


def delete_nodata_points(gdf):
    keep = ~np.isnan(gdf.geometry[::].x) & ~np.isnan(gdf.geometry[::].y)
    return gdf[keep]


def separate_by_driving_direction(gdf):
    up = gdf.direction == 'u'
    down = gdf.direction == 'd'
    return gdf[up], gdf[down]


def separate_by_bank(gdf):
    left = gdf.bank == 'L'
    right = gdf.bank == 'R'
    return gdf[left], gdf[right]


def standardize_uncertain_observations(gdf):
    mask = (gdf.permafrost.values != 'Y') & (gdf.permafrost.values != 'N')
    gdf['permafrost'] = gdf['permafrost'].where(~mask, other='U')
    return gdf


if __name__ == "__main__":
    filename = 'data/KY18_PermafrostBankIDs.xlsx'
    process_file(filename)
