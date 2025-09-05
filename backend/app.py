from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, List, Optional, Tuple
import logging
import json
import os
import time
import glob
from datetime import datetime
from functools import wraps
import statistics
from llm_provider import llm_provider
# REMOVED: generate_prompt import no longer needed (PromptManager handles all prompt logic)
from vocabulary_manager import vocabulary_manager
from prompt_manager import prompt_manager
from content_manager import content_manager

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

# === LATENCY MEASUREMENT SYSTEM ===

def setup_latency_logging():
    """Initialize latency logging with 5MB rotation strategy"""
    # Create logs directory
    os.makedirs('logs', exist_ok=True)
    
    # Rotate logs if they exceed 5MB
    rotate_logs_if_needed()
    
    # Clean up old archives (keep 5 most recent)
    cleanup_old_archives(keep_count=5)
    
    # Configure latency logger
    latency_logger = logging.getLogger('latency')
    latency_logger.setLevel(logging.INFO)
    
    # Clear existing handlers
    latency_logger.handlers.clear()
    
    # File handler for latency logs
    handler = logging.FileHandler('logs/latency.jsonl', mode='a')
    handler.setFormatter(logging.Formatter('%(message)s'))
    latency_logger.addHandler(handler)
    
    # Console handler for development
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('🕐 LATENCY: %(message)s'))
    latency_logger.addHandler(console_handler)

def rotate_logs_if_needed():
    """Rotate logs when they exceed 5MB threshold"""
    MAX_LOG_SIZE = 5_000_000  # 5MB
    
    log_files = [
        'logs/latency.jsonl',
        'logs/story_latency.jsonl'
    ]
    
    for log_file in log_files:
        if os.path.exists(log_file) and os.path.getsize(log_file) > MAX_LOG_SIZE:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            archive_name = f"{log_file}.{timestamp}.archive"
            
            print(f"📁 Rotating log file: {log_file} -> {archive_name}")
            os.rename(log_file, archive_name)

def cleanup_old_archives(keep_count=5):
    """Keep only the most recent archive files"""
    for log_type in ['latency.jsonl', 'story_latency.jsonl']:
        pattern = f"logs/{log_type}.*.archive"
        archives = glob.glob(pattern)
        
        if len(archives) > keep_count:
            # Sort by modification time, keep newest
            archives.sort(key=os.path.getmtime)
            old_archives = archives[:-keep_count]
            
            for old_file in old_archives:
                os.remove(old_file)
                print(f"🗑️ Cleaned up old archive: {old_file}")

class LatencyLogger:
    """Comprehensive request and LLM call timing measurement"""
    
    def __init__(self):
        self.logger = logging.getLogger('latency')
        self.request_start = None
        self.llm_calls = []
        
    def measure_request(self, func):
        """Decorator to measure total request processing time"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            self.request_start = time.perf_counter()
            
            try:
                result = await func(*args, **kwargs)
                
                total_time = (time.perf_counter() - self.request_start) * 1000
                
                # Log comprehensive timing data
                self.log_request_completion(
                    total_time=total_time,
                    llm_calls=self.llm_calls.copy(),
                    result_type=getattr(result, 'response_type', 'unknown')
                )
                
                return result
            finally:
                self.llm_calls.clear()
                
        return wrapper
    
    def measure_llm_call(self, call_type: str):
        """Decorator to measure individual LLM API calls"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.perf_counter()
                
                try:
                    result = await func(*args, **kwargs)
                    duration = (time.perf_counter() - start_time) * 1000
                    
                    self.llm_calls.append({
                        'type': call_type,
                        'duration': round(duration, 2),
                        'timestamp': time.time()
                    })
                    
                    return result
                except Exception as e:
                    duration = (time.perf_counter() - start_time) * 1000
                    self.llm_calls.append({
                        'type': call_type,
                        'duration': round(duration, 2),
                        'error': str(e),
                        'timestamp': time.time()
                    })
                    raise
                    
            return wrapper
        return decorator
    
    def log_request_completion(self, total_time: float, llm_calls: list, result_type: str):
        """Log comprehensive request timing data"""
        # Import here to avoid circular imports
        from llm_provider import llm_call_timings
        
        # Get LLM call timings from llm_provider and clear the list
        current_llm_calls = llm_call_timings.copy()
        llm_call_timings.clear()
        
        llm_total = sum(call['duration'] for call in current_llm_calls)
        processing_time = total_time - llm_total
        
        log_data = {
            'timestamp': time.time(),
            'total_request_time': round(total_time, 2),
            'llm_total_time': round(llm_total, 2),
            'processing_time': round(processing_time, 2),
            'llm_calls': current_llm_calls,
            'result_type': result_type,
            'llm_call_count': len(current_llm_calls)
        }
        
        self.logger.info(json.dumps(log_data))

class StoryLatencyTracker:
    """Track latency specifically for story exchanges and completion"""
    
    def __init__(self):
        self.story_exchanges = []
        self.story_start_time = None
        
    def start_story(self, topic: str, mode: str):
        """Initialize story tracking"""
        self.story_start_time = time.time()
        self.story_exchanges = []
        
    def log_exchange(self, exchange_type: str, latency: float, user_input: str, response_type: str):
        """Log individual story exchange timing"""
        exchange_data = {
            'exchange_number': len(self.story_exchanges) + 1,
            'exchange_type': exchange_type,  # 'story_continuation', 'vocab_question', 'design_phase'
            'latency': round(latency, 2),
            'response_type': response_type,
            'timestamp': time.time(),
            'user_input_length': len(user_input) if user_input else 0
        }
        
        self.story_exchanges.append(exchange_data)
        
    def complete_story(self, topic: str, mode: str):
        """Log story completion summary with latency analysis"""
        if not self.story_exchanges:
            return None
            
        total_story_time = time.time() - self.story_start_time if self.story_start_time else 0
        average_latency = sum(ex['latency'] for ex in self.story_exchanges) / len(self.story_exchanges)
        latencies = [ex['latency'] for ex in self.story_exchanges]
        
        story_summary = {
            'story_completion_time': time.time(),
            'topic': topic,
            'mode': mode,
            'total_exchanges': len(self.story_exchanges),
            'average_latency': round(average_latency, 2),
            'total_story_duration': round(total_story_time, 2),
            'exchanges': self.story_exchanges,
            'latency_distribution': {
                'min': min(latencies),
                'max': max(latencies),
                'median': round(statistics.median(latencies), 2)
            }
        }
        
        # Log to dedicated story latency file
        os.makedirs('logs', exist_ok=True)
        with open('logs/story_latency.jsonl', 'a') as f:
            f.write(json.dumps(story_summary) + '\n')
        
        # Reset for next story
        self.story_exchanges = []
        self.story_start_time = None
        
        return story_summary

# Initialize global instances
latency_logger = LatencyLogger()
story_tracker = StoryLatencyTracker()

def determine_story_exchange_type(session_data: 'SessionData', result: 'ChatResponse') -> str:
    """Determine the type of story exchange for latency tracking"""
    # Check if vocabulary question was returned
    if hasattr(result, 'vocabQuestion') and result.vocabQuestion:
        return 'vocab_question'
    
    # Check if design phase is active
    if hasattr(session_data, 'designPhase') and session_data.designPhase:
        return 'design_phase'
    
    # Check if this is story completion
    if hasattr(session_data, 'isComplete') and session_data.isComplete:
        return 'story_completion'
    
    # Check if this is topic selection
    if not session_data.topic or session_data.currentStep == 0:
        return 'topic_selection'
    
    # Default to story continuation
    return 'story_continuation'

# === END LATENCY MEASUREMENT SYSTEM ===

# Design Phase Models - Must be defined before functions that use them
class StoryMetadata(BaseModel):
    """Metadata about characters and locations introduced in the story (LEGACY)"""
    character_name: Optional[str] = None
    character_description: Optional[str] = None
    location_name: Optional[str] = None
    location_description: Optional[str] = None
    design_options: List[str] = []  # ["character", "location"] or subset
    needs_naming: bool = False  # True if entities are unnamed
    entity_descriptor: Optional[str] = None  # e.g., "the little boy", "the mysterious village"

