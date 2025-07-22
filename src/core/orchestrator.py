import openai
import re
import json


def remove_think_blocks(text: str) -> str:
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    return cleaned.strip()


class Orchestrator:
    def __init__(self, model_url, model_name, agents):
        self.model_name = model_name
        self.url = model_url
        self.agents = agents
        self.agents_responses = {}
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

    def run_agents(self, paper):
        for agent in self.agents:
            self.agents_responses[agent.name] = agent.run(paper)
            print(f"Agent {agent.name} response is completed")

    def run(self, paper, include_paper=False):
        openai.api_key = "OPENAI_API_KEY"
        openai.api_base = self.url

        self.run_agents(paper)
        prompt = ""
        if include_paper:
            prompt += f"\n\nPaper:\n{paper}"
        for agent in self.agents:
            prompt += f"\n\n{agent.name} Response:\n{self.agents_responses[agent.name]}"
        response = openai.ChatCompletion.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": self.prompt},
                {"role": "user", "content": prompt},
            ],
        )
        return remove_think_blocks(response.choices[0].message["content"])


class OrchestratorAlpha:
    def __init__(self, model_url, model_name, agents):
        self.model_name = model_name
        self.url = model_url
        self.agents = agents
        self.agents_responses = {}

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

    def run_agents(self, paper):
        for agent in self.agents:
            self.agents_responses[agent.name] = agent.run(paper)
            print(f"Agent {agent.name} response is completed")

    def run(self, paper, include_paper=False):
        openai.api_key = "OPENAI_API_KEY"
        openai.api_base = self.url

        self.run_agents(paper)
        prompt = ""
        if include_paper:
            prompt += f"\n\nPaper:\n{paper}"
        for agent in self.agents:
            prompt += f"\n\n{agent.name} Response:\n{self.agents_responses[agent.name]}"
        response = openai.ChatCompletion.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": self.prompt},
                {"role": "user", "content": prompt},
            ],
        )
        return remove_think_blocks(response.choices[0].message["content"])


class IterativeOrchestrator: # new orchestrator, not testes
    def __init__(self, model_url, model_name, agents, max_iterations=2):
        self.model_name = model_name
        self.url = model_url
        self.agents = agents
        self.agents_responses = {}
        self.max_iterations = max_iterations

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

    def run_agents(self, paper):
        for agent in self.agents:
            self.agents_responses[agent.name] = agent.run(paper)
            print(f"Agent {agent.name} response is completed")

    def refine_agents(self, paper, clarification):
        for agent in self.agents:
            add_prompt = f"\n\nNOTE: Please revise your response considering this feedback:\n{clarification[agent.name]}"
            old_agent_prompt = agent.prompt
            agent.prompt += add_prompt
            self.agents_responses[agent.name] = agent.run(paper)
            agent.prompt = old_agent_prompt

    def check_and_ask(self):
        prompt = ""
        for agent in self.agents:
            prompt += f"\n\n{agent.name} Response:\n{self.agents_responses[agent.name]}"

        response = openai.ChatCompletion.create(
            model=self.model_name,
            api_key="OPENAI_API_KEY",
            api_base=self.url,
            messages=[
                {"role": "system", "content": self.review_prompt},
                {"role": "user", "content": prompt},
            ]
        )

        result_text = remove_think_blocks(response.choices[0].message["content"])
        parsed = json.loads(result_text)
        return {entry["agent"]: entry["message"] for entry in parsed}

    def run(self, paper, include_paper=False):
        openai.api_key = "OPENAI_API_KEY"
        openai.api_base = self.url

        self.run_agents(paper)

        for i in range(self.max_iterations):
            print(f"\n🔍 Iteration {i + 1}: Checking consistency...")
            clarifications = self.check_and_ask()
            if not clarifications:
                print("✅ No contradictions found. Proceeding to synthesis.")
                break
            self.refine_agents(paper, clarifications)

        prompt = ""
        if include_paper:
            prompt += f"\n\nPaper:\n{paper}"
        for agent in self.agents:
            prompt += f"\n\n{agent.name} Response:\n{self.agents_responses[agent.name]}"
        response = openai.ChatCompletion.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": self.final_synth_prompt},
                {"role": "user", "content": prompt},
            ],
        )
        return remove_think_blocks(response.choices[0].message["content"])
