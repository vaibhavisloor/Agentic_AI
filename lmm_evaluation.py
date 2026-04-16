from openai import OpenAI
import json
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv('BASE_URL')
API_KEY = os.getenv('API_KEY')

openai = OpenAI(
    base_url = BASE_URL,
    api_key = API_KEY
    )

print('********** LLM ANSWER EVALUATOR FLOW **********')

question = str(input('Please enter a question to ask the LLM :'))
print("\n" + question + "\n")

messages_answer = [
    {'role' : 'system', 'content' : ''' 
You are an AI assistant that improves its answers iteratively.

Behavior rules:
1. When answering for the FIRST time:
   - Give a simple but slightly imperfect answer (not completely wrong, just basic or incomplete).

2. When given feedback:
   - Carefully analyze the feedback.
   - Improve the previous answer by fixing ALL issues mentioned.
   - Make the answer clearer, more correct, and better structured.

Constraints:
- Keep answers concise.
- Adapt explanation level to the user's request (e.g., for a 5-year-old, keep it very simple).
- Do NOT repeat the same mistakes.
- Do NOT mention that you are improving or refer to feedback explicitly in the final answer.

Your goal:
Produce the best possible answer after iterative refinement.
'''},
    {'role' : 'user', 'content' : question }
    ]


response = openai.chat.completions.create(
    model = 'llama-3.3-70b-versatile',
    messages= messages_answer
)


llm_output = response.choices[0].message.content

print('---------- FIRST OUTPUT ----------')
print(llm_output)

evaluator_prompt = ''' 
You are an expert evaluator of AI-generated answers.

Your job is to evaluate the given answer based on the following criteria:
1. Correctness (Is the information accurate?)
2. Clarity (Is it easy to understand?)
3. Simplicity (Is it appropriate for the target audience?)
4. Completeness (Does it fully answer the question?)

Scoring:
- Give a score from 0 to 10.

Feedback rules:
- Be specific and actionable.
- Point out exact issues.
- Suggest how to improve.

Output format:
Return ONLY valid JSON in this exact structure:
{
  "score": <integer>,
  "feedback": "<clear actionable feedback>"
}

Do NOT include any extra text outside JSON.
'''

messages_evaluator = [
    {'role':'system','content':evaluator_prompt
    },
    {'role': 'user', 'content':f"Question is {question} and answer is {llm_output}"}
    ]

response = openai.chat.completions.create(
    messages= messages_evaluator,
    model = 'llama-3.3-70b-versatile'
)

evaluation = json.loads(response.choices[0].message.content)

print('---------- FIRST EVALUATION----------')
print(evaluation)

iter = 0

while int(evaluation['score']) < 9 and iter < 5:
    iter+=1
    feedback = evaluation['feedback']
    messages_answer.append({
        'role':'user','content': f'''
Here is feedback on your previous answer:
{evaluation['feedback']}

Rewrite the answer by fixing ALL the issues mentioned.

Ensure:
- higher clarity
- better structure
- improved correctness
- appropriate level for the user

Do not repeat previous mistakes.
'''})

    response = openai.chat.completions.create(
        model = 'llama-3.3-70b-versatile',
        messages = messages_answer
    )

    llm_output = response.choices[0].message.content
    print(f'\n {llm_output} \n')

    

    response = openai.chat.completions.create(
        model = 'llama-3.3-70b-versatile',
        messages = [
    {'role':'system','content':evaluator_prompt
    },
    {'role': 'user', 'content':f"Question is {question} and answer is {llm_output}"}
    ]
    )

    evaluation = json.loads(response.choices[0].message.content)
    print(f'\n {evaluation} \n')


print('---------- FINAL ACCEPTED ANSWER ----------')
print(llm_output)
print('FINAL SCORE WAS ' + str(evaluation ['score']))