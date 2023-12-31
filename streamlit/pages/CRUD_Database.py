import requests
import streamlit as st
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import pandas as pd
import time
import pinecone
import boto3
import numpy as np
import openai
import io
import PyPDF2
from textblob import TextBlob
import tiktoken
import nltk
import numpy as np
nltk.download('punkt')
import csv



#Conecting to Pine cone database
try:
    pinecone.init(api_key=st.secrets['PINECONE_API_KEY'], environment=st.secrets['PINECONE_ENV'])
    index = pinecone.Index('bigdata')
    print("Pinecone initialization and index creation successful.")
except Exception as e:
    print("An error occurred:", str(e))


#Connecting to S3 bucket
s3_bucket = 'csv07'
s3_object_key = 'filenames.csv'
aws_access_key_id = st.secrets['AWS_ACCESS_KEY_ID']
aws_secret_access_key = st.secrets['AWS_SECRET_ACCESS_KEY']
aws_region = st.secrets['AWS_REGION']
API_ENDPOINT = st.secrets['FASTAPI_ENDPOINT']
s3_client = boto3.client('s3', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key,region_name=aws_region)
EMBEDDING_MODEL = "text-embedding-ada-002"
GPT_MODEL = "gpt-3.5-turbo"



def gen_embed(chunk_list, api_key):
    embed_list = []
    openai.api_key = api_key
    for i in chunk_list:
        text_embedding_response = openai.Embedding.create(
            model=EMBEDDING_MODEL,
            input=i,
        )
        text_embedding = text_embedding_response["data"][0]["embedding"]
        embed_list.append(text_embedding)
        time.sleep(20)
    return embed_list


def extract_sentences(text):
    blob = TextBlob(text)
    sentence_list = []
    # Iterate through the sentences and append them to the list
    for sentence in blob.sentences:
        sentence_list.append(sentence.raw)
    return sentence_list


def extract_text_with_pypdf2(pdf_content):
    pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
    text = ""
    meta_data = pdf_reader.metadata
    meta_data = list(meta_data.values())[0]
    for page_num in range(len(pdf_reader.pages)):
        page = pdf_reader.pages[page_num]
        text += page.extract_text()
    return [meta_data,text]

def create_chunk_list(sentence_list):
    l = len(sentence_list)
    chunk_list = []
    chunk = ''
    encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
    for i in range(l):
        chunk+=sentence_list[i]
        if len(encoding.encode(chunk))<3000:
            if i==l-1:
                chunk_list.append(chunk)
            continue
        else:
            chunk_list.append(chunk)
            chunk = ''
    return chunk_list


def extract_pdf_content(link, api_key):
    filename = link.split('/')[-1]
    pdf_response = requests.get(link)
    pdf_content = pdf_response.content
    meta_data, pdf_text = extract_text_with_pypdf2(pdf_content)
    sentences_list = extract_sentences(pdf_text.strip())
    chunk_list = create_chunk_list(sentences_list)
    embeddings_list = gen_embed(chunk_list, api_key)
    df_temp = pd.DataFrame({'Filename':filename,'Metadata': meta_data,'Text': chunk_list, 'Embeddings':embeddings_list})
    
    # st.write(df_temp.head(10))
    return df_temp.copy()

#########################################################################################

def get_ids_from_query(index,input_vector):
  results = index.query(vector=input_vector, top_k=10000,include_values=False)
  ids = set()
  for result in results['matches']:
    ids.add(result['id'])
  return ids


def get_all_ids_from_index(index, num_dimensions, namespace=""):
  
    input_vector = np.random.rand(1536).tolist()
    results = index.query(vector=input_vector, top_k=100,include_values=False)
    all_ids = []
    for i in results['matches']:
        all_ids.append(str(i['id']))
  
#   num_vectors = index.describe_index_stats()["namespaces"][""]["vector_count"]
# #   ["namespaces"]['']['vector_count']
#   print("Num Vectors:",num_vectors)
#   all_ids = set()
#   while len(all_ids) < num_vectors:
#     input_vector = np.random.rand(num_dimensions).tolist()
#     ids = get_ids_from_query(index,input_vector)
#     all_ids.update(ids)
    return all_ids


def add_to_pinecone(df):
    starting_index = max([int(i) for i in get_all_ids_from_index(index,1536)])+1
    df['Index'] = range(starting_index, starting_index + len(df))
    df['Index'] = df['Index'].astype(str)

    # Setting batch size as 32
    batch_size = 32
    for i in range(0, len(df), batch_size):
        batch_df = df[i:i + batch_size]
        id_list = batch_df['Index'].tolist()
        embeds = batch_df['Embeddings'].tolist()
        text_list = batch_df['Text'].tolist()
        file_list = batch_df['Filename'].tolist()
        metalist = batch_df['Metadata'].tolist()
        m_list = []
        for i in range(len(text_list)):
            m = {'Filename': file_list[i], 'Text': text_list[i], 'Metadata': metalist[i]}
            m_list.append(m)
        to_upsert = zip(id_list, embeds, m_list) 
        index.upsert(vectors=list(to_upsert))

    


def upload_csv_to_s3(name):
    file_path = st.secrets["FILENAME"]  # Replace with the path to your existing CSV file
    df = pd.read_csv(file_path)

    # Create a new DataFrame with the additional file name
    data_to_add = {'Name': [name]}
    df_to_add = pd.DataFrame(data_to_add)

    # Concatenate the two DataFrames
    combined_df = pd.concat([df, df_to_add], ignore_index=True)

    # Write the combined DataFrame back to the CSV file
    combined_df.to_csv(file_path, index=False)
     # Upload the CSV file, replacing it if it already exists.
    s3_client.upload_file(st.secrets['FILENAME'], 'csv07', "filenames.csv")





#########################################################################################

st.title('Upload a PDF file to the Big Data Index')
st.title("QA Chatbot")
# Create a textbox for user input
link = st.text_input("Enter pdf link")
api_key = st.text_input("Enter api key")

# Create an update button
update_button = st.button("Update database")


# Check if the update button is clicked
if update_button:
    if not link:
        st.warning("Please enter pdf link")
    else:
        filename = link.split('/')[-1]
        df = extract_pdf_content(link, api_key)
        add_to_pinecone(df)
        upload_csv_to_s3(filename)
        st.success("Updated") 
        st.balloons()

#########################################################################################

def options_list():
    # Read the file names from a CSV file
    filename_df = pd.read_csv(st.secrets['FILENAME'], header=None)  # No header specified
    # Extract the options as a list
    options = filename_df[0].tolist()[1:] 
    options =  [i.strip() for i in options]
    return options

st.title("Delete a file from the Big Data Index")
# Create a textbox for user input
options = options_list()
file = st.selectbox("Select a file name:", options)
# Create an update button
delete_button = st.button("Delete file")

# Check if the update button is clicked
if delete_button:
    if not file:
        st.warning("Please select a file name")
    else:
        filename_to_delete = file
        input_vector = np.random.rand(1536).tolist()
        results = index.query(vector=input_vector, top_k=10000,include_values=False, filter={"Filename": filename_to_delete})
        all_ids = [match['id'] for match in results['matches']]
        delete_response = index.delete(ids=[all_ids[0]], namespace='')
        print(delete_response)
        st.success("Deleted!") 
        st.balloons()