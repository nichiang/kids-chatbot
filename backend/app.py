from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, List, Optional
import logging
import json
import os
from llm_provider import llm_provider
# REMOVED: generate_prompt import no longer needed (PromptManager handles all prompt logic)
from vocabulary_manager import vocabulary_manager
from prompt_manager import prompt_manager

# PROMPT MANAGER ARCHITECTURE:
# Centralized prompt generation with self-documenting methods for maintainability:
# 
# PROMPT MANAGER (prompt_manager.py):
# - Single source of truth for all prompt generation
# - Clear method names show complete user experience flow
# - Self-documenting: get_story_opening_prompt(), get_grammar_feedback_prompt(), etc.
# - No documentation drift: code IS the documentation
#
# BUSINESS LOGIC (this file):
# - Session state management and educational flow control
# - Clean PromptManager usage with readable method calls
# - Vocabulary tracking, anti-repetition, progress tracking
# - Educational standards validation and fallback handling
#
# BENEFITS:
# - Complete user experience visible through method names
# - Easy to find, modify, and test individual prompts
# - Inherently maintainable without separate documentation

# Design Phase Models - Must be defined before functions that use them
class StoryMetadata(BaseModel):
    """Metadata about characters and locations introduced in the story"""
    character_name: Optional[str] = None
    character_description: Optional[str] = None
    location_name: Optional[str] = None
    location_description: Optional[str] = None
    design_options: List[str] = []  # ["character", "location"] or subset
    needs_naming: bool = False  # True if entities are unnamed
    entity_descriptor: Optional[str] = None  # e.g., "the little boy", "the mysterious village"

class StructuredStoryResponse(BaseModel):
    """Response format for story generation with metadata"""
    story: str
    metadata: StoryMetadata

class DesignPrompt(BaseModel):
    """Design prompt information for frontend UI"""
    type: str  # "character" or "location"
    subject_name: str  # The character or location name
    aspect: str  # Current aspect being designed (e.g., "appearance", "personality")
    prompt_text: str  # "Help us bring Luna to life! They are very..."
    suggested_words: List[str]  # Max 8 vocabulary suggestions
    input_placeholder: str  # Custom placeholder text for input

class VocabularyPhase(BaseModel):
    isActive: bool = False
    questionsAsked: int = 0
    maxQuestions: int = 3
    isComplete: bool = False

class SessionData(BaseModel):
    topic: Optional[str] = None
    storyParts: List[str] = []
    currentStep: int = 0
    isComplete: bool = False
    factsShown: int = 0
    currentFact: Optional[str] = None
    allFacts: List[str] = []
    askedVocabWords: List[str] = []  # Track vocabulary words that have been asked
    awaiting_story_confirmation: bool = False  # Track if waiting for user to confirm new story
    vocabularyPhase: VocabularyPhase = VocabularyPhase()  # Track vocabulary phase state
    contentVocabulary: List[str] = []  # Track vocabulary words used in generated content
    
    # Design Phase Fields
    designPhase: Optional[str] = None  # "character", "location", or None
    currentDesignAspect: Optional[str] = None  # Current aspect being designed
    designAspectHistory: List[str] = []  # Track used aspects to ensure rotation
    storyMetadata: Optional[StoryMetadata] = None  # Store LLM metadata about story elements
    designComplete: bool = False  # Track if design phase is finished
    namingComplete: bool = False  # Track if naming phase is finished for unnamed entities

class ChatRequest(BaseModel):
    message: str
    mode: str = "storywriting"  # "storywriting" or "funfacts"
    sessionData: Optional[SessionData] = None
    storyMode: Optional[str] = "auto"  # "auto", "named", or "unnamed" for testing

class VocabQuestion(BaseModel):
    question: str
    options: List[str]
    correctIndex: int

class ChatResponse(BaseModel):
    response: str
    vocabQuestion: Optional[VocabQuestion] = None
    sessionData: Optional[SessionData] = None
    suggestedTheme: Optional[str] = None
    designPrompt: Optional[DesignPrompt] = None  # New field for design phase prompts

# Load centralized theme configuration
def load_theme_config():
    """Load theme configuration from centralized JSON file"""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'config', 'theme-config.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            logging.info("Theme configuration loaded successfully from JSON file")
            return config
    except Exception as e:
        logging.error(f"Failed to load theme configuration: {e}")
        # Fallback configuration
        return {
            "topicKeywords": {
                "space": ["space", "planet", "star", "rocket", "astronaut"],
                "animals": ["animal", "dog", "cat"],
                "fantasy": ["fantasy", "magic", "magical", "dragon", "creature"],
                "sports": ["sport", "soccer", "football"],
                "ocean": ["ocean", "sea", "fish"]
            },
            "themeMapping": {
                "fantasy": "theme-fantasy",
                "sports": "theme-sports",
                "animals": "theme-animals",
                "ocean": "theme-ocean",
                "space": "theme-space"
            },
            "defaultTheme": "theme-space"
        }

# Load theme configuration at startup
THEME_CONFIG = load_theme_config()


# REMOVED: Old prompt generation functions moved to PromptManager for better organization
# - generate_vocabulary_enhanced_prompt() -> prompt_manager.enhance_with_vocabulary()
# - generate_massive_vocabulary_pool() -> prompt_manager.generate_massive_vocabulary_pool()  
# - generate_structured_story_prompt() -> prompt_manager.get_story_opening_prompt()
#
# All prompt logic now centralized in prompt_manager.py with self-documenting method names


def select_advanced_general_words(count: int = 20, exclude: List[str] = None) -> List[str]:
    """
    Select tier 2+3 words from the expanded 100-word general vocabulary pool
    
    Args:
        count: Number of words to select (default 20)
        exclude: Words to avoid selecting (prefer fresh options)
    
    Returns:
        List of tier 2+3 general vocabulary words
    """
    if exclude is None:
        exclude = []
    
    # Get all tier 2 and tier 3 words from general pool
    general_vocabulary = vocabulary_manager.general_vocabulary
    advanced_words = [word for word in general_vocabulary 
                     if word['difficulty'] in [2, 3]]  # Tier 2+3 only
    
    # Prefer words not recently used
    preferred_words = [word for word in advanced_words 
                      if word['word'] not in exclude]
    
    # If we have enough preferred words, use them; otherwise include some used words
    if len(preferred_words) >= count:
        selected_words = preferred_words[:count]
    else:
        # Use all preferred words + some used words to reach target count
        additional_needed = count - len(preferred_words)
        used_words = [word for word in advanced_words 
                     if word['word'] in exclude]
        selected_words = preferred_words + used_words[:additional_needed]
    
    # Return just the word strings
    return [word['word'] for word in selected_words[:count]]


def get_all_topic_vocabulary(topic: str) -> List[str]:
    """
    Get all available vocabulary words for a specific topic
    
    Args:
        topic: The topic name (space, animals, sports, etc.)
    
    Returns:
        List of all topic-specific vocabulary words
    """
    # Get topic vocabulary from vocabulary manager
    topic_vocabulary = vocabulary_manager.get_vocabulary_for_topic(topic)
    
    # Filter to get only topic-specific words (not general words)
    topic_lower = topic.lower()
    if topic_lower in vocabulary_manager.topic_vocabularies:
        topic_words = vocabulary_manager.topic_vocabularies[topic_lower]
        return [word['word'] for word in topic_words]
    
    # Fallback: return empty list if no topic-specific vocabulary
    return []

def extract_vocabulary_from_content(content: str, content_vocabulary: List[str] = None) -> List[str]:
    """
    Extract vocabulary words from generated content, prioritizing bolded words
    
    Args:
        content: The generated content text
        content_vocabulary: List of vocabulary words that were intended to be used
    
    Returns:
        List of vocabulary words found in the content
    """
    if content_vocabulary is None:
        content_vocabulary = []
    
    # Extract words that are bolded with **word** format
    import re
    bolded_words = re.findall(r'\*\*(.*?)\*\*', content)
    
    # Clean up the bolded words (remove extra spaces, preserve original casing)
    extracted_words = []
    for word in bolded_words:
        clean_word = word.strip()  # Keep original casing for proper noun detection
        if clean_word and len(clean_word) > 1:  # Avoid single characters or empty strings
            extracted_words.append(clean_word)
    
    # Prioritize words that were in our intended vocabulary
    context_words = []
    for word in extracted_words:
        # Check if this extracted word matches any of our intended vocabulary
        for vocab_word in content_vocabulary:
            if vocab_word.lower() == word or vocab_word.lower() in word:
                context_words.append(vocab_word)
                break
        else:
            # If no match found in intended vocabulary, add the extracted word directly
            context_words.append(word)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_words = []
    for word in context_words:
        if word.lower() not in seen:
            seen.add(word.lower())
            unique_words.append(word)
    
    logger.info(f"Extracted vocabulary from content: {unique_words}")
    return unique_words

