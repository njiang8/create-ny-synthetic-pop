import pandas as pd
import geopandas as gpd
import numpy as np
import random
from src.tools import new_distance

#Assign Work
def assign_workplaces(tract, people, od, dp):
    #print("++++++++++Assigning Work+++++++++++")
    """
    if the destination tract of a worker is not in our DP dataset
    then we assign his wp to 'DTIDw', otherwise 'DTIDw#'

    the actual size distribution of establishments is lognormal
    https://www.princeton.edu/~erossi/fsdae.pdf
    """
    # destination tracts and numbers
    # print("tract number is",tract.name, type(tract.name))
    #print("people", people)/
    #print(tract.name)
    #print(od[od['home'] == tract.name])

    tract_with_number_jobs = od[od['home'] == tract.name].set_index('work').S000 #set work index, used to be td
    tract_with_number_jobs = tract_with_number_jobs.apply(np.ceil).astype(int)  # from this tract to others, used to be td

    # 58.5%: US population (16+) - employment rate
    #https://data.bls.gov/timeseries/LNS12300000
    #print(len(people))
    #print("work people", )
    #print("there are jobs:", tract_with_number_jobs.sum())
    if tract_with_number_jobs.sum() > len(people[people.age >= 18]):
        employed = people[people.age >= 18].index  # get the employed
        dtract = pd.Series(np.repeat(tract_with_number_jobs.index.values, tract_with_number_jobs.values)).sample(
            len(people[people.age >= 18])
        )  # get the destination tract
    else:
        employed = people[people.age >= 18].sample(tract_with_number_jobs.sum()).index  # get the employed
        dtract = pd.Series(
            np.repeat(tract_with_number_jobs.index.values, tract_with_number_jobs.values)
        )  # get the destination tract
        # if 'wp' in people.columns: people.drop('wp',axis=1,inplace=True)
    people.loc[employed, "wp"] = dtract.apply(
        lambda x: x
                  + "w"
                  + str(np.random.choice(dp.loc[x, "WP_CNT"], p=dp.loc[x, "WP_PROBA"]))
        if x in dp.index
        else x + "w"
    ).values


#Assign EDU Site
def join_edu_data(data1, data2, col_name, type):
    if type == "School":
        #spatial join
        sjdf = gpd.sjoin(data1, data2, how = "inner", op = 'intersects')

        #Create new column with the valus of census tract ID
        #school
        sjdf['temp'] = sjdf.apply(lambda x:'%ss' % (x['GEOID10']),axis=1)
        #daycare
        #sjdf['temp'] = sjdf.apply(lambda x:'%sd' % (x['GEOID10']),axis=1)

        #create a column to count the number of education site within the census tract
        sjdf['count'] = 0

        #group by census tract number
        census_group = sjdf.groupby(sjdf['GEOID10'])

        #create a dataframe to hold the data
        wp = pd.DataFrame()

        #loop through each group and get count
        for i,j in census_group:
            group = pd.DataFrame(j).reset_index().drop('index',axis=1)
            for k in range (0,len(group)):
                group.loc[k,'count'] = k
                #print(group)
            #wp = wp.append(group,ignore_index = True)
            wp = pd.concat([wp, group])#wp.append(group,ignore_index = True)

        wp[col_name] = wp.apply(lambda x:'%s%s' % (x['temp'],x['count']),axis=1)

        return wp.reset_index(drop= True)

    if (type == "Daycare"):
        #spatial join
        sjdf = gpd.sjoin(data1, data2, how = "inner", op = 'intersects')

        #Create new column with the valus of census tract ID
        #daycare
        sjdf['temp'] = sjdf.apply(lambda x:'%sd' % (x['GEOID10']),axis=1)

        #create a column to count the number of education site within the census tract
        sjdf['count'] = 0

        #group by census tract number
        census_group = sjdf.groupby(sjdf['GEOID10'])

        #create a dataframe to hold the data
        wp = pd.DataFrame()

        #loop through each group and get count
        for i,j in census_group:
            group = pd.DataFrame(j).reset_index().drop('index',axis=1)
            for k in range (0,len(group)):
                group.loc[k,'count'] = k
                #print(group)
            #wp = wp.append(group,ignore_index = True)
            wp = pd.concat([wp, group])#wp.append(group,ignore_index = True)

        wp[col_name] = wp.apply(lambda x:'%s%d' % (x['temp'],x['count']),axis=1)

        return wp.reset_index(drop= True)

