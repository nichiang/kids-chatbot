from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, List, Optional
import logging
import json
import os
from llm_provider import llm_provider
from generate_prompt import generate_prompt, load_file, generate_fun_facts_prompt
from vocabulary_manager import vocabulary_manager

# Design Phase Models - Must be defined before functions that use them
class StoryMetadata(BaseModel):
    """Metadata about characters and locations introduced in the story"""
    character_name: Optional[str] = None
    character_description: Optional[str] = None
    location_name: Optional[str] = None
    location_description: Optional[str] = None
    design_options: List[str] = []  # ["character", "location"] or subset

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

class ChatRequest(BaseModel):
    message: str
    mode: str = "storywriting"  # "storywriting" or "funfacts"
    sessionData: Optional[SessionData] = None

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


def generate_vocabulary_enhanced_prompt(base_prompt: str, topic: str, used_words: List[str] = None, word_count: int = 3) -> tuple[str, List[str]]:
    """
    Generate a prompt enhanced with massive vocabulary pool for LLM intelligent selection
    
    SOLUTION 3: Massive Vocabulary Pool with LLM as Intelligent Curator
    - Provides 40 example words (20 general tier 2+3 + 20 topic words) 
    - LLM intelligently selects 2-4 most natural words for content
    - Eliminates repetition through massive selection pool
    - Maintains optimal learning targets for 2nd-3rd graders
    
    Args:
        base_prompt: The base prompt template
        topic: Topic for vocabulary selection
        used_words: Previously used words to avoid
        word_count: Ignored - now controlled by LLM intelligent selection
    
    Returns:
        Tuple of (enhanced_prompt, expected_vocabulary_range)
    """
    if used_words is None:
        used_words = []
    
    # SOLUTION 3: Generate massive vocabulary pools for LLM selection
    vocab_pools = generate_massive_vocabulary_pool(topic, used_words)
    
    if vocab_pools['general_pool'] or vocab_pools['topic_pool']:
        # Create enhanced prompt with massive vocabulary selection
        vocab_instruction = f"""

You have access to these educational vocabulary words for natural integration:

GENERAL WORDS (Tier 2+3): {', '.join(vocab_pools['general_pool'])}

TOPIC-SPECIFIC WORDS: {', '.join(vocab_pools['topic_pool'])}

CRITICAL INSTRUCTIONS:
- Select ONLY 2-4 words total that fit most naturally in your content
- Choose words that enhance meaning rather than feel forced
- Bold selected words using **word** format  
- Prioritize natural, engaging flow over vocabulary count
- Mix general and topic words for variety
- Content must feel captivating, not educational-sounding

EXAMPLE POOLS PROVIDED: {vocab_pools['total_examples']} words
TARGET USAGE: Select 2-4 most natural words only"""

        enhanced_prompt = base_prompt + vocab_instruction
        # Return expected vocabulary range instead of pre-selected words
        expected_vocab = ['LLM_SELECTED_2_TO_4_WORDS']
        
    else:
        # Fallback if no vocabulary available
        enhanced_prompt = base_prompt + " Bold 2-4 challenging or important words using **word** format. DO NOT include vocabulary questions or definitions in the content."
        expected_vocab = []
        vocab_pools = {'general_pool': [], 'topic_pool': [], 'excluded_words': used_words, 'total_examples': 0}
    
    return enhanced_prompt, expected_vocab


def generate_massive_vocabulary_pool(topic: str, used_words: List[str] = None) -> Dict[str, any]:
    """
    SOLUTION 3: Generate massive vocabulary pools for LLM intelligent selection
    
    Returns 40 total example words (20 general + 20 topic) for LLM to choose from,
    while maintaining optimal 2-4 word learning targets for children.
    
    Args:
        topic: Topic for vocabulary selection
        used_words: Previously used words to prefer fresh options
    
    Returns:
        Dictionary with general_pool, topic_pool, total_examples, and target_usage
    """
    if used_words is None:
        used_words = []
    
    # Get 20 tier 2+3 words from general pool (skip tier 1 - too easy for advanced learners)
    general_pool = select_advanced_general_words(count=20, exclude=used_words)
    
    # Get all available topic-specific words (typically 20 words per topic)
    topic_pool = get_all_topic_vocabulary(topic)
    
    return {
        'general_pool': general_pool,     # 20 tier 2+3 words
        'topic_pool': topic_pool,         # 20 topic words  
        'total_examples': len(general_pool) + len(topic_pool),  # ~40 words total
        'target_usage': '2-4 words only',  # Still optimal for learning
        'excluded_words': used_words  # For debug info
    }


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
    vocab_pools = generate_massive_vocabulary_pool(topic, used_words)
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
    
    Args:
        available_words: List of available vocabulary words to choose from
    
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