def log_vocabulary_debug_info(topic: str, used_words: List[str], content: str, context: str, session_total: int):
    """
    Log vocabulary debug information to server logs
    
    Args:
        topic: Topic for generating vocabulary pools
        used_words: Previously used words for exclusion
        content: The LLM response content
        context: Context description (e.g., "Story generation", "Fun fact")
        session_total: Total vocabulary words tracked in session
    """
    import re
    
    # Generate vocabulary pools for debug info
    vocab_pools = prompt_manager.generate_massive_vocabulary_pool(topic, used_words)
    bolded_words = re.findall(r'\*\*(.*?)\*\*', content)
    
    debug_info = {
        'general_pool': vocab_pools.get('general_pool', []),
        'topic_pool': vocab_pools.get('topic_pool', []),
        'excluded_words': vocab_pools.get('excluded_words', []),
        'total_available': vocab_pools.get('total_examples', 0),
        'llm_selected_words': bolded_words,
        'context': context,
        'content_preview': content[:100] + ('...' if len(content) > 100 else ''),
        'session_total': session_total
    }
    
    logging.info(f"🔍 DEBUG: Created {context.lower()} vocab debug info: {debug_info}")

def select_best_vocabulary_word(available_words: List[str]) -> str:
    """
    Select the best vocabulary word, filtering out multi-word proper nouns (like names)
    while preserving single words that could be legitimate vocabulary.
    
    IMPORTANT: This function should only be called ONCE per vocabulary question generation.
    The selected word should be passed to llm_provider.generate_vocabulary_question() 
    and used as-is without re-selection to prevent vocabulary repetition bugs.
    
    Args:
        available_words: List of available vocabulary words to choose from (already filtered 
                        to exclude words in session_data.askedVocabWords)
    
    Returns:
        The best vocabulary word (multi-word proper nouns filtered out)
    """
    if not available_words:
        logger.info("select_best_vocabulary_word: No available words")
        return None
    
    logger.info(f"select_best_vocabulary_word: Available words: {available_words}")
    
    # Filter out multi-word phrases (likely proper nouns like names)
    single_word_candidates = []
    for word in available_words:
        if word and len(word.split()) == 1:  # Only single words
            single_word_candidates.append(word)
        else:
            logger.info(f"select_best_vocabulary_word: Skipping multi-word: '{word}'")
    
    logger.info(f"select_best_vocabulary_word: Single word candidates: {single_word_candidates}")
    
    # Use the first single word (don't overly prioritize case)
    # This maintains original behavior for legitimate vocabulary words
    if single_word_candidates:
        selected = single_word_candidates[0]
        logger.info(f"select_best_vocabulary_word: Selected: '{selected}'")
        return selected
    else:
        # Last resort - return first available even if multi-word (shouldn't happen)
        selected = available_words[0]
        logger.warning(f"select_best_vocabulary_word: Using last resort word: '{selected}'")
        return selected

# DEPRECATED: Use prompt_manager.get_story_opening_prompt() instead
def generate_structured_story_prompt_DEPRECATED(topic: str, story_mode: str = "auto") -> str:
    """
    Generate a prompt that requests JSON format with story and metadata
    Uses 40/60 probability split between unnamed/named entities, or forced mode for testing
    
    Args:
        topic: The story topic chosen by the child
        story_mode: "auto" (random), "named" (force named), or "unnamed" (force unnamed)
        
    Returns:
        Structured prompt requesting JSON response with story and character/location metadata
    """
    import random
    import json
    from pathlib import Path
    
    try:
        # Load story generation templates
        story_templates_path = Path("prompts/story/04_story_generation.json")
        with open(story_templates_path, 'r') as f:
            templates = json.load(f)
        
        # Select template based on story mode
        if story_mode == "named":
            template_key = "named_entities"
            logger.info("🎯 Story Generation: FORCED NAMED entity template (testing mode)")
        elif story_mode == "unnamed":
            template_key = "unnamed_entities"
            logger.info("🎯 Story Generation: FORCED UNNAMED entity template (testing mode)")
        else:  # auto mode - use random selection
            if random.random() < 0.4:  # 40% probability for unnamed entities
                template_key = "unnamed_entities"
                logger.info("🎲 Story Generation: Selected UNNAMED entity template (40% probability)")
            else:  # 60% probability for named entities  
                template_key = "named_entities"
                logger.info("🎲 Story Generation: Selected NAMED entity template (60% probability)")
        
        selected_template = templates[template_key]["prompt_template"]
        logger.info(f"🎯 TEMPLATE DEBUG: Using template '{template_key}' for story_mode '{story_mode}'")
        formatted_prompt = selected_template.format(topic=topic)
        logger.info(f"🎯 PROMPT DEBUG: Formatted prompt length: {len(formatted_prompt)} characters")
        return formatted_prompt
        
    except Exception as e:
        logger.error(f"Error loading story generation templates: {e}")
        # Fallback to named entity template (current behavior)
        return f"""Create a story opening for the topic: {topic}

REQUIREMENTS:
- Write 2-4 sentences suitable for strong 2nd graders or 3rd graders
- Introduce a named character AND/OR a specific location with clear names
- Bold 2-3 vocabulary words using **word** format
- Use engaging, age-appropriate language that sparks imagination

RETURN AS VALID JSON in this exact format:
{{
  "story": "your story text here with **bolded** vocabulary words...",
  "metadata": {{
    "character_name": "character name if introduced, otherwise null",
    "character_description": "brief description if character introduced, otherwise null",
    "location_name": "location name if introduced, otherwise null", 
    "location_description": "brief description if location introduced, otherwise null",
    "design_options": ["character" and/or "location" based on what was introduced]
  }}
}}"""

def parse_structured_story_response(llm_response: str) -> StructuredStoryResponse:
    """
    Parse JSON response with fallback to plain text if parsing fails
    
    Args:
        llm_response: Raw LLM response (should be JSON)
        
    Returns:
        StructuredStoryResponse with story and metadata
    """
    try:
        # Try to parse as JSON
        import json
        data = json.loads(llm_response.strip())
        
        # Validate that we have the required structure
        if not isinstance(data, dict) or "story" not in data:
            raise ValueError("Invalid JSON structure - missing 'story' field")
            
        # Create metadata with defaults if missing
        metadata_dict = data.get("metadata", {})
        
        # Validate design_options
        design_options = metadata_dict.get("design_options", [])
        if not design_options:
            logger.warning(f"⚠️ VALIDATION: design_options is empty or missing in LLM response")
            # Try to infer design options from the story content
            if metadata_dict.get("character_name") or metadata_dict.get("character_description"):
                design_options = ["character"]
                logger.info(f"🔧 AUTO-FIX: Inferred design_options as ['character'] from metadata")
        
        metadata = StoryMetadata(
            character_name=metadata_dict.get("character_name"),
            character_description=metadata_dict.get("character_description"),
            location_name=metadata_dict.get("location_name"),
            location_description=metadata_dict.get("location_description"),
            design_options=design_options,
            needs_naming=metadata_dict.get("needs_naming", False),
            entity_descriptor=metadata_dict.get("entity_descriptor")
        )
        
        return StructuredStoryResponse(
            story=data["story"],
            metadata=metadata
        )
        
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        # Fallback: treat as plain story text with empty metadata
        logging.warning(f"Failed to parse structured story response: {e}")
        logging.warning(f"Raw response: {llm_response[:200]}...")
        
        return StructuredStoryResponse(
            story=llm_response,
            metadata=StoryMetadata(design_options=[])  # No design options available
        )

