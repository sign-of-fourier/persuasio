from flask import Flask, request

import chromadb
import pandas as pd
import re
import numpy as np 
import concurrent
import boto3
from datetime import datetime as dt
import inspect

#from sklearn.gaussian_process import GaussianProcessRegressor
#from sklearn.gaussian_process.kernels import WhiteKernel, Matern, DotProduct
#from scipy.stats import ecdf, norm

import requests
import json

import persuasio.utils as utils
import persuasio.agents as agents

app = Flask(__name__)

page = """
<html>
<p id='paragraph'>{}
<form action='/persuasio?max_tokens=256&iteration=4&product_history_included=False' method=post>
    <input type=hidden name=product_history value="{}"></input>
    <input type=hidden name=system value='You are a sales person at Amazon.'></input>
    <input type=hidden name=transcript_history value="{}"></input>
    <input type=text name='user_statement'></input>
    <input type=submit name=submissize value=nah></input></input>
</form>
</form>
<p id='pics'><div style="height:700px; width700px;border:1px sold #ccc;font:16px/26px Georgia, Garamond, Serif;overflow:auto;">{}</div>

"""
client = chromadb.PersistentClient(path="persuasio/chroma_small")
client2 = chromadb.PersistentClient(path="persuasio/chroma_small2")
description_db = client.get_collection(name="amazon_beauty_descriptions")
description_db2 = client2.get_collection(name="amazon_beauty_descriptions2")


reviews_df = pd.read_csv('persuasio/reviews.csv.gz', compression='gzip')


@app.route("/persuasio", methods = ['POST'])
def persuasio():
    
    user_statement = request.form.get('user_statement')
    system = request.form.get('system')
    transcript_history = request.form.get('transcript_history')  
    product_history = request.form.get('product_history')

    iteration = request.form.get('iteration')    
    max_tokens = request.args.get('max_tokens')
    product_history_included = request.args.get('product_history_included')


    # greeting = 'Megan: Hi, my name is Megan. Is there something I can I help you with?'

    conversation = transcript_history + "\nDasha: " + user_statement 

    search_terms = agents.search(conversation)
    try:
        search_terms = eval(search_terms)
    except Exception as e:
        print(e)
        
    results = description_db.query(
        query_texts=search_terms,
        n_results=3
    )
    results2 = description_db2.query(
        query_texts=search_terms,
        n_results=3
    )

    search_df = pd.concat([utils.get_search_df(results, iteration), utils.get_search_df(results2, iteration)], axis=0)
#    response = requests.post('https://persuasio.onrender.com/chromadb?iteration=1&max_tokens=250&include_product_history=False', data=json.dumps({'search_terms': search_terms}))
#    search_df = pd.DataFrame(json.loads(response.content.decode('utf-8')))

    if product_history_included == 'True':
        search_df = pd.concat([search_df, pd.DataFrame(product_history)], axis=0) 
    search_df = search_df.drop_duplicates(subset='id', inplace=False)
    #print("\n".join([i for i in search_df['image']]))
    
    images = ["<table><tr><td><img src='{}'></img></td></tr><tr><td><b>{}.</b> {}</td></tr></table>".format(i[1].split("\n")[0], i[0] + 1, t) for i, t in zip(enumerate(search_df['image']), search_df['title'])]
            #print(results['metadatas'][i][j]['title'], ', $' + str(results['metadatas'][i][j]['price']))

    product_info = ''
    ct = 1
    for idx, title, avg_rating, rating_n, price, text in zip(search_df['id'], search_df['title'], search_df['average_rating'],
                                                             search_df['rating_number'], search_df['price'], search_df['description']):
        review_summary = agents.summarize(utils.subsample(reviews_df[reviews_df['parent_asin'] == idx], 20))
        product_info += "{}. {}\n- {}\n\nSummary of a Sample of Reviews\n{}\n\n".format(ct, title, text, review_summary)   
        product_info += "Overall Average: {}\nNumber of Ratings: {}\nPrice: ${}\n\n".format(avg_rating, rating_n, price)
        ct += 1

    reply = re.sub("\n", ' ', agents.salesman(conversation, product_info))

    transcript = conversation + "\nMegan: " + reply
    return page.format(re.sub("\n", "<br>", re.sub('Dasha:', '<b>Dasha</b>:', re.sub('Megan:', '<b>Megan</b>:', transcript))), json.dumps(search_df.to_dict()),  transcript,  "<br>".join(images))
    
# conversation.append('Megan: ' + utils.remove_name('Megan', reply))
# reply = input(reply)
# conversation.append('Dasha: ' + utils.remove_name('Dasha', reply))
# old_search_df = search_df.copy()




@app.route("/favicon.ico", methods = ['GET'])
def favi():
    return 'Nice to see you'


