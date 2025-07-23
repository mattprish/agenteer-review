import openai
import re

def remove_think_blocks(text: str) -> str:
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    return cleaned.strip()

class BaseAgent():
    def __init__(self,name,model_url,model_name,prompt):
        self.name = name
        self.model_name = model_name
        self.url = model_url
        self.prompt = prompt

    def run(self,paper):
        openai.api_key = "OPENAI_API_KEY"  
        openai.api_base = self.url

        response = openai.ChatCompletion.create(
            model = self.model_name,  
            messages=[
                {"role": "system", "content": self.prompt},
                {"role": "user", "content": paper},
            ],
        )
        return remove_think_blocks(response.choices[0].message["content"])