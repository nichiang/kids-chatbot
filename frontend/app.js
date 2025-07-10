document.addEventListener("DOMContentLoaded", function () {
    const chatForm = document.getElementById("chat-form");
    const chatInput = document.getElementById("chat-input");
    const chatLog = document.getElementById("chat-log");
    const storywritingBtn = document.getElementById("storywriting-btn");
    const funFactsBtn = document.getElementById("fun-facts-btn");

    // App state
    let currentMode = 'storywriting'; // 'storywriting' or 'funfacts'
    let sessionData = {
        storywriting: {
            topic: null,
            storyParts: [],
            currentStep: 0,
            isComplete: false
        },
        funfacts: {
            topic: null,
            factsShown: 0,
            currentFact: null,
            isComplete: false
        }
    };

    // Mode switching
    function switchMode(mode) {
        currentMode = mode;
        
        // Update button states
        storywritingBtn.classList.toggle('active', mode === 'storywriting');
        funFactsBtn.classList.toggle('active', mode === 'funfacts');
        
        // Clear chat log
        chatLog.innerHTML = '';
        
        // Initialize the selected mode
        if (mode === 'storywriting') {
            initializeStorywriting();
        } else {
            initializeFunFacts();
        }
    }

    // Initialize Storywriting mode
    function initializeStorywriting() {
        if (!sessionData.storywriting.topic) {
            appendMessage("bot", "Hi there! I'm excited to co-write a story with you! 📚✨\n\nWhat kind of story would you like to write today? Here are some fun options:\n\n🚀 Space adventures\n🏰 Fantasy quests\n⚽ Sports excitement\n🦄 Magical creatures\n🕵️ Mystery solving\n\nWhat sounds interesting to you?");
        } else {
            // Continue existing story
            appendMessage("bot", "Let's continue our story! What happens next?");
        }
    }

    // Initialize Fun Facts mode
    function initializeFunFacts() {
        if (!sessionData.funfacts.topic) {
            appendMessage("bot", "Hey explorer! I have so many amazing facts to share! 🤓✨\n\nWhat topic would you like to learn about today?\n\n🐾 Animals\n🌌 Space\n🔬 Science inventions\n🏈 Sports\n🍕 Food\n🌊 Ocean creatures\n\nPick something that sounds cool to you!");
        } else {
            // Continue with more facts
            appendMessage("bot", "Ready for another awesome fact? Let me know when you are!");
        }
    }

    // Message handling
    function appendMessage(sender, text) {
        const msgWrapper = document.createElement("div");
        msgWrapper.className = sender === "user" ? "chat-message user" : "chat-message bot";

        const avatar = document.createElement("img");
        avatar.className = "chat-avatar";
        if (sender === "user") {
            avatar.src = "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/1f9d2.png";
            avatar.alt = "Kid";
        } else {
            avatar.src = "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/1f43b.png";
            avatar.alt = "Bear Tutor";
        }

        const bubble = document.createElement("div");
        bubble.className = "chat-bubble";
        
        // Replace **word** with colored spans for vocabulary highlighting
        const processedText = text.replace(/\*\*(.*?)\*\*/g, '<span class="vocab-word">$1</span>');
        bubble.innerHTML = processedText;

        msgWrapper.appendChild(avatar);
        msgWrapper.appendChild(bubble);

        chatLog.appendChild(msgWrapper);
        chatLog.scrollTop = chatLog.scrollHeight;
    }

    // Create vocabulary question UI
    function appendVocabQuestion(question, options, correctIndex) {
        const vocabContainer = document.createElement("div");
        vocabContainer.className = "vocab-question-container";

        // Question bubble
        const questionWrapper = document.createElement("div");
        questionWrapper.className = "chat-message bot";

        const avatar = document.createElement("img");
        avatar.className = "chat-avatar";
        avatar.src = "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/1f43b.png";
        avatar.alt = "Bear Tutor";

        const bubble = document.createElement("div");
        bubble.className = "chat-bubble";
        
        // Replace **word** with colored spans for vocabulary highlighting
        const processedQuestion = question.replace(/\*\*(.*?)\*\*/g, '<span class="vocab-word">$1</span>');
        bubble.innerHTML = processedQuestion;

        questionWrapper.appendChild(avatar);
        questionWrapper.appendChild(bubble);

        // Answer buttons
        const answersWrapper = document.createElement("div");
        answersWrapper.className = "vocab-answers-wrapper";

        const kidAvatar = document.createElement("img");
        kidAvatar.className = "kid-avatar";
        kidAvatar.src = "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/1f9d2.png";
        kidAvatar.alt = "Kid";

        const buttonsContainer = document.createElement("div");
        buttonsContainer.className = "answer-buttons-container";

        options.forEach((option, index) => {
            const button = document.createElement("button");
            button.className = "answer-button";
            button.textContent = option;
            button.addEventListener("click", () => {
                handleVocabAnswer(index, correctIndex, option, buttonsContainer, vocabContainer);
            });
            buttonsContainer.appendChild(button);
        });

        answersWrapper.appendChild(buttonsContainer);
        answersWrapper.appendChild(kidAvatar);

        vocabContainer.appendChild(questionWrapper);
        vocabContainer.appendChild(answersWrapper);

        chatLog.appendChild(vocabContainer);
        chatLog.scrollTop = chatLog.scrollHeight;
    }

    // Handle vocabulary answer
    function handleVocabAnswer(selectedIndex, correctIndex, selectedOption, buttonsContainer, vocabContainer) {
        // Disable all buttons
        Array.from(buttonsContainer.children).forEach(btn => btn.disabled = true);

        // Highlight selected button
        const selectedButton = buttonsContainer.children[selectedIndex];
        selectedButton.classList.add("selected");

        // Add checkmark to correct answer
        const correctButton = buttonsContainer.children[correctIndex];
        if (selectedIndex === correctIndex) {
            const checkmark = document.createElement("span");
            checkmark.className = "checkmark";
            checkmark.textContent = "✔";
            selectedButton.appendChild(checkmark);
        } else {
            const checkmark = document.createElement("span");
            checkmark.className = "checkmark";
            checkmark.textContent = "✔";
            correctButton.appendChild(checkmark);
            correctButton.style.background = "#2cb67d";
        }

        // Show user's selection
        appendMessage("user", selectedOption);

        // Show feedback
        const feedback = selectedIndex === correctIndex 
            ? "Correct! Great job! 🎉" 
            : `Nice try! The correct answer was ${buttonsContainer.children[correctIndex].textContent}. You'll get it next time! 💪`;
        
        appendMessage("bot", feedback);

        // Remove vocab container
        setTimeout(() => {
            vocabContainer.remove();
        }, 1000);

        // Continue fun facts flow automatically
        if (currentMode === 'funfacts') {
            setTimeout(() => {
                continueAfterVocab();
            }, 2000);
        }
    }

    // Continue fun facts flow after vocabulary question
    async function continueAfterVocab() {
        try {
            // Show thinking message
            appendMessage("bot", "Let me share another cool fact...");

            // Send continue request to backend
            const response = await fetch("http://localhost:8000/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ 
                    message: "continue", // Signal to continue
                    mode: currentMode,
                    sessionData: sessionData[currentMode]
                })
            });

            const data = await response.json();
            
            // Remove thinking message
            chatLog.removeChild(chatLog.lastChild);
            
            // Handle response
            if (data.response) {
                appendMessage("bot", data.response);
            }
            
            // Update session data
            if (data.sessionData) {
                sessionData[currentMode] = data.sessionData;
            }
            
            // Handle vocabulary questions
            if (data.vocabQuestion) {
                setTimeout(() => {
                    appendVocabQuestion(
                        data.vocabQuestion.question,
                        data.vocabQuestion.options,
                        data.vocabQuestion.correctIndex
                    );
                }, 1000);
            }

        } catch (err) {
            // Remove thinking message if it exists
            if (chatLog.lastChild && chatLog.lastChild.textContent.includes("thinking")) {
                chatLog.removeChild(chatLog.lastChild);
            }
            appendMessage("bot", "Sorry, I'm having trouble continuing right now. Please try again!");
        }
    }

    // Handle form submission
    chatForm.addEventListener("submit", async function (e) {
        e.preventDefault();
        const userMessage = chatInput.value.trim();
        if (!userMessage) return;

        appendMessage("user", userMessage);
        chatInput.value = "";

        // Show thinking message
        appendMessage("bot", "Thinking...");

        try {
            // Send to backend
            const response = await fetch("http://localhost:8000/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ 
                    message: userMessage,
                    mode: currentMode,
                    sessionData: sessionData[currentMode]
                })
            });

            const data = await response.json();
            
            // Remove thinking message
            chatLog.removeChild(chatLog.lastChild);
            
            // Handle response based on mode
            if (data.response) {
                appendMessage("bot", data.response);
            }
            
            // Update session data with backend response
            if (data.sessionData) {
                sessionData[currentMode] = data.sessionData;
            }
            
            // Handle vocabulary questions
            if (data.vocabQuestion) {
                setTimeout(() => {
                    appendVocabQuestion(
                        data.vocabQuestion.question,
                        data.vocabQuestion.options,
                        data.vocabQuestion.correctIndex
                    );
                }, 1000);
            }

        } catch (err) {
            // Remove thinking message
            chatLog.removeChild(chatLog.lastChild);
            appendMessage("bot", "Sorry, I'm having trouble connecting right now. Please try again!");
        }
    });

    // Event listeners for mode buttons
    storywritingBtn.addEventListener("click", () => switchMode('storywriting'));
    funFactsBtn.addEventListener("click", () => switchMode('funfacts'));

    // Initialize the app
    switchMode('storywriting');
});