# -*- coding: utf-8 -*-
"""
builds the roguelike dataset for use on the grogpod roguelike podcast  https://grogpod.zone
"""

# import steam_data_science as sds
import pandas as pd
import numpy as np


'''
step 1: download full html files from steamdb.info
'''

apps = []

files = ['roguelike.html', 'roguelite.html', 'traditional_roguelike.html', 'roguelike_deckbuilder.html', 'action_roguelike.html', 'roguevania.html']

# cd "F:/docs/dev/python/sds-2022-05-20/steam_data_science_copy/2023-06-05/"


for j in files:
       
    text_file = open(j, "rb")
    steamdb_text = text_file.read()
    text_file.close()

    soup = BeautifulSoup(steamdb_text, "html.parser")
    
    soup.find_all(class_="app")
    
    
    trs = [tr for tr in soup.find_all('tr')]

    for app in soup.find_all('tr'):
        apps.append(app.get('data-appid'))
    appset = list(set(apps))



# for each app, get title, reviews, tags
for i in range(0,len(appset)):
    print("{}/{}".format(i, len(appset)))
    
    if not(appset[i] is None):
        data_manager(appset[i], 'tag')
        data_manager(appset[i], 'review')
        data_manager(appset[i], 'details')




def rogue_score(tag_dict):
    '''
    takes a dictionary of tag data and votes
    adds up all tags having rogue___ 
    compare rogue___ to total and thats the score
    
    show total number of tag votes, rogue votes,
    and total tags

    '''
    
    tag_dict = eval(tag_dict) #handles string dict conversion
    
    total_votes = sum(tag_dict.values())
    
    rogue_tags = ['Roguelike', 'Roguevania', 'Action Roguelike', 'Roguelite', 'Traditional Roguelike', 'Roguelike Deckbuilder']
    rogue_dict = dict((k, tag_dict[k]) for k in rogue_tags if k in tag_dict)
    total_rogue = sum(rogue_dict.values())    
    
    
    # ?????????????? probably a way to clean this up...
    tag_keys = []
    tag_dict_keys = [tag_keys.append(key) for key in tag_dict.keys()]
   
    
    results = []
    for i in rogue_tags:
        results.append(i in tag_keys[0:5])
        
    if True in results:
        leading_rogue_flag = True
    else:
        leading_rogue_flag = False
    
    return (total_rogue, total_votes, total_rogue/total_votes, leading_rogue_flag)



'''
add logic columns here for the following:
    

playtimes for selector games
'''
    




def col_topN(data, colname, asc_bool, topN, output_name):
    '''
    look at colname and sort ascending by default
    mark the data up to the topN row
    '''
    
    # data = full_data
    # colname = "balance_score1"
    # topN = 150
    # asc_bool = True
    
    data_sort = data.sort_values(by=[colname], ascending=asc_bool)
    data_sort['RowNumber'] = data_sort.reset_index().index + 1
    data_sort[output_name] = np.where(data_sort['RowNumber'] < topN, 1, 0)
        
    return data_sort[['appid', output_name]]



    
















'''
build the final dataset
'''

# cd "F:\docs\dev\python\sds-2022-05-20\steam_data_science_copy\2023-06-05"

details = pd.read_csv('details_data.csv')
reviews = pd.read_csv('review_data.csv')
tags = pd.read_csv('tag_data_dict.csv')

full_data = details.merge(reviews, on="appid")
full_data = full_data.merge(tags, on="appid")


full_data['total_reviews'] = full_data['positive_reviews'] + full_data['negative_reviews']
full_data['score_percent'] = full_data['positive_reviews'] /  full_data['total_reviews']
full_data['rogue_score_tuples'] = full_data['tag_dict'].apply(rogue_score)
full_data[['rogue_tag_votes', 'total_tag_votes', 'rogue_score','leading_rogue_tag']] = pd.DataFrame(full_data['rogue_score_tuples'].tolist(),index=full_data.index)

full_data['review_rank'] = full_data['total_reviews'].rank(ascending=False)
full_data['review_rank_pct'] = full_data['total_reviews'].rank(pct=True)
full_data['score_rank'] = full_data['score_percent'].rank(ascending=False) #not defaulting to 1?
full_data['score_rank_pct'] = full_data['score_percent'].rank(pct=True)

