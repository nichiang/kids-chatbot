# English Learning Chatbot

A friendly, fun chatbot to help kids learn English vocabulary, spelling, and grammar, built with Python (FastAPI) and HTML/CSS/JS.

## Project Structure

```
english-chatbot/
├── backend/
│   ├── app.py
│   ├── llm_provider.py
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
└── README.md
```

## Getting Started

### 1. Install Backend Dependencies

Open a terminal and run:

```bash
cd english-chatbot/backend
pip install -r requirements.txt
```

### 2. Run the Backend Server

```bash
uvicorn app:app --reload
```

The backend will be available at `http://localhost:8000`.

### 3. Open the Frontend

Open `english-chatbot/frontend/index.html` in your web browser.

### 4. Test the Chatbot

- Type a message and click "Send".
- The bot will echo your message (for now).

---

## Next Steps

- Integrate OpenAI for real chatbot responses.
- Add grade level and topic selection.
- Build vocabulary, spelling, and grammar features based on IOWA standards.
- Make LLM provider easy to swap.
