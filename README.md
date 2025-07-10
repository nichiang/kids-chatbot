# English Learning Chatbot

An interactive English tutor for elementary school students (2nd-3rd grade) featuring dual-mode learning: collaborative storytelling and fun facts exploration. Built with Python (FastAPI) backend and vanilla JavaScript frontend.

## Features

### 🚀 Dual Learning Modes
- **Storywriting Mode**: Co-write stories with the AI tutor following a structured 10-step process
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
│   ├── app.py                 # FastAPI server with dual-mode chat endpoints
│   ├── llm_provider.py        # OpenAI integration with fallback responses
│   ├── generate_prompt.py     # Prompt generation from spec files
│   ├── intro_prompt.txt       # AI tutor personality definition
│   ├── story_steps_prompt.txt # 10-step story process instructions
│   ├── vocab.csv              # Elementary vocabulary word list
│   ├── requirements.txt       # Python dependencies
│   └── .env.example          # Environment variables template
├── frontend/
│   ├── index.html            # Main application interface
│   ├── style.css             # Space-themed UI styling
│   └── app.js                # Chat functionality and mode switching
├── design/                   # UI mockups and specifications
├── CLAUDE.md                 # Development guide for Claude Code
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

### 4. Start the Backend Server

```bash
uvicorn app:app --reload
```

The backend will be available at `http://localhost:8000`.

### 5. Open the Frontend

Open `frontend/index.html` in your web browser.

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

### Backend (FastAPI)
- RESTful `/chat` endpoint for both modes
- OpenAI GPT integration with intelligent fallbacks
- Structured prompt engineering from spec files
- Grammar analysis and vocabulary extraction
- Session state management

### Frontend (Vanilla JS)
- Real-time chat interface with avatars
- Dual-mode switching (Storywriting/Fun Facts)
- Interactive vocabulary questions with multiple choice
- Visual feedback and animations
- Space-themed responsive design

### Educational Design
- Vocabulary words highlighted in yellow (#ffe066)
- Age-appropriate content for 2nd-3rd graders
- Encouraging feedback and positive reinforcement
- Structured learning flow following educational best practices

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

## Development

The application includes comprehensive fallback responses, so it works without an OpenAI API key for testing and development.

### Running Tests
Currently no formal test framework - the application has been thoroughly tested through interactive use.

### Linting
No specific linting configuration - code follows Python PEP 8 and JavaScript ES6 standards.

## Contributing

This is an educational project. Contributions should focus on:
- Educational content quality
- Child-friendly interface improvements
- Accessibility enhancements
- Additional learning modes

## License

This project is for educational purposes.