def load_design_aspects(design_type: str) -> dict:
    """
    Load design aspects from JSON file
    
    Args:
        design_type: "character" or "location"
        
    Returns:
        Dictionary of design aspects with prompts and vocabulary
    """
    import json
    import os
    
    filename = f"{design_type}_design_aspects.json"
    file_path = os.path.join(os.path.dirname(__file__), "prompts", "design", filename)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"Design aspects file not found: {file_path}")
        return {}
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON in design aspects file {file_path}: {e}")
        return {}

def determine_entity_type_from_descriptor(metadata: StoryMetadata) -> Optional[str]:
    """
    Determine whether entity_descriptor refers to character or location
    by matching it with character_description or location_description
    
    Args:
        metadata: Story metadata with entity_descriptor and descriptions
        
    Returns:
        "character", "location", or None if no clear match
    """
    if not metadata.entity_descriptor:
        return None
    
    descriptor = metadata.entity_descriptor.strip().lower()
    
    # Check if entity_descriptor matches character_description
    if metadata.character_description:
        char_desc = metadata.character_description.strip().lower()
        if descriptor == char_desc or descriptor in char_desc or char_desc in descriptor:
            logger.info(f"🔍 ENTITY TYPE: '{metadata.entity_descriptor}' matches character_description '{metadata.character_description}'")
            return "character"
    
    # Check if entity_descriptor matches location_description  
    if metadata.location_description:
        loc_desc = metadata.location_description.strip().lower()
        if descriptor == loc_desc or descriptor in loc_desc or loc_desc in descriptor:
            logger.info(f"🔍 ENTITY TYPE: '{metadata.entity_descriptor}' matches location_description '{metadata.location_description}'")
            return "location"
    
    # If no clear match, log for debugging and return None (will fall back to random)
    logger.warning(f"🔍 ENTITY TYPE: Could not determine type for '{metadata.entity_descriptor}' - char: '{metadata.character_description}', loc: '{metadata.location_description}'")
    return None

def select_design_focus(character_name: Optional[str], location_name: Optional[str], design_options: List[str] = None, metadata: Optional[StoryMetadata] = None) -> Optional[str]:
    """
    Select character or location design with intelligent entity type determination
    For unnamed entities that need naming, determines type based on entity_descriptor match
    
    Args:
        character_name: Name of character if introduced
        location_name: Name of location if introduced  
        design_options: Available design options from metadata (fallback for unnamed entities)
        metadata: Full story metadata for intelligent entity type determination
        
    Returns:
        "character", "location", or None if neither available
    """
    import random
    
    available_options = []
    
    # Check named entities first
    if character_name:
        available_options.append("character")
    if location_name:
        available_options.append("location")
    
    # If no named entities but design_options available, use those (for unnamed entities)
    if not available_options and design_options:
        available_options = [option for option in design_options if option in ["character", "location"]]
        logger.info(f"🔧 UNNAMED ENTITY: Using design_options {design_options} -> available: {available_options}")
        
        # BUG FIX: For unnamed entities that need naming, determine entity type intelligently
        # Instead of random choice, match entity_descriptor with character/location descriptions
        if metadata and metadata.needs_naming and metadata.entity_descriptor:
            entity_type = determine_entity_type_from_descriptor(metadata)
            if entity_type and entity_type in available_options:
                logger.info(f"🎯 NAMING BUG FIX: entity_descriptor '{metadata.entity_descriptor}' -> entity_type '{entity_type}'")
                return entity_type
    
    if not available_options:
        return None
    elif len(available_options) == 1:
        return available_options[0]
    else:
        # 50/50 random choice when both are available and no specific naming requirement
        choice = random.choice(available_options)
        logger.info(f"🎲 RANDOM DESIGN CHOICE: Selected '{choice}' from {available_options}")
        return choice

def get_next_design_aspect(design_type: str, used_aspects: List[str]) -> str:
    """
    Get next design aspect using rotation logic
    
    Args:
        design_type: "character" or "location"
        used_aspects: List of aspects already used
        
    Returns:
        Next aspect to design
    """
    aspects = load_design_aspects(design_type)
    if not aspects:
        return "appearance"  # Fallback
    
    available_aspects = [aspect for aspect in aspects.keys() if aspect not in used_aspects]
    
    if not available_aspects:
        # All aspects used, start over
        available_aspects = list(aspects.keys())
    
    # Return random available aspect for variety and engagement
    import random
    selected_aspect = random.choice(available_aspects)
    logger.info(f"🎲 ASPECT SELECTION: Randomly selected '{selected_aspect}' from {available_aspects}")
    return selected_aspect

def create_design_prompt(session_data: SessionData) -> ChatResponse:
    """
    Generate design prompt based on current design phase and aspect
    
    Args:
        session_data: Current session state
        
    Returns:
        ChatResponse with designPrompt field populated
    """
    if not session_data.designPhase or not session_data.storyMetadata:
        logging.error("create_design_prompt called without active design phase")
        return ChatResponse(
            response="Let's continue with your story!",
            sessionData=session_data
        )
    
    # Determine the subject name and description
    if session_data.designPhase == "character":
        subject_name = session_data.storyMetadata.character_name or "our character"
        subject_description = session_data.storyMetadata.character_description or ""
        # For naming phase, use the entity descriptor
        if session_data.currentDesignAspect == "naming" and session_data.storyMetadata.entity_descriptor:
            subject_descriptor = session_data.storyMetadata.entity_descriptor
        else:
            subject_descriptor = subject_description
    else:  # location
        subject_name = session_data.storyMetadata.location_name or "this place"
        subject_description = session_data.storyMetadata.location_description or ""
        # For naming phase, use the entity descriptor
        if session_data.currentDesignAspect == "naming" and session_data.storyMetadata.entity_descriptor:
            subject_descriptor = session_data.storyMetadata.entity_descriptor
        else:
            subject_descriptor = subject_description
    
    # Get the next aspect to design
    if not session_data.currentDesignAspect:
        session_data.currentDesignAspect = get_next_design_aspect(
            session_data.designPhase, 
            session_data.designAspectHistory
        )
    
    # Load design aspects for this type
    aspects = load_design_aspects(session_data.designPhase)
    aspect_data = aspects.get(session_data.currentDesignAspect, {})
    
    if not aspect_data:
        # Fallback data
        aspect_data = {
            "prompt_template": f"Help us describe {subject_name}!",
            "placeholder": "Write 1-2 sentences describing them",
            "suggestions": ["wonderful", "amazing", "special", "unique", "interesting", "fantastic", "incredible", "magical"]
        }
    
    # Generate the prompt text (use descriptor for naming, name for other aspects)
    if session_data.currentDesignAspect == "naming":
        prompt_text = aspect_data.get("prompt_template", "").format(descriptor=subject_descriptor)
        placeholder_text = aspect_data.get("placeholder", "").format(descriptor=subject_descriptor)
    else:
        prompt_text = aspect_data.get("prompt_template", "").format(name=subject_name)
        placeholder_text = aspect_data.get("placeholder", "Write 1-2 sentences")
    
    # Create the design prompt
    design_prompt = DesignPrompt(
        type=session_data.designPhase,
        subject_name=subject_name,
        aspect=session_data.currentDesignAspect,
        prompt_text=prompt_text,
        suggested_words=aspect_data.get("suggestions", []),
        input_placeholder=placeholder_text
    )
    
    return ChatResponse(
        response="", # No text response when sending design prompt
        sessionData=session_data,
        designPrompt=design_prompt
    )

def should_trigger_design_phase(structured_response: StructuredStoryResponse) -> bool:
    """
    Determine if design phase should be triggered based on story response
    
    Args:
        structured_response: Parsed story response with metadata
        
    Returns:
        True if design phase should be triggered
    """
    metadata = structured_response.metadata
    
    # Only trigger if we have at least one design option
    return bool(metadata.design_options and len(metadata.design_options) > 0)

