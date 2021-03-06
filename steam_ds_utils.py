#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import pandas as pd
import json
import requests
from bs4 import BeautifulSoup
import time
import numpy as np





def get_users_games(api_key, steam_id):
    '''
    Get a users playtime stats per app via the steam api
    '''
    
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
    2022-05-06 note: this can be deprecated in favor of get_playtime_percentiles_from_steam(appid,results):
    howlongis.io doesnt seem to be updating any longer and any time we can get away
    from web scraping, the better IMO
    
    probably an eaiser way to do this but this hunts for all the percentile[x] containers
    of which there are a few, returns the first one since we dont care about the dupes,
    converts it to a string, then we pop the string on the h delimeter, remove any commas
    from the thousands mark then convert back to int so we can use it for numerical analysis later
    '''  
    # print("getting playtime stats for app {}, {}/{}".format(games_df['appid'][i], i, len(games_df)))
    
    # appid = 420
    
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

    except:
        pass

    return percentiles_pulled






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








def get_appid_tags(appid):
    '''
    Scrapes an appids store page for the embedded tag data.
    No idea why steam doesnt have an official api for this...
    '''
    # appid = 10
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
    2022-05-06 note: this might also be deprecated in favor of a similar data
    pull for the get_playtime_percentiles_from_steam(appid,results): function
    
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




    
def attribtion_modeller(appid, user, fan_rating, tag_data):
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
    
    
    
def data_manager(appid, data_type):
    '''
    update offline file storage for tag, percentile, review data, date scraped
    
    if an appid doesnt exist in the file already, scrape it and add to file
    if any of the data is more than 365 days old, re-scrape it
    
    given an appid and a data_type, go in to the appropriate file and 
    see if the appid is in there. if it exists, return it. if not, scrape
    and store the data for faster offline analysis.
    
    tag file, percentiles file, review file
    
    
    *** possible bug here: if a string of an appid is passed, the data
    manager wont find it in the csv, but will append the tags correctly
    so you could accidentally return the same data a bunch of times...
    '''
    
    '''
    2022-05-21 todo:
        if you want multiple things updated,
        it should run in parallel instead of
        series to go faster. ie: get tag and
        review data at the same time instead
        of waiting for one then the next
    '''
    
    appid = int(appid) #should fix string issue
    
    if data_type == 'tag':
        # check if data file exists, if not, create one
        try:
            tag_data = pd.read_csv("tag_data.csv")
        except:
            print("no tag data found, creating storage file")
            col_names = ['tagid','name','count','browseable','appid']
            tag_data = pd.DataFrame(columns = col_names)
            tag_data.to_csv("tag_data.csv", index=False)
            
        tag_subset = tag_data[tag_data['appid'] == appid]
        
        if len(tag_subset) < 1:
            print('no tag data stored for appid {}, scraping it now'.format(appid))
            try:
                tag_temp = get_appid_tags(appid)
                time.sleep(2)
                tag_temp_df = pd.DataFrame(tag_temp)
                tag_temp_df['appid'] = appid
                tag_data = tag_data.append(tag_temp_df)
                tag_data.to_csv("tag_data.csv", index=False)
                tag_subset = tag_temp_df
            except:
                print("couldnt find tag data for appid {}".format(appid))
            
        return tag_subset
            

    elif data_type == 'percentile':
        # check if data file exists, if not, create one
        try:
            percentile_data = pd.read_csv("percentile_data.csv")
        except:
            print("no percentile data found, creating storage file")
            col_names = ['appid','p10','p25','median','p75', 'p90']
            percentile_data = pd.DataFrame(columns = col_names)
            percentile_data.to_csv("percentile_data.csv", index=False)
            
        percentile_subset = percentile_data[percentile_data['appid'] == appid]
        
        if len(percentile_subset) < 1:
            print('no percentile data stored for appid {}, scraping it now'.format(appid))
            try:
                per_temp = get_playtime_percentiles_for_app(appid)
                time.sleep(2)
                per_temp_df = pd.DataFrame(per_temp,index=([0]))
                per_temp_df['appid'] = appid
                per_data = percentile_data.append(per_temp_df)
                per_data.to_csv("percentile_data.csv", index=False)
                percentile_subset = per_temp_df
            except:
                print("couldnt find percentiles data for appid {}".format(appid))
            
        return percentile_subset
    
    elif data_type == 'review':
        # check if data file exists, if not, create one
        try:
            review_data = pd.read_csv("review_data.csv")
        except:
            print("no review data found, creating storage file")
            col_names = ['appid','positive_reviews','negative_reviews']
            review_data = pd.DataFrame(columns = col_names)
            review_data.to_csv("review_data.csv", index=False)
            
        review_subset = review_data[review_data['appid'] == appid]
        
        if len(review_subset) < 1:
            print('no review data stored for appid {}, scraping it now'.format(appid))
            try:
                rev_temp = get_review_data(appid)
                time.sleep(2)
                rev_temp_df = pd.DataFrame(rev_temp,index=([0]))
                rev_temp_df['appid'] = appid
                rev_data = review_data.append(rev_temp_df)
                rev_data.to_csv("review_data.csv", index=False)
                review_subset = rev_temp_df
            except:
                print("couldnt find review data for appid {}".format(appid))
            
        return review_subset
    
    elif data_type == 'details':
        # check if data file exists, if not, create one
        try:
            details_data = pd.read_csv("details_data.csv")
        except:
            print("no details data found, creating storage file")
            col_names = ['appid','name','release_date']
            details_data = pd.DataFrame(columns = col_names)
            details_data.to_csv("details_data.csv", index=False)
            
        details_subset = details_data[details_data['appid'] == appid]
        
        if len(details_subset) < 1:
            print('no details data stored for appid {}, scraping it now'.format(appid))
            try:
                det_temp = get_appid_details(appid)
                time.sleep(2)
                det_temp_df = pd.DataFrame(det_temp,index=([0]))
                det_temp_df['appid'] = appid
                det_data = details_data.append(det_temp_df)
                det_data.to_csv("details_data.csv", index=False)
                details_subset = det_temp_df
            except:
                print("couldnt find details data for appid {}".format(appid))
            
        return details_subset
    
    
    
    
    


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
    
    
    

def dot(A,B): 
    '''
    dot product definition
    kudos to https://stackoverflow.com/questions/18424228/cosine-similarity-between-2-number-lists
    '''
    return (sum(a*b for a,b in zip(A,B)))


# def cosine_similarity(a,b):
#     return dot(a,b) / ( (dot(a,a) **.5) * (dot(b,b) ** .5) )



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




def get_playtime_percentiles_from_steam(appid,results):
    '''
    for a given appid and specified number of sample reviews,
    go to the steam review api and pull the data
    go to the next page, pull the data, etc
    until the result set has [results] number of data points
    then compute playtime percentiles
    
    still need to figure out cursor errors here though...
    
    if the cursor repeats, kill the loop
    '''
    
    # appid = 1245620
    # results = 250
    start_cursor = '*'
    reviews_data = pd.DataFrame()
    while len(reviews_data) <= results:          
        print('processing appid {}, cursor {}, results {}/{}'.format(appid, start_cursor, len(reviews_data), results))
        s = requests.Session()
        reviews_response = s.get('https://store.steampowered.com/appreviews/{}?json=1&filter=all&day_range=365&num_per_page=100&cursor={}'.format(appid,start_cursor))
        
        reviews_json = reviews_response.content
        json_load = json.loads(reviews_json)
        next_cursor = json_load['cursor']
        reveiws_df = pd.DataFrame.from_dict(json_load['reviews'])
        authors = reveiws_df['author'].apply(pd.Series)
        
        reviews_data = reviews_data.append(authors, ignore_index=True).drop_duplicates()
        
        if start_cursor != next_cursor:
            start_cursor = next_cursor
        else:
            print('no new cursor found, exiting data grab')
            break
        
        time.sleep(2)
                
    final_percentiles = pd.DataFrame(reviews_data['playtime_forever'].quantile([.1, .25, .5, .75, .9])/60)

    return final_percentiles
    
    
    
    

def get_appid_details(appid):
    '''
    pulls almost all info from the apps store page
    
    eg https://store.steampowered.com/api/appdetails/?appids=10
    
    store in big json file???
    
    from here i can get appid title for any game
    as well as release date among other thing like metacritic score
    
    one issue with appending a big json file is that 
    for 5k games it comes out to like 45mb for the total
    file. so storing on github could be problematic for 
    a monolithic file. this could be stored as a directory of 
    thousands of individual json files though.
    
    the obvious solution here is dump the files into a datalake
    but im sure that violates steams TOS to share that out
    to the broader world for data analytics purposes
    
    for the moment it might be best to have this scraper 
    append pulls from the json data the same way the others
    are to keep things relatively consistent for now
    '''
    # appid = 1363120
    
    s = requests.Session()
    response = s.get('https://store.steampowered.com/api/appdetails/?appids={}'.format(appid))
    
    app_details = response.json()['{}'.format(appid)]['data']
    
    results = {
        "appid": appid,
        "name": app_details['name'],
        "release_date": app_details['release_date']['date']
        }
    
    # results_df = pd.DataFrame(results)
    return results
    
    

def appid_data_builder(appids):
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
    
'''
examples



