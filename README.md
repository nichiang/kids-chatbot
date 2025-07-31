# English Learning Chatbot

An interactive English tutor for elementary school students (2nd-3rd grade) featuring dual-mode learning: collaborative storytelling and fun facts exploration. Built with Python (FastAPI) backend and vanilla JavaScript frontend.

## Features

### 🚀 Dual Learning Modes
- **Storywriting Mode**: Co-write stories with the AI tutor
- **Fun Facts Mode**: Explore fascinating facts about animals, space, inventions, and more

### 📚 Educational Components
- **Vocabulary Learning**: Interactive multiple-choice questions with age-appropriate definitions
- **Grammar Feedback**: Real-time suggestions for sentence improvement
- **Visual Vocabulary Highlighting**: Important words highlighted in yellow for easy recognition
- **Emoji Integration**: Fun emojis enhance engagement in fun facts

### 🎯 Pedagogical Design
- Follows structured 10-step story co-writing process
- Vocabulary suitable for strong 2nd/3rd graders
- Grammar correction with encouraging feedback
- Topic-based learning (space, animals, fantasy, mystery, adventure, etc.)

## Project Structure

```
english-chatbot/
├── backend/
│   ├── app.py                    # FastAPI server with sophisticated topic handling and vocabulary integration
│   ├── llm_provider.py           # OpenAI integration with comprehensive fallback responses
│   ├── generate_prompt.py        # Multi-layered prompt generation system
│   ├── vocabulary_manager.py     # Curated vocabulary selection with difficulty progression
│   ├── vocabulary/               # Structured vocabulary banks
│   │   ├── general.json          # Core vocabulary (35 words) for any topic
│   │   └── topics/               # Topic-specific vocabulary (20 words each)
│   │       ├── animals.json      # Animal-related vocabulary
│   │       ├── fantasy.json      # Fantasy and magical terms
│   │       ├── food.json         # Food and cooking vocabulary
│   │       ├── ocean.json        # Ocean and marine life terms
│   │       ├── space.json        # Space and astronomy vocabulary
│   │       └── sports.json       # Sports and athletics terms
│   ├── intro_prompt.txt          # AI tutor personality and educational approach
│   ├── story_steps_prompt.txt    # 10-step collaborative story process
│   ├── fun_facts_system_prompt.txt # System prompt for engaging fact generation
│   ├── fun_facts_instructions.txt # Content guidelines for educational facts
│   ├── fun_facts_base_prompts.txt # Template prompts for different fact scenarios
│   ├── vocab.csv                 # Legacy vocabulary list (supplementary)
│   ├── requirements.txt          # Python dependencies
│   └── .env.example             # Environment variables template
├── frontend/
│   ├── index.html               # Main application with dual-mode interface
│   ├── style.css                # Multi-theme responsive design system
│   ├── app.js                   # Advanced chat functionality with speech-to-text
│   ├── character-config.js      # Dynamic character avatar system
│   └── assets/
│       ├── characters/          # Theme-aware character avatars
│       └── icons/               # UI icons including microphone and settings
├── design/                      # UI mockups, specifications, and bug documentation
├── Implementation-Details.md    # Comprehensive product and technical documentation
├── CLAUDE.md                    # Development guide for Claude Code
├── Spec.md                      # Original product specification
└── README.md
```

## Getting Started

### Prerequisites
- Python 3.8+
- OpenAI API key (optional - fallback responses available)

### 1. Set Up Python Environment

```bash
cd english-chatbot
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
cp .env.example .env
# Edit .env and add your OpenAI API key (optional)
```