class EntityLists(BaseModel):
    """Entity lists with explicit categorization from LLM"""
    named: List[str] = []     # Named entities (e.g., ["Alex", "Maya"])
    unnamed: List[str] = []   # Unnamed entities (e.g., ["the little boy", "clever inventor"])

class StoryEntities(BaseModel):
    """Complete entity structure from LLM response"""
    characters: EntityLists = EntityLists()
    locations: EntityLists = EntityLists()

class EnhancedStoryResponse(BaseModel):
    """New response format with explicit entity metadata"""
    story: str
    entities: StoryEntities
    vocabulary_words: List[str] = []

class StructuredStoryResponse(BaseModel):
    """Response format for story generation with metadata (LEGACY)"""
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
    storyMetadata: Optional[StoryMetadata] = None  # Store LLM metadata about story elements (LEGACY)
    designComplete: bool = False  # Track if design phase is finished
    namingComplete: bool = False  # Track if naming phase is finished for unnamed entities
    
    # Enhanced Entity System Fields
    designedEntities: List[str] = []  # Track entities that have been designed
    currentEntityType: Optional[str] = None  # "character" or "location" for current entity
    currentEntityDescriptor: Optional[str] = None  # Descriptor of current entity being designed
    
    # Enhanced Story Structure Fields
    storyPhase: Optional[str] = None  # "setup", "development", "climax", "resolution"
    conflictType: Optional[str] = None  # "emotional", "social", "problem_solving", "environmental", "adventure"
    conflictScale: Optional[str] = None  # "epic_scale", "daily_scale"
    narrativeAssessment: Optional[dict] = None  # Last LLM assessment results
    characterGrowthScore: int = 0  # 0-100 scale tracking character development
    completenessScore: int = 0  # 0-100 scale tracking story completeness

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

def parse_enhanced_story_response(llm_response: str) -> EnhancedStoryResponse:
    """
    Parse JSON response with new entity-based metadata structure
    
    Args:
        llm_response: Raw LLM response with new entities format
        
    Returns:
        EnhancedStoryResponse with story and explicit entity lists
    """
    try:
        import json
        data = json.loads(llm_response.strip())
        
        # Validate basic structure
        if not isinstance(data, dict) or "story" not in data:
            raise ValueError("Invalid JSON structure - missing 'story' field")
            
        # Extract entities with validation
        entities_dict = data.get("entities", {})
        if not isinstance(entities_dict, dict):
            logging.warning("⚠️ VALIDATION: entities field is not a dictionary, using empty entities")
            entities_dict = {}
            
        # Validate and extract character entities
        characters_dict = entities_dict.get("characters", {})
        if not isinstance(characters_dict, dict):
            logging.warning("⚠️ VALIDATION: entities.characters is not a dictionary, using empty lists")
            characters_dict = {}
            
        named_chars = characters_dict.get("named", [])
        unnamed_chars = characters_dict.get("unnamed", [])
        
        # Validate list types
        if not isinstance(named_chars, list):
            logging.warning("⚠️ VALIDATION: characters.named is not a list, converting to empty list")
            named_chars = []
        if not isinstance(unnamed_chars, list):
            logging.warning("⚠️ VALIDATION: characters.unnamed is not a list, converting to empty list")
            unnamed_chars = []
            
        # Validate and extract location entities
        locations_dict = entities_dict.get("locations", {})
        if not isinstance(locations_dict, dict):
            logging.warning("⚠️ VALIDATION: entities.locations is not a dictionary, using empty lists")
            locations_dict = {}
            
        named_locs = locations_dict.get("named", [])
        unnamed_locs = locations_dict.get("unnamed", [])
        
        # Validate list types
        if not isinstance(named_locs, list):
            logging.warning("⚠️ VALIDATION: locations.named is not a list, converting to empty list")
            named_locs = []
        if not isinstance(unnamed_locs, list):
            logging.warning("⚠️ VALIDATION: locations.unnamed is not a list, converting to empty list")
            unnamed_locs = []
            
        # Extract vocabulary words
        vocab_words = data.get("vocabulary_words", [])
        if not isinstance(vocab_words, list):
            logging.warning("⚠️ VALIDATION: vocabulary_words is not a list, converting to empty list")
            vocab_words = []
            
        # Create validated entity structure
        entities = StoryEntities(
            characters=EntityLists(named=named_chars, unnamed=unnamed_chars),
            locations=EntityLists(named=named_locs, unnamed=unnamed_locs)
        )
        
        # Log successful parsing
        total_entities = len(named_chars) + len(unnamed_chars) + len(named_locs) + len(unnamed_locs)
        logging.info(f"✅ ENTITY PARSE: Found {total_entities} entities - "
                    f"chars({len(named_chars)} named, {len(unnamed_chars)} unnamed), "
                    f"locs({len(named_locs)} named, {len(unnamed_locs)} unnamed)")
        
        return EnhancedStoryResponse(
            story=data["story"],
            entities=entities,
            vocabulary_words=vocab_words
        )
        
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        # Fallback: treat as plain story text with empty entities
        logging.warning(f"Failed to parse enhanced story response: {e}")
        logging.warning(f"Raw response: {llm_response[:200]}...")
        
        # Try to fall back to legacy parsing
        try:
            legacy_response = parse_structured_story_response(llm_response)
            logging.info("🔧 FALLBACK: Successfully used legacy parser")
            
            # Convert legacy format to new format
            entities = StoryEntities()
            if legacy_response.metadata.character_name:
                entities.characters.named = [legacy_response.metadata.character_name]
            elif legacy_response.metadata.character_description:
                entities.characters.unnamed = [legacy_response.metadata.character_description]
                
            if legacy_response.metadata.location_name:
                entities.locations.named = [legacy_response.metadata.location_name]
            elif legacy_response.metadata.location_description:
                entities.locations.unnamed = [legacy_response.metadata.location_description]
                
            return EnhancedStoryResponse(
                story=legacy_response.story,
                entities=entities,
                vocabulary_words=[]  # Legacy format doesn't include vocab words explicitly
            )
            
        except Exception as legacy_error:
            logging.error(f"❌ FALLBACK FAILED: Legacy parser also failed: {legacy_error}")
            return EnhancedStoryResponse(
                story=llm_response,
                entities=StoryEntities(),
                vocabulary_words=[]
            )

def validate_entity_structure(entities: StoryEntities) -> bool:
    """
    Validate that entity structure has at least one designable entity
    
    Args:
        entities: StoryEntities to validate
        
    Returns:
        True if there are entities that need design, False otherwise
    """
    total_entities = (len(entities.characters.named) + len(entities.characters.unnamed) + 
                     len(entities.locations.named) + len(entities.locations.unnamed))
    
    if total_entities == 0:
        logging.warning("⚠️ VALIDATION: No entities found for design phase")
        return False
        
    # Check for designable entities (both named and unnamed entities can be designed)
    named_entities = len(entities.characters.named) + len(entities.locations.named)
    unnamed_entities = len(entities.characters.unnamed) + len(entities.locations.unnamed)
    total_designable = named_entities + unnamed_entities
    
    if total_designable == 0:
        logging.info("ℹ️ VALIDATION: No entities found - no design phase needed")
        return False
        
    if unnamed_entities > 0:
        logging.info(f"✅ VALIDATION: Found {unnamed_entities} unnamed entities for full design phase (naming + aspects)")
    if named_entities > 0:
        logging.info(f"✅ VALIDATION: Found {named_entities} named entities for aspect design phase (skip naming)")
        
    logging.info(f"✅ VALIDATION: Total {total_designable} entities available for design phase")
    return True

