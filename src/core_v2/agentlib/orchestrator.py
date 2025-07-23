import asyncio
import aiohttp
import re
 
 
def remove_think_blocks(text: str) -> str:
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    return cleaned.strip()
 
 
class Orchestrator:
    def __init__(self, model_url, model_name, agents):
        self.model_name = model_name
        self.url = model_url
        self.agents = agents
        self.agents_responses = {}
        self.timeout = aiohttp.ClientTimeout(total=600)
 
        # prompt that can be used, need test
        self.prompt_alpha = """
        Based on the outputs of the thematic agents (Novelty, Methodology, Clarity, Reproducibility), write a complete peer review of the paper using the following structure:
        1.	Summary: Briefly describe the paper’s goal, main method, and key results.
        2.	Strengths: List the strong aspects of the paper, aggregating the relevant points from all agents.
        3.	Weaknesses: Identify the major weaknesses mentioned by the agents.
        4.	Suggestions for Improvement: Provide actionable suggestions on how the paper can be improved, based on the identified weaknesses.
        5.	Questions to Authors: Include all clarification questions raised by the agents that should be addressed by the authors.
        6.	Overall Rating (1 to 5): Propose a final rating for the paper by averaging the agent scores and briefly justify the score.
        7.	Confidence (1 to 5): Indicate the reviewer’s confidence in their understanding of the paper. If there are any unclear sections or missing information, reflect that here.
        """
 
        self.prompt = """
            You will receive a series of evaluations for a scientific paper from different specialized agents. Each evaluation will include scores from 0 to 10 and a summary of findings. Your task is to:
            Synthesize all the individual scores into a single, overall grade for the paper out of 10. Calculate this by averaging the scores from all agents.
            Combine the summaries from each agent into a comprehensive and well-structured final review. The review should have separate sections for each aspect of the paper (Abstract & Introduction, Methodology, etc.).
            Begin the final review with a brief, high-level summary of the paper's strengths and weaknesses.
            Conclude with a clear recommendation based on the overall score:
            9-10: Accept
            7-8: Minor Revisions
            4-6: Major Revisions
            0-3: Reject
        """
 
    async def run_agents(self, paper):
        tasks = {agent.name: agent.run(paper) for agent in self.agents}
        responses = await asyncio.gather(*tasks.values())
        return dict(zip(tasks.keys(), responses))
 
    async def run(self, paper, include_paper=False):
        self.agents_responses = await self.run_agents(paper)
        prompt = ""
        if include_paper:
            prompt += f"\n\nPaper:\n{paper}"
        for agent in self.agents:
            prompt += f"\n\n{agent.name} Response:\n{self.agents_responses[agent.name]}"
 
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": "Ваш основной промпт..."},
                    {"role": "user", "content": prompt},
                ],
                "stream": False
            }
 
            async with session.post(
                    f"{self.url}/v1/chat/completions",
                    json=payload,
                    headers={"Content-Type": "application/json"}
            ) as response:
                data = await response.json()

                return {
                    "agent_results": None,
                    "final_review": remove_think_blocks(data['choices'][0]['message']['content']),
                    "processing_status": "success"
                }
 