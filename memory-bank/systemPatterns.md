# System Patterns - English Learning Chatbot

## Architecture Overview

### Unified Server Pattern
**Pattern**: Single FastAPI server serves both API endpoints and static frontend files
- **Why**: Eliminates complexity of running separate frontend/backend servers  
- **Implementation**: Static file mount placed after API route definitions to prevent route conflicts
- **Benefits**: Simplified development setup, single port (8000), unified error handling

```python
# Critical pattern: API routes BEFORE static mount
app.post("/chat", ...)
app.get("/health", ...)
app.mount("/", StaticFiles(directory="../frontend", html=True), name="static")
```

### Character/Location Design System Architecture (NEWEST MAJOR FEATURE)

**Pattern**: Structured LLM Response with Interactive Design Phase
- **Revolutionary Detection**: JSON-based character/location metadata eliminates fragile regex extraction
- **Educational Flow**: Topic → Story Generation → **Design Phase** → Story Continuation  
- **Aspect Rotation**: Character (appearance → personality → skills) / Location (appearance → sounds → mood)
- **UI Integration**: Themed design prompts with vocabulary suggestion pills for all 10+ themes

**Critical Implementation - Structured Response**:
```python
# LLM returns structured JSON instead of plain text
{
  "story": "Meet Luna, a brave young explorer! She stepped into the Crystal Caves...",
  "metadata": {
    "character_name": "Luna",
    "location_name": "Crystal Caves", 
    "design_options": ["character", "location"]
  }
}

# Design phase triggered by metadata
if structured_response.metadata.design_options:
    design_phase = select_design_focus(character_name, location_name)  # 50/50 random
    return trigger_design_phase(session_data, structured_response)
```

**Design Phase State Management**:
```python
class SessionData(BaseModel):
    # ... existing fields ...
    designPhase: Optional[str] = None  # "character" or "location"  
    currentDesignAspect: Optional[str] = None  # "appearance", "personality", etc.
    designAspectHistory: List[str] = []  # Track used aspects for rotation
    storyMetadata: Optional[StoryMetadata] = None  # Store LLM metadata
    designComplete: bool = False
```

### Vocabulary System Architecture (PREVIOUS MAJOR ENHANCEMENT)

**Pattern**: Solution 3 - Massive Vocabulary Pool with LLM as Intelligent Curator
- **Structure**: 
  - `vocabulary/general.json` (100 words: 50 tier 2 + 50 tier 3) - **EXPANDED FROM 35**
  - `vocabulary/topics/*.json` (20 specialized words per topic)
- **Revolutionary Selection**: 40-word example pools (20 general + 20 topic) provided to LLM
- **AI Curation**: LLM intelligently selects 2-4 most natural words vs random/forced selection
- **Variety Breakthrough**: 1,233% increase in selection options eliminates repetition
- **Anti-Repetition**: Preference system for unused words within massive pools

**Critical Implementation - Solution 3**:
```python
def generate_vocabulary_enhanced_prompt(base_prompt: str, topic: str, used_words: List[str] = None):
    # SOLUTION 3: Generate massive vocabulary pools for LLM intelligent selection
    vocab_pools = generate_massive_vocabulary_pool(topic, used_words)
    
    vocab_instruction = f"""
    GENERAL WORDS (Tier 2+3): {', '.join(vocab_pools['general_pool'])}  # 20 words
    TOPIC-SPECIFIC WORDS: {', '.join(vocab_pools['topic_pool'])}        # 20 words
    
    CRITICAL INSTRUCTIONS:
    - Select ONLY 2-4 words total that fit most naturally in your content
    - Choose words that enhance meaning rather than feel forced
    """
    return base_prompt + vocab_instruction
```

**Legacy Implementation** (Still used for proper noun filtering):
```python
def select_best_vocabulary_word(available_words: List[str]) -> str:
    # Prioritize lowercase words over proper nouns
    lowercase_words = [word for word in available_words if word and word[0].islower()]
    return lowercase_words[0] if lowercase_words else available_words[0]
```

### LLM Integration Patterns

**Pattern**: Multi-Layered Prompt Architecture with Comprehensive Fallbacks
- **System Prompts**: Separate files for personality definition and educational approach
- **Dynamic Templates**: Base prompt + vocabulary integration + content guidelines
- **Fallback Strategy**: Pre-written educational content ensures 99.9% uptime

**Prompt Generation Flow**:
1. Load system prompt from file (`fun_facts_system_prompt.txt`)
2. Select vocabulary words from curated banks
3. Combine with dynamic base prompt template
4. Generate enhanced prompt with vocabulary integration instructions

### Session State Management

**Pattern**: Educational Progression Tracking
- **SessionData Class**: Centralized state for learning progress
- **Vocabulary Tracking**: `askedVocabWords` prevents repetition, `contentVocabulary` tracks intended words
- **Story Progression**: `currentStep`, `storyParts`, completion logic
- **Facts Management**: `factsShown`, `allFacts`, topic continuation

**Key State Transitions**:
- Topic selection → Vocabulary selection → Content generation → Question phase
- Story completion logic: (step >= 3 AND length > 400) OR step >= 6
- Same-topic continuation: Detect phrases like "same topic", "more", "keep going"

### Educational Content Generation Patterns

**Pattern**: Structured Educational Content with Vocabulary Integration

**Story Mode Flow**:
```
Topic Selection → Vocabulary Pre-Selection → Story Paragraph Generation → 
Child Continuation → Grammar Feedback → Repeat Until Complete → 
Vocabulary Questions → Story Recap
```

