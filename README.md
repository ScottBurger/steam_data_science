# steam_data_science
A collection of data science python utilities for analyzing data from the video game platform Steam.

## Getting Started
You'll need two things here to start analyzing data: [a Steam API key from here](https://steamcommunity.com/dev/apikey) and a [user's steam64 id, which can be found here]( https://steamid.xyz/).  Otherwise, for a given user's steam profile page, if you inspect the page source, you can find your 17 digit steam id key by searching for "g_rgProfileData". An example would look like: 
```
g_rgProfileData = {"url":"https:\/\/steamcommunity.com\/profiles\/**765611________**
```

## Features
__build_tag_percentile_data(api_key, steam_ids_list)__
* returns __tag_data__, __percentiles_data__, and __aggregation_data__
  * __tag_data__ - A dataframe of tagid, name, count, appid, proportion
  * __percentiles_data__ - A dataframe of appid, p10, p25, median, p75, p90 percentile playtimes in minutes
  * __aggregation_data__ - A fingerprint dataframe of each user's tag name, and various attribution models like proportional, linear, average, median, etc.

__compute_fan_rating(data)__
* For a given game and its quartiles of playtime data, check the user's playtime against the distribution and compute what percentile the user is compared to the rest of the game's playing population.

__get_review_data(appid)__
* For a given steam app, get its positive and negative review counts for all languages and purchase types.

__get_appid_tags(appid)__
* For a given steam app, get the tag names, the counts of how many times they've been attributed, and what proportion of the total they make up that app's tags.

__get_users_games(api_key, steam_id)__
* Get a user's list of games, playtime data, and other info from the IPlayerService and dump it into a pandas dataframe.

__get_playtime_percentiles_for_app(appid)__
* For a given steam app, gently scrape the howlongis.io site for the app's playtime quartile data. 

__wishlist_analyzer(wishlist)__
* Takes in a wishlist dictionary from the steam page source code and returns a pandas dataframe with review scores, recommended magnitude rank (lower is better), and indie game category levels (lower is more indie).

## Example Usage

This example will give us a dump of all tag data, all playtime percentiles, and a user's engagement score fingerprint for various models. It can be extended to multiple users by adding additional steam ids to the list:

```
api_key = '443E...A4B'
steam_ids_list = ['76561197969025704']
tag_data, percentiles_data, agg_data = build_tag_percentile_data(api_key, steam_ids_list)
```

Each crawl of the data is defaulted to 2 seconds to avoid over-loading any systems, so a data update of 200 games will take about 7 minutes.

This example line will score an individual game for predicted engagement based on the figerprint data you've developed:

```
game_tag_scorer('427520', agg_data[['name','attr_prop_sum']])
```


This example block will score a list of games for potential engagement based on the fingerprint data you've developed:

```
candidates_list = ['505460','632360','361420','548430']
candidates_data = []
for i in candidates_list:
    candidates_data.append(game_tag_scorer(i, agg_data[['name','attr_linear_sum']]))
sorted(candidates_data, key=lambda tup: tup[1],reverse=True)
```
