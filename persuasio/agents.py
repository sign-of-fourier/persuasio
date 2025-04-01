import boto3
import json
import re
from botocore.exceptions import ClientError
import random
import os


nova_config = {'max_tokens': 256,
               'topP': .8,
               'topK': 100,
               'temp': .9}


def call_nova(system, user,config):
    text = []

    client = boto3.client(service_name="bedrock-runtime", region_name='us-east-2',
                          aws_access_key_id=os.environ['AWS_ACCESS_KEY'],
                          aws_secret_access_key=os.environ['AWS_SECRET_KEY'])

    model_id = 'arn:aws:bedrock:us-east-2:344400919253:inference-profile/us.amazon.nova-micro-v1:0'
#    model_id = 'arn:aws:bedrock:us-east-2:344400919253:inference-profile/us.amazon.nova-lite-v1:0'
    system_list = [
            {
                "text": system
            }
    ]

    message_list = [{"role": "user", "content": user}]

    # Configure the inference parameters.
    inf_params = {"maxTokens": config['max_tokens'], "topP": config['topP'], "topK": config['topK'], "temperature": config['temp']}

    request_body = {
        "schemaVersion": "messages-v1",
        "messages": message_list,
        "system": system_list,
        "inferenceConfig": inf_params,
    }

    
    response = client.invoke_model_with_response_stream(
        modelId=model_id, body=json.dumps(request_body)
    )
    
    request_id = response.get("ResponseMetadata").get("RequestId")
    
    chunk_count = 0
    time_to_first_token = None
    
    stream = response.get("body")
    if stream:
        for event in stream:
            chunk = event.get("chunk")
            if chunk:
                chunk_json = json.loads(chunk.get("bytes").decode())
                content_block_delta = chunk_json.get("contentBlockDelta")
                if content_block_delta:
#                    if time_to_first_token is None:
#                        time_to_first_token = datetime.now() - start_time    
#                    chunk_count += 1
#                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S:%f")
                    text.append(content_block_delta.get("delta").get("text"))
    else:
        print("No response stream received.")


    
    return re.sub("\n\n", "\n", ''.join(text))


def summarize(reviews):
    background = 'You are an editor'
    prompt = ['You will be given a list of product reviews',
              'Summarize all the reviews. Be sure to retain all of the important points.',
              'Only eliminate redundant points.',
              'Do not introduce or label your summary.',
              'Do not include a header',
              'Do you give any other text.',
              "\n### REVIEWS ###\n{}\n\n".format(reviews)]
    return call_nova(" ".join(background), [{'text': " ".join(prompt)}], nova_config)
#    return chuck_gpt.call(" ".join(background), " ".join(prompt))


def salesman(transcript_of_conversation: 'transcript', search_results: 'rag') -> 'string':

    background = ['You are a sales person at a beauty store and your name is \'Megan\'.',
                  'You are speaking with a customer.']
    prompt = ['Your goal is to help the customer shop.'
              'You are in the middle of a conversation',
              'You will be given a transcript of the conversation so far',
              'You will also be given the descriptions and reviews of some relevant products in our inventory.',
              'You get 10% comission. You want to maximize your comission without seeming too pushy.',
              'Do not label, introduce your response or add a heading.',
              'Respond in 5 sentances or less. Your comment can be very short if you\'re just trying to build a rapport.',
              "\n### SEARCH RESULTS ###\n{}\n\n".format(search_results),
              "\n### TRANSCRIPT OF CONVERSATION SO FAR ###\n{}\n\n".format(transcript_of_conversation)]
    answer = call_nova(" ".join(background), [{'text': " ".join(prompt)}], nova_config)
    return re.sub("\n", ' ', answer)
    
#    return chuck_gpt.call(" ".join(background), " ".join(prompt))



def prospect(transcript):
    background = ["You are a shopper at beauty store. Your name is 'Dasha'."]
    prompt = ['You are speaking with a sales person named \'Megan\'.',
              'You will be given a transcript of your conversation so far.',
              'Do not label, introduce your response or add a heading.',
              "\n### TRANSCRIPT OF DIALOGUE SO FAR ###\n{}\n\n".format(transcript)]
    reply = call_nova(" ".join(background), [{'text': " ".join(prompt)}], nova_config)