def trigger_design_phase(session_data: SessionData, structured_response: StructuredStoryResponse) -> ChatResponse:
    """
    Initialize design phase based on story metadata
    Handles naming phase first for unnamed entities, then regular design
    
    Args:
        session_data: Current session state
        structured_response: Parsed story with character/location info
        
    Returns:
        ChatResponse with design prompt (naming first if needed)
    """
    metadata = structured_response.metadata
    
    # Store the story metadata
    session_data.storyMetadata = metadata
    
    # Select what to design (character or location)
    session_data.designPhase = select_design_focus(
        metadata.character_name, 
        metadata.location_name,
        metadata.design_options,
        metadata  # Pass full metadata for intelligent entity type determination
    )
    
    if not session_data.designPhase:
        # No design options available, continue with regular story
        logging.info("No design options available, skipping design phase")
        return ChatResponse(
            response=structured_response.story,
            sessionData=session_data
        )
    
    # Reset design state
    session_data.currentDesignAspect = None
    session_data.designAspectHistory = []
    session_data.designComplete = False
    session_data.namingComplete = False  # Reset naming completion
    
    # Check if entity needs naming first
    # Only ask for naming if: needs_naming is True AND no existing name AND naming not completed
    character_has_name = metadata.character_name and metadata.character_name.strip()
    location_has_name = metadata.location_name and metadata.location_name.strip()
    entity_already_named = character_has_name or location_has_name
    
    if metadata.needs_naming and not session_data.namingComplete and not entity_already_named:
        logging.info(f"🏷️ Entity needs naming first: {metadata.entity_descriptor}")
        session_data.currentDesignAspect = "naming"
        
        # Generate naming prompt
        design_response = create_design_prompt(session_data)
        design_response.response = structured_response.story
        return design_response
    elif entity_already_named:
        logging.info(f"🏷️ Entity already named ({metadata.character_name or metadata.location_name}), skipping naming phase")
        session_data.designAspectHistory.append("naming")  # Mark naming as used so it won't be selected
    
    logging.info(f"Triggering design phase for {session_data.designPhase}: {metadata.character_name or metadata.location_name}")
    
    # Generate the design prompt (regular aspects)
    design_response = create_design_prompt(session_data)
    
    # Include the story text in the response
    design_response.response = structured_response.story
    
    return design_response

async def handle_design_phase_interaction(user_message: str, session_data: SessionData) -> ChatResponse:
    """
    Handle user input during design phase
    
    Args:
        user_message: User's design description
        session_data: Current session state
        
    Returns:
        ChatResponse with next design prompt or story continuation
    """
    if not session_data.designPhase or not session_data.currentDesignAspect:
        logging.error("handle_design_phase_interaction called without active design phase")
        return ChatResponse(
            response="Let's continue with your story!",
            sessionData=session_data
        )
    
    # Handle naming aspect specially
    if session_data.currentDesignAspect == "naming":
        # User provided a name - update the metadata
        provided_name = user_message.strip()
        if session_data.designPhase == "character":
            session_data.storyMetadata.character_name = provided_name
        else:  # location
            session_data.storyMetadata.location_name = provided_name
        
        # Mark naming as complete
        session_data.namingComplete = True
        session_data.designAspectHistory.append("naming")
        
        # Provide positive feedback about the name choice
        feedback_response = f"What a perfect name! {provided_name} is such a wonderful choice for this {session_data.designPhase}! 🌟"
        
        # Continue to next design aspect
        aspects = load_design_aspects(session_data.designPhase)
        remaining_aspects = [aspect for aspect in aspects.keys() 
                            if aspect not in session_data.designAspectHistory and aspect != "naming"]
        
        if remaining_aspects and len(session_data.designAspectHistory) < 2:  # Limit to 2 aspects total
            session_data.currentDesignAspect = remaining_aspects[0]
            
            feedback_with_transition = f"{feedback_response}\n\nNow let's bring {provided_name} to life with more details!"
            design_response = create_design_prompt(session_data)
            design_response.response = feedback_with_transition
            return design_response
        else:
            # Design phase complete after naming
            session_data.designComplete = True
            session_data.designPhase = None
            session_data.currentDesignAspect = None
            
            completion_message = f"{feedback_response}\n\nPerfect! Now let's continue our story with {provided_name}. What happens next in the adventure?"
            
            return ChatResponse(
                response=completion_message,
                sessionData=session_data
            )
    
    # Regular design aspect handling
    subject_name = (session_data.storyMetadata.character_name if session_data.designPhase == "character" 
                   else session_data.storyMetadata.location_name)
    
    # Provide brief writing feedback (act as English tutor)
    feedback_prompt = prompt_manager.get_grammar_feedback_prompt(user_message, subject_name, session_data.designPhase)
    
    try:
        feedback_response = llm_provider.generate_response(feedback_prompt)
    except Exception as e:
        logging.error(f"Error generating writing feedback: {e}")
        feedback_response = "Great description! I love how creative you are with your writing."
    
    # Add the current aspect to history
    session_data.designAspectHistory.append(session_data.currentDesignAspect)
    
    # Load design aspects to check if we should continue
    aspects = load_design_aspects(session_data.designPhase)
    remaining_aspects = [aspect for aspect in aspects.keys() 
                        if aspect not in session_data.designAspectHistory]
    
    # Decide whether to continue with more aspects (limit to 2-3 aspects total)
    should_continue_design = (
        len(session_data.designAspectHistory) < 2 and  # Limit to 2 aspects max for engagement
        len(remaining_aspects) > 0
    )
    
    if should_continue_design:
        # Continue with next aspect
        session_data.currentDesignAspect = remaining_aspects[0]
        
        # Generate response with feedback + next design prompt
        feedback_with_transition = f"{feedback_response}\n\nWonderful! Now let's add more details to make {subject_name} even more interesting!"
        
        design_response = create_design_prompt(session_data)
        design_response.response = feedback_with_transition
        
        return design_response
    
    else:
        # Design phase complete - continue with story
        session_data.designComplete = True
        session_data.currentDesignAspect = None
        
        # Create story continuation prompt that incorporates the user's designs
        story_context = " | ".join(session_data.storyParts[-3:]) if session_data.storyParts else ""
        design_summary = f"The child has helped design {subject_name} with these details from our design session."
        
        continuation_prompt = prompt_manager.get_design_continuation_prompt(
            session_data.topic, story_context, design_summary, user_message, subject_name
        )
        
        enhanced_prompt, selected_vocab = prompt_manager.enhance_with_vocabulary(
            continuation_prompt, session_data.topic, 
            session_data.askedVocabWords + session_data.contentVocabulary
        )
        
        try:
            story_continuation = llm_provider.generate_response(enhanced_prompt)
            session_data.storyParts.append(story_continuation)
            
            # Track vocabulary from continuation
            story_vocab = extract_vocabulary_from_content(story_continuation, session_data.contentVocabulary)
            if story_vocab:
                session_data.contentVocabulary.extend(story_vocab)
                logger.info(f"📋 VOCABULARY TRACKING: Added {len(story_vocab)} words from design continuation. Total: {len(session_data.contentVocabulary)}")
            
            # Complete response with feedback + story continuation
            complete_response = f"{feedback_response}\n\nPerfect! You've helped bring {subject_name} to life! Here's how the story continues:\n\n{story_continuation}"
            
            return ChatResponse(
                response=complete_response,
                sessionData=session_data
            )
            
        except Exception as e:
            logging.error(f"Error generating story continuation after design: {e}")
            return ChatResponse(
                response=f"{feedback_response}\n\nThanks for helping design {subject_name}! Let's continue our story. What happens next?",
                sessionData=session_data
            )

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Allow frontend to call backend locally
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models already defined at top of file

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(chat_request: ChatRequest):
    try:
        user_message = chat_request.message
        mode = chat_request.mode
        session_data = chat_request.sessionData or SessionData()
        
        logger.info(f"Processing {mode} message: {user_message}")
        
        if mode == "storywriting":
            story_mode = chat_request.storyMode or "auto"
            logger.info(f"🎯 STORY MODE DEBUG: Received story_mode parameter: '{story_mode}'")
            return await handle_storywriting(user_message, session_data, story_mode)
        elif mode == "funfacts":
            return await handle_funfacts(user_message, session_data)
        else:
            return ChatResponse(response="I'm not sure what mode that is! Try storywriting or fun facts.")
            
    except Exception as e:
        logger.error(f"Error processing chat request: {e}")
        return ChatResponse(response="Sorry, I'm having trouble right now. Please try again!")

