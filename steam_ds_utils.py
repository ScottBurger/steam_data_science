#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
this script is the function collection zone

new script:
    get games for user
    get playtime percentiels for each game
    get fan rating for each game
    apply attribution for each games tag distribution
    aggregate attribution scores by tag
"""


import pandas as pd
import json
import requests
from bs4 import BeautifulSoup
import time
import numpy as np




def get_users_games(api_key, steam_id):
    s = requests.Session()
    games_response = s.get('http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={}&steamid={}&format=json&include_played_free_games=1&include_appinfo=1'.format(api_key, steam_id))
    games_json = games_response.content
    json_load = json.loads(games_json)
    games_df = pd.DataFrame.from_dict(json_load['response']['games'])
    games_df['user'] = steam_id
    return games_df
    # games_df['playtime_hours'] = games_df['playtime_forever']/60





def get_playtime_percentiles_for_app(appid):
    '''
    probably an eaiser way to do this but this hunts for all the percentile[x] containers
    of which there are a few, returns the first one since we dont care about the dupes,
    converts it to a string, then we pop the string on the h delimeter, remove any commas
    from the thousands mark then convert back to int so we can use it for numerical analysis later
    '''  
    # print("getting playtime stats for app {}, {}/{}".format(games_df['appid'][i], i, len(games_df)))
    URL = "https://howlongis.io/app/{}".format(appid)
    page = requests.get(URL)
    soup = BeautifulSoup(page.text, "html.parser")
    
 
    try: # sometimes appids get redirected which breaks and the howlongis.io site cant find the playtimes. if it cant then skip.
        percentile10 = int(str([td.string for td in soup.find_all('td',itemprop='percentile10')][0]).split('h',1)[0].replace(',',''))
        percentile25 = int(str([td.string for td in soup.find_all('td',itemprop='percentile25')][0]).split('h',1)[0].replace(',',''))
        median = int(str([td.string for td in soup.find_all('td',itemprop='median')][0]).split('h',1)[0].replace(',',''))
        percentile75 = int(str([td.string for td in soup.find_all('td',itemprop='percentile75')][0]).split('h',1)[0].replace(',',''))
        percentile90 = int(str([td.string for td in soup.find_all('td',itemprop='percentile90')][0]).split('h',1)[0].replace(',',''))
        
        # we want the data at a minute level to avoid div0 issues later when scoring
        minutes10 = int(str([td.string for td in soup.find_all('td',itemprop='percentile10')][0]).split(' ',1)[1].replace(',','').replace('m',''))
        minutes25 = int(str([td.string for td in soup.find_all('td',itemprop='percentile25')][0]).split(' ',1)[1].replace(',','').replace('m',''))
        minutes_median = int(str([td.string for td in soup.find_all('td',itemprop='median')][0]).split(' ',1)[1].replace(',','').replace('m',''))
        minutes75 = int(str([td.string for td in soup.find_all('td',itemprop='percentile75')][0]).split(' ',1)[1].replace(',','').replace('m',''))
        minutes90 = int(str([td.string for td in soup.find_all('td',itemprop='percentile90')][0]).split(' ',1)[1].replace(',','').replace('m',''))
        
        pmin10 = percentile10 * 60 + minutes10
        pmin25 = percentile25 * 60 + minutes25
        pmin_median = median * 60 + minutes_median
        pmin75 = percentile75 * 60 + minutes75
        pmin90 = percentile90 * 60 + minutes90
        
        '''
        todo: ratingValue and reviewCount:
            <meta itemprop="ratingValue" content="96">
            <meta itemprop="reviewCount" content="29062">
        '''
        
        percentiles_pulled = {
                "appid": appid,
                "p10": pmin10,
                "p25": pmin25,
                "median": pmin_median,
                "p75": pmin75,
                "p90": pmin90
                }
        # time.sleep(5) # so we dont overload the website and get blocked
    except:
        pass

    return percentiles_pulled






def compute_fan_rating2(row):
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








def get_appid_tags(appid):
    appid = 10
    # thank you! https://stackoverflow.com/questions/22829309/missing-source-page-information-using-urllib2
    # Create session
    session = requests.session()

    # Get initial html
    html = session.get("http://store.steampowered.com/app/%s/" % appid).text

    # Checking if I'm in the check age page (just checking if the check age form is in the html code)
    if ('<form action="http://store.steampowered.com/agecheck/app/%s/"' % appid) in html:
            # I'm being redirected to check age page
            # let's confirm my age with a POST:
            post_data = {
                     'snr':'1_agecheck_agecheck__age-gate',
                     'ageDay':1,
                     'ageMonth':'January',
                     'ageYear':'1960'
            }
            html = session.post('http://store.steampowered.com/agecheck/app/%s/' % appid, post_data).text


    # Extracting javscript object (a json like object)
    start_tag = 'InitAppTagModal( %s,' % appid
    end_tag = '],'
    startIndex = html.find(start_tag) + len(start_tag)
    endIndex = html.find(end_tag, startIndex) + len(end_tag) - 1
    raw_data = html[startIndex:endIndex]

    # Load raw data as python json object
    data = json.loads(raw_data)
    data_df = pd.DataFrame(data)
    data_df['proportion'] = data_df['count'] / sum(data_df['count'])
    data_df['appid'] = appid
    
    data_dict = data_df.to_dict('records')
    data_dict = {
        'appid':data_df['appid'],
        'name':data_df['name'],
        'count':data_df['count'],
        'proportion':data_df['proportion']
        }
    pd.Series(data_df.name.values,index=data_df.appid).to_dict()
    return data




def get_review_data(appid):
    '''
    review data pull
    for a given appid, get its review data
    '''
    # appid = 10
    s = requests.Session()
    response = s.get('https://store.steampowered.com/appreviews/{}?json=1&language=all&purchase_type=all'.format(appid))
    results = {
        "appid": appid,
        "positive_reviews": response.json()['query_summary']['total_positive'],
        "negative_reviews": response.json()['query_summary']['total_negative']
        }
    return results




    
def attribtion_modeller(appid, user, fan_rating):
    '''
    two types of attribution here. proportional applies fan rating across
    the tag proportions. linear gives each tag that fan rating.
    '''
    # appid = merge_data['appid'][10]
    # user = merge_data['user'][10]
    # fan_rating = merge_data['fan_rating'][10]
    
    app_tag_data = tag_data[tag_data['appid']==appid]
    app_tag_data['user'] = user
    app_tag_data['attr_prop'] = fan_rating * app_tag_data['proportion']  
    app_tag_data['attr_linear'] = fan_rating / len(app_tag_data)
          
    return app_tag_data
        
        
        
        

def get_all_steam_tags():
    '''
    generate a tag_df file for offline processing of game tag data
    73 hours to compute fully???
    probably dont need this since we can just loop the game_tag_scorer() 
    over all the unique appids instead...
    '''
    s = requests.Session()
    games_response = s.get('https://api.steampowered.com/ISteamApps/GetAppList/v2/?json=1')
    games_json = games_response.content
    json_load = json.loads(games_json)
    games_df = pd.DataFrame.from_dict(json_load['applist']['apps'])

    all_steam_tags = pd.DataFrame()
    for i in games_df['appid']:
        tags_temp = pd.DataFrame(get_appid_tags(i))
        all_steam_tags = all_steam_tags.append(tags_temp)
        
    all_steam_tags.to_csv('all_steam_tags.csv',index=False)
        
    
    
def game_tag_scorer(appid, model_output):
    # appid = '582010'
    # model_output = agg_final_final[['name','attr_linear_sum']]
    model_output.rename(columns={ model_output.columns[1]: "model_value" }, inplace = True)
    
    app_tag_info = pd.DataFrame(get_appid_tags(appid))
    app_tag_info['proportion'] = app_tag_info['count']/sum(app_tag_info['count'])
    
    app_tag_info_merge = app_tag_info.merge(model_output, how='left', on='name')
    app_tag_info_merge['product'] = app_tag_info_merge['proportion'] * app_tag_info_merge['model_value']

    return (appid, round(sum(app_tag_info_merge['product']),4))




def game_similarity(appid, type='prop'):
    '''
    take an appid
    parse through tag database file
    for each lookup compute a cosine similarity
    save appid and cosine value
    return list of appids and cosines sorted descending

    two types: match based on proportion
    match based on unique tags all up
    '''




def build_tag_percentile_data(api_key, steam_ids_list):
    
    user_list_data = pd.DataFrame()
    for i in steam_ids_list:
        temp_data = pd.DataFrame(get_users_games(api_key, i))
        user_list_data = user_list_data.append(temp_data)
        
    nonzero_user_data = user_list_data[user_list_data['playtime_forever'] > 0]
    unique_games = nonzero_user_data['appid'].unique()
    
    
    percentiles_data = pd.DataFrame()
    tag_data = pd.DataFrame()
    for i in range(0,len(unique_games)):
        
        print('scraping playtime percentile data for appid {}, {}/{}'.format(unique_games[i], i, len(unique_games)))
        try:
            temp_percentiles = pd.DataFrame(get_playtime_percentiles_for_app(unique_games[i]),index=([0]))
            percentiles_data = percentiles_data.append(temp_percentiles)
        except:
            print("couldnt find percentile data, skipping")
        
        print('scraping tag data for appid {}, {}/{}'.format(unique_games[i], i, len(unique_games)))
        try:
            temp_tags = pd.DataFrame(get_appid_tags(unique_games[i]))
            temp_tags['appid'] = unique_games[i]
            temp_tags['proportion'] = temp_tags['count']/sum(temp_tags['count'])
            tag_data = tag_data.append(temp_tags)
        except:
            print('couldnt find tag data, skipping')   #sometimes apps get soft-removed and therefore cant be scraped
        time.sleep(5)
        
    #interim save step just in case
    percentiles_data.to_csv('percentiles_data.csv'.format(steam_ids_list), index=False)
    tag_data.to_csv('tag_data.csv'.format(steam_ids_list), index=False)
        
    # join tag data onto games df
    merge_data = pd.merge(nonzero_user_data, percentiles_data, how='inner', on='appid')
    
    # compute fan rating per game
    merge_data['fan_rating'] = merge_data.apply(compute_fan_rating2, axis=1)
    merge_data['fan_fix'] = merge_data['fan_rating'].apply(lambda x: 0 if x<0 else (100 if x >100 else x))
                
    # attribution models using fan rating through percentiles data
    '''
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
    
    tag_attributions = pd.DataFrame()
    for i in unique_games:
        for j in steam_ids_list:
            try:
                fan_rating_subset = merge_data[(merge_data['user'] == j) & (merge_data['appid']==i)]['fan_fix'].values[0]
                attr_df = attribtion_modeller(i, j, fan_rating_subset)
                tag_attributions = tag_attributions.append(attr_df)
            except:
                pass
    
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
    
    return tag_data, percentiles_data, agg_final_final

        
    
    
    
def refresh_tag_data(app_id_list):
    '''
    for a given list of games
    check if theyre in the tag data already
    add the missing ones
    refresh the file
    
    appid, tag_dict, update_time
    appid, percentiles_dict, update_time
    '''
    
    # if file exists
        # load it
    # else create it
    try:
        tag_data_refresh = pd.read_csv("tag_data.csv")
    except:
        print("no tag data found, creating dataset")
        tag_data_refresh = pd.DataFrame()
        tag_data_refresh.to_csv("tag_data.csv")
    
    #subset provided list to appids that arent in the table already
    app_id_list = ['505460','632360','361420','548430']
    app_ids_processed = tag_data_refresh['appid']
    
    apps_to_process = [x for x in app_id_list if x not in app_ids_processed]
    
    new_apps = pd.DataFrame()
    for i in apps_to_process:
        tag_temp = pd.DataFrame(get_appid_tags(i))
        tag_temp['appid'] = i
        new_apps = new_apps.append(tag_temp)
    ### todo: append this to current data
    
    
    
    
    
def group_recommender(steam_ids_list):
    '''
    takes a list of steam user ids
    gets their fan data
    applies that fan data through an attribution model to tags
    aggregates the tag scores
    hunts through all steam tag data to find the top 25 games to play together
    '''
    
    

'''
main
'''

api_key = '443EE200F8889091D47FA9F6AF615A4B'

steam_ids_list = ['76561197984384656', '76561197969025704', '76561197984169843', '76561198096102722']


tag_data, percentiles_data, agg_final_final = build_tag_percentile_data(api_key, steam_ids_list)

# score a list of games!
candidates_list = ['505460','632360','361420','548430']
candidates_data = []
for i in candidates_list:
    candidates_data.append(game_tag_scorer(i, agg_final_final[['name','attr_linear_sum']]))
    
sorted(candidates_data, key=lambda tup: tup[1],reverse=True)



game_tag_scorer('427520', agg_final_final[['name','attr_prop_sum']])





