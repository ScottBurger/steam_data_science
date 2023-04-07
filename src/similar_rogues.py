# -*- coding: utf-8 -*-
"""
take an appid. return 3 most similar apps by cosine
similarity of tag distributions
"""


import math
import numpy as np
import pandas as pd
import ast

s = "{'Indie': 196, 'Roguelite': 194}"
d = ast.literal_eval(s)





def cosine_similarity(dict1, dict2):
    all_keys = set(dict1.keys()).union(set(dict2.keys()))
    dict1_values = [dict1.get(key, 0) for key in all_keys]
    dict2_values = [dict2.get(key, 0) for key in all_keys]
    dot_product = np.dot(dict1_values, dict2_values)
    norm1 = np.linalg.norm(dict1_values)
    norm2 = np.linalg.norm(dict2_values)
    return dot_product / (norm1 * norm2)


# dict1 = {'a': 1, 'b': 2, 'c': 3}
# dict2 = {'b': 5690, 'c': 2220, 'd':1550}

# cosine_similarity(dict1, dict2)





rogues_data = pd.read_clipboard()

app_to_test = 'Hand of Fate'
testing_dict = rogues_data[rogues_data['name']==app_to_test]['tag_dict']
testing_dict_str = testing_dict.iloc[0]
testing_dict_d = ast.literal_eval(testing_dict_str)

similar_apps = pd.DataFrame()

for i in rogues_data['name']:
   # i = 632360
    comparison_dict = rogues_data[rogues_data['name']==i]['tag_dict']
    comparison_dict_str = comparison_dict.iloc[0]
    comparison_dict_d = ast.literal_eval(comparison_dict_str)
    
    score = cosine_similarity(testing_dict_d, comparison_dict_d)
    
    temp = {
        'Game':i,
        'Score':score    
     }
    
    similar_apps = similar_apps.append(temp,ignore_index=True)
