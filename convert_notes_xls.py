"""
Convert field notes in Excel file to polyline format
"""

import fiona
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from itertools import product, tee
from shapely.geometry import shape, LineString, MultiLineString, MultiPoint, Point
from shapely.ops import linemerge, nearest_points, snap, split


COLUMNS = ['Waypoint/location', 'lat', 'lon', 
           'ele', 'time', 'name', 
           'driving direction', 'bank L/R', 'original perma ID',
           'original notes']

RENAMED_COLUMNS = ['WP', 'lat', 'lon', 
                   'elev', 'timestamp', 'name',
                   'direction', 'bank', 'permafrost',
                   'notes']


def pairwise(iterable):
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)


def process_centerline(centerline, direction, bank):
    base = 'split/KY18_permafrost_{}_{}.shp'
    filename = base.format(direction, bank)
    gdf = gpd.read_file(filename)
    gdf = snap_to_nearest(gdf, centerline)

    line_gdf = assign_point_observations(gdf, centerline)
    line_gdf = propagate_observations(line_gdf, 'permafrost', direction[0])

    out_filename = filename.replace('permafrost', 'centerline')

    keep = list(line_gdf.columns)
    geoms = ['geometry_left', 'geometry_right', 'index_right']
    keep = [col for col in keep if col not in geoms]
    line_gdf = line_gdf[keep]
    
    line_gdf = gpd.GeoDataFrame(line_gdf)
    line_gdf.to_file(out_filename)


def process_file(filename):
    gdf = load_field_notes(filename)
    gdf = delete_nodata_points(gdf)
    gdf = standardize_uncertain_observations(gdf)
    
    upriver, downriver = separate_by_direction(gdf)
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


def lines_to_points(lines):
    points = []
    for line in lines:
        for p in line.coords:
            points.append(p)
    return MultiPoint(points)


def separate_by_direction(gdf):
    up = gdf.direction == 'u'
    down = gdf.direction == 'd'
    return gdf[up], gdf[down]


def separate_by_bank(gdf):
    left = gdf.bank == 'L'
    right = gdf.bank == 'R'
    return gdf[left], gdf[right]

def assign_point_observations(gdf, line):
    lines = [LineString([p1, p2]) for p1, p2 in pairwise(line['coordinates'])]

    geometry = [f for f in lines]
    lines_gdf = gpd.GeoDataFrame(geometry=geometry)

    out = gpd.sjoin(lines_gdf, gdf, how='left')
    out['geometry'] = out.geometry_left
    out = out.fillna('')
    out = gpd.GeoDataFrame(out)
    
    return out 


def propagate_observations(gdf, col, direction):
    if direction == 'd':
        rows = list(gdf.iterrows())
        for i, r in rows[:-1]:
            if gdf.iloc[i+1][col] == '':
                gdf.at[i+1, col] = r[col]
    elif direction == 'u':
        rows = list(gdf.iterrows())[::-1]
        for i, r in rows[:-1]:
            if gdf.iloc[i-1][col] == '':
                gdf.at[i-1, col] = r[col]
    gdf = gpd.GeoDataFrame(gdf)

    return gdf


def snap_to_nearest(gdf, line):
    points= MultiPoint([p for p in line['coordinates']])
    
    snapped = [nearest_points(points, p)[0] for p in gdf.geometry] 

    gdf = gdf.assign(snapped=snapped)
    gdf = gdf.set_geometry('snapped')

    return gdf


# XXX: This method fails to split correctly due to a floating point issue
# in shapely.ops.split
def split_centerline(gdf, line):
    lines = [LineString([p1, p2]) for p1, p2 in pairwise(line['coordinates'])]
    lines_gdf = gpd.GeoDataFrame(geometry=lines)
    split_lines = linemerge(lines_gdf.geometry.unary_union)

    gdf = snap_to_nearest(gdf, line)
    points = gdf.geometry.unary_union
    split_lines = split(split_lines, points)

    index = np.arange(len(split_lines))
    geometry = [f for f in split_lines]
    lines_gdf = gpd.GeoDataFrame(geometry=geometry)

    return lines_gdf


def standardize_uncertain_observations(gdf):
    mask = (gdf.permafrost.values != 'Y') & (gdf.permafrost.values != 'N')
    gdf['permafrost'] = gdf['permafrost'].where(~mask, other='U')
    return gdf


if __name__ == "__main__":
    filename = 'data/KY18_PermafrostBankIDs.xlsx'
    centerline_filename = 'data/KY_centerline_072018.shp'

    process_file(filename)

    c = fiona.open(centerline_filename)[0]
    centerline = c['geometry']

    directions = ['upriver', 'downriver']
    banks = ['left', 'right']

    for d, b in product(directions, banks):
        process_centerline(centerline, d, b) 
