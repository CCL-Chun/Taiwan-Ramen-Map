from sklearn.metrics.pairwise import cosine_similarity
from ast import literal_eval
from dotenv import load_dotenv
from datetime import datetime, timedelta
from openai import OpenAI
from Database import MongoDBConnection
from pymongo import UpdateOne
import pandas as pd
import numpy as np
import tiktoken
import logging
import boto3
import json
import pytz
import re
import os

## write to log
logging.basicConfig(level=logging.INFO,filename='log_embeddings.txt',filemode='a',
    format='%(asctime)s %(levelname)s:%(message)s')

load_dotenv()  # Load environment variables
s3_bucket = os.getenv("s3_bucket")
OpenAI_API_KEY = os.getenv("openAI_API_Key")
client_openai = OpenAI(api_key=OpenAI_API_KEY)
timezone = pytz.timezone('Asia/Taipei')

embedding_model = "text-embedding-3-small"
embedding_encoding = "cl100k_base"
max_tokens = 8191  # the maximum for text-embedding-3-small is 8191

## connect to cloud MongoDB
try:
    connection = MongoDBConnection()
    collection = connection.get_collection('ramen_info')
except Exception as e:
    logging.error(e)

# 
def convert_to_stars(rating):
    return '★' * int(rating)
# 
def get_embedding(text, model=embedding_model):
   text = text.replace("\n", " ")
   return client_openai.embeddings.create(input = [text],model=model).data[0].embedding

# list files to get text embeddings
def list_latest_files(bucket_name, start_datetime, end_datetime):
    s3_client = boto3.client('s3')
    paginator = s3_client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket_name)

    files_within_range = []
    for page in pages:
        for obj in page.get('Contents', []):
            if start_datetime <= obj['LastModified'] <= end_datetime:
                files_within_range.append(obj['Key'])
    return files_within_range

# processing logic
def process_json_documents(bucket_name, file_key):
    s3_client = boto3.client('s3')
    obj = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    documents = json.load(obj['Body'])
    
    # Data extraction and processing
    data = []
    operations = []

    for doc in documents:
        place_id = doc.get('place_id', None)
        name = doc.get('name', None)
        for review in doc.get('reviews', []):
            user_id = review.get('user_id')
            rating = review.get('rating')
            comment = review.get('comment',None)
            data.append({'name': name,'place_id': place_id, 'user_id': user_id, 'rating': rating, 'comment': comment})

        location = {
            "type":"Point",
            "coordinates":[
                float(doc.get("longitude", 120.9572579)),float(doc.get("latitude", 23.4699818))
            ]
        }
        query = {"name": doc["name"]}
        update = {
            "$set": {
                "name": name,
                "maps_url":doc.get("maps_url",""),
                "img_url":doc.get("img_url",""),
                "img_base64":doc.get("img_base64",""),
                "open_time":doc.get("open_time",{}),
                "website":doc.get("website",""),
                "overall_rating":doc.get("overall_rating",{}),
                "address":doc.get("address",""),
                "create_time":datetime.now(pytz.utc),
                "update_time":datetime.now(pytz.utc),
                "location": location,
                "place_id":place_id
            }
        }
        operation = UpdateOne(query, update, upsert=True)
        operations.append(operation)

    logging.info(f"Finish: Retrieve {file_key} from S3.")

    try:
        if operations:
            result = collection.bulk_write(operations, ordered=False)
            logging.info(f"Ramen data updated successfully: {result.bulk_api_result}")
        else:
            logging.info("No Ramen data to update.")
    except Exception as e:
        logging.error(f"Error during Ramen data bulk update: {e}")

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
    logging.info(f"Finish: fetching documents with embeddings. Total {df.shape[0]} reviews.")

    df[["name","place_id","user_id","rating","combined","n_tokens","embeddings"]].to_csv("new_embeddings.csv",mode='a', header=False)

    logging.info(f"Done {file_key} with embeddings. Total {df.shape[0]} reviews.")



# Start the work
start_datetime = datetime.now(timezone) - timedelta(days=1)
end_datetime = datetime.now(timezone)
file_keys = list_latest_files("ramen-selenium-results", start_datetime, end_datetime)
for file_key in file_keys:
    process_json_documents("ramen-selenium-results", file_key)


##---------------------------------------Count the similarity -------------------------------#

# df = read_csv_from_s3(s3_bucket,file_to_read)
# ## convert embeddings as numpy array
# df["embeddings"] = df.embeddings.apply(literal_eval).apply(np.array)
# ## calculate median of embeddings among the same place_id
# median = df.groupby('place_id')['embeddings'].agg(lambda x: np.median(np.array(list(x)), axis=0)).reset_index()
# print(median.head())

# ## create a place-to-place similarity DF
# # Step 1: Create a matrix of median embeddings
# embeddings_matrix = np.vstack(median['embeddings'].values)

# # Step 2: Calculate the cosine similarity matrix
# similarity_matrix = cosine_similarity(embeddings_matrix)

# # Step 3: Convert the similarity matrix to a DataFrame
# place_ids = median['place_id'].tolist()
# np.fill_diagonal(similarity_matrix, -np.inf)

# # get the indices of the top 5 elements, excluding the diagonal
# top_10_indices = np.argpartition(similarity_matrix, -10, axis=1)[:, -10:]

# # create a list for the new DataFrame
# rows_list = []

# # iterate through each place_id and its top 5 indices
# for idx, indices in enumerate(top_5_indices):
#     place_id1 = place_ids[idx]
#     for index in indices:
#         place_id2 = place_ids[index]
#         similarity = similarity_matrix[idx][index]
#         # Create a dictionary for the row and append to the list
#         row = {'place_id1': place_id1, 'place_id2': place_id2, 'similarity': similarity}
#         rows_list.append(row)

# # create a DataFrame from the list of rows
# similarity_df = pd.DataFrame(rows_list)

# # sort by place_id1 and similarity score to get the top 5 per place_id1
# similarity_df = similarity_df.sort_values(by=['place_id1', 'similarity'], ascending=[True, False])

# top_10_similarity_df = similarity_df.groupby('place_id1').head(10).reset_index(drop=True)

# local_time = datetime.now(timezone).strftime("%Y_%m_%d_%H_%M_%S")
# top_10_similarity_df.to_csv(f'similarity_{local_time}.csv')



# # connect to cloud MongoDB
# try:
#     connection = MongoDBConnection()
#     collection = connection.get_collection('ramen_info')
# except Exception as e:
#     print(e)

# from pymongo import UpdateOne
# operations = []
# for place_id1, group_df in top_5_similarity_df.groupby('place_id1'):
#     # Extract the top 5 place_id2 as a list
#     top_places = group_df['place_id2'].tolist()
#     # Prepare the update operation
#     operation = UpdateOne(
#         {'place_id': place_id1},
#         {'$set': {'top_similar': top_places}},
#         upsert=True
#     )
#     # Add the operation to the list
#     operations.append(operation)

# ## upsert top_similar_places into MongoDB by their place_id
# result = collection.bulk_write(operations,ordered=False)
