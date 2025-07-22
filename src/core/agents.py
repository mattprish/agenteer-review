from langchain.llms import HuggingFacePipeline
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline


class BaseAgent:
    def __init__(self, name, model_name="Qwen/Qwen1.5-0.5B", prompt=""):
        self.name = name
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(model_name)
        pipe = pipeline("text-generation",
                        model=model,
                        tokenizer=tokenizer,
                        return_full_text=False,
                        max_new_tokens=1000,
                        )
        self.llm = HuggingFacePipeline(pipeline=pipe)
        self.prompt = prompt

    def run(self, papers):
        if type(papers) == str:
            return self.llm(self.prompt + "\n\n" + papers)
        if type(papers) == list:
            prompts = [self.prompt + "\n\n" + paper for paper in papers]
            return self.llm(prompts)


class ExperimentAgent(BaseAgent):
    def __init__(self, model_name="Qwen/Qwen3-4B"):
        super().__init__("Experiment Agent", model_name, prompt="""
            You are the Experiment Agent. Carefully examine the paper’s methodology, experimental setup, data collection, analysis techniques, and validity of results. Address the following explicitly:
                •	Are the experiments and methods described clearly and comprehensively?
                •	Are the experiments sufficiently rigorous, reproducible, and statistically sound?
                •	Are there any flaws, limitations, or oversights in the experimental design or analysis?
            Provide clear examples from the paper and suggest areas for improvement if necessary.        
        """)


class NoveltyAgent(BaseAgent):
    def __init__(self, model_name="Qwen/Qwen3-4B"):
        super().__init__("Novelty Agent", model_name, prompt="""
            You are the Novelty Agent. Critically analyze the paper’s originality and innovation:
                •	Does the paper introduce genuinely new concepts, methods, datasets, or findings?
                •	How does this work differ from existing literature or previously published research?
                •	Clearly identify and evaluate the unique contributions of this paper.
            Provide explicit references or comparisons to relevant existing works to substantiate your assessment.
        """)


class ImpactAgent(BaseAgent):
    def __init__(self, model_name="Qwen/Qwen3-4B"):
        super().__init__("Impact Agent", model_name, prompt="""
            You are the Impact Agent. Evaluate the potential impact of the paper:
                •	What are the practical or theoretical implications of this research within the broader field?
                •	How significant or influential could this research become in academia, industry, policy, or society?
                •	Are the results or conclusions clearly connected to real-world applications or advancements in knowledge?
            Clearly articulate the paper’s potential impact, explicitly addressing both immediate and long-term significance.
        """)
