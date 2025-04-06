import os

from flask import Flask, request
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
<title>Persuasio</title>

<table>
<tr>
<td>
<p id='paragraph'>{}
<form action='/persuasio?max_tokens=256&iteration={}&product_history_included=True' method=post>
    <input type=hidden name=product_history value='{}'></input>
    <input type=hidden name=system value='You are a sales person at Amazon.'></input>
    <input type=hidden name=transcript_history value="{}"></input>
    <input type=text name='user_statement'></input>
    <input type=submit name=submissize value=Chat></input></input>
</form>
</td>
<td>
<p id='pics'><div style="height:700px; width700px;border:1px sold #ccc;font:16px/26px Georgia, Garamond, Serif;overflow:auto;">{}</div>
</td>
</tr>
"""
name = 'Megan'
url = ''
if 'CHROMADB' in os.environ.keys():
    import chromadb
    client = chromadb.PersistentClient(path="persuasio/chroma_small")
    client2 = chromadb.PersistentClient(path="persuasio/chroma_small2")
    description_db = client.get_collection(name="amazon_beauty_descriptions")
    description_db2 = client2.get_collection(name="amazon_beauty_descriptions2")


reviews_df = pd.read_csv('persuasio/reviews.csv.gz', compression='gzip')

welcome_page = """
<html>
<title>Persuasio</title>
<center><h2>Persuasio </h2></center>
<hr>
Meet Persephone. The worlds first persuasive shopping assistant!
<br>
She is knolwedgable about beauty products.
<form action='/persuasio?max_tokens=205&iteration=0&product_history_included=False' method=post>
    <input type=hidden name=product_history value='None'></input>
    <input type=hidden name=system value='You are a sales person at Amazon.'></input>
    <input type=hidden name=transcript_history value='Megan: Hi. How can I help you?'></input>
    <input type=text name='user_statement' value="What's the best perfume?"></input>
    <input type=submit name=submissize value=Chat></input></input>
</form>
</html>
"""
@app.route("/")
def welcome():
    return welcome_page

@app.route('/chromadb', methods = ['POST'])
def embeddingdb():
    
    data = json.loads(request.data)
    results = description_db.query(
        query_texts=data['search_terms'],
        n_results=3
        )
    results2 = description_db2.query(
        query_texts=data['search_terms'],
        n_results=3
    )
    search_df = pd.concat([utils.get_search_df(results, data['iteration']), utils.get_search_df(results2, data['iteration'])], axis=0)
    
    return json.dumps(search_df.to_dict())
        
def chat_bot(user_statement, system, transcript_history, product_history, iteration, max_tokens, product_history_included):

    conversation = transcript_history + "\nDasha: " + user_statement 

    search_terms = agents.search(conversation)
    try:
        search_terms = eval(search_terms)
    except Exception as e:
        print(e)
        
    
    if 'CHROMADB' in os.environ.keys():
        
        results = description_db.query(
            query_texts=search_terms,
            n_results=3
        )
        results2 = description_db2.query(
            query_texts=search_terms,
            n_results=3
        )
        search_df = pd.concat([utils.get_search_df(results, iteration), utils.get_search_df(results2, iteration)], axis=0)
    else:
        response = requests.post('https://persuasio.onrender.com/chromadb?iteration=1&max_tokens=250&include_product_history=False', data=json.dumps({'search_terms': search_terms, 'iteration': iteration}))
        try:
            search_df = pd.DataFrame(json.loads(response.content.decode('utf-8')))
        except Exception as e:
            print(e)
            return response.content
    if product_history_included == 'True':
        search_df = pd.concat([search_df, pd.DataFrame(json.loads(product_history))], axis=0) 
        
    search_df = search_df.drop_duplicates(subset='id', inplace=False)
    #print("\n".join([i for i in search_df['image']]))
    
    images = ["<table><tr><td><img src='{}'></img></td></tr><tr><td><b>{}.</b> {}</td></tr></table>\n".format(i[1].split("\n")[0], i[0] + 1, t) for i, t in zip(enumerate(search_df['image']), search_df['title'])]
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
    search_df_text = re.sub("'", "&apos;", json.dumps(search_df.to_dict()))
    return page.format(re.sub("\n", "<br>", re.sub('Dasha:', '<b>Dasha</b>:', re.sub('Megan:', '<b>Megan</b>:', transcript))), 
                       iteration+1,
                       search_df_text,  transcript,  "<br>".join(images), iteration+1)

@app.route("/persuasio_json", methods = ['POST'])
def persuasio_json():
    

    data = json.loads(request.data)
    return chat_bot(data['user_statement'], data['system'], data['transcript_history'],
                    data['product_history'], data['iteration']+1,  request.args.get('max_tokens'),
                    request.args.get('product_history_included'))
    

@app.route("/persuasio", methods = ['POST'])
def persuasio():
    return chat_bot(request.form.get('user_statement'), request.form.get('system'), request.form.get('transcript_history'),
                    request.form.get('product_history'), int(request.args.get('iteration'))+1,  request.args.get('max_tokens'),
                    request.args.get('product_history_included'))
    




@app.route("/favicon.ico", methods = ['GET'])
def favi():
    return 'Nice to see you'


