"""Test fixtures for vocabulary system testing"""

import pytest
from typing import Dict, List, Any

# Mock vocabulary banks for testing
MOCK_GENERAL_VOCABULARY = {
    "vocabulary": [
        {"word": "enormous", "definition": "extremely large", "difficulty": 2, "type": "adjective", "example": "The enormous elephant walked slowly.", "grade_level": "2-3"},
        {"word": "investigate", "definition": "to look into something carefully", "difficulty": 2, "type": "verb", "example": "The detective will investigate the mystery.", "grade_level": "2-3"},
        {"word": "discover", "definition": "to find something new", "difficulty": 2, "type": "verb", "example": "Scientists discover new things every day.", "grade_level": "2-3"},
        {"word": "magnificent", "definition": "very beautiful or impressive", "difficulty": 3, "type": "adjective", "example": "The sunset was truly magnificent.", "grade_level": "3-4"},
        {"word": "ancient", "definition": "very old", "difficulty": 2, "type": "adjective", "example": "The ancient castle was built 800 years ago.", "grade_level": "2-3"},
        {"word": "constellation", "definition": "a group of stars that forms a pattern", "difficulty": 3, "type": "noun", "example": "Orion is a famous constellation.", "grade_level": "3-4"},
        {"word": "coordination", "definition": "the ability to move body parts together smoothly", "difficulty": 3, "type": "noun", "example": "Gymnasts need excellent coordination.", "grade_level": "3-4"},
        {"word": "determination", "definition": "the quality of continuing to try", "difficulty": 3, "type": "noun", "example": "Her determination helped her succeed.", "grade_level": "3-4"},
        {"word": "fascinating", "definition": "extremely interesting", "difficulty": 3, "type": "adjective", "example": "The documentary was fascinating.", "grade_level": "3-4"},
        {"word": "mysterious", "definition": "difficult to understand or explain", "difficulty": 3, "type": "adjective", "example": "The abandoned house looked mysterious.", "grade_level": "3-4"}
    ]
}

MOCK_TOPIC_VOCABULARY = {
    "space": {
        "vocabulary": [
            {"word": "spacecraft", "definition": "a vehicle designed for travel in space", "difficulty": 3, "type": "noun", "example": "The spacecraft landed on Mars.", "grade_level": "3-4"},
            {"word": "asteroid", "definition": "a rocky object that orbits the sun", "difficulty": 3, "type": "noun", "example": "An asteroid flew past Earth.", "grade_level": "3-4"},
            {"word": "gravity", "definition": "the force that pulls objects toward Earth", "difficulty": 2, "type": "noun", "example": "Gravity keeps us on the ground.", "grade_level": "2-3"},
            {"word": "orbit", "definition": "to move in a circle around something", "difficulty": 2, "type": "verb", "example": "The moon orbits around Earth.", "grade_level": "2-3"},
            {"word": "telescope", "definition": "an instrument for looking at distant objects", "difficulty": 2, "type": "noun", "example": "We used a telescope to see the stars.", "grade_level": "2-3"}
        ]
    },
    "animals": {
        "vocabulary": [
            {"word": "habitat", "definition": "the natural home of an animal", "difficulty": 2, "type": "noun", "example": "The forest is the bear's habitat.", "grade_level": "2-3"},
            {"word": "predator", "definition": "an animal that hunts other animals", "difficulty": 3, "type": "noun", "example": "The lion is a fierce predator.", "grade_level": "3-4"},
            {"word": "camouflage", "definition": "colors or patterns that help hide", "difficulty": 3, "type": "noun", "example": "The chameleon's camouflage is amazing.", "grade_level": "3-4"},
            {"word": "migration", "definition": "moving from one place to another", "difficulty": 3, "type": "noun", "example": "Bird migration happens every spring.", "grade_level": "3-4"},
            {"word": "nocturnal", "definition": "active at night", "difficulty": 3, "type": "adjective", "example": "Owls are nocturnal animals.", "grade_level": "3-4"}
        ]
    },
    "sports": {
        "vocabulary": [
            {"word": "teamwork", "definition": "working together as a group", "difficulty": 2, "type": "noun", "example": "Good teamwork wins games.", "grade_level": "2-3"},
            {"word": "strategy", "definition": "a plan for achieving something", "difficulty": 3, "type": "noun", "example": "The coach explained the game strategy.", "grade_level": "3-4"},
            {"word": "endurance", "definition": "the ability to keep going for a long time", "difficulty": 3, "type": "noun", "example": "Marathon runners need great endurance.", "grade_level": "3-4"},
            {"word": "agility", "definition": "the ability to move quickly and easily", "difficulty": 3, "type": "noun", "example": "The cat showed impressive agility.", "grade_level": "3-4"},
            {"word": "competition", "definition": "a contest between people or teams", "difficulty": 2, "type": "noun", "example": "The swimming competition was exciting.", "grade_level": "2-3"}
        ]
    }
}

# Test scenarios for vocabulary selection
VOCABULARY_SELECTION_SCENARIOS = {
    "empty_used_words": {
        "topic": "space",
        "used_words": [],
        "expected_count": 20,  # Should return all available words
        "description": "First vocabulary selection with no used words"
    },
    "some_used_words": {
        "topic": "space", 
        "used_words": ["spacecraft", "gravity"],
        "expected_count": 18,  # Should exclude used words
        "description": "Vocabulary selection with some words already used"
    },
    "solution_3_pool": {
        "topic": "animals",
        "used_words": ["habitat"],
        "expected_structure": {
            "general_pool": 20,  # 20 general vocabulary words
            "topic_pool": 20,    # 20 topic-specific words
            "total": 40
        },
        "description": "Solution 3 massive vocabulary pool generation"
    }
}

# Edge cases for testing
VOCABULARY_EDGE_CASES = {
    "unknown_topic": {
        "topic": "underwater_basketweaving",
        "expected_behavior": "fallback_to_general_only",
        "description": "Topic not in curated vocabulary banks"
    },
    "exhausted_vocabulary": {
        "topic": "space",
        "used_words": ["spacecraft", "asteroid", "gravity", "orbit", "telescope"],  # All topic words
        "expected_behavior": "use_general_vocabulary",
        "description": "All topic-specific vocabulary has been used"
    },
    "word_form_variations": {
        "examples": [
            {"intended": "constellation", "actual": "constellations"},
            {"intended": "olympics", "actual": "Olympics,"},
            {"intended": "animal", "actual": "animals!"},
            {"intended": "space", "actual": "Space."}
        ],
        "description": "Different word forms that should match"
    }
}

@pytest.fixture
def mock_general_vocabulary():
    """Mock general vocabulary for testing"""
    return MOCK_GENERAL_VOCABULARY

@pytest.fixture
def mock_topic_vocabulary():
    """Mock topic-specific vocabulary for testing"""
    return MOCK_TOPIC_VOCABULARY

@pytest.fixture
def vocabulary_selection_scenarios():
    """Test scenarios for vocabulary selection logic"""
    return VOCABULARY_SELECTION_SCENARIOS

@pytest.fixture
def vocabulary_edge_cases():
    """Edge cases for vocabulary system testing"""
    return VOCABULARY_EDGE_CASES

@pytest.fixture
def solution_3_test_data():
    """Specific test data for Solution 3 massive vocabulary pool"""
    return {
        "expected_pool_size": 40,
        "general_words_count": 20,
        "topic_words_count": 20,
        "word_selection_range": [2, 4],
        "repetition_reduction": 0.9,  # 90% reduction expected
        "description": "Revolutionary vocabulary system with LLM curation"
    }