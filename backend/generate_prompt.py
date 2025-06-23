import random
from pathlib import Path

general_vocab_pool = [
    "observe", "protect", "enormous", "discover", "experiment",
    "analyze", "predict", "structure", "benefit", "solution",
    "visible", "require", "assist", "fortunate", "design",
    "approach", "compare", "detail", "opinion", "evidence"
]

# Topic-specific vocabulary
topic_word_map = {
    "animals": ["habitat", "creature", "adapt", "survive"],
    "soccer": ["goalkeeper", "teamwork", "strategy", "defend", "attempt"],
    "cooking": ["ingredients", "mixture", "measure", "combine", "recipe"],
    "superheroes": ["rescue", "brave", "mission", "powerful", "secret"],
    "space": ["planet", "explore", "astronaut", "gravity", "launch"],
    "sea creatures": ["ocean", "deep", "marine", "waves", "current"],
    "inventions": ["tool", "create", "machine", "invent", "improve"]
}

topics = list(topic_word_map.keys())

def generate_prompt(topic=None, mode="fact", grade="4th"):
    if topic is None:
        topic = random.choice(topics)