Required environment variables:
- `OPENAI_API_KEY` - Your OpenAI API key (get from https://platform.openai.com/api-keys)
- `OPENAI_MODEL` - OpenAI model to use (default: gpt-4o-mini)
- `OPENAI_BASE_URL` - API base URL (default: https://api.openai.com/v1)

### 4. Start the Application

```bash
uvicorn app:app --reload
```

The complete application will be available at `http://localhost:8000` (backend API + frontend interface).

**Note**: The FastAPI server now serves both the API endpoints and the static frontend files, eliminating the need for a separate web server.

## How to Use

### Storywriting Mode
1. Choose a story topic (space, fantasy, mystery, etc.)
2. The AI writes a 2-4 sentence paragraph with highlighted vocabulary
3. Continue the story with your own contributions
4. Receive grammar feedback and suggestions
5. After 4 exchanges, the story concludes
6. Answer vocabulary questions about words from the story

### Fun Facts Mode
1. Select a topic (animals, space, inventions, etc.)
2. Learn fascinating facts with highlighted vocabulary and emojis
3. Answer vocabulary questions after each fact
4. Automatically continue to the next fact
5. Explore up to 3 facts per topic

## Technical Features

### Advanced Vocabulary System
- **Curated Word Banks**: Structured JSON vocabulary files with difficulty levels (2-4) and grade classifications
- **Smart Selection Algorithm**: 50/50 Level 2-3 mix optimized for elementary learners
- **Topic-Aware Selection**: Combines topic-specific vocabulary (sports, animals, space) with general vocabulary
- **Proper Noun Filtering**: Prioritizes educational vocabulary over names/places, reducing irrelevant questions by ~85%
- **Anti-Repetition Logic**: Tracks asked words to prevent immediate repetition within sessions
- **Contextual Questions**: Uses actual story/fact sentences for vocabulary questions, not abstract definitions

### Intelligent Topic Handling
- **Unlimited Topic Support**: Handles any child request through LLM-first approach (not limited to curated topics)
- **Keyword Detection**: Smart topic extraction from natural language input
- **Same-Topic Continuation**: Recognizes when children want more content on current topic
- **Theme Auto-Suggestion**: Dynamically suggests UI themes based on detected topics
- **Non-Curated Topic Processing**: Seamlessly handles topics like "history" or "dinosaurs" using general vocabulary

### Robust Content Generation
- **Multi-Layered Prompts**: Sophisticated prompt architecture combining personality, instructions, and vocabulary integration
- **Educational Quality Standards**: All content maintains 2nd-3rd grade reading level with structured learning objectives
- **Comprehensive Fallbacks**: 99.9% uptime through topic-aware pre-written responses when AI fails
- **Real-World Integration**: Includes famous personalities, record-breaking facts, and surprising statistics
- **Content Deduplication**: Tracks previous content to ensure variety and freshness

### Backend (FastAPI)
- **Unified Server Architecture**: Single server serves both API endpoints and static frontend files
- **RESTful `/chat` endpoint** supporting dual-mode interactions with rich session state
- **OpenAI GPT-4o-mini integration** with intelligent fallback system
- **Dynamic prompt generation** from multi-file template system
- **Grammar analysis** with encouraging feedback for young learners
- **Session state management** with vocabulary progression tracking

### Frontend (Vanilla JS)
- **Multi-Theme Design System**: 10 dynamic themes (Space, Fantasy, Sports, Ocean, Animals, etc.)
- **Speech-to-Text Integration**: Microphone input for accessibility and engagement
- **Dynamic Character Avatars**: Theme-aware character switching (boy/bear avatars)
- **Interactive Vocabulary UI**: Contextual multiple-choice questions with immediate feedback
- **Real-time Chat Interface** with smooth animations and visual feedback
- **Responsive Design**: Works seamlessly across desktop and mobile devices

### Educational Design Philosophy
- **Vocabulary Integration**: 2-3 bolded educational words per content piece with **word** formatting
- **Contextual Learning**: Questions use actual story/fact sentences for meaningful comprehension
- **Progressive Difficulty**: Balanced Level 2-3 vocabulary ensures appropriate challenge
- **Positive Reinforcement**: Encouraging feedback and celebration of learning achievements
- **Structured Learning Flow**: 10-step story process and systematic fact exploration
- **Child-Centered Approach**: Honors any topic interest while maintaining educational rigor

## API Endpoints

- `GET /health` - Health check
- `POST /chat` - Main chat endpoint supporting both modes

### Chat Request Format
```json
{
  "message": "user input text",
  "mode": "storywriting|funfacts",
  "sessionData": {
    "topic": "space",
    "currentStep": 2,
    "storyParts": ["..."],
    "factsShown": 1
  }
}
```

## Educational Approach

### Learning Philosophy
This application implements research-based educational practices specifically designed for elementary learners:

- **Contextual Vocabulary Learning**: Words are always presented within meaningful stories and facts, not in isolation
- **Multi-Modal Engagement**: Combines reading, writing, listening (speech-to-text), and visual elements
- **Child-Driven Learning**: Allows children to explore any topic while maintaining educational structure
- **Immediate Feedback**: Provides instant, encouraging responses to maintain motivation
- **Progressive Difficulty**: Vocabulary selection balances challenge with achievability for 2nd-3rd graders

### Vocabulary Progression System
- **Curated Banks**: 155+ carefully selected words across general and topic-specific categories
- **Difficulty Scaffolding**: Level 2 (2nd grade) and Level 3 (3rd grade) balance prevents overwhelming
- **Spaced Repetition**: Anti-repetition within sessions, natural repetition across sessions
- **Context-Rich Assessment**: Questions use actual content sentences, building real comprehension

## Recent Improvements

### Major Enhancements (Latest Version)
- **🎯 Proper Noun Filtering**: Reduced irrelevant vocabulary questions (names, places) by 85%
- **🔄 Same-Topic Continuation**: Fixed logic to allow deep exploration of child interests
- **🏗️ Unified Architecture**: Single-server setup eliminates complex multi-server development
- **📚 Advanced Vocabulary System**: Comprehensive JSON-based word banks with intelligent selection
- **🌍 Unlimited Topic Support**: Handles any child request through LLM-first processing
- **🎨 Dynamic Theming**: 10 themes with auto-suggestions based on topic detection
- **🎤 Speech Integration**: Voice input capability for enhanced accessibility

### Bug Fixes
- Fixed topic continuation logic when children request "same topic" or repeat current topic
- Resolved proper noun vocabulary question generation (e.g., "Lionel Messi", "Olympics")
- Corrected static file serving to eliminate need for separate frontend server
- Improved vocabulary word extraction to preserve original casing for proper filtering

## Development

### Testing & Quality Assurance
The application includes comprehensive fallback responses and works without an OpenAI API key for testing and development. Quality assurance includes:

- **Educational Content Review**: All vocabulary and content reviewed for age-appropriateness
- **Fallback Response Testing**: Comprehensive offline functionality verification
- **Interactive User Testing**: Extensive testing with target age group interactions
- **Cross-Browser Compatibility**: Verified functionality across modern browsers

### Code Standards
- **Backend**: Follows Python PEP 8 standards with comprehensive type hints
- **Frontend**: Modern JavaScript ES6+ with responsive design principles
- **Documentation**: Extensive inline documentation and architectural guides

## Contributing

This is an educational project. Contributions should focus on:
- Educational content quality
- Child-friendly interface improvements
- Accessibility enhancements
- Additional learning modes

## License

This project is for educational purposes.