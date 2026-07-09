from agents import Agent, Runner, OpenAIChatCompletionsModel
from openai import AsyncOpenAI
from dotenv import load_dotenv
import os
import asyncio

load_dotenv()

client = AsyncOpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.getenv("GROQ_API_KEY"),
)

model = OpenAIChatCompletionsModel(
    model="openai/gpt-oss-120b",
    openai_client=client,
)

# Specialists

billing_agent = Agent(
    name="Billing Agent",
    instructions="""
    Compulsarily start the conversation by introducing yourself.
    You ONLY answer billing questions.
    Examples:
    - refunds
    - invoices
    - payment failed
    - subscriptions
    """,
    model=model,
)

technical_agent = Agent(
    name="Technical Agent",
    instructions="""
    Compulsarily start the conversation by introducing yourself.
    You ONLY answer technical support questions.
    Examples:
    - login problems
    - password reset
    - bugs
    - API issues
    """,
    model=model,
)

sales_agent = Agent(
    name="Sales Agent",
    instructions="""
    Compulsarily start the conversation by introducing yourself.
    You ONLY answer sales questions.
    Examples:
    - pricing
    - enterprise plans
    - discounts
    """,
    model=model,
)

# Receptionist

receptionist = Agent(
    name="Receptionist",
    instructions="""
    You are the receptionist.

    Decide which specialist should help.

    Never answer the question yourself.

    Always hand the conversation to the appropriate specialist.
    """,
    handoffs=[
        billing_agent,
        technical_agent,
        sales_agent,
    ],
    model=model,
)


async def main():
    result = await Runner.run(
        receptionist,
        "My login failed yesterday."
    )

    print(result.final_output)


asyncio.run(main())