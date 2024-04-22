from openai import OpenAI
from Database import MongoDBConnection
from dotenv import load_dotenv
import pandas as pd
import tiktoken
import logging
import re
import os

## write to log
logging.basicConfig(level=logging.INFO,filename='log_embeddings.txt',filemode='a',
    format='%(asctime)s %(levelname)s:%(message)s')

## load .env to get OpenAI_API_KEY
load_dotenv()
OpenAI_API_KEY = os.getenv("openAI_API_Key")
client_openai = OpenAI(api_key=OpenAI_API_KEY)

embedding_model = "text-embedding-3-small"
embedding_encoding = "cl100k_base"
max_tokens = 8191  # the maximum for text-embedding-3-small is 8191
# 
def convert_to_stars(rating):
    return '★' * int(rating)
# 
def get_embedding(text, model=embedding_model):
   text = text.replace("\n", " ")
   return client_openai.embeddings.create(input = [text],model=model).data[0].embedding


## connect to cloud MongoDB
try:
    connection = MongoDBConnection()
    collection = connection.get_collection('ramen_info')
except Exception as e:
    logging.error(e)

# batch size and start position
batch_size = 50
start_position = 0

total_documents = collection.count_documents({})

while start_position < total_documents:
    try:
        documents = list(collection.find({}).skip(start_position).limit(batch_size))

        data = []
        for doc in documents:
            object_id = doc.get('_id')
            place_id = doc.get('place_id', None)
            name = doc.get('name', None)
            for review in doc.get('reviews', []):
                user_id = review.get('user_id')
                rating = review.get('rating')
                comment = review.get('comment',None)
                data.append({'name': name,'place_id': place_id, 'user_id': user_id, 'rating': rating, 'comment': comment})

        logging.info(f"Finish: Retrieve {documents} ramen from Database.")
        logging.info(f"Start: Start to request {len(data)} embeddings from OpenAI API.")

        df = pd.DataFrame(data)
        df.dropna(subset=["comment"],inplace=True)
        df["comment"].replace({'\n': ' ', '\r\n': ' '}, regex=True, inplace=True)
        df["combined"] = (
            'Score: ' + df['rating'].apply(convert_to_stars) + '; Content: ' + df['comment'].astype(str).str.strip()
        )

        encoding = tiktoken.get_encoding(embedding_encoding)
        df["n_tokens"] = df.combined.apply(lambda x: len(encoding.encode(x)))
        df = df[df.n_tokens <= max_tokens]
        df['embeddings'] = df.combined.apply(lambda x: get_embedding(x, model=embedding_model))
        logging.info(f"Finish: fetching {start_position} documents with embeddings. Total {df.shape[0]} reviews.")

        df[["name","place_id","user_id","rating","combined","n_tokens","embeddings"]].to_csv("test.csv",mode='a', header=False)
        
        start_position += batch_size

        logging.info(f"Done {start_position} documents with embeddings. Total {df.shape[0]} reviews.")
    except Exception as e:
        logging.exception(f'An error occurred at batch position {start_position}: {str(e)}')
        break
