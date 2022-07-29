#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETLs and api data grabbing processes
"""

import requests
import json
import pandas as pd
import time
import os
import utils


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
        
    
    
    
    
    
   
def data_manager(appid, data_type, refresh='N'):
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
    if refresh='Y', then re-pull the data. track via timestamps of data pulls?
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
                per_temp = get_playtime_percentiles_from_steam(appid)
                time.sleep(2)
                per_temp_df = pd.DataFrame(per_temp,index=([0]))
                per_temp_df['appid'] = appid
                per_data = percentile_data.append(per_temp_df)
                per_data.to_csv("percentile_data.csv", index=False)
                percentile_subset = per_temp_df
            except:
                print("couldnt find tag data for appid {}".format(appid))
            
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
    
    




def get_playtime_percentiles_from_steam(appid,results):
    '''
    for a given appid and specified number of sample reviews,
    go to the steam review api and pull the data
    go to the next page, pull the data, etc
    until the result set has [results] number of data points
    then compute playtime percentiles
    
    still need to figure out cursor errors here though...
    
    if the cursor repeats, kill the loop
    
    invalid cursors for squad troubling the execution when imported?
    '''
    
    # appid = 251130
    # results = 200
    start_cursor = '*'
    reviews_data = pd.DataFrame()
    loop_iter = 0
    while (len(reviews_data) <= results and loop_iter < 5):          
        reviews_len_start = len(reviews_data)
        
        print('processing appid {}, cursor {}, results {}/{}, loop {}'.format(appid, start_cursor, len(reviews_data), results, loop_iter))
        s = requests.Session()
        reviews_response = s.get('https://store.steampowered.com/appreviews/{}?json=1&filter=all&day_range=365&num_per_page=100&cursor={}'.format(appid,start_cursor))
        
        reviews_json = reviews_response.content
        json_load = json.loads(reviews_json)
        
        try: 
            next_cursor = json_load['cursor']
        except:
            print('no new cursor found, exiting data grab')
            break
        
        reveiws_df = pd.DataFrame.from_dict(json_load['reviews'])
        authors = reveiws_df['author'].apply(pd.Series)
        
        reviews_data = reviews_data.append(authors, ignore_index=True).drop_duplicates()
        
        reviews_len_end = len(reviews_data)
        
        if start_cursor != next_cursor:
            start_cursor = next_cursor
        else:
            print('no new cursor found, exiting data grab')
            break
        
        if reviews_len_end - reviews_len_start <= 10:
            print('results dwindling, exiting data grab')
            break
        
        time.sleep(2)
        
        loop_iter += 1
                
    final_percentiles = pd.DataFrame(reviews_data['playtime_forever'].quantile([.1, .25, .5, .75, .9])/60)

    return final_percentiles
    


