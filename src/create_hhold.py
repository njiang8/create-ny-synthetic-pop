import pandas as pd
import numpy as np
from itertools import chain



def create_households(tract, people):
    # print("++++++++++Create Hhold+++++++++++")
    # get the amount of each household type (GOOD)
    hh_cnt = get_hh_cnts(tract)
    # print(hh_cnt)

    # create a empty df to hold indivadual hhold
    hholds = pd.DataFrame()

    # create a column to in hhold to hold the households types info
    hholds['htype'] = np.repeat(hh_cnt.index, hh_cnt)
    # print(hholds[hholds.htype == 6])
    # hholds = hholds[hholds.htype != 6].sort_values('htype',ascending=False).concat(hholds[hholds.htype == 6])
    # hholds = hholds[hholds.htype != 6].sort_values('htype',ascending=False).append(hholds[hholds.htype == 6])

    temp1 = hholds[hholds.htype != 6].sort_values('htype', ascending=False)
    # print(temp1)
    temp2 = hholds[hholds.htype == 6]
    # print(temp2)
    hholds = pd.concat([temp1, temp2])  # .sort_values('htype',ascending=False)
    # print(hholds)
    # create member for each households;
    # for remaining populating, populate them in households as relatives and those living in group quarter (non-household)
    populate_households(tract, people, hholds)


# Get the number of household under different household types
def get_hh_cnts(tract):
    """
    Eleven household types:
    0         h&w (no<18)
    1      h&w&ch (ch<18)
    2        male (no<18)
    3        male (ch<18)
    4      female (no<18)
    5      female (ch<18)
    6     nonfamily group
    7       lone male <65
    8       lone male >65
    9      lone female<65
    10     lone female>65
    """

    householdConstraints = (tract[150:166]).astype(int)  # HOUSEHOLDS BY TYPE
    # print(householdConstraints.head())
    hh_cnt = pd.Series(np.zeros(11), dtype=int)  # 11 household types (group quarters are not household)

    # husband/wife families
    # husband-wife family DP0130004 - DP0130005: Husband-wife family - With own children under 18 years
    hh_cnt[0] = householdConstraints[4] - householdConstraints[5]
    # husband-wife family DP0130005, OWN CHILDREN < 18
    hh_cnt[1] = householdConstraints[5]

    # male householders
    # single male householder DP0130006 - DP0130007: Male householder, no wife present - Male householder, no wife present
    hh_cnt[2] = householdConstraints[6] - householdConstraints[7]
    # single male householder DP0130007, OWN CHILDREN < 18
    hh_cnt[3] = householdConstraints[7]

    # female householders
    # single female householder DP0130008 - DP0130009: Female householder, no husband present - With own children under 18 years

    # single female householder DP0130009, OWN CHILDREN < 18
    hh_cnt[4] = householdConstraints[8] - householdConstraints[9]  # single female householder
    hh_cnt[5] = householdConstraints[9]  # single female householder, OWN CHILDREN < 18

    # nonfamily householder
    hh_cnt[6] = householdConstraints[10] - householdConstraints[11]  # nonfamily group living
    hh_cnt[7] = householdConstraints[12] - householdConstraints[13]  # lone male < 65
    hh_cnt[8] = householdConstraints[13]  # lone male >= 65
    hh_cnt[9] = householdConstraints[14] - householdConstraints[15]  # lone female < 65
    hh_cnt[10] = householdConstraints[15]  # lone female >= 65

    return hh_cnt