# build a user's profile of data based on playtime statistics
api_key = '44...A4B'
steam_ids_list = ['76561197969025704']
# steam_ids_list = ['76561197984384656', '76561197969025704', '76561197984169843', '76561198096102722']
user1 = build_user_profile(api_key, steam_ids_list)

# generate an attribution fingerprint for a user's played tags
user1_fingerprint = compute_profile_fingerprint(user1)

# score a game! 
game_tag_scorer('824600', user1_fingerprint[['name','attr_prop_sum']])

# score a list of games!
candidates_list = ['505460','632360','361420','548430']
candidates_data = []
for i in candidates_list:
    candidates_data.append(game_tag_scorer(i, user1_fingerprint[['name','attr_prop_sum']]))
sorted(candidates_data, key=lambda tup: tup[1],reverse=True)


# wishlist example
wishlist = {"appid":80,"priority":0,"added":1639364367},{"appid":34010,"priority":45,"added":1539439975},{"appid":91700,"priority":0,"added":1613247718}
wishlist_analysis = wishlist_analyzer(wishlist)



# how similar is this game to another?
cosine_simil(1443430,811320)
'''


'''

# import pyperclip as pyp
# steamdb_text = str(pyp.paste())

apps = []

files = ['roguelike.html', 'roguelite.html', 'traditional_roguelike.html', 'roguelike_deckbuilder.html', 'action_roguelike.html', 'roguevania.html']

for j in files:
    
    text_file = open(j, "rb")
    steamdb_text = text_file.read()
    text_file.close()

    soup = BeautifulSoup(steamdb_text, "html.parser")
    trs = [tr for tr in soup.find_all('tr')]

    for app in soup.find_all('tr'):
        apps.append(app.get('data-appid'))
    appset = list(set(apps))



# for each app, get title, reviews, tags
for i in range(0,len(appset)):
    print("{}/{}".format(i, len(appset)))
    
    if not(appset[i] is None):
        # data_manager(appset[i], 'tag')
        # data_manager(appset[i], 'review')
        data_manager(appset[i], 'details')


'''
