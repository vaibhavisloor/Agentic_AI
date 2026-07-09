from agents import Agent,Runner,function_tool,OpenAIChatCompletionsModel
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI
import asyncio

load_dotenv()

RESUME_CORE = '''
**ResumeCore** is an AI-powered resume optimization platform that helps Indian job seekers understand why their resumes aren't getting shortlisted and how to fix them. It provides honest, recruiter-level feedback instead of inflated ATS scores, analyzes resumes against job descriptions, identifies missing keywords and skills, and gives actionable suggestions to improve interview chances.

Its core features include:

* Resume Analysis
* ATS Score Checker
* Job Description (JD) Match Analysis
* AI Resume Builder
* AI Resume Editor/Rewriter with PDF export
* Honest recruiter-style resume scoring
* ATS compatibility and keyword optimization

For **JD Match**, users can edit their resume directly in the browser based on AI suggestions and download the updated resume immediately.

### Pricing

**Free Tier**

* 1 Resume Analysis
* 1 JD Match
* Browser-based resume editing during JD Match
* Download the edited resume

**Pro Plan – ₹299/month**

* 20 Resume Analyses per month
* 20 JD Matches per month
* Browser-based resume editing and resume download for every JD Match

The goal of ResumeCore is simple: **help people stop sending the same resume everywhere and instead submit resumes that are tailored, ATS-friendly, and genuinely more likely to get interviews.** It is positioned as an **AI SaaS product in the CareerTech/HRTech space**, focused on delivering realistic feedback rather than misleading "95% ATS scores."

'''
gemini_client = AsyncOpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.getenv('GROQ_API_KEY')
)

model  = OpenAIChatCompletionsModel(
    model = 'openai/gpt-oss-120b',
    openai_client= gemini_client
)

# Main Agent tools
@function_tool
def understand_resumeCore():
    print('understanding what is resume core')
    return RESUME_CORE

funny_writer = Agent(name='funny_writer', instructions='You are a professional funny email sales agent. Write a funny email promoting Resume Core ',tools=[understand_resumeCore],model=model)

simple_writer = Agent(name='email_writer', instructions='You are a professional email sales agent. Write a funny email promoting Resume Core ',tools=[understand_resumeCore],model=model)

urgency_writer = Agent(name='urgency_writer', instructions='You are a professional urgency email sales agent. Write a funny email promoting Resume Core ',tools=[understand_resumeCore],model=model)

agent = Agent(name='Sales Manager',instructions='You are the sales manager of a resumecore. You have 3 email writers. Get the emails from them and decided which is best. Rename it to the sender by just saying Hi, with no name. In the end, sent by Team ResumeCore',model = model,tools=[
    understand_resumeCore,

    funny_writer.as_tool(tool_name='funny_email_promotion_writer',tool_description='Writes up a funny email for promoting ResumeCore via Email'),

    simple_writer.as_tool(tool_name='email_promotion_writer',tool_description='Writes up a professional email for promoting ResumeCore via Email'),

    urgency_writer.as_tool(tool_name='urgency_promotion_writer',tool_description='Writes up a professional urgency email for promoting ResumeCore via Email')

    ])

async def execute():
    print('Generating an sales email for resumecore')
    result = Runner.run_streamed(agent, 'Give me the best email for resumecore. Dont create any fake personalities or fake discounts. The email should only be from Team ResumeCore,hello@resumecore.in. No contact number. Understadn what is ResumeCore')
    async for event in result.stream_events():
        print(event)


    print(result.final_output)

asyncio.run(execute())