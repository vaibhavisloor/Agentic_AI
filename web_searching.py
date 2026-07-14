from agents import Agent,Runner, function_tool, OpenAIChatCompletionsModel
from openai import AsyncOpenAI

import os
from dotenv import load_dotenv
from ddgs import DDGS
import asyncio

load_dotenv()

client = AsyncOpenAI(
    base_url='https://generativelanguage.googleapis.com/v1beta/openai/',
    api_key= os.getenv('GEMINI_API_KEY')
)

model = OpenAIChatCompletionsModel(
    model = 'gemini-2.5-flash',
    openai_client=client
)
@function_tool
def search_the_web_buddy(query):
    'Enter a query to search the web. Get back top 5 results from realtime'
    print('\033[4m WEB SEARCH CALLED \033[0m')
    print('\033[4m QUERY ENTERED WAS \033[0m' + query)
    result = DDGS().text(query=query,max_results=5)
    return result

my_agent = Agent(name='Mahashiv', instructions='You answer based on facts, ONLY if you dont know the answer use the tools', tools=[search_the_web_buddy], model = model)

async def execute():
    result = await Runner.run(my_agent, 'Whats the current update on the IRAN US WAR. Also tell me what is the meaning of asyncio')
    print(result.final_output)

asyncio.run(execute())