#    reply = chuck_gpt.call(" ".join(background), " ".join(prompt))
    return reply




example = """John: Hello, How can I help you?
Lisa: Hi. I'm remodeling my bathroom and I was wondering if you can help me pick out some good lighting? It's for the vanity.
"""
example2 = """Bart: Hello, How can I help you?
Jose: Hello. I need a lawn mower.
Bart: OK. I can help you with that. Are you looking for a riding lawnmower or push?
Jose: Push
Bart: Electric or Gas
Jose: Gas. Those electric ones aren't very powerful and I think they breakdown.
Bart: Well, actually they've gotten better but I can show you the as ones first and then if you'd like to take a quick glance at the electric ones, I can show you thoses as well
"""
answer = "```[\"Bathroom lighting that is arranged above the mirror in a bathroom is sometimes described as 'Vanity Bathroom Lighting'.\"]```"
answer2 = "```[\"A gas powered push lawn mower tends to have power and durability.\", \"Electric powered push lawnmowers are more enironmentally friendly and can save money on gas. Sometimes they have less power than gas mowers, but recently, they have been getting better.\"]```"

def search(transcript):
    background = 'You are a solution designer. Your job is to take a conversation and create relevant product descriptions.'
    prompt = ['You will be given a transcript of a conversation between a sales associate and a customer.',
              'Come up with descriptions of products discussed in the conversation.',
              'There may be more than one product being mentioned.',
              'ONLY provide the descriptions in a list format surrounded by tickmarks.',
              'DO NOT include introductions, context, rationales or any other text',
              "\n### EXAMPLE TRANSCRIPT 1 ###\n{}\n\n".format(example),
              "### EXAMPLE ANSWER 1 ###\n{}\n\n".format(answer),
              "### EXAMPLE TRANSCRIPT 2 ###\n{}\n\n".format(example2),
              "### EXAMPLE ANSWER 2 ###\n{}\n\n".format(answer2),
              "### REAL TRANSCRIPT ###\n{}\n\n".format(transcript)]

    search_terms = call_nova(" ".join(background), [{'text': " ".join(prompt)}], nova_config)
    return eval(re.sub('`', '', (search_terms)))
#    return chuck_gpt.call(" ".join(background), " ".join(prompt))

def embedding(input_text):

    client = boto3.client(service_name="bedrock-runtime", region_name='us-east-2',
                          aws_access_key_id=os.environ['AWS_ACCESS_KEY'],
                          aws_secret_access_key=os.environ['AWS_ACCESS_SECRET'])
    
    model_id = "amazon.titan-embed-text-v2:0"

    accept = "application/json"
    content_type = "application/json"
    body = json.dumps({
        "inputText": input_text,
        'dimensions': 512#,
#        "embeddingTypes": ["binary"]
    })
    response = client.invoke_model(
        body=body, modelId=model_id, accept=accept, contentType=content_type
    )

    response_body = json.loads(response.get('body').read())

    return response_body['embedding']
    


eval_config = {'max_tokens': 512,
               'topP': .5,
               'topK': 50,
               'temp': .01}


def evaluator(transcript):
    list_of_items = """
    {'pink skirt': 'low',
     'aviator sunglasses': 'low',
     'women\'s green socks': 'medium',
     'vinyl jacket': 'very low'}
"""
    background = ["You are a sales trainer.",
                  "Your job is to estimate the probability that a conversation will lead to a sale."]
    prompt = ["You will be given a transcript of a conversation.",
              "State the likliehood that conversation will lead to the sale of each item as 'Very High', 'High', 'Medium', 'Low' or 'Very Low'",
              "Always use lower case and put your answer in json format like this:{}\n".format(list_of_items),
              "Do not include any other text, introduction, rationale or explanation.",
              "### TRANSCRIPT ###\n{}\n\n".format(transcript)]
   
    return call_nova(" ".join(background), [{'text': " ".join(prompt)}], eval_config) 