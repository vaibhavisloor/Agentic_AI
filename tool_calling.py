import os
from google import genai
from google.genai import types
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

def get_datetime():
    return datetime.now()

TOOLS = {
    'get_datetime' : get_datetime
}

datetime_tool = types.FunctionDeclaration(
    name = 'get_datetime',
    description = 'Returns the current date and time of the system.',
    parameters={
        "type": "object",
        "properties": {}
    }
)

client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

response = client.models.generate_content(
    model='gemini-2.5-flash', 
    contents='What is the time here', 
    config=types.GenerateContentConfig(
        tools =[types.Tool(function_declarations=[datetime_tool])]
    )
)

if response.candidates[0].content.parts[0].function_call:
    function = response.candidates[0].content.parts[0].function_call.name
    result = TOOLS['get_datetime']()
    # print(result)

    final_response = client.models.generate_content(
        model = 'gemini-2.5-flash',
        contents= [
            types.Content(role='user', parts=[types.Part(text='What is the time here')]),
            response.candidates[0].content,
            types.Content(
                role='user',
                parts=[
                    types.Part.from_function_response(
                        name='get_datetime',
                        response = {'datetime': result.isoformat()}
                    )
                ]
            ),
        ],
        config=types.GenerateContentConfig(
        tools=[types.Tool(function_declarations=[datetime_tool])]
    )
    )
    print(final_response.candidates[0].content.parts[0].text)
else:
    print(response.candidates[0].content.parts[0].text)