def generate_structured_story_prompt(topic: str) -> str:
    """
    Generate a prompt that requests JSON format with story and metadata
    
    Args:
        topic: The story topic chosen by the child
        
    Returns:
        Structured prompt requesting JSON response with story and character/location metadata
    """
    return f"""Create a story opening for the topic: {topic}

REQUIREMENTS:
- Write 2-4 sentences suitable for strong 2nd graders or 3rd graders
- Introduce a named character AND/OR a specific location with clear names
- End by inviting the child to continue (no multiple choice options)
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
    "design_options": ["character", "location"]
  }}
}}

IMPORTANT NOTES:
- design_options should only include elements you actually introduced
- If only character introduced: design_options: ["character"]
- If only location introduced: design_options: ["location"]  
- If both introduced: design_options: ["character", "location"]
- Character and location names should be clearly identifiable, not vague
- Make the story exciting and engaging for young children

Example topics and approaches:
- Space: Introduce astronaut character or space station location
- Fantasy: Introduce magical character or enchanted place
- Ocean: Introduce sea creature character or underwater location
- Animals: Introduce animal character or habitat location"""

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
        metadata = StoryMetadata(
            character_name=metadata_dict.get("character_name"),
            character_description=metadata_dict.get("character_description"),
            location_name=metadata_dict.get("location_name"),
            location_description=metadata_dict.get("location_description"),
            design_options=metadata_dict.get("design_options", [])
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
    file_path = os.path.join(os.path.dirname(__file__), filename)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"Design aspects file not found: {file_path}")
        return {}
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON in design aspects file {file_path}: {e}")
        return {}

