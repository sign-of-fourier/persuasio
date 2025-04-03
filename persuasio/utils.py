import re
import pandas as pd

def extract_json(answer):

    cleaned_answer = re.sub('`', '', answer)
    cleaned_answer = re.sub('json', '', cleaned_answer)
    cleaned_answer = re.sub('null', 'np.nan', cleaned_answer)
    cleaned_answer = re.sub("\n", ' ', cleaned_answer)
    cleaned_answer = re.sub("”", "\"", cleaned_answer)
    cleaned_answer = re.sub("\$", '', cleaned_answer)
    
    return eval(cleaned_answer)
    
def remove_name(name, text):
    lines = [x for x in text.split("\n") if len(x) > 0]
    lines[0] = re.sub(name + ': ', '', lines[0])
    return lines[0] + "\n" + "\n".join(['     '  + x for x in lines[1:]])

def subsample(df, n):
    if df.shape[0] > n:
        sdf = df.sample(n)
    else:
        sdf = df
    return "\n".join(["Review: {}\n- {}\nRating: {}\n".format(t, v, r) for t, v, r in zip(sdf['title'], 
                                                                                          sdf['text'],
                                                                                          sdf['rating'])])

def get_search_df(results, iteration):
    search_df = pd.DataFrame({'title': [title['title'] for meta in results['metadatas'] for title in meta],
                              'description': [d for doc in results['documents'] for d in doc],
                              'average_rating': [m['average_rating'] for meta in results['metadatas'] for m in meta],
                              'rating_number': [m['rating_number'] for meta in results['metadatas'] for m in meta],
                              'price': [m['price'] for meta in results['metadatas'] for m in meta],
                              'id': [idx for ids in results['ids'] for idx in ids],
                              'image': [i['large'] for images in results['metadatas'] for i in images],
                              'distances': [d for distance in results['distances'] for d in distance],
                              'iteration': iteration})
    return search_df
