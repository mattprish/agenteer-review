from langchain.llms import HuggingFacePipeline
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline


class BaseOrchestrator:
    def __init__(self):
        pass

    def run(self, paper):
        pass


class OrchestratorAlpha(BaseOrchestrator):
    def __init__(self, agents, model_name="Qwen/Qwen3-4B"):
        super().__init__()
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(model_name)
        pipe = pipeline("text-generation", model=model, tokenizer=tokenizer, return_full_text=False)
        self.llm = HuggingFacePipeline(pipeline=pipe)
        self.agents = agents
        self.prompt = """
            You are the Orchestrator Agent tasked with reviewing a research paper. Your job involves coordinating specialized review agents: the Experiment Agent evaluates methodology, robustness, and reproducibility; the Novelty Agent assesses originality, uniqueness, and contributions to existing knowledge; and the Impact Agent gauges potential significance, relevance, and real-world applications. Provide explicit instructions to each agent, consolidate their analyses, and present a structured, insightful summary. Clearly highlight overall strengths, weaknesses, and recommendation for acceptance, revision, or rejection.
        """

    def run(self, papers, include_paper=True):
        responses = {}
        for agent in self.agents:
            responses[agent.name] = agent.run(papers)
        if type(papers) == str:
            prompt = self.prompt
            for agent in self.agents:
                prompt += f"\n\n {agent.name}: \n {responses[agent.name]}"
            return self.llm(prompt)
        elif type(papers) == list:
            prompt = [self.prompt] * len(papers)
            for i in range(len(papers)):
                if include_paper:
                    prompt[i] += f"\n\n {papers[i]}"
                for agent in self.agents:
                    prompt[i] += f"\n\n {agent.name}: \n {responses[agent.name][i]}"
            return self.llm(prompt)


def _parse_feedback(raw_text: str):
    result = {}
    lines = raw_text.strip().split("\n")
    for line in lines:
        if ":" in line:
            name, msg = line.split(":", 1)
            result[name.strip()] = msg.strip()
    return result


class OrchestratorBeta(BaseOrchestrator):  # not ready, only for test
    def __init__(self, agents, model_name="Qwen/Qwen3-4B", *args, **kwargs):
        super().__init__()
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(model_name)
        pipe = pipeline("text-generation", model=model, tokenizer=tokenizer, return_full_text=False)
        self.llm = HuggingFacePipeline(pipeline=pipe)
        self.agents = agents
        self.num_ = 1
        self.prompt = """
            You are the Orchestrator Agent tasked with reviewing a research paper. Your job involves coordinating specialized review agents: the Experiment Agent evaluates methodology, robustness, and reproducibility; the Novelty Agent assesses originality, uniqueness, and contributions to existing knowledge; and the Impact Agent gauges potential significance, relevance, and real-world applications. Provide explicit instructions to each agent, consolidate their analyses, and present a structured, insightful summary. Clearly highlight overall strengths, weaknesses, and recommendation for acceptance, revision, or rejection.
        """

    def run(self, paper):
        agent_responses = {}
        feedback_texts = {agent.name: "" for agent in self.agents}
        for i in range(self.num_):
            for agent in self.agents:
                if feedback_texts[agent.name]:
                    agent.prompt += f"\n\n {feedback_texts[agent.name]}"
                agent_responses[agent.name] = agent.run(paper)
            combined_responses = "\n\n".join([f"{name}:\n{resp}" for name, resp in agent_responses.items()])
            analysis_prompt = f"""
You are an Coordinator reviewing the outputs of three expert agents who evaluated the same research paper.

Their responses:
{combined_responses}

Your tasks:
1. Identify any contradictions, inconsistencies, or conflicting conclusions between the agents.
2. For each agent, write a short critical feedback message suggesting what they should improve or clarify (if needed).
3. If a response is consistent and well-aligned with others, reply "No changes needed."

Format:
AgentName: [Feedback or "No changes needed"]
"""
            feedback_text = self.llm(analysis_prompt)
            print("📋 Orchestrator Feedback:\n", feedback_text)

            feedback = _parse_feedback(feedback_text)
            print("\n\n📋 PARSED Orchestrator Feedback:\n", feedback_text)
            for name in agent_responses:
                if feedback.get(name) and feedback[name].lower() != "no changes needed":
                    agent_responses[name] = feedback[name]

        print("_" * 100, agent_responses)

        prompt = self.prompt
        for agent in self.agents:
            prompt += f"\n\n {agent.name}: \n {agent_responses[agent.name]}"
        return self.llm(prompt)