def select_design_focus(character_name: Optional[str], location_name: Optional[str]) -> Optional[str]:
    """
    Randomly select character or location design (50/50 split)
    
    Args:
        character_name: Name of character if introduced
        location_name: Name of location if introduced
        
    Returns:
        "character", "location", or None if neither available
    """
    import random
    
    available_options = []
    if character_name:
        available_options.append("character")
    if location_name:
        available_options.append("location")
    
    if not available_options:
        return None
    elif len(available_options) == 1:
        return available_options[0]
    else:
        # 50/50 random choice when both are available
        return random.choice(available_options)

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
    
    # Return first available aspect (maintains consistent order)
    return available_aspects[0]

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
    else:  # location
        subject_name = session_data.storyMetadata.location_name or "this place"
        subject_description = session_data.storyMetadata.location_description or ""
    
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
    
    # Generate the prompt text
    prompt_text = aspect_data.get("prompt_template", "").format(name=subject_name)
    
    # Create the design prompt
    design_prompt = DesignPrompt(
        type=session_data.designPhase,
        subject_name=subject_name,
        aspect=session_data.currentDesignAspect,
        prompt_text=prompt_text,
        suggested_words=aspect_data.get("suggestions", []),
        input_placeholder=aspect_data.get("placeholder", "Write 1-2 sentences")
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
    
    Args:
        session_data: Current session state
        structured_response: Parsed story with character/location info
        
    Returns:
        ChatResponse with design prompt
    """
    metadata = structured_response.metadata
    
    # Store the story metadata
    session_data.storyMetadata = metadata
    
    # Select what to design (character or location)
    session_data.designPhase = select_design_focus(
        metadata.character_name, 
        metadata.location_name
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
    
    logging.info(f"Triggering design phase for {session_data.designPhase}: {metadata.character_name or metadata.location_name}")
    
    # Generate the design prompt
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
    
    # Process the user's design input
    subject_name = (session_data.storyMetadata.character_name if session_data.designPhase == "character" 
                   else session_data.storyMetadata.location_name)
    
    # Provide brief writing feedback (act as English tutor)
    feedback_prompt = f"""As a friendly English tutor, provide very brief feedback on this child's descriptive writing about their {session_data.designPhase} {subject_name}:

"{user_message}"

Give 1-2 sentences of encouraging feedback. If there are grammar issues, gently suggest improvements. If the description is good, celebrate it! Keep it very brief and positive."""
    
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
        
        continuation_prompt = f"""Continue the story about {session_data.topic}. Previous context: {story_context}

{design_summary} The child just described: "{user_message}"

Write a paragraph that is 2-4 sentences long incorporating the child's creative input about {subject_name}. Use vocabulary suitable for a strong 2nd grader or 3rd grader. Then invite the child to continue the story without giving them any options. Bold 2-3 vocabulary words using **word** format."""
        
        enhanced_prompt, selected_vocab = generate_vocabulary_enhanced_prompt(
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
            return await handle_storywriting(user_message, session_data)
        elif mode == "funfacts":
            return await handle_funfacts(user_message, session_data)
        else:
            return ChatResponse(response="I'm not sure what mode that is! Try storywriting or fun facts.")
            
    except Exception as e:
        logger.error(f"Error processing chat request: {e}")
        return ChatResponse(response="Sorry, I'm having trouble right now. Please try again!")

async def handle_storywriting(user_message: str, session_data: SessionData) -> ChatResponse:
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
        structured_prompt = generate_structured_story_prompt(topic)
        enhanced_prompt, selected_vocab = generate_vocabulary_enhanced_prompt(
            structured_prompt, topic, session_data.askedVocabWords
        )
        
        raw_response = llm_provider.generate_response(enhanced_prompt)
        structured_response = parse_structured_story_response(raw_response)
        
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
        if should_trigger_design_phase(structured_response):
            logger.info(f"Triggering design phase with options: {structured_response.metadata.design_options}")
            design_response = trigger_design_phase(session_data, structured_response)
            design_response.suggestedTheme = get_theme_suggestion(topic)
            return design_response
        
        # No design phase needed, continue with regular story
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
                base_prompt = f"The child has chosen the topic: {potential_new_topic}. Now write a paragraph that is 2-4 sentences long using vocabulary suitable for a strong 2nd grader or 3rd grader. Then invite the child to continue the story without giving them any options. DO NOT include vocabulary questions - those will be handled separately."
                enhanced_prompt, selected_vocab = generate_vocabulary_enhanced_prompt(
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
                    response=f"Great choice! Let's write a {potential_new_topic} story! 🌟\\n\\n{story_response}",
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
                    base_prompt = f"The child has chosen the topic: {potential_new_topic}. Now write a paragraph that is 2-4 sentences long using vocabulary suitable for a strong 2nd grader or 3rd grader. Then invite the child to continue the story without giving them any options. DO NOT include vocabulary questions - those will be handled separately."
                    enhanced_prompt, selected_vocab = generate_vocabulary_enhanced_prompt(
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
            base_prompt = f"End the story about {session_data.topic}. Previous context: {story_context}. Write a final paragraph that is 2-4 sentences long using vocabulary suitable for a strong 2nd grader or 3rd grader. End the story with a satisfying conclusion and add 'The end!' at the very end. DO NOT ask the child to continue. DO NOT include vocabulary questions - those will be handled separately."
            enhanced_prompt, selected_vocab = generate_vocabulary_enhanced_prompt(
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
            base_prompt = f"Continue the story about {session_data.topic}. Previous context: {story_context}. Write a paragraph that is 2-4 sentences long using vocabulary suitable for a strong 2nd grader or 3rd grader. Then invite the child to continue the story without giving them any options. Keep this a short story - try to end it before it goes over 300 words total. DO NOT include vocabulary questions - those will be handled separately."
            enhanced_prompt, selected_vocab = generate_vocabulary_enhanced_prompt(
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
    
    # Find a vocabulary word that hasn't been asked yet
    available_words = [word for word in content_vocab_words if word not in session_data.askedVocabWords]
    
    if available_words:
        # Use a word from the story content, prioritizing lowercase words over proper nouns
        selected_word = select_best_vocabulary_word(available_words)
        session_data.askedVocabWords.append(selected_word)
        session_data.vocabularyPhase.questionsAsked = 1
        
        # Use the actual story content as context for the vocabulary question
        vocab_question = llm_provider.generate_vocabulary_question(selected_word, context=all_story_text)
        
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
    
    # Find a vocabulary word that hasn't been asked yet
    available_words = [word for word in content_vocab_words if word not in session_data.askedVocabWords]
    
    if available_words:
        # Use a word from the story content, prioritizing lowercase words over proper nouns
        selected_word = select_best_vocabulary_word(available_words)
        session_data.askedVocabWords.append(selected_word)
        session_data.vocabularyPhase.questionsAsked += 1
        
        # Use the actual story content as context for the vocabulary question
        vocab_question = llm_provider.generate_vocabulary_question(selected_word, context=all_story_text)
        
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
    
    story_completion_prompt = "Wonderful job with the vocabulary! You've done great! Would you like to write another story? Here are some fun ideas:\n\n🚀 Space adventures\n🏰 Fantasy quests\n⚽ Sports excitement\n🦄 Magical creatures\n🕵️ Mystery solving\n🍕 Food adventures\n🐾 Animal stories\n🌊 Ocean explorations\n\nWhat sounds interesting to you?"
    
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
        base_prompt = generate_fun_facts_prompt('first_fact', topic=topic)
        enhanced_prompt, selected_vocab = generate_vocabulary_enhanced_prompt(
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
            base_prompt = generate_fun_facts_prompt(
                'continuing_fact', 
                topic=session_data.topic, 
                fact_number=session_data.factsShown + 1,
                previous_facts=previous_facts
            )
            enhanced_prompt, selected_vocab = generate_vocabulary_enhanced_prompt(
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
                base_prompt = generate_fun_facts_prompt('new_topic', topic=session_data.topic)
                enhanced_prompt, selected_vocab = generate_vocabulary_enhanced_prompt(
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
                base_prompt = generate_fun_facts_prompt('new_topic', topic=new_topic)
                enhanced_prompt, selected_vocab = generate_vocabulary_enhanced_prompt(
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