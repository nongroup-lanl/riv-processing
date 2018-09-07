"""
Utilities for copying attributes between vector datasets

Example use case: retagging scraped OSM vector data
"""

import fiona
import geopandas as gpd
from collections import OrderedDict


def main(vec_filename, poly_filename):
    print('Retagging features...')
    tagged_filename = retag_features(vec_filename)
    print('Naming polygons...')
    named = name_polygons(poly_filename, tagged_filename)
    named = named[named['name'] != 'NA']
    print('Merging polygons...')
    # named = named.drop_duplicates(subset='OBJECTID')
    out = named.dissolve(by='name', as_index=False)
    print('Writing results...')
    out_filename = poly_filename[:-4] + '_names_merged.shp'
    out.to_file(out_filename)


def calculate_intersection_scores(poly_filename, vec_filename):
    pass


def name_polygons(poly_filename, named_filename):
    polys = gpd.read_file(poly_filename)
    named = gpd.read_file(named_filename)
    out = gpd.sjoin(polys, named, how='inner')

    columns = list(polys.columns)
    columns.append('name')
    out = out[columns]

    return out


def parse_tag(tag):
    tags = tag.split(',')
    props = {'name': 'NA'}
    for t in tags:
        try:
            k, v = t.split('=>')
            k = k.replace('"', '')
            v = v.replace('"', '')
            if k == 'name':
                props[k] = v
        except ValueError:
            pass
    return props


def retag_features(filename):
    src = fiona.open(filename)
    schema = src.schema
    props = OrderedDict([('osm_id', 'str:254'), ('name', 'str:254')])
    schema.update(properties=props)

    records = []
    for x in list(src):
        props = x['properties']
        tag = x['properties']['other_tags']
        new_tags = parse_tag(tag)
        props.pop('other_tags')
        props.update(**new_tags)
        x['properties'] = props
        records.append(x)

    out_filename = filename[:-4] + '_retag.shp'
    with fiona.open(out_filename,
                    'w',
                    driver=src.driver,
                    crs=src.crs,
                    schema=schema) as out:
        for rec in records:
            out.write(rec)

    return out_filename


if __name__ == "__main__":
    vec_filename = 'data/South_America_split.shp'
    poly_filename = 'data/rivbuff.shp'

    main(vec_filename, poly_filename)