async def handle_storywriting(user_message: str, session_data: SessionData, story_mode: str = "auto") -> ChatResponse:
    """Handle storywriting mode interactions following the 10-step process"""
    
    # Handle distinct vocabulary phase messages
    if user_message == "start_vocabulary":
        return await handle_start_vocabulary(session_data)
    elif user_message == "next_vocabulary":
        return await handle_next_vocabulary(session_data)
    elif user_message == "finish_vocabulary":
        return await handle_finish_vocabulary(session_data)
    
    # Handle design phase interactions
    if session_data.designPhase and not session_data.designComplete:
        return await handle_design_phase_interaction(user_message, session_data)
    
    # If no topic is set, user is choosing a topic (Step 1)
    if not session_data.topic:
        # Extract topic from user message
        topic = extract_topic_from_message(user_message)
        session_data.topic = topic
        session_data.currentStep = 2  # Moving to Step 2 after topic selection
        
        # Generate story beginning with structured response (includes character/location metadata)
        structured_prompt = prompt_manager.get_story_opening_prompt(topic, story_mode)
        enhanced_prompt, selected_vocab = prompt_manager.enhance_with_vocabulary(
            structured_prompt, topic, session_data.askedVocabWords
        )
        
        raw_response = llm_provider.generate_response(enhanced_prompt)
        logger.info(f"🎯 LLM RESPONSE DEBUG: Raw response length: {len(raw_response)} characters")
        logger.info(f"🎯 LLM RESPONSE DEBUG: First 200 chars: {raw_response[:200]}...")
        
        structured_response = parse_structured_story_response(raw_response)
        logger.info(f"🎯 METADATA DEBUG: Parsed metadata: {structured_response.metadata}")
        logger.info(f"🎯 METADATA DEBUG: design_options: {structured_response.metadata.design_options}")
        logger.info(f"🎯 METADATA DEBUG: needs_naming: {getattr(structured_response.metadata, 'needs_naming', 'NOT_SET')}")
        
        # Add story to parts for tracking
        session_data.storyParts.append(structured_response.story)
        
        # Track vocabulary words used in the story
        story_vocab_words = extract_vocabulary_from_content(structured_response.story, session_data.contentVocabulary)
        if story_vocab_words:
            session_data.contentVocabulary.extend(story_vocab_words)
            logger.info(f"📋 VOCABULARY TRACKING: Added {len(story_vocab_words)} words from story content. Total tracked: {len(session_data.contentVocabulary)}")
        
        # Log vocabulary debug info to server logs  
        log_vocabulary_debug_info(
            topic, session_data.askedVocabWords, structured_response.story, "Initial Story Generation", len(session_data.contentVocabulary)
        )
        
        # Check if design phase should be triggered
        should_trigger = should_trigger_design_phase(structured_response)
        logger.info(f"🎯 DESIGN PHASE DEBUG: should_trigger_design_phase() returned: {should_trigger}")
        logger.info(f"🎯 DESIGN PHASE DEBUG: design_options length: {len(structured_response.metadata.design_options) if structured_response.metadata.design_options else 0}")
        
        if should_trigger:
            logger.info(f"✅ DESIGN PHASE: Triggering design phase with options: {structured_response.metadata.design_options}")
            design_response = trigger_design_phase(session_data, structured_response)
            design_response.suggestedTheme = get_theme_suggestion(topic)
            return design_response
        
        # No design phase needed, continue with regular story
        logger.info(f"❌ DESIGN PHASE: Skipping design phase - no design options or empty array")
        suggested_theme = get_theme_suggestion(topic)
        
        return ChatResponse(
            response=structured_response.story,
            sessionData=session_data,
            suggestedTheme=suggested_theme
        )
    
    # Check if story is already complete - handle vocabulary questions or new story
    elif session_data.isComplete:
        message_lower = user_message.lower().strip()
        
        # If we're awaiting confirmation for a new story
        if session_data.awaiting_story_confirmation:
            # Check for confirmation signals
            positive_responses = ["yes", "yeah", "yep", "sure", "ok", "okay", "i want", "let's", "space", "fantasy", "sports", "ocean", "animals", "mystery", "adventure", "food", "creative", "magic"]
            negative_responses = ["no", "nah", "not now", "maybe later", "i'm done", "that's it", "bye"]
            
            # Check if user is declining
            if any(neg in message_lower for neg in negative_responses):
                # User doesn't want another story
                session_data.awaiting_story_confirmation = False
                return ChatResponse(
                    response="That's perfectly fine! Thanks for sharing this wonderful story adventure with me. You did such a great job! 🌟",
                    sessionData=session_data
                )
            
            # Check if user is confirming (either explicitly or by mentioning a topic)
            elif any(pos in message_lower for pos in positive_responses) or len(user_message.split()) >= 1:
                # User wants to write another story - extract topic
                potential_new_topic = extract_topic_from_message(user_message)
                
                # Reset session data for new story
                session_data.topic = potential_new_topic
                session_data.storyParts = []
                session_data.currentStep = 2
                session_data.isComplete = False
                session_data.askedVocabWords = []
                session_data.awaiting_story_confirmation = False
                session_data.vocabularyPhase = VocabularyPhase()  # Reset vocabulary phase
                session_data.contentVocabulary = []  # Reset content vocabulary for new story
                
                # Generate story beginning with vocabulary integration
                base_prompt = prompt_manager.get_topic_selection_story_prompt(potential_new_topic)
                enhanced_prompt, selected_vocab = prompt_manager.enhance_with_vocabulary(
                    base_prompt, potential_new_topic, session_data.askedVocabWords
                )
                story_response = llm_provider.generate_response(enhanced_prompt)
                session_data.storyParts.append(story_response)
                
                # Track vocabulary words that were intended to be used
                if selected_vocab:
                    logger.info(f"New story generation included vocabulary: {selected_vocab}")
                    session_data.contentVocabulary.extend(selected_vocab)
                    logger.info(f"📋 VOCABULARY TRACKING: Added {len(selected_vocab)} words to session. Total tracked: {len(session_data.contentVocabulary)}")
                
                # Log vocabulary debug info to server logs
                log_vocabulary_debug_info(
                    potential_new_topic, session_data.askedVocabWords, story_response, "New Story Generation", len(session_data.contentVocabulary)
                )
                
                # Get theme suggestion for new topic
                suggested_theme = get_theme_suggestion(potential_new_topic)
                
                return ChatResponse(
                    response=f"Great choice! Let's write a {potential_new_topic} story! 🌟\n\n{story_response}",
                    sessionData=session_data,
                    suggestedTheme=suggested_theme
                )
            else:
                # Unclear response - ask for clarification
                return ChatResponse(
                    response="I'm not sure if you want to write another story. Would you like to pick one of those story ideas, or are you done for now?",
                    sessionData=session_data
                )
        
        # If not awaiting confirmation, check for spontaneous new topic requests (old logic)
        else:
            # Skip topic detection for generic responses or questions about vocabulary
            generic_responses = ["yes", "no", "ok", "okay", "sure", "thanks", "thank you", "great", "cool", "awesome", "nice"]
            vocab_related = ["what", "how", "why", "when", "where", "explain", "tell me", "show me"]
            
            should_check_for_new_topic = (
                len(user_message.split()) >= 2 and  # Message has at least 2 words
                not any(response in message_lower for response in generic_responses) and
                not any(word in message_lower for word in vocab_related) and
                not message_lower.startswith(("i ", "we ", "that ", "this ", "it "))  # Avoid pronouns that refer to current story
            )
            
            if should_check_for_new_topic:
                potential_new_topic = extract_topic_from_message(user_message)
                if potential_new_topic and potential_new_topic != session_data.topic:
                    # User wants to start a new story - reset session data
                    session_data.topic = potential_new_topic
                    session_data.storyParts = []
                    session_data.currentStep = 2
                    session_data.isComplete = False
                    session_data.askedVocabWords = []
                    session_data.awaiting_story_confirmation = False
                    session_data.vocabularyPhase = VocabularyPhase()  # Reset vocabulary phase
                    session_data.contentVocabulary = []  # Reset content vocabulary for new story
                    
                    # Generate story beginning with vocabulary integration
                    base_prompt = prompt_manager.get_topic_selection_story_prompt(potential_new_topic)
                    enhanced_prompt, selected_vocab = prompt_manager.enhance_with_vocabulary(
                        base_prompt, potential_new_topic, session_data.askedVocabWords
                    )
                    story_response = llm_provider.generate_response(enhanced_prompt)
                    session_data.storyParts.append(story_response)
                    
                    # Track vocabulary words that were intended to be used
                    if selected_vocab:
                        logger.info(f"Story topic switch included vocabulary: {selected_vocab}")
                        session_data.contentVocabulary.extend(selected_vocab)
                        logger.info(f"📋 VOCABULARY TRACKING: Added {len(selected_vocab)} words to session. Total tracked: {len(session_data.contentVocabulary)}")
                    
                    # Log vocabulary debug info to server logs
                    log_vocabulary_debug_info(
                        potential_new_topic, session_data.askedVocabWords, story_response, "Story Topic Switch", len(session_data.contentVocabulary)
                    )
                    
                    # Get theme suggestion for new topic
                    suggested_theme = get_theme_suggestion(potential_new_topic)
                    
                    return ChatResponse(
                        response=story_response,
                        sessionData=session_data,
                        suggestedTheme=suggested_theme
                    )
        
        # Story is done - vocabulary phase will be handled by new system
        # Mark story as complete and let the frontend trigger vocabulary phase
        return ChatResponse(
            response="The end! 🌟",
            sessionData=session_data
        )
    
    # Story is in progress (Steps 5-6)
    else:
        # Add user's contribution to story
        session_data.storyParts.append(f"User: {user_message}")
        
        # Provide grammar feedback if needed (Step 5)
        grammar_feedback = llm_provider.provide_grammar_feedback(user_message)
        
        # Generate next part of story (Steps 2-4 repeated)
        story_context = "\n".join(session_data.storyParts[-3:])  # Last 3 parts for context
        
        # Check if story should end (minimum 2 exchanges, maximum 5, or if story is getting long)
        total_story_length = len(' '.join(session_data.storyParts))
        should_end_story = (session_data.currentStep >= 3 and total_story_length > 400) or session_data.currentStep >= 6
        if should_end_story:
            # End the story with vocabulary integration
            base_prompt = prompt_manager.get_story_ending_prompt(session_data.topic, story_context)
            enhanced_prompt, selected_vocab = prompt_manager.enhance_with_vocabulary(
                base_prompt, session_data.topic, session_data.askedVocabWords + session_data.contentVocabulary
            )
            story_response = llm_provider.generate_response(enhanced_prompt)
            
            # Track vocabulary words that were intended to be used
            if selected_vocab:
                logger.info(f"Story ending included vocabulary: {selected_vocab}")
                session_data.contentVocabulary.extend(selected_vocab)
                logger.info(f"📋 VOCABULARY TRACKING: Added {len(selected_vocab)} words to session. Total tracked: {len(session_data.contentVocabulary)}")
            
            # Log vocabulary debug info to server logs
            log_vocabulary_debug_info(
                session_data.topic, session_data.askedVocabWords + session_data.contentVocabulary, story_response, "Story Ending", len(session_data.contentVocabulary)
            )
            
            # Add grammar feedback if available
            if grammar_feedback:
                story_response = grammar_feedback + "\n\n" + story_response
            
            session_data.storyParts.append(story_response)
            session_data.isComplete = True
            
            # DO NOT send vocabulary questions immediately with story ending
            # They will be sent in a follow-up interaction after user sees "The end!"
            
            return ChatResponse(
                response=story_response,
                vocabQuestion=None,  # No vocab question with story ending
                sessionData=session_data
            )
        else:
            # Continue story with vocabulary integration
            base_prompt = prompt_manager.get_continue_story_prompt(session_data.topic, story_context)
            enhanced_prompt, selected_vocab = prompt_manager.enhance_with_vocabulary(
                base_prompt, session_data.topic, session_data.askedVocabWords + session_data.contentVocabulary
            )
            story_response = llm_provider.generate_response(enhanced_prompt)
            
            # Track vocabulary words that were intended to be used
            if selected_vocab:
                logger.info(f"Story continuation included vocabulary: {selected_vocab}")
                session_data.contentVocabulary.extend(selected_vocab)
                logger.info(f"📋 VOCABULARY TRACKING: Added {len(selected_vocab)} words to session. Total tracked: {len(session_data.contentVocabulary)}")
            
            # Log vocabulary debug info to server logs
            log_vocabulary_debug_info(
                session_data.topic, session_data.askedVocabWords + session_data.contentVocabulary, story_response, "Story Continuation", len(session_data.contentVocabulary)
            )
            
            # Add grammar feedback if available
            if grammar_feedback:
                story_response = grammar_feedback + "\n\n" + story_response
            
            session_data.storyParts.append(story_response)
            session_data.currentStep += 1
            
            return ChatResponse(
                response=story_response,
                sessionData=session_data
            )

