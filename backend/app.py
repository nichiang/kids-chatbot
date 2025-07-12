from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional
import logging
from llm_provider import llm_provider
from generate_prompt import generate_prompt, load_file

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
    
    # If no topic is set, user is choosing a topic (Step 1)
    if not session_data.topic:
        # Extract topic from user message
        topic = extract_topic_from_message(user_message)
        session_data.topic = topic
        session_data.currentStep = 2  # Moving to Step 2 after topic selection
        
        # Generate story beginning following Steps 2-4
        story_prompt = f"The child has chosen the topic: {topic}. Now write a paragraph that is 2-4 sentences long using vocabulary suitable for a strong 2nd grader or 3rd grader. Bold 2-3 tricky or important words. Then invite the child to continue the story without giving them any options. DO NOT include vocabulary questions - those will be handled separately."
        story_response = llm_provider.generate_response(story_prompt)
        session_data.storyParts.append(story_response)
        
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
                
                # Generate story beginning for new topic
                story_prompt = f"The child has chosen the topic: {potential_new_topic}. Now write a paragraph that is 2-4 sentences long using vocabulary suitable for a strong 2nd grader or 3rd grader. Bold 2-3 tricky or important words. Then invite the child to continue the story without giving them any options. DO NOT include vocabulary questions - those will be handled separately."
                story_response = llm_provider.generate_response(story_prompt)
                session_data.storyParts.append(story_response)
                
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
                    
                    # Generate story beginning for new topic
                    story_prompt = f"The child has chosen the topic: {potential_new_topic}. Now write a paragraph that is 2-4 sentences long using vocabulary suitable for a strong 2nd grader or 3rd grader. Bold 2-3 tricky or important words. Then invite the child to continue the story without giving them any options. DO NOT include vocabulary questions - those will be handled separately."
                    story_response = llm_provider.generate_response(story_prompt)
                    session_data.storyParts.append(story_response)
                    
                    # Get theme suggestion for new topic
                    suggested_theme = get_theme_suggestion(potential_new_topic)
                    
                    return ChatResponse(
                        response=story_response,
                        sessionData=session_data,
                        suggestedTheme=suggested_theme
                    )
        
        # Story is done, now show vocabulary questions
        all_story_text = " ".join(session_data.storyParts)
        vocab_words = llm_provider.extract_vocabulary_words(all_story_text)
        vocab_question = None
        if vocab_words:
            vocab_word = select_new_vocab_word(vocab_words, session_data.askedVocabWords)
            if vocab_word:
                session_data.askedVocabWords.append(vocab_word)
                vocab_question = llm_provider.generate_vocabulary_question(vocab_word, all_story_text)
        
        if vocab_question:
            return ChatResponse(
                response="Great story! Now let's test your vocabulary:",
                vocabQuestion=VocabQuestion(**vocab_question),
                sessionData=session_data
            )
        else:
            # No more vocabulary words to ask about - offer to write another story
            session_data.awaiting_story_confirmation = True
            story_completion_prompt = f"Wonderful story! You've mastered all the vocabulary words. Would you like to write another story? Here are some fun ideas:\\n\\n🚀 Space adventures\\n🏰 Fantasy quests\\n⚽ Sports excitement\\n🦄 Magical creatures\\n🕵️ Mystery solving\\n🍕 Food adventures\\n🐾 Animal stories\\n🌊 Ocean explorations\\n\\nWhat sounds interesting to you?"
            return ChatResponse(
                response=story_completion_prompt,
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
            # End the story (Step 7)
            story_prompt = f"End the story about {session_data.topic}. Previous context: {story_context}. Write a final paragraph that is 2-4 sentences long using vocabulary suitable for a strong 2nd grader or 3rd grader. Bold 2-3 tricky or important words. End the story with a satisfying conclusion and add 'The end!' at the very end. DO NOT ask the child to continue. DO NOT include vocabulary questions - those will be handled separately."
            story_response = llm_provider.generate_response(story_prompt)
            
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
            # Continue story (Steps 2-4 repeated)
            story_prompt = f"Continue the story about {session_data.topic}. Previous context: {story_context}. Write a paragraph that is 2-4 sentences long using vocabulary suitable for a strong 2nd grader or 3rd grader. Bold 2-3 tricky or important words. Then invite the child to continue the story without giving them any options. Keep this a short story - try to end it before it goes over 300 words total. DO NOT include vocabulary questions - those will be handled separately."
            story_response = llm_provider.generate_response(story_prompt)
            
            # Add grammar feedback if available
            if grammar_feedback:
                story_response = grammar_feedback + "\n\n" + story_response
            
            session_data.storyParts.append(story_response)
            session_data.currentStep += 1
            
            return ChatResponse(
                response=story_response,
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
        
        # Generate first fact
        fact_prompt = f"Generate a fun fact about: {topic}. Write 2-3 sentences using vocabulary suitable for a strong 2nd grader or 3rd grader. Bold 2-3 tricky or important words using **word** format. End with relevant emojis that match the topic."
        fact_response = llm_provider.generate_response(fact_prompt)
        session_data.currentFact = fact_response
        session_data.allFacts.append(fact_response)
        session_data.factsShown += 1
        
        # Generate vocabulary question
        vocab_words = llm_provider.extract_vocabulary_words(fact_response)
        vocab_question = None
        if vocab_words:
            vocab_word = select_new_vocab_word(vocab_words, session_data.askedVocabWords)
            if vocab_word:
                session_data.askedVocabWords.append(vocab_word)
                vocab_question = llm_provider.generate_vocabulary_question(vocab_word, fact_response)
        
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
            # Generate another fact
            previous_facts = " | ".join(session_data.allFacts) if session_data.allFacts else "None"
            fact_prompt = f"Generate a completely different and NEW fun fact about: {session_data.topic}. This is fact #{session_data.factsShown + 1}. DO NOT repeat any of these previous facts: {previous_facts}. Make sure this is a totally different aspect or detail about {session_data.topic}. Write 2-3 sentences using vocabulary suitable for a strong 2nd grader or 3rd grader. Bold 2-3 tricky or important words using **word** format. End with relevant emojis that match the topic."
            fact_response = llm_provider.generate_response(fact_prompt)
            session_data.currentFact = fact_response
            session_data.allFacts.append(fact_response)
            session_data.factsShown += 1
            
            # Generate vocabulary question
            vocab_words = llm_provider.extract_vocabulary_words(fact_response)
            vocab_question = None
            if vocab_words:
                vocab_word = select_new_vocab_word(vocab_words, session_data.askedVocabWords)
                if vocab_word:
                    session_data.askedVocabWords.append(vocab_word)
                    vocab_question = llm_provider.generate_vocabulary_question(vocab_word, fact_response)
            
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
                
                # Generate first fact for new topic
                fact_prompt = f"Generate a fun fact about: {new_topic}. Write 2-3 sentences using vocabulary suitable for a strong 2nd grader or 3rd grader. Bold 2-3 tricky or important words using **word** format. End with relevant emojis that match the topic."
                fact_response = llm_provider.generate_response(fact_prompt)
                session_data.currentFact = fact_response
                session_data.allFacts.append(fact_response)
                session_data.factsShown += 1
                
                # Generate vocabulary question
                vocab_words = llm_provider.extract_vocabulary_words(fact_response)
                vocab_question = None
                if vocab_words:
                    vocab_word = select_new_vocab_word(vocab_words, session_data.askedVocabWords)
                    if vocab_word:
                        session_data.askedVocabWords.append(vocab_word)
                        vocab_question = llm_provider.generate_vocabulary_question(vocab_word, fact_response)
                
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

def select_new_vocab_word(vocab_words: List[str], asked_words: List[str]) -> Optional[str]:
    """Select a vocabulary word that hasn't been asked yet"""
    for word in vocab_words:
        if word.lower() not in [asked.lower() for asked in asked_words]:
            return word
    # If all words have been asked, return the first one (shouldn't happen often)
    return vocab_words[0] if vocab_words else None

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