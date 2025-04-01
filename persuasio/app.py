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

import utils
import agents

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


    print(product_history)
    print('----')
#    user_statment = request.form.get('user_statement')
#    system = request.form.get('system')
#    transcript_history = request.form.get('transcript_history')
  
#    product_history = request.form.get('product_history')
#    max_tokens = request.args.get('max_tokens')


    
    # message = client.messages.create(
    #     model = 'us.anthropic.claude-3-haiku-20240307-v1:0',
    #     max_tokens = int(max_tokens),
    #     system = system,
    #     messages=[{"role": "user", "content": prompt}]
    # )

    # new_results = history + "\n<b>You</b>: " + prompt + "\n<b>Claude</b>: " + message.content[0].text
    # return page.format(re.sub("\n", "<br>", new_results), new_results)

    client = chromadb.PersistentClient(path="chroma_small")
    description_db = client.get_collection(name="amazon_beauty_descriptions")
    reviews_df = pd.read_csv('reviews.csv.gz', compression='gzip')

    # greeting = 'Megan: Hi, my name is Megan. Is there something I can I help you with?'

    conversation = transcript_history + "\nDasha: " + user_statement + "\n"


    search_terms = agents.search(conversation)
    results = description_db.query(
        query_texts=search_terms,
        n_results=3
    )
    search_df = pd.DataFrame({'title': [title['title'] for meta in results['metadatas'] for title in meta],
                             'description': [d for doc in results['documents'] for d in doc],
                             'id': [idx for ids in results['ids'] for idx in ids]})
    if len(product_history) > 0:
        pd.concat([search_df, pd.DataFrame(product_history)], axis=0) 

    search_df = search_df.drop_duplicates(subset='id', inplace=False)
    images = []
    for i in range(len(results['metadatas'])):
        for j in range(len(results['metadatas'][i])):
            images.append("<img src='{}'></img>".format(results['metadatas'][i][j]['thumb'].split("\n")[0]))
            #print(results['metadatas'][i][j]['title'], ', $' + str(results['metadatas'][i][j]['price']))

    product_info = ''
    for y in range(len(results['ids'])):
        for x in range(len(results['ids'][y])):
            review_summary = agents.summarize(utils.subsample(reviews_df[reviews_df['parent_asin'] == results['ids'][y][x]], 20))
            product_info += "{}. {}\n- {}\n\nSummary of a Sample of Reviews\n{}\n\n".format(x+1, results['metadatas'][y][x]['title'], results['documents'][y][x], review_summary)   
            product_info += "Overall Average: {}\nNumber of Ratings: {}\nPrice: ${}\n\n".format(results['metadatas'][y][x]['average_rating'], 
                                                                                                results['metadatas'][y][x]['rating_number'],
                                                                                                results['metadatas'][y][x]['price'])
    return "\n".join(images) + "<br><p>" + product_info

# reply = agents.salesman(" ".join(conversation), product_info)
# conversation.append('Megan: ' + utils.remove_name('Megan', reply))
# reply = input(reply)
# conversation.append('Dasha: ' + utils.remove_name('Dasha', reply))
# old_search_df = search_df.copy()




@app.route("/favicon.ico", methods = ['GET'])
def favi():
    return 'Nice to see you'


