import asyncio
import aiohttp
import re


def remove_think_blocks(text: str) -> str:
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    return cleaned.strip()


class BaseAgent:
    def __init__(self, name, model_url, model_name, prompt):
        self.name = name
        self.model_name = model_name
        self.url = model_url
        self.prompt = prompt

        self.timeout = aiohttp.ClientTimeout(total=600)

    # def run(self, paper): # async
    async def run(self, paper):
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": self.prompt},
                    {"role": "user", "content": paper},
                ],
                "stream": False
            }

            async with session.post(
                    f"{self.url}/v1/chat/completions",
                    json=payload,
                    headers={"Content-Type": "application/json"}
            ) as response:
                data = await response.json()
                return remove_think_blocks(data['choices'][0]['message']['content'])

