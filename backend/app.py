from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional
import logging
from llm_provider import llm_provider
from generate_prompt import generate_prompt, load_file, generate_fun_facts_prompt
from vocabulary_manager import vocabulary_manager

def generate_vocabulary_enhanced_prompt(base_prompt: str, topic: str, used_words: List[str] = None, word_count: int = 3) -> tuple[str, List[str]]:
    """
    Generate a prompt enhanced with vocabulary integration and return selected vocabulary words
    
    Args:
        base_prompt: The base prompt template
        topic: Topic for vocabulary selection
        used_words: Previously used words to avoid
        word_count: Number of vocabulary words to include
    
    Returns:
        Tuple of (enhanced_prompt, selected_vocabulary_words)
    """
    if used_words is None:
        used_words = []
    
    # Pre-select vocabulary words from curated banks
    selected_vocab_words = []
    for _ in range(word_count):
        vocab_word_data = vocabulary_manager.select_vocabulary_word(
            topic=topic,
            used_words=used_words + selected_vocab_words
        )
        if vocab_word_data:
            selected_vocab_words.append(vocab_word_data['word'])
    
    if selected_vocab_words:
        vocab_instruction = f" Naturally incorporate these educational vocabulary words into your content: {', '.join(selected_vocab_words)}. Bold these words using **word** format. DO NOT include vocabulary questions, definitions, or explanations - just use the words naturally in the content."
        enhanced_prompt = base_prompt + vocab_instruction
    else:
        # Fallback if no vocabulary available
        enhanced_prompt = base_prompt + " Bold 2-3 challenging or important words using **word** format. DO NOT include vocabulary questions or definitions in the content."
        selected_vocab_words = []
    
    return enhanced_prompt, selected_vocab_words

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
    
    # Clean up the bolded words (remove extra spaces, convert to lowercase for comparison)
    extracted_words = []
    for word in bolded_words:
        clean_word = word.strip().lower()
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
        enhanced_prompt, selected_vocab = generate_vocabulary_enhanced_prompt(
            base_prompt, topic, session_data.askedVocabWords
        )
        story_response = llm_provider.generate_response(enhanced_prompt)
        session_data.storyParts.append(story_response)
        
        # Track vocabulary words that were intended to be used
        if selected_vocab:
            logger.info(f"Story generation included vocabulary: {selected_vocab}")
            # Store them for later vocabulary question generation
            session_data.contentVocabulary.extend(selected_vocab)
        
        # Get theme suggestion for this topic
        suggested_theme = get_theme_suggestion(topic)
        
        return ChatResponse(
            response=story_response,
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
        # Use a word from the story content
        selected_word = available_words[0]
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
        # Use a word from the story content
        selected_word = available_words[0]
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
    
    story_completion_prompt = "Wonderful job with the vocabulary! You've done great! Would you like to write another story? Here are some fun ideas:\\n\\n🚀 Space adventures\\n🏰 Fantasy quests\\n⚽ Sports excitement\\n🦄 Magical creatures\\n🕵️ Mystery solving\\n🍕 Food adventures\\n🐾 Animal stories\\n🌊 Ocean explorations\\n\\nWhat sounds interesting to you?"
    
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
        
        # Generate vocabulary question using content-based extraction
        fact_vocab_words = extract_vocabulary_from_content(fact_response, session_data.contentVocabulary)
        vocab_question = None
        
        # Find a vocabulary word that hasn't been asked yet from the fact content
        available_fact_words = [word for word in fact_vocab_words if word not in session_data.askedVocabWords]
        
        if available_fact_words:
            selected_word = available_fact_words[0]
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
            
            # Generate vocabulary question using content-based extraction
            fact_vocab_words = extract_vocabulary_from_content(fact_response, session_data.contentVocabulary)
            vocab_question = None
            
            # Find a vocabulary word that hasn't been asked yet from the fact content
            available_fact_words = [word for word in fact_vocab_words if word not in session_data.askedVocabWords]
            
            if available_fact_words:
                selected_word = available_fact_words[0]
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
            if user_message.lower().strip() == "continue":
                new_topic = None  # Ignore topic extraction for continue signals
            else:
                new_topic = extract_topic_from_message(user_message)
            
            # If a new topic is detected and it's different from current topic, switch topics
            if new_topic and new_topic != session_data.topic:
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
                
                # Generate vocabulary question using content-based extraction
                fact_vocab_words = extract_vocabulary_from_content(fact_response, session_data.contentVocabulary)
                vocab_question = None
                
                # Find a vocabulary word that hasn't been asked yet from the fact content
                available_fact_words = [word for word in fact_vocab_words if word not in session_data.askedVocabWords]
                
                if available_fact_words:
                    selected_word = available_fact_words[0]
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
                return ChatResponse(
                    response=f"We've explored some great {session_data.topic} facts! Would you like to learn about a different topic? Try animals, space, inventions, or something else!",
                    sessionData=session_data
                )

# Legacy function removed - now using vocabulary_manager.select_vocabulary_word()

def extract_topic_from_message(message: str) -> str:
    """Extract topic from user message"""
    message_lower = message.lower()
    
    # Topic mapping
    topic_keywords = {
        "space": ["space", "planet", "star", "rocket", "astronaut", "jupiter", "mars", "galaxy", "alien"],
        "animals": ["animal", "dog", "cat", "elephant", "lion", "whale", "bird", "creature"],
        "inventions": ["invention", "science", "technology", "robot", "computer"],
        "sports": ["sport", "soccer", "football", "basketball", "tennis", "baseball"],
        "food": ["food", "cooking", "eat", "pizza", "ice cream", "fruit"],
        "ocean": ["ocean", "sea", "fish", "shark", "whale", "coral", "water"],
        "fantasy": ["fantasy", "magic", "magical", "dragon", "unicorn", "wizard", "fairy", "enchanted", "mystical"],
        "mystery": ["mystery", "detective", "clue", "solve", "secret", "hidden"],
        "adventure": ["adventure", "explore", "journey", "quest", "travel"]
    }
    
    for topic, keywords in topic_keywords.items():
        if any(keyword in message_lower for keyword in keywords):
            return topic
    
    # Default topic extraction - use first word that looks like a topic
    words = message.split()
    return words[0] if words else "adventure"

def get_theme_suggestion(topic: str) -> str:
    """Map topic to theme suggestion for frontend"""
    topic_to_theme = {
        'fantasy': 'theme-fantasy',
        'sports': 'theme-sports', 
        'food': 'theme-food',
        'animals': 'theme-animals',
        'ocean': 'theme-ocean',
        'space': 'theme-space',
        'mystery': 'theme-elegant',
        'adventure': 'theme-elegant',
        'inventions': 'theme-space'  # Technical topics default to space
    }
    
    return topic_to_theme.get(topic.lower(), 'theme-space')

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "English Learning Chatbot API is running!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)