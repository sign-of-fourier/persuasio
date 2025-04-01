import chromadb
import pandas as pd
import re
import numpy as np 
import concurrent
import boto3
from datetime import datetime as dt
import inspect

from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import WhiteKernel, Matern, DotProduct
from scipy.stats import ecdf, norm
import requests
import json

from PIL import Image
import urllib.request
from io import BytesIO 

client = chromadb.PersistentClient(path="chroma_small")
description_db = client.get_collection(name="amazon_beauty_descriptions")
reviews_df = pd.read_csv('reviews.csv', compression='gzip')

greeting = 'Megan: Hi, my name is Megan. Is there something I can I help you with?'
reply = input(greeting)
conversation = [greeting, 'Dasha: ' + reply]


search_terms = agents.search("\n".join(conversation))
results = description_db.query(
    query_texts=search_terms,
    n_results=3
)
search_df = pd.DataFrame({'title': [title['title'] for meta in results['metadatas'] for title in meta],
                          'description': [d for doc in results['documents'] for d in doc],
                          'id': [idx for ids in results['ids'] for idx in ids]})
if iter > 0:
    search_df = pd.concat([search_df, old_search_df], axis=0)
search_df = search_df.drop_duplicates(subset='id', inplace=False)

for i in range(len(results['metadatas'])):
    for j in range(len(results['metadatas'][i])):
        images = results['metadatas'][i][j]['thumb'].split("\n")
        with urllib.request.urlopen(images[0]) as url:
            img = Image.open(BytesIO(url.read()))
        display(img)
        print(results['metadatas'][i][j]['title'], ', $' + str(results['metadatas'][i][j]['price']))

product_info = ''
for y in range(len(results['ids'])):
    for x in range(len(results['ids'][y])):
        review_summary = agents.summarize(utils.subsample(reviews_df[reviews_df['parent_asin'] == results['ids'][y][x]], 20))
        product_info += "{}. {}\n- {}\n\nSummary of a Sample of Reviews\n{}\n\n".format(x+1, results['metadatas'][y][x]['title'], results['documents'][y][x], review_summary)   
        product_info += "Overall Average: {}\nNumber of Ratings: {}\nPrice: ${}\n\n".format(results['metadatas'][y][x]['average_rating'], 
                                                                                            results['metadatas'][y][x]['rating_number'],
                                                                                            results['metadatas'][y][x]['price'])


reply = agents.salesman(" ".join(conversation), product_info)
conversation.append('Megan: ' + utils.remove_name('Megan', reply))
reply = input(reply)
#reply = agents.prospect("\n".join(conversation))
#print(reply)
conversation.append('Dasha: ' + utils.remove_name('Dasha', reply))
old_search_df = search_df.copy()
