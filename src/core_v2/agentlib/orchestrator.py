import openai
import re

def remove_think_blocks(text: str) -> str:
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    return cleaned.strip()

class Orchestrator:
    def __init__(self,model_url,model_name,agents):
        self.model_name = model_name
        self.url = model_url
        self.agents = agents
        self.agents_respones = {}
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

    def run_agents(self,paper):
        for agent in self.agents:
            self.agents_respones[agent.name] = agent.run(paper)
            print(f"Agent {agent.name} response is completed")
    
    def run(self,paper,include_paper = False):
        openai.api_key = "OPENAI_API_KEY"  
        openai.api_base = self.url 

        self.run_agents(paper)
        prompt = ""
        if include_paper:
            prompt+= f"\n\nPaper:\n{paper}"
        for agent in self.agents:
            prompt += f"\n\n{agent.name} Response:\n{self.agents_respones[agent.name]}"
        response = openai.ChatCompletion.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": self.prompt},
                {"role": "user", "content": prompt},
            ],
        )
        return remove_think_blocks(response.choices[0].message["content"])