def get_next_design_entity(entities: StoryEntities, designed_entities: List[str] = None) -> Optional[Tuple[str, str, bool]]:
    """
    Get the next entity that needs design from entity lists
    
    Args:
        entities: StoryEntities with all entities
        designed_entities: List of entities already designed
        
    Returns:
        Tuple of (entity_type, entity_descriptor, is_named) or None if no more entities
        is_named indicates whether to skip naming phase (True = skip naming, False = start with naming)
    """
    if designed_entities is None:
        designed_entities = []
        
    # Priority 1: Unnamed entities (need full design: naming + aspects)
    # Check unnamed characters first
    for char in entities.characters.unnamed:
        if char not in designed_entities:
            logging.info(f"🎯 DESIGN: Next entity is unnamed character '{char}' (full design)")
            return ("character", char, False)  # is_named = False, so start with naming
            
    # Check unnamed locations next
    for loc in entities.locations.unnamed:
        if loc not in designed_entities:
            logging.info(f"🎯 DESIGN: Next entity is unnamed location '{loc}' (full design)")
            return ("location", loc, False)  # is_named = False, so start with naming
    
    # Priority 2: Named entities (aspect design only, skip naming)
    # Check named characters
    for char in entities.characters.named:
        if char not in designed_entities:
            logging.info(f"🎯 DESIGN: Next entity is named character '{char}' (aspect design only)")
            return ("character", char, True)  # is_named = True, so skip naming
            
    # Check named locations
    for loc in entities.locations.named:
        if loc not in designed_entities:
            logging.info(f"🎯 DESIGN: Next entity is named location '{loc}' (aspect design only)")
            return ("location", loc, True)  # is_named = True, so skip naming
            
    logging.info("✅ DESIGN: All entities have been designed")
    return None

def load_design_aspects(design_type: str) -> dict:
    """
    Load design aspects from ContentManager
    
    Args:
        design_type: "character" or "location"
        
    Returns:
        Dictionary of design aspects with prompts and vocabulary
    """
    try:
        # Get design templates from ContentManager
        design_templates = content_manager.content.get("design_templates", {})
        aspects = design_templates.get(design_type, {})
        
        if not aspects:
            logging.warning(f"No design aspects found for type: {design_type}")
            return {}
            
        logging.info(f"✅ Loaded design aspects for {design_type} from ContentManager")
        return aspects
        
    except Exception as e:
        logging.error(f"❌ Failed to load design aspects for {design_type}: {e}")
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
            response=content_manager.get_bot_response("story_mode.continue_story"),
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
        # Fallback data based on current aspect
        if session_data.currentDesignAspect == "naming":
            aspect_data = {
                "prompt_template": "What should we call {descriptor}?",
                "placeholder": "What would you like to name them?",
                "suggestions": ["Alex", "Maya", "Sam", "Riley", "Jordan", "Casey", "Taylor", "Morgan"]
            }
        else:
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

def trigger_enhanced_design_phase(session_data: SessionData, enhanced_response: EnhancedStoryResponse) -> ChatResponse:
    """
    Initialize design phase using new entity-based metadata system
    
    Args:
        session_data: Current session state
        enhanced_response: Parsed story with explicit entity lists
        
    Returns:
        ChatResponse with design prompt for first designable entity
    """
    entities = enhanced_response.entities
    
    # Initialize entity tracking if not exists
    if not hasattr(session_data, 'designedEntities'):
        session_data.designedEntities = []
    if not hasattr(session_data, 'currentEntityType'):
        session_data.currentEntityType = None
    if not hasattr(session_data, 'currentEntityDescriptor'):
        session_data.currentEntityDescriptor = None
        
    # Reset design state
    session_data.currentDesignAspect = None
    session_data.designAspectHistory = []
    session_data.designComplete = False
    session_data.namingComplete = False
    
    # Get the next entity that needs design
    next_entity = get_next_design_entity(entities, session_data.designedEntities)
    if not next_entity:
        # No more entities to design, continue with regular story
        logging.info("✅ ENHANCED DESIGN: All entities designed, continuing with story")
        return ChatResponse(
            response=enhanced_response.story,
            sessionData=session_data
        )
        
    entity_type, entity_descriptor, is_named = next_entity
    session_data.currentEntityType = entity_type
    session_data.currentEntityDescriptor = entity_descriptor
    
    # Set design phase type
    session_data.designPhase = entity_type
    
    # Determine starting aspect based on whether entity is already named
    if is_named:
        # Named entity: Skip naming, start with appearance/personality/etc
        session_data.namingComplete = True  # Mark as already named
        # Choose a random aspect for variety (appearance, personality, dreams, skills)
        import random
        aspects = ["appearance", "personality", "dreams", "skills"] 
        session_data.currentDesignAspect = random.choice(aspects)
        logging.info(f"🎯 ENHANCED DESIGN: Named entity '{entity_descriptor}' - starting with {session_data.currentDesignAspect} aspect")
    else:
        # Unnamed entity: Start with naming as before
        session_data.currentDesignAspect = "naming"
        logging.info(f"🎯 ENHANCED DESIGN: Unnamed entity '{entity_descriptor}' - starting with naming")
    
    logging.info(f"🎯 ENHANCED DESIGN: Starting design for {entity_type} '{entity_descriptor}'")
    
    # Create design prompt using the enhanced entity system
    design_response = create_enhanced_design_prompt(session_data)
    design_response.response = enhanced_response.story
    
    return design_response

def create_enhanced_design_prompt(session_data: SessionData) -> ChatResponse:
    """
    Create design prompt using enhanced entity system
    
    Args:
        session_data: Current session state with entity information
        
    Returns:
        ChatResponse with design prompt
    """
    from content_manager import content_manager
    
    entity_type = session_data.currentEntityType
    entity_descriptor = session_data.currentEntityDescriptor
    current_aspect = session_data.currentDesignAspect
    
    if current_aspect == "naming":
        # Generate naming prompt
        try:
            # Get naming templates
            naming_template = content_manager.get_design_template(f"{entity_type}.naming")
            
            # Create naming prompt
            prompt_text = f"Can you name {entity_descriptor}?"
            
            # Get name suggestions based on entity type
            if entity_type == "character":
                suggested_words = ["Alex", "Maya", "Sam", "River", "Sky", "Sage", "Blake", "Quinn"]
            else:  # location
                suggested_words = ["Crystal Palace", "Mystic Falls", "Adventure Park", "Sunset Beach", "Secret Garden", "Magic Library", "Wonder Cave", "Star Station"]
                
            placeholder = f"Enter a name for {entity_descriptor}"
            
            design_prompt = DesignPrompt(
                type=entity_type,
                subject_name=entity_descriptor,
                aspect=current_aspect,
                prompt_text=prompt_text,
                suggested_words=suggested_words,
                input_placeholder=placeholder
            )
            
            return ChatResponse(
                response="",  # No story text for design prompts
                sessionData=session_data,
                designPrompt=design_prompt
            )
            
        except Exception as e:
            logging.error(f"❌ Failed to create enhanced naming prompt: {e}")
            # Fallback to simple prompt
            design_prompt = DesignPrompt(
                type=entity_type,
                subject_name=entity_descriptor,
                aspect="naming",
                prompt_text=f"Can you name {entity_descriptor}?",
                suggested_words=["Alex", "Maya", "Sam", "River"],
                input_placeholder=f"Enter a name for {entity_descriptor}"
            )
            
            return ChatResponse(
                response="",
                sessionData=session_data,
                designPrompt=design_prompt
            )
    else:
        # Handle description aspects (appearance, personality, dreams, skills, flaws)
        try:
            # Get the named entity - prioritize enhanced system for named entities
            entity_name = "the entity"  # fallback
            
            # For enhanced system: check if we have a current entity descriptor 
            if hasattr(session_data, 'currentEntityDescriptor') and session_data.currentEntityDescriptor:
                # If this is a design phase for a named entity (already has a name in storyMetadata)
                # or if the descriptor looks like a name (single word, capitalized), use it directly
                descriptor = session_data.currentEntityDescriptor
                
                # Check if this looks like a proper name (single capitalized word)
                if descriptor and len(descriptor.split()) == 1 and descriptor[0].isupper():
                    entity_name = descriptor
                    logging.info(f"🎯 ENHANCED ENTITY NAME: Using currentEntityDescriptor '{entity_name}' (detected as proper name)")
                # Otherwise, check storyMetadata for the actual name (for entities that went through naming)
                elif session_data.storyMetadata:
                    if entity_type == "character" and session_data.storyMetadata.character_name:
                        entity_name = session_data.storyMetadata.character_name
                        logging.info(f"🎯 ENHANCED ENTITY NAME: Using storyMetadata character_name '{entity_name}' for descriptor '{descriptor}'")
                    elif entity_type == "location" and session_data.storyMetadata.location_name:
                        entity_name = session_data.storyMetadata.location_name
                        logging.info(f"🎯 ENHANCED ENTITY NAME: Using storyMetadata location_name '{entity_name}' for descriptor '{descriptor}'")
                    else:
                        # If no name in storyMetadata, use descriptor as fallback
                        entity_name = descriptor
                        logging.info(f"🎯 ENHANCED ENTITY NAME: Using currentEntityDescriptor '{entity_name}' as fallback")
                else:
                    # Use descriptor directly if no storyMetadata
                    entity_name = descriptor
                    logging.info(f"🎯 ENHANCED ENTITY NAME: Using currentEntityDescriptor '{entity_name}' (no storyMetadata)")
            
            # Legacy system fallback: check storyMetadata only
            elif session_data.storyMetadata:
                if entity_type == "character" and session_data.storyMetadata.character_name:
                    entity_name = session_data.storyMetadata.character_name
                elif entity_type == "location" and session_data.storyMetadata.location_name:
                    entity_name = session_data.storyMetadata.location_name
                logging.info(f"🎯 LEGACY ENTITY NAME: Using storyMetadata name '{entity_name}'")
            
            # Get design template for this aspect
            design_templates = content_manager.content.get("design_templates", {})
            entity_templates = design_templates.get(entity_type, {})
            aspect_template = entity_templates.get(current_aspect, {})
            
            # Extract template information
            prompt_template = aspect_template.get("prompt_template", f"Tell me about {entity_name}'s {current_aspect}")
            placeholder = aspect_template.get("placeholder", f"Describe the {current_aspect}")
            suggestions = aspect_template.get("suggestions", [])
            
            # Format the prompt with the entity name
            prompt_text = prompt_template.format(name=entity_name, descriptor=entity_descriptor)
            
            logging.info(f"🎯 ENHANCED DESIGN: Created {current_aspect} prompt for {entity_name}")
            
            design_prompt = DesignPrompt(
                type=entity_type,
                subject_name=entity_name,
                aspect=current_aspect,
                prompt_text=prompt_text,
                suggested_words=suggestions[:8] if suggestions else [],  # Limit to 8 suggestions
                input_placeholder=placeholder
            )
            
            return ChatResponse(
                response="",
                sessionData=session_data,
                designPrompt=design_prompt
            )
            
        except Exception as e:
            logging.error(f"❌ Failed to create enhanced description prompt: {e}")
            # Final fallback to legacy system
            return create_design_prompt(session_data)

