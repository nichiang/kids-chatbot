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

class VocabularyDebugInfo(BaseModel):
    """Debug information about vocabulary generation and selection"""
    general_pool: List[str] = []
    topic_pool: List[str] = []
    excluded_words: List[str] = []
    total_available: int = 0
    llm_selected_words: List[str] = []
    context: str = ""
    content_preview: str = ""
    session_total: int = 0

def generate_vocabulary_enhanced_prompt(base_prompt: str, topic: str, used_words: List[str] = None, word_count: int = 3, vocab_pools: dict = None) -> tuple[str, List[str]]:
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
        vocab_pools: Optional pre-generated vocabulary pools (for debug consistency)
    
    Returns:
        Tuple of (enhanced_prompt, expected_vocabulary_range)
    """
    if used_words is None:
        used_words = []
    
    # SOLUTION 3: Generate massive vocabulary pools for LLM selection (if not provided)
    if vocab_pools is None:
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

def generate_vocabulary_enhanced_prompt_with_debug(base_prompt: str, topic: str, used_words: List[str] = None) -> tuple[str, List[str], dict]:
    """
    Generate vocabulary enhanced prompt and return debug info for browser console
    
    Returns:
        Tuple of (enhanced_prompt, expected_vocab, vocab_pools)
    """
    if used_words is None:
        used_words = []
    
    # Generate vocabulary pools for debug info
    vocab_pools = generate_massive_vocabulary_pool(topic, used_words)
    
    # Generate the enhanced prompt using the same vocab_pools to ensure consistency
    enhanced_prompt, expected_vocab = generate_vocabulary_enhanced_prompt(base_prompt, topic, used_words, vocab_pools=vocab_pools)
    
    return enhanced_prompt, expected_vocab, vocab_pools


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

def create_vocabulary_debug_info(vocab_pools: dict, content: str, context: str, session_total: int) -> VocabularyDebugInfo:
    """
    Create vocabulary debug information for browser console display
    
    Args:
        vocab_pools: The vocabulary pools that were generated
        content: The LLM response content
        context: Context description (e.g., "Story generation", "Fun fact")
        session_total: Total vocabulary words tracked in session
    
    Returns:
        VocabularyDebugInfo object for frontend display
    """
    import re
    bolded_words = re.findall(r'\*\*(.*?)\*\*', content)
    
    return VocabularyDebugInfo(
        general_pool=vocab_pools.get('general_pool', []),
        topic_pool=vocab_pools.get('topic_pool', []),
        excluded_words=vocab_pools.get('excluded_words', []),
        total_available=vocab_pools.get('total_examples', 0),
        llm_selected_words=bolded_words,
        context=context,
        content_preview=content[:100] + ('...' if len(content) > 100 else ''),
        session_total=session_total
    )

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


# Request/Response models
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
    vocabularyDebug: Optional[VocabularyDebugInfo] = None

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
    
    # If no topic is set, user is choosing a topic (Step 1)
    if not session_data.topic:
        # Extract topic from user message
        topic = extract_topic_from_message(user_message)
        session_data.topic = topic
        session_data.currentStep = 2  # Moving to Step 2 after topic selection
        
        # Generate story beginning with vocabulary integration
        base_prompt = f"The child has chosen the topic: {topic}. Now write a paragraph that is 2-4 sentences long using vocabulary suitable for a strong 2nd grader or 3rd grader. Then invite the child to continue the story without giving them any options. DO NOT include vocabulary questions - those will be handled separately."
        enhanced_prompt, selected_vocab, vocab_pools = generate_vocabulary_enhanced_prompt_with_debug(
            base_prompt, topic, session_data.askedVocabWords
        )
        story_response = llm_provider.generate_response(enhanced_prompt)
        session_data.storyParts.append(story_response)
        
        # Track vocabulary words that were intended to be used
        if selected_vocab:
            logger.info(f"Story generation included vocabulary: {selected_vocab}")
            # Store them for later vocabulary question generation
            session_data.contentVocabulary.extend(selected_vocab)
            logger.info(f"📋 VOCABULARY TRACKING: Added {len(selected_vocab)} words to session. Total tracked: {len(session_data.contentVocabulary)}")
        
        # Create vocabulary debug info for browser console
        vocab_debug = create_vocabulary_debug_info(
            vocab_pools, story_response, "Initial Story Generation", len(session_data.contentVocabulary)
        )
        logger.info(f"🔍 DEBUG: Created vocab debug info: {vocab_debug.model_dump()}")
        
        # Get theme suggestion for this topic
        suggested_theme = get_theme_suggestion(topic)
        
        logger.info(f"🔍 DEBUG: Returning ChatResponse with vocabularyDebug: {vocab_debug is not None}")
        
        return ChatResponse(
            response=story_response,
            sessionData=session_data,
            suggestedTheme=suggested_theme,
            vocabularyDebug=vocab_debug
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
                enhanced_prompt, selected_vocab, vocab_pools = generate_vocabulary_enhanced_prompt_with_debug(
                    base_prompt, potential_new_topic, session_data.askedVocabWords
                )
                story_response = llm_provider.generate_response(enhanced_prompt)
                session_data.storyParts.append(story_response)
                
                # Track vocabulary words that were intended to be used
                if selected_vocab:
                    logger.info(f"New story generation included vocabulary: {selected_vocab}")
                    session_data.contentVocabulary.extend(selected_vocab)
                    logger.info(f"📋 VOCABULARY TRACKING: Added {len(selected_vocab)} words to session. Total tracked: {len(session_data.contentVocabulary)}")
                
                # Create vocabulary debug info for browser console
                vocab_debug = create_vocabulary_debug_info(
                    vocab_pools, story_response, "New Story Generation", len(session_data.contentVocabulary)
                )
                
                # Get theme suggestion for new topic
                suggested_theme = get_theme_suggestion(potential_new_topic)
                
                return ChatResponse(
                    response=f"Great choice! Let's write a {potential_new_topic} story! 🌟\\n\\n{story_response}",
                    sessionData=session_data,
                    suggestedTheme=suggested_theme,
                    vocabularyDebug=vocab_debug
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
                    enhanced_prompt, selected_vocab, vocab_pools = generate_vocabulary_enhanced_prompt_with_debug(
                        base_prompt, potential_new_topic, session_data.askedVocabWords
                    )
                    story_response = llm_provider.generate_response(enhanced_prompt)
                    session_data.storyParts.append(story_response)
                    
                    # Track vocabulary words that were intended to be used
                    if selected_vocab:
                        logger.info(f"Story topic switch included vocabulary: {selected_vocab}")
                        session_data.contentVocabulary.extend(selected_vocab)
                        logger.info(f"📋 VOCABULARY TRACKING: Added {len(selected_vocab)} words to session. Total tracked: {len(session_data.contentVocabulary)}")
                    
                    # Create vocabulary debug info for browser console
                    vocab_debug = create_vocabulary_debug_info(
                        vocab_pools, story_response, "Story Topic Switch", len(session_data.contentVocabulary)
                    )
                    
                    # Get theme suggestion for new topic
                    suggested_theme = get_theme_suggestion(potential_new_topic)
                    
                    return ChatResponse(
                        response=story_response,
                        sessionData=session_data,
                        suggestedTheme=suggested_theme,
                        vocabularyDebug=vocab_debug
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
            enhanced_prompt, selected_vocab, vocab_pools = generate_vocabulary_enhanced_prompt_with_debug(
                base_prompt, session_data.topic, session_data.askedVocabWords + session_data.contentVocabulary
            )
            story_response = llm_provider.generate_response(enhanced_prompt)
            
            # Track vocabulary words that were intended to be used
            if selected_vocab:
                logger.info(f"Story ending included vocabulary: {selected_vocab}")
                session_data.contentVocabulary.extend(selected_vocab)
                logger.info(f"📋 VOCABULARY TRACKING: Added {len(selected_vocab)} words to session. Total tracked: {len(session_data.contentVocabulary)}")
            
            # Create vocabulary debug info for browser console
            vocab_debug = create_vocabulary_debug_info(
                vocab_pools, story_response, "Story Ending", len(session_data.contentVocabulary)
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
                sessionData=session_data,
                vocabularyDebug=vocab_debug
            )
        else:
            # Continue story with vocabulary integration
            base_prompt = f"Continue the story about {session_data.topic}. Previous context: {story_context}. Write a paragraph that is 2-4 sentences long using vocabulary suitable for a strong 2nd grader or 3rd grader. Then invite the child to continue the story without giving them any options. Keep this a short story - try to end it before it goes over 300 words total. DO NOT include vocabulary questions - those will be handled separately."
            enhanced_prompt, selected_vocab, vocab_pools = generate_vocabulary_enhanced_prompt_with_debug(
                base_prompt, session_data.topic, session_data.askedVocabWords + session_data.contentVocabulary
            )
            story_response = llm_provider.generate_response(enhanced_prompt)
            
            # Track vocabulary words that were intended to be used
            if selected_vocab:
                logger.info(f"Story continuation included vocabulary: {selected_vocab}")
                session_data.contentVocabulary.extend(selected_vocab)
                logger.info(f"📋 VOCABULARY TRACKING: Added {len(selected_vocab)} words to session. Total tracked: {len(session_data.contentVocabulary)}")
            
            # Create vocabulary debug info for browser console
            vocab_debug = create_vocabulary_debug_info(
                vocab_pools, story_response, "Story Continuation", len(session_data.contentVocabulary)
            )
            
            # Add grammar feedback if available
            if grammar_feedback:
                story_response = grammar_feedback + "\n\n" + story_response
            
            session_data.storyParts.append(story_response)
            session_data.currentStep += 1
            
            return ChatResponse(
                response=story_response,
                sessionData=session_data,
                vocabularyDebug=vocab_debug
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
        enhanced_prompt, selected_vocab, vocab_pools = generate_vocabulary_enhanced_prompt_with_debug(
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
        
        # Create vocabulary debug info for browser console
        vocab_debug = create_vocabulary_debug_info(
            vocab_pools, fact_response, "Initial Fun Fact", len(session_data.contentVocabulary)
        )
        logger.info(f"🔍 DEBUG: Created fun fact vocab debug info: {vocab_debug.model_dump()}")
        
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
        
        logger.info(f"🔍 DEBUG: Returning fun fact ChatResponse with vocabularyDebug: {vocab_debug is not None}")
        
        return ChatResponse(
            response=fact_response,
            vocabQuestion=VocabQuestion(**vocab_question) if vocab_question else None,
            sessionData=session_data,
            suggestedTheme=suggested_theme,
            vocabularyDebug=vocab_debug
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
            enhanced_prompt, selected_vocab, vocab_pools = generate_vocabulary_enhanced_prompt_with_debug(
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
            
            # Create vocabulary debug info for browser console
            vocab_debug = create_vocabulary_debug_info(
                vocab_pools, fact_response, "Continuing Fun Fact", len(session_data.contentVocabulary)
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
                sessionData=session_data,
                vocabularyDebug=vocab_debug
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
                enhanced_prompt, selected_vocab, vocab_pools = generate_vocabulary_enhanced_prompt_with_debug(
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
                
                # Create vocabulary debug info for browser console
                vocab_debug = create_vocabulary_debug_info(
                    vocab_pools, fact_response, "Same Topic Continuation", len(session_data.contentVocabulary)
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
                    sessionData=session_data,
                    vocabularyDebug=vocab_debug
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
                enhanced_prompt, selected_vocab, vocab_pools = generate_vocabulary_enhanced_prompt_with_debug(
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
                
                # Create vocabulary debug info for browser console
                vocab_debug = create_vocabulary_debug_info(
                    vocab_pools, fact_response, "New Topic Fun Fact", len(session_data.contentVocabulary)
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
                    suggestedTheme=suggested_theme,
                    vocabularyDebug=vocab_debug
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