def assign_school(data, school, daycare):

    #if pd.isnull(test.loc[i,'wp']):
    if pd.isnull(data.wp):
        #print("wp is null")
        if data.age > 17:
            #print("work from home")
            return data.hhold
        #indi_buffer = data.geometry.buffer(0.08)
        #print(type(indi_buffer))
        #Assign edu site based on age
        elif data.age >= 4 and data.age <= 17:
            #print("school")
            return find_eduid(data.lat, data.long, data.geometry, school)

        elif data.age < 4:
            #print("daycare")
            return find_eduid(data.lat, data.long, data.geometry, daycare)

    else:
        return data.wp


def find_eduid (x, y, position, edu_site):
    #TODO go to the schools within the same tract if no school found, select one of schools from neightbor tract
    buff = position.buffer(0.08)
    s_in = edu_site[edu_site.intersects(buff)].copy()

    if len(s_in) == 0:
        #TODO add a function reduce reduncency
        buff = position.buffer(0.2)
        s_in = edu_site[edu_site.intersects(buff)].copy()

        #Intersect Road Point Lat list
        sx = s_in.loc[:,'LATITUDE'].tolist()
        #Intersect Road Point Long list
        sy = s_in.loc[:, 'LONGITUDE'].tolist()

        #Calculate Distance between the point and intersected road points
        dist = [] #distance list
        for j in range(0, len(s_in)):
            d = new_distance(x, y, sx[j], sy[j])
            dist.append(d)

        #school ID list
        sid = s_in.loc[:,'SchID']

        #Create DF to hold the School ID an the their distance to Kids
        df_sch_in = pd.DataFrame({'SchID': sid, 'Dist':dist}).sort_values(by='Dist')#.reset_index(drop=True)
        #print("++++")
        #print(df_sch_in)

        sch_AgeDistAccept = [s for s in df_sch_in.index if edu_site.loc[s, 'current'] < edu_site.loc[s, 'ENROLLMENT']]
        #print(sch_AgeDistAccept)

        if sch_AgeDistAccept != []:
            j = sch_AgeDistAccept[0]
            #print(df_sch_in.loc[j, 'SchID'])
            return df_sch_in.loc[j, 'SchID']
        else:
            return random.choice(sid)

        school.loc[sch_id, 'current'] += 1

    else:
        # Intersect Road Point Lat list
        sx = s_in.loc[:, 'LATITUDE'].tolist()
        # Intersect Road Point Long list
        sy = s_in.loc[:, 'LONGITUDE'].tolist()

        # Calculate Distance between the point and intersected road points
        dist = []  # distance list
        for j in range(0, len(s_in)):
            d = new_distance(x, y, sx[j], sy[j])
            dist.append(d)

        # school ID list
        sid = s_in.loc[:, 'SchID']

        # Create DF to hold the School ID an the their distance to Kids
        df_sch_in = pd.DataFrame({'SchID': sid, 'Dist': dist}).sort_values(by='Dist')  # .reset_index(drop=True)
        # print("++++")
        # print(df_sch_in)

        sch_AgeDistAccept = [s for s in df_sch_in.index if edu_site.loc[s, 'current'] < edu_site.loc[s, 'ENROLLMENT']]
        # print(sch_AgeDistAccept)

        if sch_AgeDistAccept != []:
            j = sch_AgeDistAccept[0]
            # print(df_sch_in.loc[j, 'SchID'])
            return df_sch_in.loc[j, 'SchID']
        else:
            return random.choice(sid)

        school.loc[sch_id, 'current'] += 1