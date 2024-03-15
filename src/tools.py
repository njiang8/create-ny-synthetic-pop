import pandas as pd
import numpy as np
import geopandas as gpd
from shapely import Point
from math import sin, cos, sqrt, atan2, radians
from sklearn.preprocessing import normalize

#==================
# 1 Preprocessing
#==================
def number_of_wp_old(data, od, cbp):
    """
    calculate number of workplaces for each tract
    wp_tract = wp_cty * (tract_employed / county_employed)
    """
    try:
        tract_number = data.GEOID10#.astype(int)
        county_number = tract_number[:5]
        #print("the tract number is:", tract_number)
        #print("+++++++")
        #print("the county number is:", county_number)
        #employed
        #tract employed
        tract_employed_df = od[['work','S000']].groupby('work').sum().reset_index()
        tract_employed_df = tract_employed_df.astype({"work": str})

        #print(tract_employed_df.head())
        #print(tract_employed_df.work.unique())

        tract_employed = tract_employed_df.loc[tract_employed_df.work == tract_number, 'S000'].values[0]

        #print(tract_employed)
        #county employed
        tract_employed_df['county'] = tract_employed_df.work.astype(str).str[:5]
        #print(tract_employed_df.head())
        county_employed_df = tract_employed_df[['county','S000']].groupby('county').sum().reset_index()
        #print(county_employed_df.head())

        #county wrk place establishment number
        cbp['county'] = cbp.GEO_ID.astype(str).str[-5:]
        cbp = cbp[cbp.county == county_number].copy()#.groupby('county').sum().reset_index()
        cbp = cbp.astype({"ESTAB": int})
        #print(cbp)
        county_wrk_count = cbp.groupby('county').sum().reset_index()
        county_df = county_employed_df.merge(county_wrk_count, on="county", how="inner")
        #print(county_df)

        wp_cty = county_df.loc[county_df.county == county_number, 'ESTAB'].values[0]
        county_employed = county_df.loc[county_df.county == county_number, 'S000'].values[0]
        #print (wp_cty)
        #print(county_employed)

        return int(wp_cty * (tract_employed / county_employed))
    except:
        return 0



def number_of_wp(data, od, cbp):
    """
    calculate number of workplaces for each tract
    wp_tract = wp_cty * (tract_employed / county_employed)
    """
    try:
        """
        calculate number of workplaces for each tract
        wp_tract = wp_cty * (tract_employed / county_employed) #commute peaple amout
        """

        #print("++++++++++")
        # use "od data" to get number of jobs in each census tract
        # and number of jobs in each county
        tract_number = data.GEOID10#.astype(int)
        tract_jobs_df = od[['work','S000']].groupby('work').sum().reset_index()
        tract_jobs_df = tract_jobs_df.astype({"work": str})
        tract_jobs_number = int(tract_jobs_df.loc[tract_jobs_df.work == tract_number, 'S000'].values[0]) # total number of job in each tract
        #print("Tract", tract_number, "has", tract_jobs_number, "jobs")

        #county total number of job
        county_number = tract_number[:5]
        tract_jobs_df['county'] = tract_jobs_df.work.astype(str).str[:5]
        county_job_df = tract_jobs_df[['county','S000']].groupby('county').sum().reset_index()
        county_job_number = int(county_job_df.S000[0])
        #print("County", county_number, "has", county_job_number, "jobs")
        #print("++++++++++")

        #use company number
        #county wrk place establishment number
        #cbp['county'] = cbp.GEO_ID.astype(str).str[-5:]
        #print("==========")
        campany_df = cbp.loc[:,['county', 'NAME', 'ESTAB']]
        county_campany_number = int(campany_df[campany_df.county == county_number].ESTAB.values[0])
        #print("County", county_number, "has", county_campany_number, "company")

        tract_wp_number = int(county_campany_number * (tract_jobs_number / county_job_number))

        #print("Tract",  tract_number, "has", tract_wp_number, "companys")
        return tract_wp_number
    except:
        print(tract_number, "has issue")
        return 0
