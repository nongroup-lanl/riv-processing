"""
Convert field notes in Excel file to polyline format
"""

import fiona
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from itertools import product, tee
from shapely.geometry import shape, LineString, MultiLineString, Point
from shapely.ops import linemerge, snap, split


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
    gdf = gdf.from_file(filename)
    gdf, centerline = snap_to_centerline(gdf, centerline)
    line_gdf = split_centerline(gdf, centerline)
    line_gdf = map_observations(gdf, line_gdf)

    out_filename = filename.replace('permafrost', 'splitcenterline')
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


def map_observations(gdf, line_gdf):
    """
    
    Assumes that the waypoint number increases in the direction of travel

    For example, if waypoint 1 has a 'Y' permafrost observation, the center
    line segments between waypoints 1 and 2 will be labelled as 'Y'
    """

    # In the case of Koyukuk, the observer is travelling NE -> SW
    # if direction == 'u':
    # In the case of Koyukuk, the observer is travelling SW -> NE
    # elif direction =='d':


def delete_nodata_points(gdf):
    keep = ~np.isnan(gdf.geometry[::].x) & ~np.isnan(gdf.geometry[::].y)
    return gdf[keep]


def separate_by_direction(gdf):
    up = gdf.direction == 'u'
    down = gdf.direction == 'd'
    return gdf[up], gdf[down]


def separate_by_bank(gdf):
    left = gdf.bank == 'L'
    right = gdf.bank == 'R'
    return gdf[left], gdf[right]


def snap_to_centerline(gdf, line):
    lines = [LineString([p1, p2]) for p1, p2 in pairwise(line['coordinates'])]
    lines_gdf = gpd.GeoDataFrame(geometry=lines)
    lines = lines_gdf.geometry.unary_union
    
    snapped = [lines.interpolate(lines.project(p)) for p in gdf.geometry] 

    gdf = gdf.assign(snapped=snapped)
    gdf = gdf.set_geometry('snapped')

    return gdf


def split_centerline(gdf, line):
    lines = [LineString([p1, p2]) for p1, p2 in pairwise(line['coordinates'])]
    lines_gdf = gpd.GeoDataFrame(geometry=lines)
    split_lines = linemerge(lines_gdf.geometry.unary_union)

    points = gdf.geometry.unary_union
    points = snap(points, split_lines, 0.0001)
    split_lines = split(split_lines, points)
    split_lines = MultiLineString(split_lines)

    index = np.arange(len(split_lines))
    data = {'index' : index, 'permafrost' : len(index) * ['']}
    geometry = [f for f in split_lines]
    lines_gdf = gpd.GeoDataFrame(data=data, 
                                 geometry=geometry,
                                 columns=['index', 'permafrost'])

    lines_gdf.plot(linewidth=2, cmap='Set1', zorder=0)
    gdf.plot(marker='^', zorder=1, ax=plt.gca())
    plt.show()

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
