import functools
from openai import OpenAI
from flask import Flask, request, jsonify, render_template
import asyncio

async def run_async(non_async_function, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, functools.partial(non_async_function, *args, **kwargs))

with open('key_openai.txt', 'r') as f:
    client = OpenAI(api_key=f.read())

async def get_response(messages, model='gpt-3.5-turbo-1106', temperature=0, max_tokens=1000,  functions=[], **kwargs):
    return await run_async(
        client.chat.completions.create,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=messages,
        functions=functions,
        **kwargs
    )

app = Flask(__name__)

@app.route('/', methods=['GET'])
async def index():
    return render_template('index.html')

@app.route('/static/<path:path>')
async def send_static(path):
    return await app.send_static_file(path)

GRADING_SYSTEM = """# MISSION
Evaluate an International Baccalaureate (IB) free response question by:

- Analyzing the student's response.
- Assigning points according to the mark scheme.
- Providing justifications for marks awarded, especially for lower scores.

# PROCESS
1. **Receive Input**
   - Obtain the IB free response question.
   - Acquire the point-mark scheme for the question.
   - Collect the student's response.

2. **Analysis**
   - Compare the student's response with the mark scheme.
   - Identify key elements, concepts, and criteria required by the question.

3. **Scoring**
   - Allocate points for each category based on the student's performance.
   - Ensure that the total points do not exceed the maximum available for the question.
   - Be strict on the scoring, do not hand out points freely.

4. **Feedback**
   - For each category where full marks are not awarded, provide clear, concise explanations.
   - Highlight specific areas where the response did not meet the criteria.
   - Suggest improvements or missing elements that could have enhanced the score.
   - Sections with full marks need no feedback.
   - Address the feedback to the student.

5. **Summary**
   - Summarize the total points awarded.
   - Offer an overall assessment of the student's performance in relation to the mark scheme.

# OUTPUT
- Present the scores in a structured format, category-wise.
- Include justifications for scores next to the relevant category.
- Ensure feedback is constructive and aimed at student improvement."""

import random

@app.route('/get-question')
async def get_question():
    with open('questions.json', 'r') as f:
        questions = json.load(f)
    index = random.randint(0, len(questions) - 1)
    return jsonify({
        'questionId': str(index),
        'questionText': questions[index]['question']
    })

def simplify_criterion_name(name):
    out = ""
    for c in name:
        if c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            out += c.lower()
        elif c in "abcdefghijklmnopqrstuvwxyz":
            out += c
        elif c in "0123456789":
            out += c
        elif c == " ":
            out += "_"
    return out

@app.route('/grade', methods=['POST'])
async def grade():
    data = request.get_json()
    with open('questions.json', 'r') as f:
        questions = json.load(f)
    question = questions[int(data['questionId'])]
    user_answer = data['userAnswer']
    mark_scheme = question['markScheme']
    total_marks = mark_scheme['totalMarks']
    criteria = mark_scheme['criteria']
    for criterion in criteria:
        criterion['simpleName'] = simplify_criterion_name(criterion['description'])
    prompt = ""
    prompt += "Question: " + question['question'] + "\n"
    prompt += "Mark Scheme:\n"
    prompt += f"Award up to [{total_marks} max].\n"
    for criterion in criteria:
        prompt += f"Award [{criterion['marks']}] for {criterion['description']}.\n"
    prompt += "Student Answer:\n"
    prompt += user_answer
    messages = [
        {
            'role': 'system',
            'content': GRADING_SYSTEM
        },
        {
            'role': 'user',
            'content': prompt
        }
    ]
    functions = [
        {
            "name": "output",
            "description": "Output the grading.",
            "parameters": {
                "type": "object",
                "properties": {criterion['simpleName']: {"type": "number"} for criterion in criteria},
                "required": [criterion['simpleName'] for criterion in criteria]
            }
        }
    ]
    response = await get_response(
        messages,
        functions=functions,
        function_call={
            'name': 'output',
        }
    )
    message = response.choices[0].message
    messages.append(message)
    print(message)
    func_call_args = message.function_call.arguments
    print(func_call_args)
    func_call_args_processed = json.loads(func_call_args)
    out = []
    for criterion in criteria:
        out.append({
            'category': criterion['description'],
            'maxScore': criterion['marks'],
            'score': func_call_args_processed[criterion['simpleName']],
            'feedback': None
        })
    # get feedback
    feedback_needed = []
    for criterion in criteria:
        if func_call_args_processed[criterion['simpleName']] < criterion['marks']:
            feedback_needed.append(criterion)
    while len(feedback_needed) > 0:
        messages.append({
            'role': 'user',
            'content': "Now you will be asked to provide feedback for each category where full marks were not awarded."
        })
        functions = [
            {
                "name": "outputFeedback",
                "description": "Output the feedback.",
                "parameters": {
                    "type": "object",
                    "properties": {criterion['simpleName']: {"type": "string"} for criterion in feedback_needed},
                    "required": [criterion['simpleName'] for criterion in feedback_needed]
                }
            }
        ]
        response = await get_response(
            messages,
            functions=functions,
            function_call={
                'name': 'outputFeedback',
            }
        )
        message = response.choices[0].message
        messages.append(message)
        print(message)
        func_call_args = message.function_call.arguments
        print(func_call_args)
        func_call_args_processed = json.loads(func_call_args)
        torem = []
        for criterion in feedback_needed:
            for category in out:
                if category['category'] == criterion['description']:
                    try:
                        category['feedback'] = func_call_args_processed[criterion['simpleName']]
                        torem.append(criterion)
                    except:
                        category['feedback'] = None
        for criterion in torem:
            feedback_needed.remove(criterion)
        messages.pop(len(messages) - 1)
        messages.pop(len(messages) - 1)
    return jsonify(out)

import json

if __name__ == '__main__':
    app.run(debug=True)