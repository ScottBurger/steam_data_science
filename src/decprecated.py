#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
deprecated functions no longer in use but kept for historical record
"""

def cosine_similarity(a,b):
    return dot(a,b) / ( (dot(a,a) **.5) * (dot(b,b) ** .5) )








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
    
    