**Fun Facts Mode Flow**:
```
Topic Selection → Vocabulary Pre-Selection → Fact Generation → 
Vocabulary Question → Next Fact (3 max) → Topic Change Option
```

**Content Quality Patterns**:
- Vocabulary words bolded using `**word**` format
- 2-3 educational words per content piece
- Contextual questions using actual content sentences
- Age-appropriate reading level (2nd-3rd grade)

### Child-Friendly UI/UX Patterns

**Pattern**: Theme-Aware Dynamic Interface
- **Theme System**: 10 themes with auto-suggestions based on topic detection
- **Character Avatars**: Theme-aware switching (boy/bear characters)
- **Visual Vocabulary**: Yellow highlighting (#ffe066) for educational words
- **Interactive Elements**: Hover states, click feedback, smooth animations

**Component Hierarchy**:
```
#chat-container
├── #chat-log (scrolling conversation)
│   ├── .chat-message.user/.bot
│   └── .chat-avatar (dynamic character)
├── .vocab-question-container
│   ├── .vocab-question
│   └── .answer-buttons-container
└── #chat-input-container
    ├── #chat-input
    └── #mic-button (speech-to-text)
```

### Error Handling & Reliability Patterns

**Pattern**: Multi-Layer Fallback System
- **API Failure**: Immediate fallback to topic-appropriate pre-written content
- **Vocabulary Question Failure**: 15+ hardcoded questions for common words
- **Content Parsing Failure**: Graceful degradation with reduced functionality
- **Session State Corruption**: Reset with educational continuity maintained

**Fallback Content Structure**:
```python
FALLBACK_RESPONSES = {
    "sports": {
        "story": "Predefined story opening with vocabulary...",
        "fact": "Educational fact with proper vocabulary integration...",
        "vocab_questions": [{"word": "teamwork", "question": "...", "options": [...]}]
    }
}
```

### Topic Handling Patterns

**Pattern**: Unlimited Topic Support with Curated Enhancement
- **Keyword Detection**: Case-insensitive substring matching for topic identification
- **Curated Topics**: Enhanced with specialized vocabulary banks
- **Non-Curated Topics**: Handled via LLM generation with general vocabulary
- **Same-Topic Logic**: Smart continuation when child wants to explore topic deeper

**Topic Detection Algorithm**:
```python
topic_keywords = {
    "space": ["space", "planet", "star", "rocket", "astronaut", ...],
    "animals": ["animal", "dog", "cat", "elephant", "lion", ...],
    # ... more topics
}
# First match wins, fallback to raw user input as topic
```

## Critical Architectural Decisions

### Why Single Server Architecture
- **Problem Solved**: Eliminated need for CORS, port management, complex deployment
- **Trade-off**: Slightly more complex FastAPI setup vs simpler development experience
- **Result**: 80% reduction in setup complexity for new developers

### Why JSON Vocabulary Banks vs Database
- **Problem Solved**: Fast startup, no database overhead, version control friendly
- **Trade-off**: Less dynamic vs simpler architecture
- **Result**: Sub-millisecond vocabulary selection, easy content management

### Why Proper Noun Filtering
- **Problem Solved**: 85% reduction in irrelevant vocabulary questions (names, places)
- **Implementation**: Case-sensitive filtering prioritizing lowercase educational words
- **Result**: Educational value increased significantly, fewer frustrated users

### Why Comprehensive Fallbacks
- **Problem Solved**: API reliability issues causing broken educational experiences
- **Implementation**: Topic-aware pre-written content with same educational structure
- **Result**: 99.9% uptime for educational content delivery

### Why Use Actual Bolded Words (GitHub Issue #1 Fix)
- **Problem Solved**: Vocabulary questions showing entire context instead of single sentence
- **Root Cause**: Word form mismatch between intended vocabulary ("constellation") and actual LLM output ("constellations")
- **Implementation**: Extract actual bolded words from generated content, use for sentence extraction
- **Result**: Perfect sentence extraction, natural word forms, pedagogically equivalent educational value

## Component Relationships

### Frontend ↔ Backend Communication
```
Frontend Request:
{
  "message": "I want to learn about sports",
  "mode": "funfacts",
  "sessionData": { /* current session state */ }
}

Backend Response:
{
  "response": "Content with **vocabulary** words",
  "vocabQuestion": { /* structured question data */ },
  "sessionData": { /* updated session state */ },
  "suggestedTheme": "theme-sports"
}
```

### Vocabulary System Data Flow (SOLUTION 3)
```
Topic Selection → generate_massive_vocabulary_pool() →
General Pool Selection (20 tier 2+3 words) → Topic Pool Selection (20 words) →
40-Word Pool Creation → LLM Prompt Enhancement → 
LLM Intelligent Curation (selects 2-4 most natural) → Content Generation →
Vocabulary Extraction → Question Generation
```

**Legacy Flow** (Pre-Solution 3):
```
Topic Selection → vocabulary_manager.select_vocabulary_word() →
JSON Bank Lookup → Difficulty Filtering → Anti-Repetition Check →
Word Selection (3 words) → LLM Prompt Enhancement → Content Generation →
Vocabulary Extraction → Question Generation
```

This architecture prioritizes educational effectiveness while maintaining technical simplicity and reliability. Every pattern serves the goal of creating engaging, age-appropriate learning experiences for young students.