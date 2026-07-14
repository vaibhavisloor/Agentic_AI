from agents import Runner,OpenAIChatCompletionsModel,Agent,function_tool
from openai import AsyncOpenAI
from pydantic import BaseModel
import os
from dotenv import load_dotenv
import asyncio 
from typing import Literal
import tempfile
import subprocess


load_dotenv()

client = AsyncOpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=os.getenv('GEMINI_API_KEY')
)

model = OpenAIChatCompletionsModel(
    model= 'gemini-2.5-flash',
    openai_client= client
)

@function_tool
def run_python_code(code:str)->str:
    '''Accepts python code as a string and executes it. Returns the result'''
    print("TOOL HAS BEEN CALLED YO")
    with tempfile.NamedTemporaryFile(
        mode='w',
        suffix='.py',
        delete=False
    ) as f:
        f.write(code)
        filename = f.name
    try:
        result = subprocess.run(
        ['python',filename],
        capture_output=True,
        text=True
    )
        if result.returncode == 0:
            return result.stdout
        else:
            return result.stderr

    finally:
        os.remove(filename)

coding_agent = Agent(name='coding_agent', instructions='Understadnd the task needed. Compulsorily use the tools to first excute the code , verify and then return the corrected code to the user. JUST RETURN THE CODE.NO EXPLANATION REQUIRED',model=model,tools=[run_python_code])

async def execute():
    result = await Runner.run(coding_agent, 'Give me the python code to see kanye west quotes..hit the "api.kanye.rest" route with get and it should be a streamlit code.')
    print(result.final_output)

asyncio.run(execute())