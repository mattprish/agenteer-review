import asyncio
import aiohttp
import re
from src.core.prompts import orchestrator_prompts


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

        self.prompt = orchestrator_prompts["Orchestrator"]

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
                    {"role": "system", "content": self.prompt},
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
                return {"answer": remove_think_blocks(data['choices'][0]['message']['content'])}


class IterativeOrchestrator:  # new orchestrator, not testes
    def __init__(self, model_url, model_name, agents, max_iterations=1):
        self.model_name = model_name
        self.url = model_url
        self.agents = agents
        self.agents_responses = {}
        self.max_iterations = max_iterations
        self.timeout = aiohttp.ClientTimeout(total=600)

        self.review_prompt = """
        You will receive evaluation responses from several reviewing agents who assessed different aspects of a scientific paper.

        Your task:
        - Identify any contradictions, inconsistencies, or conflicting evaluations across the agents' responses.
        - Suggest clarifying instructions to the agents who need to revise or refine their feedback.
        - Return a **JSON array**, where each item is an object with keys "agent" and "message".
        
        If no clarification is needed, return an empty list: `[]`
        
        Example:
        [
        {"agent": "AbstractAgent", "message": "The clarity score contradicts the MethodologyAgent's comments."},
        {"agent": "ResultsAgent", "message": "Unsupported claims detected—please clarify with evidence."}
        ]
        """

        # prompt that can be used, need test
        self.final_synth_prompt_alpha = """
            Based on the outputs of the thematic agents (Novelty, Methodology, Clarity, Reproducibility), write a complete peer review of the paper using the following structure:
            1.	Summary: Briefly describe the paper’s goal, main method, and key results.
            2.	Strengths: List the strong aspects of the paper, aggregating the relevant points from all agents.
            3.	Weaknesses: Identify the major weaknesses mentioned by the agents.
            4.	Suggestions for Improvement: Provide actionable suggestions on how the paper can be improved, based on the identified weaknesses.
            5.	Questions to Authors: Include all clarification questions raised by the agents that should be addressed by the authors.
            6.	Overall Rating (1 to 5): Propose a final rating for the paper by averaging the agent scores and briefly justify the score.
            7.	Confidence (1 to 5): Indicate the reviewer’s confidence in their understanding of the paper. If there are any unclear sections or missing information, reflect that here.
        """

        self.final_synth_prompt = """
        You are the final reviewer.
        You will receive the final responses from five specialized reviewing agents for a scientific paper.
        
        Your tasks:
        1. Average all numerical scores to assign an overall grade from 0 to 10.
        2. Write a structured review with the following sections:
           - High-Level Summary
           - Abstract & Introduction
           - Methodology
           - Results & Discussion
           - Language
           - Citations
        3. Provide clear, concise explanations in each section using agent responses.
        4. Conclude with a final recommendation based on the average score:
           - 9–10: Accept
           - 7–8: Minor Revisions
           - 4–6: Major Revisions
           - 0–3: Reject
        """

    async def run_agents(self, paper):
        tasks = {agent.name: agent.run(paper) for agent in self.agents}
        responses = await asyncio.gather(*tasks.values())
        return dict(zip(tasks.keys(), responses))

    async def refine_agents(self, paper, clarification):
        old_prompts = {agent.name: agent.prompt for agent in self.agents}
        for agent in clarification:
            add_prompt = f"\n\nNOTE: Please revise your response considering this feedback:\n{clarification[agent.name]}"
            agent.prompt += add_prompt
        for agent in self.agents:
            add_prompt = f"\n\nNOTE: Please revise your response considering this feedback:\n{clarification[agent.name]}"
            agent.prompt += add_prompt
        tasks = {agent.name: agent.run(paper) for agent in self.agents}
        responses = await asyncio.gather(*tasks.values())
        for agent in self.agents:
            agent.prompt = old_prompts[agent.name]
        return dict(zip(tasks.keys(), responses))

    async def check_and_ask(self):
        print("-"*100)
        print("CHECK AND ASK")
        prompt = ""
        for agent in self.agents:
            prompt += f"\n\n{agent.name} Response:\n{self.agents_responses[agent.name]}"
        print(prompt)
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": self.review_prompt},
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
                print(data['choices'][0]['message']['content'])
                return remove_think_blocks(data['choices'][0]['message']['content'])

    async def run(self, paper, include_paper=False):
        self.agents_responses = await self.run_agents(paper)
        print("!!!!!!!Agent run:")
        print(self.agents_responses)

        for i in range(self.max_iterations):
            print(f"\n🔍 Iteration {i + 1}: Checking consistency...")
            clarifications = await self.check_and_ask()
            print(clarifications)
            print(not clarifications)
            if not clarifications:
                print("✅ No contradictions found. Proceeding to synthesis.")
                break
            await self.refine_agents(paper, clarifications)

        prompt = ""
        if include_paper:
            prompt += f"\n\nPaper:\n{paper}"
        for agent in self.agents:
            prompt += f"\n\n{agent.name} Response:\n{self.agents_responses[agent.name]}"

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": self.final_synth_prompt},
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
                return {"answer": remove_think_blocks(data['choices'][0]['message']['content'])}