async def handle_start_vocabulary(session_data: SessionData) -> ChatResponse:
    """Start vocabulary phase after story completion"""
    logger.info("Starting vocabulary phase")
    
    # Activate vocabulary phase
    session_data.vocabularyPhase.isActive = True
    session_data.vocabularyPhase.questionsAsked = 0
    session_data.vocabularyPhase.isComplete = False
    
    # Extract vocabulary words from the generated story content
    all_story_text = "\n".join(session_data.storyParts)
    content_vocab_words = extract_vocabulary_from_content(all_story_text, session_data.contentVocabulary)
    
    # DEBUG: Log vocabulary processing for first question
    logger.info("🔍 VOCAB DEBUG - First vocabulary question processing:")
    logger.info(f"  Received askedVocabWords: {session_data.askedVocabWords}")
    logger.info(f"  Content vocabulary words found: {content_vocab_words}")
    
    # Find a vocabulary word that hasn't been asked yet
    available_words = [word for word in content_vocab_words if word not in session_data.askedVocabWords]
    logger.info(f"  Available words (not asked yet): {available_words}")
    
    if available_words:
        # Use a word from the story content, prioritizing lowercase words over proper nouns
        selected_word = select_best_vocabulary_word(available_words)
        logger.info(f"  Selected word: '{selected_word}'")
        
        session_data.askedVocabWords.append(selected_word)
        session_data.vocabularyPhase.questionsAsked = 1
        
        logger.info(f"  Updated askedVocabWords: {session_data.askedVocabWords}")
        
        # Use the actual story content as context for the vocabulary question
        vocab_question = llm_provider.generate_vocabulary_question(selected_word, context=all_story_text)
        logger.info(f"  Generated question: '{vocab_question.get('question', 'N/A')}'")
        
        return ChatResponse(
            response="Great story! Now let's test your vocabulary:",
            vocabQuestion=VocabQuestion(**vocab_question),
            sessionData=session_data
        )
    else:
        # Fallback to curated vocabulary if no words found in content
        vocab_word_data = vocabulary_manager.select_vocabulary_word(
            topic=session_data.topic or "general",
            used_words=session_data.askedVocabWords
        )
        
        if vocab_word_data:
            session_data.askedVocabWords.append(vocab_word_data['word'])
            session_data.vocabularyPhase.questionsAsked = 1
            vocab_question = llm_provider.generate_vocabulary_question(
                vocab_word_data['word'], 
                context=vocab_word_data['definition']
            )
            
            return ChatResponse(
                response="Great story! Now let's test your vocabulary:",
                vocabQuestion=VocabQuestion(**vocab_question),
                sessionData=session_data
            )
    
    # If no vocabulary words available, finish vocabulary phase
    return await handle_finish_vocabulary(session_data)