def wp_proba(x):
    """
    probability of an employee working in that workplace is lognormal:
    http://www.haas.berkeley.edu/faculty/pdf/wallace_dynamics.pdf
    """
    if x == 0: return np.zeros(0)
    b = np.random.lognormal(mean=2,size=x).reshape(-1, 1)
    return np.sort(normalize(b,norm='l1',axis=0).ravel())



#==================
# 2 Verification
#==================

def get_errors(tract,people):
    """Percentage errors"""
    err = {}
    #portion = tract.geometry.area / tract.Shape_Area # what portion of the tract is included
    #senior_actual = int(tract.DP0150001 * portion) # Households with individuals 65 years and over
    senior_actual = int(tract.DP0150001)
    #minor_actual = int(tract.DP0140001 * portion) # Households with individuals under 18 years
    minor_actual = int(tract.DP0140001)
    #err['tract'] = tract.name
    err['population'] = tract.DP0010001
    err['in_gq'] = tract.DP0120014
    avg_synthetic_family = people[people.htype<6].groupby('hhold').size().mean()
    err['avg_family'] = 100*(avg_synthetic_family - tract.DP0170001) / tract.DP0170001
    err['avg_hh'] = 100*(people[people.htype!=11].groupby('hhold').size().mean() - tract.DP0160001) / tract.DP0160001
    err['senior_hh'] = 100*(people[people.age>=65].hhold.nunique() - senior_actual) / senior_actual
    err['minor_hh'] = 100*(people[people.age<18].hhold.nunique() - minor_actual) / minor_actual
    return pd.Series(err,name=tract.name)

#==================
# 3 After Analysis
#==================

def CollectResultsPop(results, X):
    if X == "Pop":
        print("Population")
        temp_df = pd.DataFrame()
        for i in results:
            temp_df = pd.concat([temp_df, i])

        temp_df = temp_df.reset_index().drop(['code'], axis=1)
        temp_df.rename(columns={temp_df.columns[0]: 'id'}, inplace=True)
        print(temp_df.head())

        final_df = gpd.GeoDataFrame(temp_df, geometry='geometry')
        final_df['long'] = final_df['geometry'].x
        final_df['lat'] = final_df['geometry'].y
        print("=====GP Data=====")
        print(final_df.head())
        return final_df  # return pandas df with geometry

    if X == "Work":
        print("Work")
        wp = pd.DataFrame()
        for j in results:
            wp = pd.concat([wp, j])
            # wp = wp.append(j, ignore_index=True)
        wp = wp.reset_index()
        wp.rename(columns={wp.columns[0]: 'wp', wp.columns[1]: 'geometry'}, inplace=True)

        print("=====Work Data=====")
        print(wp.head())
        return wp

    else:
        # Errors
        print("Error")
        er = pd.DataFrame()
        for e in results:
            # print(e)
            er = pd.concat([er, e])
        # print(er.head())
        return er



from shapely import Point
def pop_to_geo_df(data):
    #lat long, lat:40.xxxx, long: -78.xxxx
    #data['geometry'] = data.apply(lambda x: Point((float(x.lat), float(x.long))), axis=1)#combine lat and lon column to a shapely Point() object
    data['geometry'] = data.apply(lambda x: Point((float(x.long), float(x.lat))),
                                  axis=1)  # combine lat and lon column to a shapely Point() object
    gdf = gpd.GeoDataFrame(data, geometry='geometry')
    #WGS84 Coordinate System
    #gdf.crs = {'init' :'epsg:4326'}
    gdf = gdf.set_crs("EPSG:4326")
    return gdf


# From Geo Panda DataFram, change the data to spatial data
def edu_to_gpd(data):
    from shapely.geometry import Point
    # combine lat and lon column to a shapely Point() object
    data['geometry'] = data.apply(lambda x: Point((float(x.LONGITUDE), float(x.LATITUDE))), axis=1)
    data = gpd.GeoDataFrame(data, geometry='geometry')
    # WGS84 Coordinate System
    data.crs = {'init': 'epsg:4326'}

    return data

def new_distance(x1, y1, x2, y2):
    # approximate radius of earth in km
    R = 6373.0

    lat1 = radians(x1)
    long1 = radians(y1)
    lat2 = radians(x2)
    long2 = radians(y2)

    dlon = long2 - long1
    dlat = lat2 - lat1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = R * c
    return distance