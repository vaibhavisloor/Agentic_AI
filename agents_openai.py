from agents import Agent, Runner, trace, OpenAIChatCompletionsModel, set_tracing_disabled,function_tool
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI
import asyncio
import requests

load_dotenv()

set_tracing_disabled(False)

gemini_client = AsyncOpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

model = OpenAIChatCompletionsModel(
    model="gemini-2.5-flash",
    openai_client=gemini_client,
)

@function_tool
async def motivational_quote():
    ''' Get a Motivational quote'''
    response = requests.get('https://api.kanye.rest/text')
    return response.text

agent = Agent(name='MaxiGod', instructions='You are a joke teller', model=model, tools=[motivational_quote])

async def execute():
    result = await Runner.run(agent,'Give me a motivational quote and tell me if the function call was used')
    print(result)

asyncio.run(execute())