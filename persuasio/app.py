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

<table border=1>
    <tr>
      <td>
      <form action='/persuasio?max_tokens=256&iteration={}&product_history_included=True' method=post>
          <input type=hidden name=product_history value='{}'></input>
          <b>Department</b>: {}
          <input type=hidden name=department value="{}"></input>
             <br><br>
             {}<br><br>
             <input type=hidden name=transcript_history value="{}"></input>
          <input type=text name='user_statement'></input>
          <input type=submit name=submissize value=Chat></input></input>
      </form>
      </td>
      <td>
      <p id='pics'><div style="height:700px; width700px;border:1px sold #ccc;font:16px/26px Georgia, Garamond, Serif;overflow:auto;">{}</div>
      </td>
    </tr>
</table>
<br>
<br><a href="https://persuasio.onrender.com/">Start a new conversation.</a>
<font color='white'>{}</font>

"""
name = 'Persephone'
customer_name = 'Guest'

url = ''
if 'CHROMADB' in os.environ.keys():
    import chromadb
    
    descriptions_db = {'Beauty': [chromadb.PersistentClient(path="persuasio/chroma_small").get_collection(name="amazon_beauty_descriptions"),
                                  chromadb.PersistentClient(path="persuasio/chroma_small2").get_collection(name="amazon_beauty_descriptions2")],
                       'Appliances': [chromadb.PersistentClient(path="persuasio/chroma_appliances").get_collection(name="amazon_appliances_descriptions"),
                                      chromadb.PersistentClient(path="persuasio/chroma_appliances2").get_collection(name="amazon_appliances_descriptions2"),
                                      chromadb.PersistentClient(path="persuasio/chroma_appliances3").get_collection(name="amazon_appliances_descriptions3")]
                            } 

reviews_df = {'Beauty': pd.read_csv('persuasio/reviews.csv.gz', compression='gzip'),
              'Appliances': pd.read_csv('persuasio/appliances_reviews.csv.gz', compression='gzip')}

welcome_page = """
<html>
<title>Persuasio</title>
<center><h2>Persephone </h2></center>
<hr>
Meet Persephone. The worlds first persuasive shopping assistant!
<br>
She is knolwedgable about a variety of products and their reviews.<br>
<form action='/persuasio?max_tokens=205&iteration=0&product_history_included=False' method=post>
    <input type=hidden name=product_history value='None'></input>
    <label for=Department>Department:</label>
    <select name="department" id="department">
        <option value="Beauty">Beauty</option>
        <option value="Appliances">Appliances</option>
    </select><br><br>
    <input type=hidden name=transcript_history value='{}: Hi. How can I help you?'></input>
    <input type=text name='user_statement' value="What's the best perfume?"></input>
    <input type=submit name=submissize value=Chat></input></input>
</form>
</html>
"""
@app.route("/")
def welcome():
    return welcome_page.format(name)

    
def embeddingdb(department, search_terms, iteration):
    
    results = []
    for db in descriptions_db[department]:
        results.append(db.query(
            query_texts=search_terms,
            n_results=3
        )
                      )

    return pd.concat([utils.get_search_df(r, iteration) for r in results], axis=0)


def chat_bot(user_statement, department, transcript_history, product_history, iteration, max_tokens, product_history_included):

    conversation = transcript_history + "\n"+customer_name+": " + user_statement 
    search_terms = agents.search("\n".join(conversation.split("\n")[:10]), department)
    try:
        search_terms = eval(search_terms)
    except Exception as e:
        print(e)

    if 'CHROMADB' in os.environ.keys():
        search_df = embeddingdb(department, search_terms, iteration)
    else:
        response = requests.post('https://persuasio.onrender.com/chromadb?iteration={}&max_tokens={}&include_product_history={}'.format(iteration, max_tokens, product_history_included), data=json.dumps({'search_terms': search_terms, 'iteration': iteration, 'department': department}))
        try:
            search_df = pd.DataFrame(json.loads(response.content.decode('utf-8')))
        except Exception as e:
            print(e)
            return response.content
    if product_history_included == 'True':
        search_df = pd.concat([search_df, pd.DataFrame(json.loads(product_history))], axis=0) 

    mx = np.max(pd.DataFrame(search_df)['iteration'])
    search_df = search_df[search_df['iteration'] >= (int(mx)-2)].sort_values('distances').head(10)
    search_df = search_df.drop_duplicates(subset='id', inplace=False)
    
    #print("\n".join([i for i in search_df['image']]))
    
    images = ["<table><tr><td><img src='{}'></img></td></tr><tr><td><b>{}.</b> {}</td></tr></table>\n".format(i[1].split("\n")[0], i[0] + 1, t) for i, t in zip(enumerate(search_df['image']), search_df['title'])]
            #print(results['metadatas'][i][j]['title'], ', $' + str(results['metadatas'][i][j]['price']))

    product_info = ''
    ct = 1
    for idx, title, avg_rating, rating_n, price, text in zip(search_df['id'], search_df['title'], search_df['average_rating'],
                                                             search_df['rating_number'], search_df['price'], search_df['description']):
        review_summary = agents.summarize(utils.subsample(reviews_df[department][reviews_df[department]['parent_asin'] == idx], 20))
        product_info += "{}. {}\n- {}\n\nSummary of a Sample of Reviews\n{}\n\n".format(ct, title, text, review_summary)   
        product_info += "Overall Average: {}\nNumber of Ratings: {}\nPrice: ${}\n\n".format(avg_rating, rating_n, price)
        ct += 1

    reply = re.sub("\n", ' ', agents.salesman(department, conversation, product_info))

    transcript = conversation + "\n" + name + ": " + reply
    search_df_text = re.sub("'", "&apos;", json.dumps(search_df.to_dict()))
    return page.format(iteration+1, search_df_text, department, department,
                       re.sub("\n", "<br>", re.sub(customer_name+':', '<b>'+customer_name+'</b>:', re.sub(name+':', '<b>'+name+'</b>:', transcript))), 
                       transcript,  "<br>".join(images), search_terms)

@app.route("/persuasio_json", methods = ['POST'])
def persuasio_json():

    data = json.loads(request.data)
    return chat_bot(data['user_statement'], data['department'], data['transcript_history'],
                    data['product_history'], data['iteration'],  request.args.get('max_tokens'),
                    request.args.get('product_history_included'))

@app.route("/persuasio", methods = ['POST'])
def persuasio():
    return chat_bot(request.form.get('user_statement'), request.form.get('department'), request.form.get('transcript_history'),
                    request.form.get('product_history'), int(request.args.get('iteration')),  request.args.get('max_tokens'),
                    request.args.get('product_history_included'))



@app.route('/chromadb', methods = ['POST'])
def call_chroma():
    data = json.loads(request.data)
    return json.dumps(embeddingdb(data['department'], data['search_terms'], data['iteration']).to_dict())


@app.route("/favicon.ico", methods = ['GET'])
def favi():
    return 'Nice to see you'