# Generate household members based on hhold type
def gen_households(hh_type, people, mask):
    """
    Eleven household types:
    0         h&w (no<18) husband and wife no kids
    1      h&w&ch (ch<18) husband and wife with kids
    2        male (no<18) male with no kids (wife not present)
    3        male (ch<18) male with kids (wife not present)
    4      female (no<18) female with no kids (husband not present)
    5      female (ch<18) female with kids (husband not present)
    6     nonfamily group
    7       lone male <65 male younger than 65 lives alone
    8       lone male >65 male older than 65 lives alone
    9      lone female<65 female younger than 65 lives alone
    10     lone female>65 female older than 65 lives alone
    """
    # create a list to hold household member
    members = []

    # first, create household head, 11 types
    # age range of the householder for each household type  (the range comes from dp age range above)
    head_ranges = [
        range(4, 18), range(4, 14), range(4, 18), range(4, 14), range(22, 36), range(22, 30),
        # 6
        chain(range(4, 18), range(21, 36)),
        range(4, 13), range(13, 18), range(21, 31), range(31, 36)
    ]

    '''
        meaning of the head_ranges: 
        [(15,99)/m/hh0,(20,70)/m/hh1,(15,99)/m/hh2,(20,70)/m/hh3,(15,99)/f/hh0,(20,70)/f/hh1,
        (15,99)/f/hh4,(15,65)/f/hh5,(20,65)/m/hh7,(65,99)/m/hh8,(15,65)/f/hh9,(65,99)/f/hh10]

        head_sex:
        [(1'm'),(2'm'),(3'm'),(4'm'),(5'f'),(6'f'),(7'f'),(8'f'),(9'm'),(10'm'),(11'f'),(12'f')]

    '''
    # add the householder
    pot = people[mask].code  # potential's age or age group

    # selcet households head
    iindex = pot[pot.isin(head_ranges[hh_type])].index[0]  # potential's age is in the range of this hh type
    # what is hh_type

    h1 = people.loc[iindex]  # age & sex of h1, what is h1

    mask[iindex] = False
    members.append(iindex)

    # if living alone then return the members
    if hh_type > 6:
        return members

    # if husband and wife, add the wife
    if hh_type in (0, 1):
        pot = people[mask].code
        if h1.code == 4:  # if husband is 20~24
            iindex = pot[pot.isin(range(h1.code + 17, h1.code + 20))].index[0]  # wife is -4~14 + husband age
        else:  # if husband is older than 20~24
            iindex = pot[pot.isin(range(h1.code + 16, h1.code + 20))].index[0]
        h2 = people.loc[iindex]  # -4 < husband.age - wife.age < 9
        mask[iindex] = False
        members.append(iindex)

    """A child includes a son or daughter by birth (biological child), a stepchild,
    or an adopted child of the householder, regardless of the child’s age or marital status.
    The category excludes sons-in-law, daughters- in-law, and foster children."""
    # household types with at least one child (18-)
    if hh_type in (1, 3, 5):
        # https://www.census.gov/hhes/families/files/graphics/FM-3.pdf
        if hh_type == 1:
            num_of_child = max(1, abs(int(np.random.normal(2))))  # gaussian touch
        elif hh_type == 3:
            num_of_child = max(1, abs(int(np.random.normal(1.6))))  # gaussian touch
        elif hh_type == 5:
            num_of_child = max(1, abs(int(np.random.normal(1.8))))  # gaussian touch

        pot = people[mask]
        if hh_type == 1:
            iindices = pot[(pot.age < 18) & (45 > h2.age - pot.age)].index[:num_of_child]
        else:  # father (mother) and child age difference not to exceed 50 (40)
            age_diff = 45 if hh_type == 5 else 55
            iindices = pot[(pot.age < 18) & (age_diff > h1.age - pot.age)].index[:num_of_child]
        for i in iindices:
            child = people.loc[i]
            mask[i] = False
            members.append(i)

    # if nonfamily group then either friends or unmarried couples
    if hh_type == 6:
        pot = people[mask].code
        num_of_friends = max(1, abs(int(np.random.normal(1.3))))  # gaussian touch
        iindices = pot[pot.isin(range(h1.code - 2, h1.code + 3))].index[:num_of_friends]
        for i in iindices:
            friend = people.loc[i]
            mask[i] = False
            members.append(i)

    return members


def populate_households(tract, people, hholds):
    # What is the mask for?
    mask = pd.Series(True, index=people.index)  # [True]*len(people)

    hholds['members'] = hholds.htype.apply(gen_households, args=(people, mask,))

    """The seven types of group quarters are categorized as institutional group quarters
    (correctional facilities for adults, juvenile facilities, nursing facilities/skilled-nursing facilities,
    and other institutional facilities) or noninstitutional group quarters (college/university student housing,
    military quarters, and other noninstitutional facilities)."""

    group_population = int(tract.DP0120014)  # people living in group quarters (not in households)

    # gq_indices = people[(people.age>=65) | (people.age<18)].index[:group_population]
    gq_indices = people[mask].index[:group_population]

    # for i in gq_indices: mask[i] = False
    mask.loc[gq_indices] = False

    # now distribute the remaining household guys as relatives...
    relatives = people[mask].index
    it = iter(relatives)  # sample by replacement
    relative_hhs = hholds[hholds.htype < 7].sample(n=len(relatives), replace=True)
    relative_hhs.members.apply(lambda x: x.append(next(it)))  # appends on mutable lists
    # for i in relatives: mask[i] = False
    mask.loc[relatives] = False
    # print('is anyone left homeless:',any(mask))
    # add those living in group quarters as all living in a house of 12th type
    if group_population > 0:
        hholds.loc[len(hholds)] = {'htype': 11, 'members': gq_indices}

    # name households
    hholds = hholds.set_index(tract.name + 'h' + pd.Series(np.arange(len(hholds)).astype(str)))

    ## where is hh???
    def hh_2_people(hh, people):
        for m in hh.members:
            people.loc[m, 'hhold'] = hh.name
            people.loc[m, 'htype'] = hh.htype

    hholds.apply(hh_2_people, args=(people,), axis=1)
    people['htype'] = people.htype.astype(int)