async def handle_next_vocabulary(session_data: SessionData) -> ChatResponse:
    """Request next vocabulary question with count validation"""
    logger.info(f"Requesting vocabulary question {session_data.vocabularyPhase.questionsAsked + 1} of {session_data.vocabularyPhase.maxQuestions}")
    
    # Check if we've reached the maximum
    if session_data.vocabularyPhase.questionsAsked >= session_data.vocabularyPhase.maxQuestions:
        logger.info("Max vocabulary questions reached, finishing vocabulary phase")
        return await handle_finish_vocabulary(session_data)
    
    # Extract vocabulary words from the generated story content (same approach as handle_start_vocabulary)
    all_story_text = "\n".join(session_data.storyParts)
    content_vocab_words = extract_vocabulary_from_content(all_story_text, session_data.contentVocabulary)
    
    # DEBUG: Log vocabulary processing for next question
    logger.info("🔍 VOCAB DEBUG - Next vocabulary question processing:")
    logger.info(f"  Received askedVocabWords: {session_data.askedVocabWords}")
    logger.info(f"  Content vocabulary words found: {content_vocab_words}")
    
    # Find a vocabulary word that hasn't been asked yet
    available_words = [word for word in content_vocab_words if word not in session_data.askedVocabWords]
    logger.info(f"  Available words (not asked yet): {available_words}")
    
    if available_words:
        # Use a word from the story content, prioritizing lowercase words over proper nouns
        selected_word = select_best_vocabulary_word(available_words)
        logger.info(f"  Selected word: '{selected_word}'")
        
        session_data.askedVocabWords.append(selected_word)
        session_data.vocabularyPhase.questionsAsked += 1
        
        logger.info(f"  Updated askedVocabWords: {session_data.askedVocabWords}")
        logger.info(f"  Updated questionsAsked: {session_data.vocabularyPhase.questionsAsked}")
        
        # Use the actual story content as context for the vocabulary question
        vocab_question = llm_provider.generate_vocabulary_question(selected_word, context=all_story_text)
        logger.info(f"  Generated question: '{vocab_question.get('question', 'N/A')}'")
        
        return ChatResponse(
            response="Let's try another vocabulary question:",
            vocabQuestion=VocabQuestion(**vocab_question),
            sessionData=session_data
        )
    else:
        # Fallback to curated vocabulary if no more words found in content
        vocab_word_data = vocabulary_manager.select_vocabulary_word(
            topic=session_data.topic or "general",
            used_words=session_data.askedVocabWords
        )
        
        if vocab_word_data:
            session_data.askedVocabWords.append(vocab_word_data['word'])
            session_data.vocabularyPhase.questionsAsked += 1
            vocab_question = llm_provider.generate_vocabulary_question(
                vocab_word_data['word'], 
                context=vocab_word_data['definition']
            )
            
            return ChatResponse(
                response="Let's try another vocabulary question:",
                vocabQuestion=VocabQuestion(**vocab_question),
                sessionData=session_data
            )
    
    # If no more vocabulary words available, finish vocabulary phase
    logger.info("No more vocabulary words available, finishing vocabulary phase")
    return await handle_finish_vocabulary(session_data)

async def handle_finish_vocabulary(session_data: SessionData) -> ChatResponse:
    """Finish vocabulary phase and ask for new story"""
    logger.info("Finishing vocabulary phase, asking for new story")
    
    # Mark vocabulary phase as complete
    session_data.vocabularyPhase.isComplete = True
    session_data.vocabularyPhase.isActive = False
    session_data.awaiting_story_confirmation = True
    
    story_completion_prompt = prompt_manager.get_story_completion_prompt()
    
    return ChatResponse(
        response=story_completion_prompt,
        sessionData=session_data
    )

