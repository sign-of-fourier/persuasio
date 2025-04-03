from flask import Flask, request

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

import persuasio.utils
import persuasio.agents

app = Flask(__name__)

page = """
<html>
<p>{}
<form id=claude action='http://127.0.0.1:5000/claude?max_tokens=256' method=POST>
<input type = 'hidden' name='history' rows=5 cols=80 value="{}"><br>
<input id='prompt' name='prompt' type=text size=100></input>
<input name='system' type='hidden' value='You are from New Jersey. Speak in a thick Jersey accent.'></input>
<input type='submit' value='Submit'></input>
</form>
"""

@app.route("/persuasio", methods = ['POST'])
def persuasio():
    data = json.loads(request.data)   
    transcript_history = data['transcript_history']
    user_statement = data['user_statement']
    product_history = data['product_history']
    iteration = data['iteration']


#    user_statment = request.form.get('user_statement')
#    system = request.form.get('system')
#    transcript_history = request.form.get('transcript_history')
  
#    product_history = request.form.get('product_history')
    max_tokens = request.args.get('max_tokens')
    product_history_included = request.args.get('product_history_included')

    client = chromadb.PersistentClient(path="chroma_small")
    client2 = chromadb.PersistentClient(path="chroma_small2")
    description_db = client.get_collection(name="amazon_beauty_descriptions")
    description_db2 = client2.get_collection(name="amazon_beauty_descriptions2")
    reviews_df = pd.read_csv('reviews.csv.gz', compression='gzip')

    # greeting = 'Megan: Hi, my name is Megan. Is there something I can I help you with?'

    conversation = transcript_history + "\nDasha: " + user_statement + "\n"


    search_terms = agents.search(conversation)
    try:
        search_terms = eval(search_terms)
    except Exception as e:
        print(e)
#    print(search_terms)
        
    results = description_db.query(
        query_texts=search_terms,
        n_results=3
    )
    results2 = description_db2.query(
        query_texts=search_terms,
        n_results=3
    )

    search_df = pd.concat([utils.get_search_df(results, iteration), utils.get_search_df(results2, iteration)], axis=0)
    if product_history_included == 'True':
        search_df = pd.concat([search_df, pd.DataFrame(product_history)], axis=0) 
    
    search_df = search_df.drop_duplicates(subset='id', inplace=False)
    images = ["<img src='{}'></img>{}".format(i.split("\n")[0], t) for i, t in zip(search_df['image'], search_df['title'])]
            #print(results['metadatas'][i][j]['title'], ', $' + str(results['metadatas'][i][j]['price']))

    product_info = ''
    ct = 1
    for idx, title, avg_rating, rating_n, price, text in zip(search_df['id'], search_df['title'], search_df['average_rating'],
                                                             search_df['rating_number'], search_df['price'], search_df['description']):
        review_summary = agents.summarize(utils.subsample(reviews_df[reviews_df['parent_asin'] == idx], 20))
        product_info += "{}. {}\n- {}\n\nSummary of a Sample of Reviews\n{}\n\n".format(ct, title, text, review_summary)   
        product_info += "Overall Average: {}\nNumber of Ratings: {}\nPrice: ${}\n\n".format(avg_rating, rating_n, price)
        ct += 1

    reply = agents.salesman(conversation, product_info)
    return json.dumps({'images': "\n".join(images), 
                      'product_info': product_info, 'transcript_history': conversation + "\nMegan: " + reply,  'reply': reply,
                      'product_history': search_df.to_dict()}) 

# conversation.append('Megan: ' + utils.remove_name('Megan', reply))
# reply = input(reply)
# conversation.append('Dasha: ' + utils.remove_name('Dasha', reply))
# old_search_df = search_df.copy()




@app.route("/favicon.ico", methods = ['GET'])
def favi():
    return 'Nice to see you'


