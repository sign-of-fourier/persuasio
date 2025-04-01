import re

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