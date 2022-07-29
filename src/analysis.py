#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
things to do computing
"""

import numpy as np
import pandas as pd
import requests
import json
import time
from workflows import *
from utils import *



def compute_fan_rating2(row):
    '''
    For a given playtime percentile for an app and a users
    total playtime in minutes, calculate where on the distribution
    the user would lie. 
    
    Theres some nuance here about predicting percentiles based on
    a curve fit, so instead of letting the values go lower than 0
    or higher than 100, the values are capped between them. There
    could be an argument made for negatives here, but well put that
    in the theory pile for now...
    '''
    
    p10 = row['p10']
    p25 = row['p25']
    median = row['median']
    p75 = row['p75']
    p90 = row['p90']
    user_playtime = row['playtime_forever']
    appid = row['appid']
    
    x_data = np.array([10, 25, 50, 75, 90])
    y_data = np.array([p10,p25,median,p75,p90])
                       
    log_y_data = np.log(y_data)
    curve_fit = np.polyfit(x_data, log_y_data, 1)
    beta = curve_fit[0] #beta
    alpha = curve_fit[1] #alpha
    # https://www.kite.com/python/answers/how-to-do-exponential-and-logarithmic-curve-fitting-in-python
    # appid_lookup = playtime_percentiles['appid'][i]
    # appid_playtime_minutes = games_df[games_df['appid'] == int(appid_lookup)]['playtime_forever'].values[0]
    fan_percentile = (np.log(user_playtime) - alpha) / beta
    fan_data = {
        "appid": appid,
        "playtime_distribution": y_data,
        "coefficients": [beta,alpha],
        "playtime_minutes": user_playtime,
        "fan_percentile": fan_percentile
    }
    return fan_percentile






def compute_attribtion_modeller(appid, user, fan_rating, tag_data):
    '''
    two types of attribution here. proportional applies fan rating across
    the tag proportions. linear gives each tag that fan rating.
    '''    
    # appid = i
    # user = j
    # fan_rating = fan_rating_subset
    app_tag_data = tag_data[tag_data['appid']==appid]
    
    '''
    block to add dummy tags for games with less than 20 tags
    add up to as many so the total length is 20
    then do proportions. later well remove the dummy tags
    from the analysis, which should clean up some of the over
    indexing on games with fewer tags in their distribution.
    '''
    
    dummytags = {
        'tagid':000000,
        'name':'dummytag',
        'count':1,
        'browseable':True,
        'appid':000000,
        }
    while len(app_tag_data) < 20:
        app_tag_data = app_tag_data.append(dummytags,ignore_index=True)
    
    app_tag_data['proportion'] = (app_tag_data['count']/ app_tag_data['count'].sum())
    app_tag_data['user'] = user
    app_tag_data['attr_prop'] = fan_rating * app_tag_data['proportion']  
    app_tag_data['attr_linear'] = fan_rating / len(app_tag_data)
    app_tag_data['attr_fixed'] = fan_rating / 20
          
    return app_tag_data




def compute_game_tag_scorer(appid, model_output):
    '''
    Takes in an appid and a specific fingerprint engagement
    model type, then returns the appid and that value applied 
    across the tags
    
    seems like theres as much attribution work to be done here as
    with the modelling procedure. do we apply the tag scores proprotionally?
    how about for games with 2 tags? linear proportions? sums? avgs???
    '''
    # appid = 654910    # nan for 346110???   # over-indexed for yankais peak 654910
    # model_output = user1_fingerprint[['name','attr_prop_sum']]
    model_output.rename(columns={ model_output.columns[1]: "model_value" }, inplace = True)
    
    #app_tag_info = pd.DataFrame(get_appid_tags(appid))
    app_tag_info = data_manager(appid, 'tag')
    
    dummytags = {
        'tagid':000000,
        'name':'dummytag',
        'count':1,
        'browseable':True,
        'appid':000000,
        }
    while len(app_tag_info) < 20:
        app_tag_info = app_tag_info.append(dummytags,ignore_index=True)
    
    
    
    app_tag_info['proportion'] = app_tag_info['count']/sum(app_tag_info['count'])
    
    app_tag_info_merge = app_tag_info.merge(model_output, how='left', on='name')
    app_tag_info_merge['proportion'] = app_tag_info_merge['count'] / (app_tag_info_merge['count'].sum())
    app_tag_info_merge['model_value'] = app_tag_info_merge['model_value'].fillna(0)
    app_tag_info_merge['product'] = app_tag_info_merge['proportion'] * app_tag_info_merge['model_value']

    return (appid, round(sum(app_tag_info_merge['product']),4))






def wishlist_analyzer(wishlist):
    '''
    Given a users wishlist data, dump out a pandas dataframe that 
    includes a ranking based on both positivity of reviews and
    number of reviews.
    
    Steam recently made all wishlist data private, so you have to 
    manually dump it from page source off the g_rgWishlistData variable.
    An example would be like: var g_rgWishlistData = 
    [{"appid":80,"priority":0,"added":1639364367},
     {"appid":34010,"priority":45,"added":1539439975},...]
    Just copy paste the data between the []s. 
    '''
    
    # extract the appids only, dont care about the priority or when added for the moment
    wishlist_apps = []
    for i in range(0,len(wishlist)):
        #i=0
        appid = wishlist[i]['appid']
        wishlist_apps.append(appid)
    
    
    wishlist_data = pd.DataFrame()
    s = requests.Session()
    for i in range(0,len(wishlist_apps)):
        
        # i=3
        try:
            print("getting review data for {}, {}/{}".format(wishlist_apps[i], i, len(wishlist_apps)))
            response = s.get('https://store.steampowered.com/appreviews/{}?json=1&language=all&purchase_type=all'.format(wishlist_apps[i]))
            results = {
                "appid": str(wishlist_apps[i]),
                "positive_reviews": response.json()['query_summary']['total_positive'],
                "negative_reviews": response.json()['query_summary']['total_negative']
                }
            wishlist_data = wishlist_data.append(results, ignore_index = True)
            time.sleep(2)
        except:
            print("couldnt find data, skipping...")
    
    wishlist_data['total_reviews'] = wishlist_data['positive_reviews'] + wishlist_data['negative_reviews']
    wishlist_data['percent_positive'] = wishlist_data['positive_reviews'] / wishlist_data['total_reviews']
    wishlist_data['percent_rank'] = wishlist_data['percent_positive'].rank(ascending=False)
    wishlist_data['volume_rank'] = wishlist_data['total_reviews'].rank(ascending=False)
    wishlist_data['magnitude_rank'] = (wishlist_data['percent_rank']**2 + wishlist_data['volume_rank']**2)**(1/2)
    
    
    '''
    an interesting second level cut of the data here
    would be to bin the total reviews by rounded log values
    then filter each bin to games over 90%, then take the top 5
    this would be a way to get some good input from indies that
    are high quality but might be missed by the magnitude sort
    '''
    wishlist_data['indie_rank'] = round(np.log(wishlist_data['total_reviews']))
    
    '''
    steam also doesnt seem to have an api for providing an appid
    and getting an appname as a result, which seems odd and annoying.
    here i have to get the full list of appids on steam, then convert
    to a df, then join the wishlist data off this big df of steamids
    '''
    s = requests.Session()
    games_response = s.get('https://api.steampowered.com/ISteamApps/GetAppList/v2/?json=1')
    games_json = games_response.content
    json_load = json.loads(games_json)
    games_df = pd.DataFrame.from_dict(json_load['applist']['apps'])
    
    games_df['appid'] = games_df['appid'].astype(str)
    wishlist_merge = wishlist_data.merge(games_df, on='appid', how='left')
    wishlist_merge.drop_duplicates(inplace=True)
    
    return wishlist_merge





def build_user_profile(api_key, steam_ids_list):
    '''
    Takes a user id and returns the nonzero playtime games
    along with playtime percentiles, review data, and fan scores
    '''    

    
    user_list_data = pd.DataFrame()
    for i in steam_ids_list:
        temp_data = pd.DataFrame(get_users_games(api_key, i))
        user_list_data = user_list_data.append(temp_data)
        
    nonzero_user_data = user_list_data[user_list_data['playtime_forever'] > 0]
    unique_games = nonzero_user_data['appid'].unique()
    
    
    percentiles_data = pd.DataFrame()
    review_data = pd.DataFrame()
    for i in range(0,len(unique_games)):
    
        # i = 0
        
        print('getting playtime percentile data for appid {}, {}/{}'.format(unique_games[i], i, len(unique_games)))
        try:
            percentiles_temp = data_manager(unique_games[i], 'percentile')
            percentiles_data = percentiles_data.append(percentiles_temp)
        except:
            print("couldnt get percentile data, skipping")
        
        print('getting tag data for appid {}, {}/{}'.format(unique_games[i], i, len(unique_games)))
        try:
            data_manager(unique_games[i], 'tag')
        except:
            print('couldnt get tag data, skipping')   #sometimes apps get soft-removed and therefore cant be scraped
        
        print('getting review data for appid {}, {}/{}'.format(unique_games[i], i, len(unique_games)))
        try:
            review_temp = data_manager(unique_games[i], 'review')
            review_data = review_data.append(review_temp)
        except:
            print('couldnt get review data, skipping')
        
        
   
        
    # join tag data onto games df
    merge_data = pd.merge(nonzero_user_data, percentiles_data, how='inner', on='appid')
    merge_data = pd.merge(merge_data, review_data, how='inner', on='appid')
    merge_data['total_reviews'] = merge_data['positive_reviews'] + merge_data['negative_reviews']
    
    # compute fan rating per game
    merge_data['fan_rating'] = merge_data.apply(compute_fan_rating2, axis=1)
    merge_data['fan_fix'] = merge_data['fan_rating'].apply(lambda x: 0 if x<0 else (100 if x >100 else x)) # caps at 0-100 values
                
    # attribution models using fan rating through percentiles data
    
    return merge_data





def compute_profile_fingerprint(user_profile):
    '''
    break this part out into a separate function?
    
    for computing across multiple users, does it make more sense to aggregate
    the playtimes first across the group then use that aggregation for a fan rating?
    the goal is to find something that appeals to everyone. summing, like averaging, 
    would skew positively towards outliers. so if a group of 10 no one plays planetside
    but one person puts a thousand hours in, the system will bias towards that. it probably
    makes more sense to use a median? then for the group use that median playtime to
    calculate a percentile group score. or maybe not?
    
    or do we just apply attributions then average/median/sum those attributions at the 
    tag level? 
    '''
    # user_profile = sseagal_test
    
    unique_games = list(set(user_profile['appid']))
    steam_ids_list = list(set(user_profile['user']))
    tag_data = pd.read_csv('tag_data.csv')
    
    tag_attributions = pd.DataFrame()
    for i in unique_games:
        for j in steam_ids_list:
            # i=unique_games[1]
            # j=steam_ids_list[0]
            fan_rating_subset = user_profile[(user_profile['user'] == j) & (user_profile['appid']==i)]['fan_fix'].values[0]
            attr_df = attribtion_modeller(i, j, fan_rating_subset, tag_data)
            tag_attributions = tag_attributions.append(attr_df)

    # aggregate the attributed tag score data
    '''
    tag, sum_linear, avg_linear, med_linear, sum_prop, avg_prop, med_prop
    '''
    agg_sums = tag_attributions.groupby(['name']).sum().reset_index()
    agg_avgs = tag_attributions.groupby(['name']).mean().reset_index()
    agg_meds = tag_attributions.groupby(['name']).median().reset_index()
    agg_sums.rename(columns={'attr_prop':'attr_prop_sum', 'attr_linear':'attr_linear_sum'},inplace=True)
    agg_avgs.rename(columns={'attr_prop':'attr_prop_avg', 'attr_linear':'attr_linear_avg'},inplace=True)
    agg_meds.rename(columns={'attr_prop':'attr_prop_med', 'attr_linear':'attr_linear_med'},inplace=True)
    agg_final = agg_sums.merge(agg_avgs, how='left', on='name')
    agg_final = agg_final.merge(agg_meds, how='left', on='name')
    agg_final_final = agg_final[['name','attr_prop_sum','attr_linear_sum','attr_prop_avg','attr_linear_avg', 'attr_prop_med','attr_linear_med']]
    
    return agg_final_final








def backlog_analyzer(user_profile, user_fingerprint):
    '''
    takes a steam users playtime data list
    and applies a fingerprint profile to it
    to see if a user is missing out on a game
    they havent invested much time in that 
    could be worth their while
    '''
    
    # user_profile = user1
    # user_fingerprint = user1_fingerprint
    
    unique_games = list(set(user_profile['appid']))
    
    processed_games = pd.DataFrame()
    for i in unique_games:
         temp = {
        'appid':i,
        'predicted_engagement':game_tag_scorer(i, user_fingerprint[['name','attr_prop_sum']])[1]
        }
         processed_games = processed_games.append(temp, ignore_index=True)




def cosine_simil(appid1,appid2):
    '''
    takes in appid1 and appid2 and records tag data for each
    then computes a cosine similarity between 1 and 2
    closer to 1 is more similar
    '''
    # appid1 = 1253920   # rogue legacy 2
    # appid2 = 1443430   # 1980 rogue
    
    app1_tags = pd.DataFrame(get_appid_tags(appid1))
    app2_tags = pd.DataFrame(get_appid_tags(appid2))
    tags_values = app1_tags.merge(app2_tags,on="name",how='outer').fillna(0)
    a = tags_values['count_x']
    b = tags_values['count_y']
    return dot(a,b) / ( (dot(a,a) **.5) * (dot(b,b) ** .5) )








def rogue_appid_data_builder(appids):
    '''
    appid, name, reviews, tag_dict, release date
    '''
    details = pd.read_csv('details_data.csv')
    reviews = pd.read_csv('review_data.csv')
    tags = pd.read_csv('tag_data_dict.csv')
    
    full_data = details.merge(reviews, on="appid")
    full_data = full_data.merge(tags, on="appid")
    full_data['total_reviews'] = full_data['positive_reviews'] + full_data['negative_reviews']
    full_data['score_percent'] = full_data['positive_reviews'] /  full_data['total_reviews']
    
    full_data['rogue_score_tuples'] = full_data['tag_dict'].apply(rogue_score)
    full_data[['rogue_tag_votes', 'total_tag_votes', 'rogue_score','leading_rogue_tag']] = pd.DataFrame(full_data['rogue_score_tuples'].tolist(),index=full_data.index)
    full_data = full_data.drop_duplicates()
    
    
    
def tag_dict_converter(tag_file):
    '''
    converts a long-form list of tag data
    into a single row with tag distribution
    compressed into a dictionary for that row
    
    ie: 
    appid    tag_dict
    10    {action:5,co-op:9,roguelike:20,...}
    '''
    tag_data = pd.read_csv('tag_data.csv')
    apps = set(tag_data['appid'])
    
    new_data = pd.DataFrame()
    for i in apps:
        # i = 248820
        subset = tag_data[tag_data['appid'] == i][['name','count']]
        tag_dict = dict(subset.values)
    
        tmp = {
            'appid':i,
            'tag_dict': tag_dict
            }
        
        new_data = new_data.append(tmp, ignore_index=True)    
    new_data.to_csv('tag_data_dict.csv',index=False)
    
    
    
    
    
    
    
def rogue_score(tag_dict):
    '''
    takes a dictionary of tag data and votes
    adds up all tags having rogue___ 
    compare rogue___ to total and thats the score
    
    show total number of tag votes, rogue votes,
    and total tags
    
    
    todo:
    also hunt through the first 5 tags. if rogue_
    is among them, then flag it as such
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
    