async def handle_design_phase_interaction(user_message: str, session_data: SessionData) -> ChatResponse:
    """
    Handle user input during design phase
    
    Args:
        user_message: User's design description
        session_data: Current session state
        
    Returns:
        ChatResponse with next design prompt or story continuation
    """
    # Import content_manager at function scope to avoid variable scope issues
    from content_manager import content_manager
    
    if not session_data.designPhase or not session_data.currentDesignAspect:
        logging.error("handle_design_phase_interaction called without active design phase")
        return ChatResponse(
            response=content_manager.get_bot_response("story_mode.continue_story"),
            sessionData=session_data
        )
    
    # Handle naming aspect specially
    if session_data.currentDesignAspect == "naming":
        # User provided a name - update the metadata
        provided_name = user_message.strip()
        
        # Handle both enhanced and legacy session structures
        if hasattr(session_data, 'currentEntityType') and session_data.currentEntityType:
            # Enhanced system: store the provided name and track designed entities
            if not hasattr(session_data, 'designedEntities'):
                session_data.designedEntities = []
            session_data.designedEntities.append(session_data.currentEntityDescriptor)
            
            # Store the provided name in storyMetadata for later use
            if not session_data.storyMetadata:
                session_data.storyMetadata = StoryMetadata()
            
            if session_data.currentEntityType == "character":
                session_data.storyMetadata.character_name = provided_name
            else:  # location
                session_data.storyMetadata.location_name = provided_name
            
            logging.info(f"🏷️ ENHANCED NAMING: Named '{session_data.currentEntityDescriptor}' as '{provided_name}'")
        elif session_data.storyMetadata:
            # Legacy system: update storyMetadata
            if session_data.designPhase == "character":
                session_data.storyMetadata.character_name = provided_name
            else:  # location
                session_data.storyMetadata.location_name = provided_name
            logging.info(f"🏷️ LEGACY NAMING: Updated {session_data.designPhase} name to '{provided_name}'")
        else:
            # Initialize storyMetadata if it doesn't exist
            session_data.storyMetadata = StoryMetadata()
            if session_data.designPhase == "character":
                session_data.storyMetadata.character_name = provided_name
            else:
                session_data.storyMetadata.location_name = provided_name
            logging.info(f"🏷️ INIT NAMING: Created storyMetadata and set {session_data.designPhase} name to '{provided_name}'")
        
        # Mark naming as complete
        session_data.namingComplete = True
        session_data.designAspectHistory.append("naming")
        
        # Provide positive feedback about the name choice
        feedback_response = content_manager.get_bot_response(
            "design_phase.naming_feedback", 
            provided_name=provided_name, 
            design_phase=session_data.designPhase
        )
        
        # Check if this is enhanced system and if there are more entities to design
        if hasattr(session_data, 'currentEntityType') and session_data.currentEntityType:
            # Enhanced system: continue to description phase after naming
            entity_type = session_data.currentEntityType
            
            # Get available design aspects from templates
            try:
                design_templates = content_manager.content.get("design_templates", {})
                entity_templates = design_templates.get(entity_type, {})
                
                # Available aspects excluding naming
                available_aspects = [aspect for aspect in entity_templates.keys() 
                                   if aspect != "naming" and aspect not in session_data.designAspectHistory]
                
                # Continue to description phase if we haven't done one yet (limit to 2 total: naming + 1 description)
                if available_aspects and len(session_data.designAspectHistory) < 2:
                    # Select a random aspect for variety
                    import random
                    selected_aspect = random.choice(available_aspects)
                    session_data.currentDesignAspect = selected_aspect
                    
                    logging.info(f"🎯 ENHANCED DESIGN: Continuing to {selected_aspect} aspect for {entity_type}")
                    
                    # Create transition message and description prompt
                    transition_message = f"Now let's bring {provided_name} to life with more details!"
                    feedback_with_transition = f"{feedback_response}\n\n{transition_message}"
                    
                    # Create design prompt for the selected aspect
                    design_response = create_enhanced_design_prompt(session_data)
                    design_response.response = feedback_with_transition
                    return design_response
                    
            except Exception as e:
                logging.error(f"❌ Failed to continue enhanced design phase: {e}")
            
            # Fallback or completion after naming - generate story continuation
            session_data.designComplete = True
            session_data.designPhase = None
            session_data.currentDesignAspect = None
            
            # Generate consolidated story continuation after naming completion
            story_context = " | ".join(session_data.storyParts[-3:]) if session_data.storyParts else ""
            design_details = f"The child named this {session_data.currentEntityType} '{provided_name}'"
            
            logging.info(f"Generating consolidated story continuation after naming {provided_name}")
            
            try:
                # Use consolidated prompts for story continuation after naming
                result = llm_provider.generate_story_response(
                    topic=session_data.topic,
                    user_input=design_details,
                    story_step="continuation",
                    include_feedback=False,
                    include_vocabulary=True
                )
                
                if result and "story_content" in result:
                    story_continuation = result["story_content"]
                    session_data.storyParts.append(story_continuation)
                    
                    # Handle vocabulary words from consolidated result
                    if "vocabulary_words" in result:
                        vocab_words = result["vocabulary_words"]
                        session_data.contentVocabulary.extend(vocab_words)
                        logging.info(f"📋 CONSOLIDATED NAMING CONTINUATION: Added {len(vocab_words)} vocab words. Total: {len(session_data.contentVocabulary)}")
                    
                    # Complete response with feedback + story continuation
                    complete_response = f"{feedback_response}\n\nGreat! Now that we've named {provided_name}, let's continue with our story!\n\n{story_continuation}"
                    
                    logging.info(f"✅ CONSOLIDATED NAMING CONTINUATION: Generated continuation after naming {provided_name}")
                    
                    # Clean up entity tracking
                    session_data.currentEntityType = None
                    session_data.currentEntityDescriptor = None
                    
                    return ChatResponse(
                        response=complete_response,
                        sessionData=session_data
                    )
                else:
                    raise Exception("No story content in consolidated response")
                
            except Exception as e:
                logging.error(f"❌ Error generating consolidated story continuation after naming: {e}")
                # Clean up and fallback to simple continuation message
                session_data.currentEntityType = None
                session_data.currentEntityDescriptor = None
                completion_message = f"{feedback_response}\n\nGreat! Now that we've designed {provided_name}, let's continue with our story!"
                
                return ChatResponse(
                    response=completion_message,
                    sessionData=session_data
                )
        else:
            # Legacy system: continue to next design aspect
            aspects = load_design_aspects(session_data.designPhase)
            remaining_aspects = [aspect for aspect in aspects.keys() 
                                if aspect not in session_data.designAspectHistory and aspect != "naming"]
            
            if remaining_aspects and len(session_data.designAspectHistory) < 2:  # Limit to 2 aspects total
                session_data.currentDesignAspect = remaining_aspects[0]
                
                transition_message = content_manager.get_bot_response("design_phase.naming_transition", provided_name=provided_name)
                feedback_with_transition = f"{feedback_response}\n\n{transition_message}"
                design_response = create_design_prompt(session_data)
                design_response.response = feedback_with_transition
                return design_response
            else:
                # Design phase complete after naming
                session_data.designComplete = True
                session_data.designPhase = None
                session_data.currentDesignAspect = None
                
                design_completion = content_manager.get_bot_response("design_phase.design_completion_simple", feedback_response=feedback_response, subject_name=provided_name)
                completion_message = design_completion
                
                return ChatResponse(
                    response=completion_message,
                    sessionData=session_data
                )
    
    # Handle description aspects for enhanced system
    if hasattr(session_data, 'currentEntityType') and session_data.currentEntityType and session_data.currentDesignAspect != "naming":
        # Enhanced system description completion
        entity_type = session_data.currentEntityType
        provided_description = user_message.strip()
        
        # Get the entity name from storyMetadata
        entity_name = "the entity"  # fallback
        if session_data.storyMetadata:
            if entity_type == "character" and session_data.storyMetadata.character_name:
                entity_name = session_data.storyMetadata.character_name
            elif entity_type == "location" and session_data.storyMetadata.location_name:
                entity_name = session_data.storyMetadata.location_name
        
        logging.info(f"🎯 ENHANCED DESIGN: Completed {session_data.currentDesignAspect} description for {entity_name}")
        
        # Provide feedback on the description
        feedback_response = f"Wonderful description! I love how you described {entity_name}. That really brings them to life!"
        
        # Complete design phase after description
        session_data.designComplete = True
        session_data.designPhase = None  
        session_data.currentDesignAspect = None
        session_data.currentEntityType = None
        session_data.currentEntityDescriptor = None
        
        # CONSOLIDATED: Generate story continuation after design phase using consolidated prompts
        story_context = " | ".join(session_data.storyParts[-3:]) if session_data.storyParts else ""
        design_details = f"The child named this {entity_type} '{entity_name}' and described: {provided_description}"
        
        logging.info(f"Generating consolidated story continuation after design phase for {entity_name}")
        
        try:
            # Use consolidated prompts for story continuation after design
            result = llm_provider.generate_story_response(
                topic=session_data.topic,
                user_input=design_details,
                story_step="continuation",
                include_feedback=False,
                include_vocabulary=True
            )
            
            if result and "story_content" in result:
                story_continuation = result["story_content"]
                session_data.storyParts.append(story_continuation)
                
                # Handle vocabulary words from consolidated result
                if "vocabulary_words" in result:
                    vocab_words = result["vocabulary_words"]
                    session_data.contentVocabulary.extend(vocab_words)
                    logging.info(f"📋 CONSOLIDATED DESIGN CONTINUATION: Added {len(vocab_words)} vocab words. Total: {len(session_data.contentVocabulary)}")
                
                # Complete response with feedback + story continuation
                complete_response = f"{feedback_response}\n\nPerfect! You've helped bring {entity_name} to life! Here's how the story continues:\n\n{story_continuation}"
                
                logging.info(f"✅ CONSOLIDATED DESIGN CONTINUATION: Generated continuation after designing {entity_name}")
                
                return ChatResponse(
                    response=complete_response,
                    sessionData=session_data
                )
            else:
                raise Exception("No story content in consolidated response")
            
        except Exception as e:
            logging.error(f"❌ Error generating consolidated story continuation after design: {e}")
            # Fallback to simple continuation message
            completion_message = f"{feedback_response}\n\nThanks for helping design {entity_name}! Let's continue our story. What happens next?"
            
            return ChatResponse(
                response=completion_message,
                sessionData=session_data
            )
    
    # Regular design aspect handling (legacy system)
    if session_data.storyMetadata:
        subject_name = (session_data.storyMetadata.character_name if session_data.designPhase == "character" 
                       else session_data.storyMetadata.location_name)
    else:
        # Fallback if storyMetadata is missing
        subject_name = "the entity"
        logging.warning("Regular design aspect handling called but storyMetadata is None")
    
    # Provide brief writing feedback (act as English tutor)
    feedback_prompt = prompt_manager.get_grammar_feedback_prompt(user_message, subject_name, session_data.designPhase)
    
    try:
        feedback_response = llm_provider.generate_response(feedback_prompt)
    except Exception as e:
        logging.error(f"Error generating writing feedback: {e}")
        feedback_response = content_manager.get_bot_response("encouragement.creative_writing")
    
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
        
        # CONSOLIDATED: Generate story continuation after legacy design phase using consolidated prompts  
        story_context = " | ".join(session_data.storyParts[-3:]) if session_data.storyParts else ""
        design_details = f"The child designed {subject_name} with these details: {user_message}"
        
        logging.info(f"Generating consolidated story continuation after legacy design phase for {subject_name}")
        
        try:
            # Use consolidated prompts for story continuation after design
            result = llm_provider.generate_story_response(
                topic=session_data.topic,
                user_input=design_details,
                story_step="continuation",
                include_feedback=False,
                include_vocabulary=True
            )
            
            if result and "story_content" in result:
                story_continuation = result["story_content"]
                session_data.storyParts.append(story_continuation)
                
                # Handle vocabulary words from consolidated result
                if "vocabulary_words" in result:
                    vocab_words = result["vocabulary_words"]
                    session_data.contentVocabulary.extend(vocab_words)
                    logging.info(f"📋 CONSOLIDATED LEGACY DESIGN CONTINUATION: Added {len(vocab_words)} vocab words. Total: {len(session_data.contentVocabulary)}")
                
                # Complete response with feedback + story continuation
                complete_response = f"{feedback_response}\n\nPerfect! You've helped bring {subject_name} to life! Here's how the story continues:\n\n{story_continuation}"
                
                return ChatResponse(
                    response=complete_response,
                    sessionData=session_data
                )
            else:
                raise Exception("No story content in consolidated response")
            
        except Exception as e:
            logging.error(f"❌ Error generating consolidated story continuation after legacy design: {e}")
            return ChatResponse(
                response=f"{feedback_response}\n\nThanks for helping design {subject_name}! Let's continue our story. What happens next?",
                sessionData=session_data
            )

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Initialize latency logging on startup
@app.on_event("startup")
async def startup_event():
    setup_latency_logging()
    print("Latency logging initialized with 5MB rotation")

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
@latency_logger.measure_request
async def chat_endpoint(chat_request: ChatRequest):
    request_start = time.perf_counter()
    
    try:
        user_message = chat_request.message
        mode = chat_request.mode
        session_data = chat_request.sessionData or SessionData()
        
        logger.info(f"Processing {mode} message: {user_message}")
        
        if mode == "storywriting":
            story_mode = chat_request.storyMode or "auto"
            logger.info(f"🎯 STORY MODE DEBUG: Received story_mode parameter: '{story_mode}'")
            
            # Initialize story tracking if this is a new story
            if not session_data.topic or session_data.currentStep == 0:
                story_tracker.start_story(topic=session_data.topic or "unknown", mode=mode)
            
            result = await handle_storywriting(user_message, session_data, story_mode)
            
            # Log story exchange timing
            request_latency = (time.perf_counter() - request_start) * 1000
            exchange_type = determine_story_exchange_type(session_data, result)
            story_tracker.log_exchange(
                exchange_type=exchange_type,
                latency=request_latency,
                user_input=user_message,
                response_type=getattr(result, 'response_type', 'story_response')
            )
            
            # Check if story completed and log summary
            if result.sessionData and result.sessionData.isComplete:
                story_summary = story_tracker.complete_story(
                    topic=result.sessionData.topic or "unknown",
                    mode=mode
                )
                # Add summary to response for frontend logging
                if hasattr(result, 'latency_summary'):
                    result.latency_summary = story_summary
            
            return result
            
        elif mode == "funfacts":
            return await handle_funfacts(user_message, session_data)
        else:
            return ChatResponse(response=content_manager.get_bot_response("errors.mode_error"))
            
    except Exception as e:
        logger.error(f"Error processing chat request: {e}")
        return ChatResponse(response=content_manager.get_bot_response("errors.processing_error"))

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
        
        # CONSOLIDATED: Generate story beginning with single API call
        logger.info(f"Generating consolidated story opening for topic: {topic}")
        consolidated_response = llm_provider.generate_story_response(
            topic=topic,
            story_step="opening",
            include_feedback=False,  # No user input yet for feedback
            include_vocabulary=True
        )
        
        # Extract story content and metadata
        story_content = consolidated_response.get("story_content", "")
        entities = consolidated_response.get("entities", {})
        vocab_words = consolidated_response.get("vocabulary_words", [])
        
        logger.info(f"✅ CONSOLIDATED: Story generated with {len(vocab_words)} vocabulary words")
        logger.info(f"🎯 ENTITY DEBUG: Entities found: {entities}")
        
        # Add story to parts for tracking
        session_data.storyParts.append(story_content)
        
        # Track vocabulary words from consolidated response
        if vocab_words:
            session_data.contentVocabulary.extend(vocab_words)
            logger.info(f"📋 VOCABULARY TRACKING: Added {len(vocab_words)} words from consolidated response. Total tracked: {len(session_data.contentVocabulary)}")
        
        # Log vocabulary debug info  
        log_vocabulary_debug_info(
            topic, session_data.askedVocabWords, story_content, "Consolidated Story Generation", len(session_data.contentVocabulary)
        )
        
        # Check if design phase should be triggered (simplified check based on entities)
        should_trigger = bool(entities.get("characters", {}).get("unnamed") or entities.get("locations", {}).get("unnamed"))
        logger.info(f"🎯 DESIGN PHASE DEBUG: Consolidated entity check returned: {should_trigger}")
        
        # Create structured response for compatibility
        class ConsolidatedResponse:
            def __init__(self, story, entities, vocab_words):
                self.story = story
                self.entities = self._create_entity_structure(entities)
                self.vocabulary_words = vocab_words
                
            def _create_entity_structure(self, entities_dict):
                class EntityStructure:
                    def __init__(self, entities):
                        self.characters = type('Characters', (), {
                            'named': entities.get('characters', {}).get('named', []),
                            'unnamed': entities.get('characters', {}).get('unnamed', [])
                        })()
                        self.locations = type('Locations', (), {
                            'named': entities.get('locations', {}).get('named', []),
                            'unnamed': entities.get('locations', {}).get('unnamed', [])
                        })()
                return EntityStructure(entities)
        
        structured_response = ConsolidatedResponse(story_content, entities, vocab_words)
        
        if should_trigger:
            # Log appropriate information based on response type
            if hasattr(structured_response, 'entities'):
                # Enhanced response
                total_entities = (len(structured_response.entities.characters.unnamed) + 
                                len(structured_response.entities.locations.unnamed))
                logger.info(f"✅ DESIGN PHASE: Triggering design phase with {total_entities} designable entities")
                design_response = trigger_enhanced_design_phase(session_data, structured_response)
            else:
                # Legacy response
                logger.info(f"✅ DESIGN PHASE: Triggering legacy design phase with options: {structured_response.metadata.design_options}")
                design_response = trigger_design_phase(session_data, structured_response)
                
            design_response.suggestedTheme = get_theme_suggestion(topic)
            return design_response
        
        # No design phase needed, continue with regular story
        logger.info(f"❌ DESIGN PHASE: Skipping design phase - no designable entities found")
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
                    response=content_manager.get_bot_response("story_mode.session_goodbye"),
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
                
                # Reset ALL design phase fields for new story
                session_data.designPhase = None
                session_data.currentDesignAspect = None
                session_data.designAspectHistory = []
                session_data.storyMetadata = None
                session_data.designComplete = False
                session_data.namingComplete = False
                session_data.designedEntities = []
                session_data.currentEntityType = None
                session_data.currentEntityDescriptor = None
                session_data.storyPhase = None
                session_data.conflictType = None
                session_data.conflictScale = None
                session_data.narrativeAssessment = None
                
                # Generate story beginning with enhanced entity metadata system
                story_prompt = prompt_manager.get_story_opening_prompt(potential_new_topic, "auto")
                raw_response = llm_provider.generate_response(story_prompt)
                
                # Parse response using same logic as first story (enhanced entity system)
                try:
                    # Try enhanced parsing first (with entity metadata)
                    enhanced_response = parse_enhanced_story_response(raw_response)
                    logger.info(f"✅ ENTITY PARSE: Found {len(enhanced_response.entities.characters.named + enhanced_response.entities.characters.unnamed)} characters, {len(enhanced_response.entities.locations.named + enhanced_response.entities.locations.unnamed)} locations")
                    
                    # Add story to parts and track vocabulary
                    session_data.storyParts.append(enhanced_response.story)
                    
                    # Track vocabulary using enhanced method
                    if enhanced_response.vocabulary_words:
                        session_data.contentVocabulary.extend(enhanced_response.vocabulary_words)
                        logger.info(f"📋 VOCABULARY TRACKING: Enhanced - Added {len(enhanced_response.vocabulary_words)} words from entity metadata. Total tracked: {len(session_data.contentVocabulary)}")
                    
                    # Log vocabulary debug info
                    log_vocabulary_debug_info(
                        potential_new_topic, session_data.askedVocabWords, enhanced_response.story, "New Story Generation", len(session_data.contentVocabulary)
                    )
                    
                    # Check if design phase should be triggered
                    should_trigger = validate_entity_structure(enhanced_response.entities)
                    logger.info(f"🎯 NEW STORY DESIGN: validate_entity_structure() returned: {should_trigger}")
                    
                    if should_trigger:
                        # Trigger design phase for new story
                        total_entities = (len(enhanced_response.entities.characters.unnamed) + 
                                        len(enhanced_response.entities.locations.unnamed))
                        logger.info(f"✅ NEW STORY DESIGN: Triggering design phase with {total_entities} designable entities")
                        design_response = trigger_enhanced_design_phase(session_data, enhanced_response)
                        design_response.response = f"Great choice! Let's write a {potential_new_topic} story! 🌟\n\n{enhanced_response.story}"
                        design_response.suggestedTheme = get_theme_suggestion(potential_new_topic)
                        return design_response
                    
                    # No design phase needed for new story
                    logger.info(f"❌ NEW STORY DESIGN: Skipping design phase - no designable entities found")
                    return ChatResponse(
                        response=f"Great choice! Let's write a {potential_new_topic} story! 🌟\n\n{enhanced_response.story}",
                        sessionData=session_data,
                        suggestedTheme=get_theme_suggestion(potential_new_topic)
                    )
                    
                except Exception as e:
                    logger.warning(f"⚠️ NEW STORY FALLBACK: Enhanced parsing failed, using simple generation: {e}")
                    # Fallback to simple story generation
                    base_prompt = prompt_manager.get_topic_selection_story_prompt(potential_new_topic)
                    enhanced_prompt, selected_vocab = prompt_manager.enhance_with_vocabulary(
                        base_prompt, potential_new_topic, session_data.askedVocabWords
                    )
                    story_response = llm_provider.generate_response(enhanced_prompt)
                    session_data.storyParts.append(story_response)
                    
                    # Track vocabulary words from fallback
                    if selected_vocab:
                        session_data.contentVocabulary.extend(selected_vocab)
                        logger.info(f"📋 VOCABULARY TRACKING: Fallback - Added {len(selected_vocab)} words. Total: {len(session_data.contentVocabulary)}")
                    
                    log_vocabulary_debug_info(
                        potential_new_topic, session_data.askedVocabWords, story_response, "New Story Generation (Fallback)", len(session_data.contentVocabulary)
                    )
                    
                    return ChatResponse(
                        response=f"Great choice! Let's write a {potential_new_topic} story! 🌟\n\n{story_response}",
                        sessionData=session_data,
                        suggestedTheme=get_theme_suggestion(potential_new_topic)
                    )
            else:
                # Unclear response - ask for clarification
                return ChatResponse(
                    response=content_manager.get_bot_response("errors.clarification_needed"),
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
                    
                    # Reset ALL design phase fields for new story (topic switch)
                    session_data.designPhase = None
                    session_data.currentDesignAspect = None
                    session_data.designAspectHistory = []
                    session_data.storyMetadata = None
                    session_data.designComplete = False
                    session_data.namingComplete = False
                    session_data.designedEntities = []
                    session_data.currentEntityType = None
                    session_data.currentEntityDescriptor = None
                    session_data.storyPhase = None
                    session_data.conflictType = None
                    session_data.conflictScale = None
                    session_data.narrativeAssessment = None
                    
                    # Generate story beginning with enhanced entity metadata system (topic switch)
                    story_prompt = prompt_manager.get_story_opening_prompt(potential_new_topic, "auto")
                    raw_response = llm_provider.generate_response(story_prompt)
                    
                    # Parse response using same logic as first story (enhanced entity system)
                    try:
                        # Try enhanced parsing first (with entity metadata)
                        enhanced_response = parse_enhanced_story_response(raw_response)
                        logger.info(f"✅ TOPIC SWITCH PARSE: Found {len(enhanced_response.entities.characters.named + enhanced_response.entities.characters.unnamed)} characters, {len(enhanced_response.entities.locations.named + enhanced_response.entities.locations.unnamed)} locations")
                        
                        # Add story to parts and track vocabulary
                        session_data.storyParts.append(enhanced_response.story)
                        
                        # Track vocabulary using enhanced method
                        if enhanced_response.vocabulary_words:
                            session_data.contentVocabulary.extend(enhanced_response.vocabulary_words)
                            logger.info(f"📋 VOCABULARY TRACKING: Topic Switch Enhanced - Added {len(enhanced_response.vocabulary_words)} words from entity metadata. Total tracked: {len(session_data.contentVocabulary)}")
                        
                        # Log vocabulary debug info
                        log_vocabulary_debug_info(
                            potential_new_topic, session_data.askedVocabWords, enhanced_response.story, "Story Topic Switch", len(session_data.contentVocabulary)
                        )
                        
                        # Check if design phase should be triggered
                        should_trigger = validate_entity_structure(enhanced_response.entities)
                        logger.info(f"🎯 TOPIC SWITCH DESIGN: validate_entity_structure() returned: {should_trigger}")
                        
                        if should_trigger:
                            # Trigger design phase for topic switch story
                            total_entities = (len(enhanced_response.entities.characters.unnamed) + 
                                            len(enhanced_response.entities.locations.unnamed))
                            logger.info(f"✅ TOPIC SWITCH DESIGN: Triggering design phase with {total_entities} designable entities")
                            design_response = trigger_enhanced_design_phase(session_data, enhanced_response)
                            design_response.response = enhanced_response.story
                            design_response.suggestedTheme = get_theme_suggestion(potential_new_topic)
                            return design_response
                        
                        # No design phase needed for topic switch story
                        logger.info(f"❌ TOPIC SWITCH DESIGN: Skipping design phase - no designable entities found")
                        return ChatResponse(
                            response=enhanced_response.story,
                            sessionData=session_data,
                            suggestedTheme=get_theme_suggestion(potential_new_topic)
                        )
                        
                    except Exception as e:
                        logger.warning(f"⚠️ TOPIC SWITCH FALLBACK: Enhanced parsing failed, using simple generation: {e}")
                        # Fallback to simple story generation
                        base_prompt = prompt_manager.get_topic_selection_story_prompt(potential_new_topic)
                        enhanced_prompt, selected_vocab = prompt_manager.enhance_with_vocabulary(
                            base_prompt, potential_new_topic, session_data.askedVocabWords
                        )
                        story_response = llm_provider.generate_response(enhanced_prompt)
                        session_data.storyParts.append(story_response)
                        
                        # Track vocabulary words from fallback
                        if selected_vocab:
                            session_data.contentVocabulary.extend(selected_vocab)
                            logger.info(f"📋 VOCABULARY TRACKING: Topic Switch Fallback - Added {len(selected_vocab)} words. Total: {len(session_data.contentVocabulary)}")
                        
                        log_vocabulary_debug_info(
                            potential_new_topic, session_data.askedVocabWords, story_response, "Story Topic Switch (Fallback)", len(session_data.contentVocabulary)
                        )
                        
                        return ChatResponse(
                            response=story_response,
                            sessionData=session_data,
                            suggestedTheme=get_theme_suggestion(potential_new_topic)
                        )
        
        # Story is done - vocabulary phase will be handled by new system
        # Mark story as complete and let the frontend trigger vocabulary phase
        return ChatResponse(
            response=content_manager.get_bot_response("story_mode.story_ending"),
            sessionData=session_data
        )
    
    # Story is in progress (Steps 5-6)
    else:
        # Add user's contribution to story
        session_data.storyParts.append(f"User: {user_message}")
        
        # CONSOLIDATED: Generate story continuation, feedback, and vocabulary in single call
        logger.info(f"Generating consolidated story continuation with feedback")
        consolidated_response = llm_provider.generate_story_response(
            topic=session_data.topic,
            user_input=user_message,
            story_step="continuation",
            include_feedback=True,
            include_vocabulary=True
        )
        
        # Extract feedback
        writing_feedback = consolidated_response.get("writing_feedback", {})
        grammar_feedback = writing_feedback.get("feedback") if writing_feedback else None
        
        # Get story context for assessment
        story_context = "\n".join(session_data.storyParts[-3:])  # Last 3 parts for context
        
        # ENHANCED STORY STRUCTURE: Intelligent story assessment
        # Replace rigid character count + step rules with narrative intelligence
        
        # Step 1: Assess current story narrative structure
        if session_data.currentStep >= 2:  # Only assess after some story development
            try:
                # Get story arc assessment from LLM
                assessment_prompt = prompt_manager.get_story_arc_assessment_prompt(
                    session_data.storyParts, session_data.topic
                )
                assessment_response = llm_provider.generate_response(assessment_prompt)
                
                # Parse assessment JSON
                import json
                assessment = json.loads(assessment_response)
                
                # Update session data with assessment
                session_data.narrativeAssessment = assessment
                session_data.storyPhase = assessment.get('current_phase', 'development')
                session_data.characterGrowthScore = assessment.get('character_growth', 0)
                session_data.completenessScore = assessment.get('completeness_score', 0)
                session_data.conflictType = assessment.get('conflict_type', 'none')
                
                logger.info(f"📖 STORY ARC ASSESSMENT: Phase={session_data.storyPhase}, Growth={session_data.characterGrowthScore}%, Complete={session_data.completenessScore}%, Conflict={session_data.conflictType}")
                
            except Exception as e:
                logger.error(f"❌ Story assessment failed: {e}, falling back to quality gates")
                session_data.narrativeAssessment = None
        
        # Step 2: Intelligent story ending decision  
        should_end_story, ending_reason = prompt_manager.should_end_story_intelligently(session_data)
        logger.info(f"📖 STORY ENDING DECISION: {should_end_story}, reason: {ending_reason}")
        
        if should_end_story:
            # CONSOLIDATED: End the story with consolidated call (already got response above)
            story_response = consolidated_response.get("story_content", "")
            vocab_words = consolidated_response.get("vocabulary_words", [])
            
            # Track vocabulary words from consolidated response
            if vocab_words:
                logger.info(f"Story ending included vocabulary: {vocab_words}")
                session_data.contentVocabulary.extend(vocab_words)
                logger.info(f"📋 VOCABULARY TRACKING: Added {len(vocab_words)} words to session. Total tracked: {len(session_data.contentVocabulary)}")
            
            # Log vocabulary debug info to server logs
            log_vocabulary_debug_info(
                session_data.topic, session_data.askedVocabWords + session_data.contentVocabulary, story_response, "Consolidated Story Ending", len(session_data.contentVocabulary)
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
            # CONSOLIDATED: Continue story (already got response from consolidated call above)
            story_response = consolidated_response.get("story_content", "")
            vocab_words = consolidated_response.get("vocabulary_words", [])
            
            logger.info(f"📖 CONSOLIDATED CONTINUATION: Generated story continuation with {len(vocab_words)} vocab words")
            
            # Track vocabulary words from consolidated response
            if vocab_words:
                logger.info(f"Story continuation included vocabulary: {vocab_words}")
                session_data.contentVocabulary.extend(vocab_words)
                logger.info(f"📋 VOCABULARY TRACKING: Added {len(vocab_words)} words to session. Total tracked: {len(session_data.contentVocabulary)}")
            
            # Log vocabulary debug info to server logs
            log_vocabulary_debug_info(
                session_data.topic, session_data.askedVocabWords + session_data.contentVocabulary, story_response, "Consolidated Story Continuation", len(session_data.contentVocabulary)
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
            response=content_manager.get_bot_response("vocabulary.intro_after_story"),
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
                response=content_manager.get_bot_response("vocabulary.intro_after_story"),
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
            response=content_manager.get_bot_response("vocabulary.next_question"),
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
                response=content_manager.get_bot_response("vocabulary.next_question"),
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
        
        # CONSOLIDATED: Generate first fact with vocabulary in single API call
        logger.info(f"Generating consolidated fact for topic: {topic}")
        consolidated_response = llm_provider.generate_story_response(
            topic=topic,
            story_step="opening",
            include_feedback=False,  # No user input for facts mode
            include_vocabulary=True,
            content_type="fact"
        )
        
        # Extract fact content and vocabulary
        fact_response = consolidated_response.get("story_content", "")
        vocab_words = consolidated_response.get("vocabulary_words", [])
        vocab_question_data = consolidated_response.get("vocabulary_question", {})
        
        session_data.currentFact = fact_response
        session_data.allFacts.append(fact_response)
        session_data.factsShown += 1
        
        # Track vocabulary words from consolidated response
        if vocab_words:
            logger.info(f"Consolidated fact included vocabulary: {vocab_words}")
            session_data.contentVocabulary.extend(vocab_words)
            logger.info(f"📋 VOCABULARY TRACKING: Added {len(vocab_words)} words to session. Total tracked: {len(session_data.contentVocabulary)}")
        
        # Log vocabulary debug info to server logs
        log_vocabulary_debug_info(
            topic, session_data.askedVocabWords, fact_response, "Consolidated Initial Fact", len(session_data.contentVocabulary)
        )
        
        # Use vocabulary question from consolidated response
        vocab_question = None
        if vocab_question_data and vocab_question_data.get("question"):
            # Track the vocabulary word
            if vocab_words:
                session_data.askedVocabWords.append(vocab_words[0])
            vocab_question = vocab_question_data
        else:
            # Fallback to curated vocabulary if consolidated response didn't include a question
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
            # CONSOLIDATED: Generate continuing fact with vocabulary in single API call
            logger.info(f"Generating consolidated continuing fact for topic: {session_data.topic}")
            consolidated_response = llm_provider.generate_story_response(
                topic=session_data.topic,
                story_step="continuation", 
                include_feedback=False,  # No user input for facts mode
                include_vocabulary=True,
                content_type="fact"
            )
            
            # Extract fact content and vocabulary
            fact_response = consolidated_response.get("story_content", "")
            vocab_words = consolidated_response.get("vocabulary_words", [])
            vocab_question_data = consolidated_response.get("vocabulary_question", {})
            
            session_data.currentFact = fact_response
            session_data.allFacts.append(fact_response)
            session_data.factsShown += 1
            
            # Track vocabulary words from consolidated response
            if vocab_words:
                logger.info(f"Consolidated continuing fact included vocabulary: {vocab_words}")
                session_data.contentVocabulary.extend(vocab_words)
                logger.info(f"📋 VOCABULARY TRACKING: Added {len(vocab_words)} words to session. Total tracked: {len(session_data.contentVocabulary)}")
            
            # Log vocabulary debug info to server logs
            log_vocabulary_debug_info(
                session_data.topic, session_data.askedVocabWords, fact_response, "Consolidated Continuing Fact", len(session_data.contentVocabulary)
            )
            
            # Use vocabulary question from consolidated response
            vocab_question = None
            if vocab_question_data and vocab_question_data.get("question"):
                # Track the vocabulary word
                if vocab_words:
                    session_data.askedVocabWords.append(vocab_words[0])
                vocab_question = vocab_question_data
            else:
                # Fallback to curated vocabulary if consolidated response didn't include a question
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
                
                # CONSOLIDATED: Generate first fact for same topic continuation
                logger.info(f"Generating consolidated fact for same topic continuation: {session_data.topic}")
                consolidated_response = llm_provider.generate_story_response(
                    topic=session_data.topic,
                    story_step="opening",  # New start for same topic
                    include_feedback=False,  # No user input for facts mode
                    include_vocabulary=True,
                    content_type="fact"
                )
                
                # Extract fact content and vocabulary
                fact_response = consolidated_response.get("story_content", "")
                vocab_words = consolidated_response.get("vocabulary_words", [])
                vocab_question_data = consolidated_response.get("vocabulary_question", {})
                
                logger.info(f"Consolidated response for same topic continuation: {fact_response[:100]}...")
                session_data.currentFact = fact_response
                session_data.allFacts.append(fact_response)
                session_data.factsShown += 1
                
                # Track vocabulary words from consolidated response
                if vocab_words:
                    logger.info(f"Consolidated same topic continuation included vocabulary: {vocab_words}")
                    session_data.contentVocabulary.extend(vocab_words)
                    logger.info(f"📋 VOCABULARY TRACKING: Added {len(vocab_words)} words to session. Total tracked: {len(session_data.contentVocabulary)}")
                
                # Log vocabulary debug info to server logs
                log_vocabulary_debug_info(
                    session_data.topic, session_data.askedVocabWords, fact_response, "Consolidated Same Topic Continuation", len(session_data.contentVocabulary)
                )
                
                # Use vocabulary question from consolidated response
                vocab_question = None
                if vocab_question_data and vocab_question_data.get("question"):
                    # Track the vocabulary word
                    if vocab_words:
                        session_data.askedVocabWords.append(vocab_words[0])
                    vocab_question = vocab_question_data
                else:
                    # Fallback to curated vocabulary if consolidated response didn't include a question
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
                
                # CONSOLIDATED: Generate first fact for new topic
                logger.info(f"Generating consolidated fact for new topic: {new_topic}")
                consolidated_response = llm_provider.generate_story_response(
                    topic=new_topic,
                    story_step="opening",
                    include_feedback=False,  # No user input for facts mode
                    include_vocabulary=True,
                    content_type="fact"
                )
                
                # Extract fact content and vocabulary
                fact_response = consolidated_response.get("story_content", "")
                vocab_words = consolidated_response.get("vocabulary_words", [])
                vocab_question_data = consolidated_response.get("vocabulary_question", {})
                
                session_data.currentFact = fact_response
                session_data.allFacts.append(fact_response)
                session_data.factsShown += 1
                
                # Track vocabulary words from consolidated response
                if vocab_words:
                    logger.info(f"Consolidated new topic fact included vocabulary: {vocab_words}")
                    session_data.contentVocabulary.extend(vocab_words)
                    logger.info(f"📋 VOCABULARY TRACKING: Added {len(vocab_words)} words to session. Total tracked: {len(session_data.contentVocabulary)}")
                
                # Log vocabulary debug info to server logs
                log_vocabulary_debug_info(
                    new_topic, session_data.askedVocabWords, fact_response, "Consolidated New Topic Fact", len(session_data.contentVocabulary)
                )
                
                # Use vocabulary question from consolidated response
                vocab_question = None
                if vocab_question_data and vocab_question_data.get("question"):
                    # Track the vocabulary word
                    if vocab_words:
                        session_data.askedVocabWords.append(vocab_words[0])
                    vocab_question = vocab_question_data
                else:
                    # Fallback to curated vocabulary if consolidated response didn't include a question
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