full_data['balance_score1'] = (full_data['review_rank']**2 + full_data['score_rank']**2)**(1/2)
full_data['balance_score2'] = (full_data['review_rank_pct']**2 + full_data['score_rank_pct']**2)**(1/2)


# interesting: log10 is more mainstream-based, log_e is more indie-based
full_data['steamdb_score'] = full_data['score_percent'] - (full_data['score_percent'] - 0.5)*(2**(-np.log10(full_data['total_reviews'] + 1)))

full_data['steamdb_score_ebase'] = full_data['score_percent'] - (full_data['score_percent'] - 0.5)*(2**(-np.log(full_data['total_reviews'] + 1)))



###
###
###


full_data = full_data.merge(col_topN(full_data, "balance_score1", True, 150, "top150_bs1"), how='left', on='appid')

full_data = full_data.merge(col_topN(full_data, "balance_score2", False, 150, "top150_bs2"), how='left', on='appid')

full_data = full_data.merge(col_topN(full_data, "steamdb_score", False, 150, "top150_steamdb"), how='left', on='appid')

full_data = full_data.merge(col_topN(full_data, "steamdb_score_ebase", False, 150, "top150_steamdb_ebase"), how='left', on='appid')

#######################
#######################
#######################

full_data = full_data.merge(col_topN(full_data[full_data['tag_dict'].str.contains("Traditional Roguelike")], "balance_score2", False, 25, "t25_tradRL_bs2"), how='left', on='appid')

full_data = full_data.merge(col_topN(full_data[full_data['tag_dict'].str.contains("Action Roguelike")], "balance_score2", False, 25, "t25_actionRL_bs2"), how='left', on='appid')

full_data = full_data.merge(col_topN(full_data[full_data['tag_dict'].str.contains("Roguelike")], "balance_score2", False, 25, "t25_roguelike_bs2"), how='left', on='appid')

full_data = full_data.merge(col_topN(full_data[full_data['tag_dict'].str.contains("Roguelite")], "balance_score2", False, 25, "t25_lite_bs2"), how='left', on='appid')

full_data = full_data.merge(col_topN(full_data[full_data['tag_dict'].str.contains("Roguelike Deckbuilder")], "balance_score2", False, 25, "t25_deckRL_bs2"), how='left', on='appid')

full_data = full_data.merge(col_topN(full_data[full_data['tag_dict'].str.contains("Roguevania")], "balance_score2", False, 25, "t25_rogueVainia_bs2"), how='left', on='appid')

full_data['top_any'] = full_data[list(full_data.columns[21:31])].sum(axis=1, min_count=1)

full_data = full_data.merge(col_topN(full_data[full_data['top_any']==0],"total_reviews", False, 50, "pop_leftover"), how='left', on='appid')


###
###
###

full_data['quality_filter'] = np.where(
    (full_data["score_percent"] >= 0.8) &
    (full_data["total_reviews"] >= 200) &
    (full_data["rogue_score"] >= 0.04)
    , 1, 0)
    

###
###
###

full_data['selector'] = np.where(
    (full_data['quality_filter'] > 0) & 
    (
     (full_data['top_any'] > 0) | 
     (full_data['pop_leftover'] > 0)
    )
    , 1, 0)



###
###
###    


seagal_games = pd.DataFrame(get_users_games("api_key_here", steam_user_id))
full_data = pd.merge(full_data, seagal_games[['appid','name']], how="left", on="appid")

###
###
###

playtime_list = full_data[full_data['selector']==1]
playtime_apps = list(playtime_list['appid'])

playtime_results = pd.DataFrame()

for i in range(0,len(playtime_apps)):

    
    print("{}/{}".format(i, len(playtime_apps)))
    
    try:
        game_playtime = get_playtime_percentiles_from_steam_2(playtime_apps[i])
    except:
        print("some issue, moving to next app")
    
    playtime_results = playtime_results.append(game_playtime, ignore_index=True)
    

full_data = pd.merge(full_data, playtime_results, how="left", on="appid")


full_data_unique = full_data.drop_duplicates()

full_data.to_csv('full_data.csv',index=False)