async def handle_funfacts(user_message: str, session_data: SessionData) -> ChatResponse:
    """Handle fun facts mode interactions"""
    
    # If no topic is set, user is choosing a topic
    if not session_data.topic:
        # Extract topic from user message
        topic = extract_topic_from_message(user_message)
        session_data.topic = topic
        session_data.factsShown = 0
        session_data.contentVocabulary = []  # Reset content vocabulary for new topic
        
        # Generate first fact with vocabulary integration using external prompt system
        base_prompt = prompt_manager.get_first_fact_prompt(topic)
        enhanced_prompt, selected_vocab = prompt_manager.enhance_with_vocabulary(
            base_prompt, topic, session_data.askedVocabWords
        )
        fact_response = llm_provider.generate_response(enhanced_prompt, system_prompt=llm_provider.fun_facts_system_prompt)
        session_data.currentFact = fact_response
        session_data.allFacts.append(fact_response)
        session_data.factsShown += 1
        
        # Track vocabulary words that were intended to be used
        if selected_vocab:
            logger.info(f"Fun fact generation included vocabulary: {selected_vocab}")
            session_data.contentVocabulary.extend(selected_vocab)
            logger.info(f"📋 VOCABULARY TRACKING: Added {len(selected_vocab)} words to session. Total tracked: {len(session_data.contentVocabulary)}")
        
        # Log vocabulary debug info to server logs
        log_vocabulary_debug_info(
            topic, session_data.askedVocabWords, fact_response, "Initial Fun Fact", len(session_data.contentVocabulary)
        )
        
        # Generate vocabulary question using content-based extraction
        fact_vocab_words = extract_vocabulary_from_content(fact_response, session_data.contentVocabulary)
        vocab_question = None
        
        # Find a vocabulary word that hasn't been asked yet from the fact content
        available_fact_words = [word for word in fact_vocab_words if word not in session_data.askedVocabWords]
        
        if available_fact_words:
            selected_word = select_best_vocabulary_word(available_fact_words)
            session_data.askedVocabWords.append(selected_word)
            
            # Use the actual fact content as context for the vocabulary question
            vocab_question = llm_provider.generate_vocabulary_question(selected_word, context=fact_response)
        else:
            # Fallback to curated vocabulary if no words found in fact content
            vocab_word_data = vocabulary_manager.select_vocabulary_word(
                topic=topic,
                used_words=session_data.askedVocabWords
            )
            if vocab_word_data:
                session_data.askedVocabWords.append(vocab_word_data['word'])
                vocab_question = llm_provider.generate_vocabulary_question(
                    vocab_word_data['word'], 
                    context=vocab_word_data['definition']
                )
        
        # Get theme suggestion for this topic
        suggested_theme = get_theme_suggestion(topic)
        
        
        return ChatResponse(
            response=fact_response,
            vocabQuestion=VocabQuestion(**vocab_question) if vocab_question else None,
            sessionData=session_data,
            suggestedTheme=suggested_theme
        )
    
    # Topic is set, continue with more facts
    else:
        if session_data.factsShown < 3:  # Show 3 facts per topic
            # Generate another fact with vocabulary integration using external prompt system
            previous_facts = " | ".join(session_data.allFacts) if session_data.allFacts else "None"
            base_prompt = prompt_manager.get_continuing_fact_prompt(
                session_data.topic, 
                session_data.factsShown + 1,
                previous_facts
            )
            enhanced_prompt, selected_vocab = prompt_manager.enhance_with_vocabulary(
                base_prompt, session_data.topic, session_data.askedVocabWords + session_data.contentVocabulary
            )
            fact_response = llm_provider.generate_response(enhanced_prompt, system_prompt=llm_provider.fun_facts_system_prompt)
            session_data.currentFact = fact_response
            session_data.allFacts.append(fact_response)
            session_data.factsShown += 1
            
            # Track vocabulary words that were intended to be used
            if selected_vocab:
                logger.info(f"Continuing fun fact included vocabulary: {selected_vocab}")
                session_data.contentVocabulary.extend(selected_vocab)
                logger.info(f"📋 VOCABULARY TRACKING: Added {len(selected_vocab)} words to session. Total tracked: {len(session_data.contentVocabulary)}")
            
            # Log vocabulary debug info to server logs
            log_vocabulary_debug_info(
                session_data.topic, session_data.askedVocabWords, fact_response, "Continuing Fun Fact", len(session_data.contentVocabulary)
            )
            
            # Generate vocabulary question using content-based extraction
            fact_vocab_words = extract_vocabulary_from_content(fact_response, session_data.contentVocabulary)
            vocab_question = None
            
            # Find a vocabulary word that hasn't been asked yet from the fact content
            available_fact_words = [word for word in fact_vocab_words if word not in session_data.askedVocabWords]
            
            if available_fact_words:
                selected_word = select_best_vocabulary_word(available_fact_words)
                session_data.askedVocabWords.append(selected_word)
                
                # Use the actual fact content as context for the vocabulary question
                vocab_question = llm_provider.generate_vocabulary_question(selected_word, context=fact_response)
            else:
                # Fallback to curated vocabulary if no words found in fact content
                vocab_word_data = vocabulary_manager.select_vocabulary_word(
                    topic=session_data.topic,
                    used_words=session_data.askedVocabWords
                )
                if vocab_word_data:
                    session_data.askedVocabWords.append(vocab_word_data['word'])
                    vocab_question = llm_provider.generate_vocabulary_question(
                        vocab_word_data['word'], 
                        context=vocab_word_data['definition']
                    )
            
            return ChatResponse(
                response=fact_response,
                vocabQuestion=VocabQuestion(**vocab_question) if vocab_question else None,
                sessionData=session_data
            )
        else:
            # Check if user wants to switch to a new topic
            # Don't extract topic from "continue" messages - these are continuation signals, not topic changes
            message_lower = user_message.lower().strip()
            if message_lower == "continue":
                new_topic = None  # Ignore topic extraction for continue signals
                logger.info(f"User requested continue - no topic change")
            elif message_lower in ["same topic", "same", "more", "keep going", "this topic"]:
                new_topic = session_data.topic  # Explicitly set to current topic for same-topic continuation
                logger.info(f"User requested same topic continuation - current topic: {session_data.topic}")
            else:
                new_topic = extract_topic_from_message(user_message)
                logger.info(f"Extracted topic from message '{user_message}': {new_topic}")
                logger.info(f"Current session topic: {session_data.topic}")
            
            # Check if user wants to continue with same topic or switch to new topic
            if new_topic and new_topic == session_data.topic:
                # User wants to continue with same topic - reset for more facts
                session_data.factsShown = 0
                session_data.allFacts = []
                session_data.currentFact = None
                session_data.askedVocabWords = []  # Reset vocabulary words for fresh start
                session_data.contentVocabulary = []  # Reset content vocabulary for fresh start
                
                # Generate first fact for continuing topic using external prompt system
                base_prompt = prompt_manager.get_new_topic_fact_prompt(session_data.topic)
                enhanced_prompt, selected_vocab = prompt_manager.enhance_with_vocabulary(
                    base_prompt, session_data.topic, session_data.askedVocabWords
                )
                logger.info(f"Continuing same topic '{session_data.topic}' - generated prompt: {enhanced_prompt[:200]}...")
                fact_response = llm_provider.generate_response(enhanced_prompt, system_prompt=llm_provider.fun_facts_system_prompt)
                logger.info(f"LLM response for same topic continuation: {fact_response[:100]}...")
                session_data.currentFact = fact_response
                session_data.allFacts.append(fact_response)
                session_data.factsShown += 1
                
                # Track vocabulary words that were intended to be used
                if selected_vocab:
                    logger.info(f"Same topic continuation included vocabulary: {selected_vocab}")
                    session_data.contentVocabulary.extend(selected_vocab)
                    logger.info(f"📋 VOCABULARY TRACKING: Added {len(selected_vocab)} words to session. Total tracked: {len(session_data.contentVocabulary)}")
                
                # Log vocabulary debug info to server logs
                log_vocabulary_debug_info(
                    session_data.topic, session_data.askedVocabWords, fact_response, "Same Topic Continuation", len(session_data.contentVocabulary)
                )
                
                # Generate vocabulary question using content-based extraction
                fact_vocab_words = extract_vocabulary_from_content(fact_response, session_data.contentVocabulary)
                vocab_question = None
                
                # Find a vocabulary word that hasn't been asked yet from the fact content
                available_fact_words = [word for word in fact_vocab_words if word not in session_data.askedVocabWords]
                
                if available_fact_words:
                    selected_word = select_best_vocabulary_word(available_fact_words)
                    session_data.askedVocabWords.append(selected_word)
                    
                    # Use the actual fact content as context for the vocabulary question
                    vocab_question = llm_provider.generate_vocabulary_question(selected_word, context=fact_response)
                else:
                    # Fallback to curated vocabulary if no words found in fact content
                    vocab_word_data = vocabulary_manager.select_vocabulary_word(
                        topic=session_data.topic,
                        used_words=session_data.askedVocabWords
                    )
                    if vocab_word_data:
                        session_data.askedVocabWords.append(vocab_word_data['word'])
                        vocab_question = llm_provider.generate_vocabulary_question(
                            vocab_word_data['word'], 
                            context=vocab_word_data['definition']
                        )
                
                return ChatResponse(
                    response=f"Great! Let's continue with more {session_data.topic} facts!\n\n{fact_response}",
                    vocabQuestion=VocabQuestion(**vocab_question) if vocab_question else None,
                    sessionData=session_data
                )
            elif new_topic and new_topic != session_data.topic:
                # Reset session state for new topic
                session_data.topic = new_topic
                session_data.factsShown = 0
                session_data.allFacts = []
                session_data.currentFact = None
                session_data.askedVocabWords = []  # Reset vocabulary words for new topic
                session_data.contentVocabulary = []  # Reset content vocabulary for new topic
                
                # Generate first fact for new topic with vocabulary integration using external prompt system
                base_prompt = prompt_manager.get_new_topic_fact_prompt(new_topic)
                enhanced_prompt, selected_vocab = prompt_manager.enhance_with_vocabulary(
                    base_prompt, new_topic, session_data.askedVocabWords
                )
                fact_response = llm_provider.generate_response(enhanced_prompt, system_prompt=llm_provider.fun_facts_system_prompt)
                session_data.currentFact = fact_response
                session_data.allFacts.append(fact_response)
                session_data.factsShown += 1
                
                # Track vocabulary words that were intended to be used
                if selected_vocab:
                    logger.info(f"New topic fun fact included vocabulary: {selected_vocab}")
                    session_data.contentVocabulary.extend(selected_vocab)
                    logger.info(f"📋 VOCABULARY TRACKING: Added {len(selected_vocab)} words to session. Total tracked: {len(session_data.contentVocabulary)}")
                
                # Log vocabulary debug info to server logs
                log_vocabulary_debug_info(
                    new_topic, session_data.askedVocabWords, fact_response, "New Topic Fun Fact", len(session_data.contentVocabulary)
                )
                
                # Generate vocabulary question using content-based extraction
                fact_vocab_words = extract_vocabulary_from_content(fact_response, session_data.contentVocabulary)
                vocab_question = None
                
                # Find a vocabulary word that hasn't been asked yet from the fact content
                available_fact_words = [word for word in fact_vocab_words if word not in session_data.askedVocabWords]
                
                if available_fact_words:
                    selected_word = select_best_vocabulary_word(available_fact_words)
                    session_data.askedVocabWords.append(selected_word)
                    
                    # Use the actual fact content as context for the vocabulary question
                    vocab_question = llm_provider.generate_vocabulary_question(selected_word, context=fact_response)
                else:
                    # Fallback to curated vocabulary if no words found in fact content
                    vocab_word_data = vocabulary_manager.select_vocabulary_word(
                        topic=new_topic,
                        used_words=session_data.askedVocabWords
                    )
                    if vocab_word_data:
                        session_data.askedVocabWords.append(vocab_word_data['word'])
                        vocab_question = llm_provider.generate_vocabulary_question(
                            vocab_word_data['word'], 
                            context=vocab_word_data['definition']
                        )
                
                # Get theme suggestion for new topic
                suggested_theme = get_theme_suggestion(new_topic)
                
                return ChatResponse(
                    response=fact_response,
                    vocabQuestion=VocabQuestion(**vocab_question) if vocab_question else None,
                    sessionData=session_data,
                    suggestedTheme=suggested_theme
                )
            else:
                # No new topic detected, ask if they want to switch topics
                topic_name = session_data.topic if session_data.topic else "general"
                return ChatResponse(
                    response=f"We've explored some great {topic_name} facts! Would you like to learn about a different topic? Try animals, space, inventions, or something else!",
                    sessionData=session_data
                )

# Legacy function removed - now using vocabulary_manager.select_vocabulary_word()

def extract_topic_from_message(message: str) -> str:
    """Extract topic from user message using centralized config"""
    message_lower = message.lower()
    
    # Use centralized topic keywords from config
    for topic, keywords in THEME_CONFIG['topicKeywords'].items():
        if any(keyword in message_lower for keyword in keywords):
            return topic
    
    # Default topic extraction - use first word that looks like a topic
    words = message.split()
    return words[0] if words else "adventure"

def get_theme_suggestion(topic: str) -> str:
    """Map topic to theme suggestion for frontend using centralized config"""
    return THEME_CONFIG['themeMapping'].get(topic.lower(), THEME_CONFIG['defaultTheme'])

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "English Learning Chatbot API is running!"}

# Mount static files from frontend directory AFTER all API routes
import os
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/", StaticFiles(directory=frontend_path, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)