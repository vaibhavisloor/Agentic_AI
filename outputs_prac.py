from agents import Runner,OpenAIChatCompletionsModel,Agent
from openai import AsyncOpenAI
from pydantic import BaseModel
import os
from dotenv import load_dotenv
import asyncio 
from typing import Literal

load_dotenv()

RESUME_INFO = '''
Vaibhav Isloor

Software Engineer | Python • Full-Stack • AI
+91 9900855730 | viisloor@gmail.com | Bengaluru, Karnataka
vaibhavisloor.com | LinkedIn | Github| Leetcode (150+ problems)

SUMMARY
Software engineer building production AI systems. Founder of ResumeCore (live AI resume platform, 100+
users) and previously at Zebra Technologies. IEEE-published (ICCAI 2025, Kyoto) and GATE DA 2026 qualified.
Strong in Python, FastAPI, React, and RAG. Seeking AI Engineer and Full-Stack roles.

EDUCATION

B.Tech (Computer Science)

PES University
CGPA : 8.05

Qualified GATE DA 2026.

Solved 700+ problems across ML, Probability, DSA

2021 - 2025

SKILLS
Programming Languages : Python, C , Javascript, TypeScript
Frontend : HTML, CSS, Bootstrap, React.js
Backend : Node.js, Express.js, Flask, FastAPI, REST APIs
Databases : MySQL, MongoDB, Supabase
Big Data : Apache Spark, Apache Kafka
Generative AI : LangChain, RAG, Vector DB, FAISS, OpenAI API, Prompt Engineering, LLM, Agentic AI, n8n, MCP
DevOps & Tools : Docker, Jenkins, CI/CD
Version Control : Git and GitHub

RESEARCH PUBLICATIONS
Localization of Deepfake Facial Images Through U-Net Architecture

IEEE Xplore

ICCAI 2025, Kyoto, Japan — IEEE, March 2025 · DOI: 10.1109/ICCAI66501.2025.00023

Co-authored an IEEE-published paper proposing a U-Net-based deep learning architecture for pixel-level
localization of manipulated regions in deepfake facial images, moving beyond binary classification to
forensic-grade segmentation.

EXPERIENCE
ResumeCore (www.resumecore.in)

Oct 2025 - Present

Founder

Launched a production AI resume platform; 100+ users and dozens of resume generations within 30
days.
Built an async FastAPI backend with a modular Python pipeline that parses resumes, performs JD-toresume semantic matching, and orchestrates Gemini calls with JSON-schema-constrained outputs.
Integrated Razorpay with signed webhook handlers (idempotent processing, signature verification) and
Clerk-based auth with protected backend routes.
Architected the full stack: React + Vite on Vercel, FastAPI on Railway, Supabase (Postgres + storage);
instrumented funnel analytics to debug latency and drop-off.

Zebra Technologies

Jan 2025 - Oct 2025

Software Engineer 1

Executed 30+ test cases for the Zebra Workcloud Sync mobile application across multiple Android
environments, identifying and reporting 20+ bugs to improve release quality.
Software Engineering Intern

Engineered FarmVille, an end to end automated printer testing platform built with React and Flask,
reducing build and test execution time from 10 minutes to ~2 minutes (80% faster), eliminating manual test
coordination across engineering teams.
Architected automated CI/CD pipelines using Jenkins and Docker, enabling consistent environment parity
across development and production with zero manual deployment steps.
Budget Tracking Dashboard - Replaced Excel based expense tracking for 8+ Zebra managers by building
a full stack budget dashboard with real time financial analysis, accessible on any device. Adopted as the
team's primary financial reporting tool within weeks of launch.

Wisdomleaf Technologies

July 2024 - August 2024

Python Developer Intern

Built an LLM-powered health report analyzer using OpenAI APIs and prompt engineering to extract and
interpret medical data, enabling real-time diagnostic insights. The system facilitated real-time data
processing, delivering comprehensive diagnostic insights, significantly improving healthcare decisionmaking.

PROJECTS
1. Medicine Query Bot using LLM + RAG

Built a RAG-based LLM system that retrieves and generates context-aware medical responses (uses,
dosages, etc.) from a private dataset, ensuring accuracy, low latency, and secure data handling.
2. Reverse Proxy with Load Balancing, Rate Limiting, and Security Filtering

Built a reverse proxy server using round-robin load balancing to distribute traffic evenly across multiple
backend servers. Implemented rate-limiting to prevent abuse and added security filters to block malicious
requests, such as SQL injection and XSS attempts, ensuring a balance between performance and security.

CERTIFICATIONS
The Complete 2024 Web Development Bootcamp
100 Days of Code: The Complete Python Pro Bootcamp
Supervised Machine Learning: Regression and Classification

'''

client = AsyncOpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=os.getenv('GEMINI_API_KEY')
)

model = OpenAIChatCompletionsModel(
    model= 'gemini-2.5-flash',
    openai_client= client
)

class Student(BaseModel):
    name: str
    age: int
    hire_possibility : Literal['High','Medium','Low']
    feedback : str

# async def execute():
#     response = await client.responses.create(
#     model='openai/gpt-oss-120b',
#     input='What is the capital of USA'
# )

#     print(response)

# asyncio.run(execute())


resume_analyser = Agent(
    name='Pinto',
    instructions='You are a resume analyzer. Analyse the resume and give proper feedback.',
    model=model,
    output_type=Student
    )


async def execute():
    response = await Runner.run(resume_analyser,RESUME_INFO)
    print(response.final_output)
    print(type(response.final_output))

asyncio.run(execute())