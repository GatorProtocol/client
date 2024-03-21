from dotenv import load_dotenv
from groq import Groq

import os

load_dotenv()

client = Groq(
    api_key=os.environ["GROQ_API_KEY"]
)

def infer(modelid, prompt, entropy):
    prompt_dict = eval(prompt)
    messages = prompt_dict["messages"]

    completion = client.chat.completions.create(
        messages=messages,
        stop=None,
        stream=False,
        temperature=0.5,
        model="gemma-7b-it",
        seed=int(entropy),
    )
    
    out = completion.choices[0].message.content
    return out