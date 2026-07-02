from functions import extract_text, add_user_info
from google import genai
from google.genai import types
import os
from dotenv import load_dotenv
import json
import streamlit as st

load_dotenv()

st.set_page_config(page_title="Vaibhav's Assistant", page_icon="🤖")

CV_INFO = extract_text('my_resume.pdf')

SYS_INSTRUCT = f'''You are a personal assistant of Vaibhav. Answer to only questions regarding Vaibhav. For any irrelevant or out of topic questions reply saying "I am Vaibhav's assistant and will answer only questions regading him". Use the tools as required and keep your answer just based on the below information If anyone wants to context. 

{CV_INFO}
'''

add_user_tool = {
'type' : 'function',
'name' : 'add_user_info',
'description' : 'If any user wants to contact Vaibhav. He shares their name, email and contact and we save it to a file',
'parameters' : {
    'type' : 'object',
    "properties" : {
        'name' : {'type':"string", 'description' : 'The user name'},
        'email' : {'type':'string', 'description' : 'The user email'},
        'contact_number' : {'type':'string','description' : 'The user contact' }
    },
    'required':['name','email','contact_number']
}
}

TOOLS = {
    'add_user_info' : add_user_info
}

client = genai.Client(api_key = os.getenv('GEMINI_API_KEY'))

st.title("Vaibhav's Personal Assistant")
st.write("Hi ! Im Vaibhav's personal assistant. Im happy to answer your questions about him")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "last_id" not in st.session_state:
    st.session_state.last_id = None

for role, text in st.session_state.chat_history:
    with st.chat_message(role):
        st.write(text)

question = st.chat_input('Type your question :')

if question:
    with st.chat_message("user"):
        st.write(question)
    st.session_state.chat_history.append(("user", question))

    response = client.interactions.create(
    model = 'gemini-2.5-flash',
    input = question,
    system_instruction=SYS_INSTRUCT,
    tools=[add_user_tool],
    previous_interaction_id= st.session_state.last_id
    )

    st.session_state.last_id = response.id

    with st.chat_message("assistant"):
        if response.steps[0].type and response.steps[0].type == 'function_call':
            function_call = TOOLS[response.steps[0].name]
            arguments_dict = response.steps[0].arguments

            name = arguments_dict['name']
            email = arguments_dict['email']
            contact_number = arguments_dict['contact_number']

            try:
                function_call(name,email,contact_number)
                st.write('Info has been successfully saved')
                st.session_state.chat_history.append(("assistant", "Info has been successfully saved"))
            except Exception as e:
                st.write(f"An error occurred: {e}")
                st.session_state.chat_history.append(("assistant", f"An error occurred: {e}"))
        else:
            reply = response.steps[1].content[0].text
            st.write(reply)
            st.session_state.chat_history.append(("assistant", reply))