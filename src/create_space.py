import pandas as pd
import geopandas as gpd
import numpy as np
from shapely import MultiLineString
from shapely import Point

# create space
#shapely geometries are not hashable, here is my hash function to check the duplicates
def hash_geom(g):
    #print("Get the lat and long of the road segment and output to tuple")
    if g.geom_type == 'MultiLineString':
        #print("MultiLineString")
        #print(g.geoms)
        cord_list = []
        for line in g.geoms:
            for lat,lon in line.coords[:]:
                #print((round(lat,6),round(lon,6)))
                cord_list.append((round(lat,6),round(lon,6)))
        #print(cord_list)
        cord_tuple = tuple(item for item in cord_list)
        #print("Tuple")
        #print(cord_tuple)
        return tuple(item for item in cord_list)
    else:
        #print("Line")
        #print(tuple((round(lat,6),round(lon,6)) for lat,lon in g.coords[:]))
        return tuple((round(lat,6),round(lon,6)) for lat,lon in g.coords[:]) #shaply older version
        #return tuple((round(lat,6),round(lon,6)) for lat,lon in g.geoms) #shapely 2.0 or later version


def create_home_location(tract, hcnt, road):
    # print("Creating House Space...")
    # create houses
    if tract.DP0120014 > 0: hcnt += 1  # people living in group quarters (not in households)

    mask = road.intersects(tract.geometry)  # get the road with in the census tract
    # home road
    hmask = mask & road.MTFCC.str.contains('S1400|S1740')  # get the home road
    hrd = road[hmask].intersection(tract.geometry)  # get the geometry of home road
    hrd = hrd[hrd.geom_type.isin(['LinearRing', 'LineString', 'MultiLineString'])]
    hrd = hrd[~hrd.apply(
        hash_geom).duplicated()]  # remove the duplicate lat and long by returning boolean Series denoting duplicate rows (using .duplicated()).

    HD = 0.0005
    houses = hrd.apply(lambda x: pd.Series([x.interpolate(seg) for seg in np.arange(HD, x.length, HD)]))
    # print(houses)
    houses = houses.unstack().dropna().reset_index(drop=True)  # flatten
    houses = houses.sample(n=hcnt, replace=True).reset_index(drop=True)
    houses.index = tract.name + 'h' + houses.index.to_series().astype(str)

    return gpd.GeoSeries(houses)


def create_work_location(tract, road):
    # from shapely import MultiLineString, Point, ops, LineString

    WD = 0.0002

    mask = road.intersects(tract.geometry)  # get the road with in the census tract
    """
        * Home Road
        S1400 Local Neighborhood Road, Rural Road, City Street
        S1740 Private Road for service vehicles (logging, oil fields, ranches, etc.) 
        * Work Road
        S1100 Primary Road
        S1200 Secondary Road
    """
    # work road
    wmask = mask & road.MTFCC.str.contains('S1200')  # S1100 Primary Road; S1200 Secondary Road,
    wrd = road[wmask].intersection(tract.geometry)  # get the geometry of work road
    wrd = wrd[wrd.geom_type.isin(['LinearRing', 'LineString', 'MultiLineString'])]
    wrd = wrd[~wrd.apply(
        hash_geom).duplicated()]  # remove the duplicate lat and long by returning boolean Series denoting duplicate rows (using .duplicated()).

    # home road
    hmask = mask & road.MTFCC.str.contains('S1400|S1740')  # get the home road
    hrd = road[hmask].intersection(tract.geometry)  # get the geometry of home road
    hrd = hrd[hrd.geom_type.isin(['LinearRing', 'LineString', 'MultiLineString'])]
    hrd = hrd[~hrd.apply(
        hash_geom).duplicated()]  # remove the duplicate lat and long by returning boolean Series denoting duplicate rows (using .duplicated()).

    wrk_point = wrd.apply(lambda x: pd.Series([x.interpolate(seg) for seg in np.arange(WD, x.length,
                                                                                       WD)]))  # Get the workplace loaction point on each road segment
    # print(wrk_point)
    # workplaces on the intersection of home roads with types S1400|S1740
    # rwps = hrd.apply(lambda x: Point(x.coords[0]) if type(x) != MultiLineString else Point(x[0].coords[0]))
    rwps = hrd.apply(lambda x: Point(x.coords[0]) if type(x) != MultiLineString else Point(x.geoms[0].coords[0]))
    # print(rwps)

    wrk_place = pd.DataFrame()
    # print(wrk_point)
    if len(wrk_point) > 0:
        temp = wrk_point.unstack().dropna().reset_index(drop=True)
        wrk_place = pd.concat([rwps, temp])
        # wrk_place = rwps.append(wrk_point.unstack().dropna().reset_index(drop=True))
    else:
        wrk_place = rwps
    wrk_place = wrk_place.sample(n=tract.WP_CNT, replace=True).reset_index(drop=True)
    wrk_place.index = tract.name + 'w' + wrk_place.index.to_series().astype(str)
    # print("workplace")
    # print(wrk_place)'

    return gpd.GeoSeries(wrk_place)