'''
utils.py

base level functions used elsewhere

ie math and stuff

'''

import os, sys

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(ROOT_DIR, '/data/')

def dot(A,B): 
    '''
    dot product definition
    kudos to https://stackoverflow.com/questions/18424228/cosine-similarity-between-2-number-lists
    '''
    return (sum(a*b for a,b in zip(A,B)))


