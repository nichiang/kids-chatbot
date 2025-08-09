"""Test fixtures for educational content testing"""

import pytest

# Sample educational content for testing
SAMPLE_STORY_CONTENT = {
    "space": {
        "content": "Captain Maya stepped aboard her shiny new **spacecraft** and prepared for the most **incredible** adventure of her life. The **mysterious** planet in the distance was calling to her through the darkness of space.",
        "vocabulary_words": ["spacecraft", "incredible", "mysterious"],
        "expected_sentence": "Captain Maya stepped aboard her shiny new **spacecraft** and prepared for the most **incredible** adventure of her life.",
        "topic": "space"
    },
    "animals": {
        "content": "The **enormous** elephant trumpeted loudly as it walked through the **dense** jungle. Its **powerful** trunk could lift heavy logs with ease.",
        "vocabulary_words": ["enormous", "dense", "powerful"],  
        "expected_sentence": "The **enormous** elephant trumpeted loudly as it walked through the **dense** jungle.",
        "topic": "animals"
    },
    "sports": {
        "content": "The **determined** soccer player showed great **coordination** during practice. Her **amazing** skills impressed all the coaches.",
        "vocabulary_words": ["determined", "coordination", "amazing"],
        "expected_sentence": "The **determined** soccer player showed great **coordination** during practice.",
        "topic": "sports"
    }
}

SAMPLE_FACTS_CONTENT = {
    "ocean": {
        "content": "Did you know that the **deepest** part of the ocean is over 36,000 feet down? The **pressure** at that depth would crush a human instantly! Scientists use special **submarines** to explore these mysterious depths. 🌊🔬⚡",
        "vocabulary_words": ["deepest", "pressure", "submarines"],
        "expected_sentence": "Did you know that the **deepest** part of the ocean is over 36,000 feet down?",
        "topic": "ocean"
    },
    "space": {
        "content": "The **International** Space Station travels around Earth at 17,500 miles per hour! Astronauts experience **weightlessness** and can see 16 sunrises and sunsets every day. The **gravitational** pull of Earth keeps the station in orbit. 🚀🌍⭐",
        "vocabulary_words": ["International", "weightlessness", "gravitational"],
        "expected_sentence": "The **International** Space Station travels around Earth at 17,500 miles per hour!",
        "topic": "space"
    }
}

# Common vocabulary words for testing at different difficulty levels
VOCABULARY_SAMPLES = {
    "tier_2": [
        {"word": "enormous", "definition": "extremely large", "difficulty": 2},
        {"word": "investigate", "definition": "to look into something carefully", "difficulty": 2},
        {"word": "discover", "definition": "to find something new", "difficulty": 2},
        {"word": "magnificent", "definition": "very beautiful or impressive", "difficulty": 2},
        {"word": "ancient", "definition": "very old", "difficulty": 2}
    ],
    "tier_3": [
        {"word": "constellation", "definition": "a group of stars that forms a pattern", "difficulty": 3},
        {"word": "coordination", "definition": "the ability to move body parts together smoothly", "difficulty": 3},
        {"word": "determination", "definition": "the quality of continuing to try to achieve something", "difficulty": 3},
        {"word": "fascinating", "definition": "extremely interesting", "difficulty": 3},
        {"word": "mysterious", "definition": "difficult to understand or explain", "difficulty": 3}
    ]
}

# Expected question formats for testing
EXPECTED_QUESTION_FORMAT = {
    "question_structure": "What does the word **{word}** mean?",
    "options_count": 4,
    "correct_index_range": [0, 1, 2, 3],
    "sentence_reference_pattern": '".*{word}.*"'
}

# Age-appropriate content standards for testing
CONTENT_STANDARDS = {
    "max_sentence_length": 20,  # words per sentence
    "reading_level_range": [2.0, 4.0],  # Flesch-Kincaid grade level
    "vocabulary_per_content": [2, 4],  # min, max vocabulary words
    "forbidden_topics": ["violence", "adult", "scary", "inappropriate"],
    "required_elements": ["positive", "educational", "engaging"]
}

@pytest.fixture
def story_content_samples():
    """Provide sample story content for testing"""
    return SAMPLE_STORY_CONTENT

@pytest.fixture  
def facts_content_samples():
    """Provide sample facts content for testing"""
    return SAMPLE_FACTS_CONTENT

@pytest.fixture
def vocabulary_samples():
    """Provide vocabulary samples at different difficulty levels"""
    return VOCABULARY_SAMPLES

@pytest.fixture
def question_format_expectations():
    """Provide expected question format standards"""
    return EXPECTED_QUESTION_FORMAT

@pytest.fixture
def educational_standards():
    """Provide age-appropriate content standards"""
    return CONTENT_STANDARDS

@pytest.fixture
def problematic_content_examples():
    """Examples of content that should trigger the bug fixes"""
    return {
        "word_form_mismatch": {
            "intended_word": "constellation",
            "content": "Did you know there are 88 **constellations** in the sky?",
            "actual_word": "constellations"
        },
        "case_punctuation_mismatch": {
            "intended_word": "olympics",
            "content": "The **Olympics,** happen every four years!",
            "actual_word": "Olympics"
        },
        "multiple_vocabulary": {
            "content": "The **amazing** athlete showed **determination** during the **challenging** race.",
            "words": ["amazing", "determination", "challenging"]
        }
    }