class CheckedOrchestrator:  # new orchestrator, not testes
    def __init__(self, model_url, model_name, agents, max_iterations=1):
        self.model_name = model_name
        self.url = model_url
        self.agents = agents
        self.agents_responses = {}
        self.timeout = aiohttp.ClientTimeout(total=600)


        # prompt that can be used, need test
        self.final_synth_prompt_alpha = """
            Based on the outputs of the thematic agents (Novelty, Methodology, Clarity, Reproducibility), write a complete peer review of the paper using the following structure:
            1.	Summary: Briefly describe the paper’s goal, main method, and key results.
            2.	Strengths: List the strong aspects of the paper, aggregating the relevant points from all agents.
            3.	Weaknesses: Identify the major weaknesses mentioned by the agents.
            4.	Suggestions for Improvement: Provide actionable suggestions on how the paper can be improved, based on the identified weaknesses.
            5.	Questions to Authors: Include all clarification questions raised by the agents that should be addressed by the authors.
            6.	Overall Rating (1 to 5): Propose a final rating for the paper by averaging the agent scores and briefly justify the score.
            7.	Confidence (1 to 5): Indicate the reviewer’s confidence in their understanding of the paper. If there are any unclear sections or missing information, reflect that here.
        """

        self.final_synth_prompt = """
        You are the final reviewer.
        You will receive the final responses from five specialized reviewing agents for a scientific paper.

        Your tasks:
        1. Average all numerical scores to assign an overall grade from 0 to 10.
        2. Write a structured review with the following sections:
           - High-Level Summary
           - Abstract & Introduction
           - Methodology
           - Results & Discussion
           - Language
           - Citations
        3. Provide clear, concise explanations in each section using agent responses.
        4. Conclude with a final recommendation based on the average score:
           - 9–10: Accept
           - 7–8: Minor Revisions
           - 4–6: Major Revisions
           - 0–3: Reject
        """

    async def run_agents(self, paper):
        tasks = {agent.name: agent.run(paper) for agent in self.agents}
        responses = await asyncio.gather(*tasks.values())
        return dict(zip(tasks.keys(), responses))

    async def refine_agents(self, paper, clarification):
        old_prompts = {agent.name: agent.prompt for agent in self.agents}
        for agent in self.agents:
            add_prompt = f"\n\nNOTE: Please revise your response considering this feedback:\n{clarification[agent.name]}"
            agent.prompt += add_prompt
        tasks = {agent.name: agent.run(paper) for agent in self.agents}
        responses = await asyncio.gather(*tasks.values())
        for agent in self.agents:
            agent.prompt = old_prompts[agent.name]
        return dict(zip(tasks.keys(), responses))

    async def check_and_ask(self):
        prompt = ""
        for agent in self.agents:
            prompt += f"\n\n{agent.name} Response:\n{self.agents_responses[agent.name]}"

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": self.review_prompt},
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
                return remove_think_blocks(data['choices'][0]['message']['content'])

    async def run(self, paper, include_paper=False):
        self.agents_responses = await self.run_agents(paper)

        for i in range(self.max_iterations):
            print(f"\n🔍 Iteration {i + 1}: Checking consistency...")
            clarifications = await self.check_and_ask()
            print(clarifications)
            if not clarifications:
                print("✅ No contradictions found. Proceeding to synthesis.")
                break
            await self.refine_agents(paper, clarifications)

        prompt = ""
        if include_paper:
            prompt += f"\n\nPaper:\n{paper}"
        for agent in self.agents:
            prompt += f"\n\n{agent.name} Response:\n{self.agents_responses[agent.name]}"

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": self.final_synth_prompt},
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
                return {"answer": remove_think_blocks(data['choices'][0]['message']['content'])}
