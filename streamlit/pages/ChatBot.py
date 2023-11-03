import requests
import streamlit as st
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import uuid
import logging
import pandas as pd
import time
import numpy as np
import os
import dotenv
dotenv.load_dotenv()




API_ENDPOINT = os.environ['FASTAPI_ENDPOINT']
logging.basicConfig(filename='errors.log', level=logging.ERROR)
logging.basicConfig(filename='info.log', level=logging.INFO)
#########################################################################################

#Function to get options list
def options_list():
    # Read the file names from a CSV file
    filename_df = pd.read_csv(os.environ['FILENAME'], header=None)  # No header specified
    # Extract the options as a list
    options = filename_df[0].tolist()[1:] 
    options =  [i.strip() for i in options]
    options.append('All')
    return options


#Function to get token
def get_token(username, password):
    payload = {
        'username': username,
        'password': password
    }

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    try:
        response = requests.post(f"{API_ENDPOINT}/token", data=payload, headers=headers)
        if response.status_code == 200:
            token_data = response.json()
            st.success('Token retrieved successfully!')
            return token_data.get('access_token')
        else:
            st.error(f"Failed to retrieve token: {response.json().get('detail', 'No detail provided by server.')}")
            logging.error(f"Failed to retrieve token: {response.json().get('detail', 'No detail provided by server.')}")
    except requests.RequestException as e:
        st.error(f"An error occurred while retrieving token: {e}")
        logging.error(f"An error occurred while retrieving token: {e}")

    return None



#Function to get user details
def get_user_details(token, retries=1):
    """Function to get user details with a simple retry mechanism."""
    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    for attempt in range(retries + 1):
        try:
            response = requests.get(f"{API_ENDPOINT}/users", headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as http_err:
            # Handle 401 Unauthorized separately
            if response.status_code == 401:
                if attempt < retries:
                    # Log the unauthorized attempt
                    logging.warning("Unauthorized. Retrying...")
                    continue
                else:
                    # Log the final unauthorized error
                    logging.error(f"401 Unauthorized: {response.json().get('detail', 'No detail provided by server.')}")
            else:
                # Log other HTTP errors
                logging.error(f"HTTP error occurred: {http_err}: {response.json().get('detail', 'No detail provided by server.')}")
        except Exception as e:
            # Log unexpected errors
            logging.error(f"An unexpected error occurred: {e}")
        # Wait a bit before retrying (if needed)
        if attempt < retries:
            time.sleep(1)
    return None

#Function to get answer
def handle_new_message(question, file, api_key, token):
    """Function to send a message to the chatbot and get a response."""
    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    data = {
        "query_model": {
            "query": question,
            "filename": file
        },
        "openai_model": {
            "api_key": api_key
        }
    }
    try:
        response = requests.post(f"{API_ENDPOINT}/answer/", headers=headers, json=data)
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err} - Response Body: {http_err.response.text}")
    except Exception as e:
        print(e,"culprit 2")
        st.error(f"An unexpected error occurred: {e}")


#Function to display chat history
def display_chat(history):
    """Function to display the chat history."""
    for idx, chat in enumerate(history):
        unique_id = str(uuid.uuid4()) 
        st.text_area(f"Q: {chat['question']}", value=chat['answer'], height=75, key=unique_id)


# Initialize session state for chat history
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# Sidebar for user authentication
if 'access_token' not in st.session_state:
    with st.sidebar:
        st.subheader("Sign In")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Sign In"):
            print("fetching token", username, password)
            token = get_token(username, password)
            if token:
                st.session_state['access_token'] = token
                st.success('You are successfully signed in!')

#########################################################################################


st.title('Chatbot')

# Main page logic
if 'access_token' in st.session_state:
    # Retrieve and display user details
    user_details = get_user_details(st.session_state.access_token, retries=1)
    if user_details:
        st.subheader(f"Welcome {user_details['username']}!")
        st.text(f"Email: {user_details['email']}")
        st.text(f"Logs: {user_details.get('logs', 'No logs available.')}")
    
    # Input for new questions
    with st.form("chat_form"):
        options = options_list()
        question = st.text_input('Ask a question')
        file = st.selectbox("Select a file name:", options)
        openai_key = st.text_input('OpenAI Key', type="password")
        submit_button = st.form_submit_button(label='Submit')
    
    if submit_button and question and file and openai_key:
        print(st.session_state.access_token, "fectct")
        answer_data = handle_new_message(question, file, openai_key, st.session_state.access_token)
        print(answer_data)
        if answer_data:
            st.session_state.chat_history.append({
                'question': question,
                'answer': answer_data.get('choices', 'No answer returned')[0]['message']['content']
            })
            display_chat(st.session_state.chat_history)
else:
    st.warning('Please sign in to use the chatbot.')


