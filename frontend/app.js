document.addEventListener("DOMContentLoaded", async function () {
    const chatForm = document.getElementById("chat-form");
    const chatInput = document.getElementById("chat-input");
    const chatLog = document.getElementById("chat-log");
    const storywritingBtn = document.getElementById("storywriting-btn");
    const funFactsBtn = document.getElementById("fun-facts-btn");
    const micButton = document.getElementById("mic-button");

    // Load theme configuration from centralized JSON file
    let themeConfig = null;
    try {
        const response = await fetch('/config/theme-config.json');
        themeConfig = await response.json();
        console.log('Theme configuration loaded successfully');
    } catch (error) {
        console.error('Failed to load theme configuration, using fallback:', error);
        // Fallback configuration in case JSON loading fails
        themeConfig = {
            topicKeywords: {
                "space": ["space", "planet", "star", "rocket", "astronaut"],
                "animals": ["animal", "dog", "cat", "creature"],
                "fantasy": ["fantasy", "magic", "magical", "dragon"],
                "sports": ["sport", "soccer", "football"],
                "ocean": ["ocean", "sea", "fish"],
                "food": ["food", "cooking", "eat"]
            },
            themeMapping: {
                "fantasy": "theme-fantasy",
                "sports": "theme-sports",
                "animals": "theme-animals",
                "ocean": "theme-ocean",
                "space": "theme-space"
            },
            defaultTheme: "theme-space"
        };
    }

    // App state
    let currentMode = 'funfacts'; // 'storywriting' or 'funfacts'
    let sessionData = {
        storywriting: {
            topic: null,
            storyParts: [],
            currentStep: 0,
            isComplete: false,
            vocabularyPhase: {
                isActive: false,
                questionsAsked: 0,
                maxQuestions: 3,
                isComplete: false
            }
        },
        funfacts: {
            topic: null,
            factsShown: 0,
            currentFact: null,
            isComplete: false
        }
    };

    // Speech Recognition Setup
    let speechRecognition = null;
    let isRecording = false;

    // Initialize speech recognition
    function initializeSpeechRecognition() {
        // Check for speech recognition API support
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        
        if (!SpeechRecognition) {
            console.error("Speech recognition not supported in this browser. Please use Chrome, Edge, Safari, or Firefox with HTTPS.");
            micButton.style.display = 'none';
            return false;
        }

        // Check if we're on HTTPS (required for microphone access)
        if (location.protocol !== 'https:' && location.hostname !== 'localhost' && location.hostname !== '127.0.0.1') {
            console.error("Speech recognition requires HTTPS or localhost. Current protocol:", location.protocol);
            micButton.style.display = 'none';
            return false;
        }

        try {
            speechRecognition = new SpeechRecognition();
            speechRecognition.continuous = false;
            speechRecognition.interimResults = true;
            speechRecognition.lang = 'en-US';

            speechRecognition.onstart = function() {
                console.log("Speech recognition started");
                isRecording = true;
                micButton.classList.add('recording');
                micButton.title = 'Recording... Click to stop';
            };

            speechRecognition.onresult = function(event) {
                let transcript = '';
                for (let i = event.resultIndex; i < event.results.length; i++) {
                    transcript += event.results[i][0].transcript;
                }
                chatInput.value = transcript;
            };

            speechRecognition.onend = function() {
                console.log("Speech recognition ended");
                isRecording = false;
                micButton.classList.remove('recording');
                micButton.title = 'Click to speak';
            };

            speechRecognition.onerror = function(event) {
                console.error("Speech recognition error:", event.error);
                isRecording = false;
                micButton.classList.remove('recording');
                micButton.title = 'Click to speak';
                
                // User-friendly error messages
                let errorMessage = "Speech recognition error: ";
                switch(event.error) {
                    case 'not-allowed':
                        errorMessage += "Microphone permission denied. Please allow microphone access and try again.";
                        break;
                    case 'no-speech':
                        errorMessage += "No speech detected. Please try speaking closer to your microphone.";
                        break;
                    case 'audio-capture':
                        errorMessage += "No microphone found. Please check your microphone connection.";
                        break;
                    case 'network':
                        errorMessage += "Network error. Please check your internet connection.";
                        break;
                    default:
                        errorMessage += event.error;
                }
                console.error(errorMessage);
            };

            // Show microphone button since speech recognition is supported
            micButton.style.display = 'block';
            console.log("Speech recognition initialized successfully");
            return true;

        } catch (error) {
            console.error("Failed to initialize speech recognition:", error);
            micButton.style.display = 'none';
            return false;
        }
    }

    // Microphone button click handler
    micButton.addEventListener('click', function() {
        if (!speechRecognition) {
            console.error("Speech recognition not available");
            return;
        }

        if (isRecording) {
            // Stop recording
            speechRecognition.stop();
        } else {
            // Start recording
            try {
                speechRecognition.start();
            } catch (error) {
                console.error("Failed to start speech recognition:", error);
            }
        }
    });

    // Initialize speech recognition on page load
    initializeSpeechRecognition();

    // Mode switching
    function switchMode(mode) {
        currentMode = mode;
        
        // Update button states
        storywritingBtn.classList.toggle('active', mode === 'storywriting');
        funFactsBtn.classList.toggle('active', mode === 'funfacts');
        
        // Clear chat log
        chatLog.innerHTML = '';
        
        // No automatic theme switching when changing modes
        // Theme is now manually controlled by user
        
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

    // Global scroll indicator element (will be created dynamically)
    let scrollIndicator = null;

    // Check if content overflows the viewport
    function checkContentOverflow() {
        const windowHeight = window.innerHeight;
        const chatLog = document.getElementById('chat-log');
        const inputContainer = document.getElementById('chat-form');
        
        // Use chat log content height instead of entire document
        const chatLogHeight = chatLog ? chatLog.scrollHeight : 0;
        const inputContainerHeight = inputContainer ? inputContainer.offsetHeight : 0;
        
        // Add buffer for anticipated AI response (approximately 200px)
        const contentBuffer = 200;
        const totalContentHeight = chatLogHeight + inputContainerHeight + contentBuffer;
        
        return {
            overflows: totalContentHeight > windowHeight,
            chatLogHeight: chatLogHeight,
            windowHeight: windowHeight,
            inputContainerHeight: inputContainerHeight
        };
    }

    // Check if user is near the bottom of the page
    function isUserNearBottom() {
        const windowHeight = window.innerHeight;
        const documentHeight = document.body.scrollHeight;
        const currentScrollPosition = window.scrollY;
        
        return (currentScrollPosition + windowHeight) >= (documentHeight - 50);
    }

    // Reposition user input to top of viewport (ChatGPT-style)
    function repositionUserInputToTop() {
        requestAnimationFrame(() => {
            const chatLog = document.getElementById('chat-log');
            const userMessages = chatLog.querySelectorAll('.chat-message.user');
            
            if (userMessages.length > 0) {
                const lastUserMessage = userMessages[userMessages.length - 1];
                
                // Scroll to position the user's message at the top
                lastUserMessage.scrollIntoView({ 
                    behavior: 'smooth', 
                    block: 'start'
                });
            }
        });
    }

    // Smart repositioning - only reposition if content would overflow
    function repositionIfNeeded() {
        requestAnimationFrame(() => {
            const overflowCheck = checkContentOverflow();
            
            if (overflowCheck.overflows) {
                // Content will overflow - reposition user input to top
                repositionUserInputToTop();
            }
            // If content fits in viewport, don't reposition - keep natural position
            
            // Always update scroll indicator state
            updateScrollIndicator();
        });
    }

    // Create scroll-to-bottom indicator if it doesn't exist
    function createScrollIndicator() {
        if (!scrollIndicator) {
            scrollIndicator = document.createElement('div');
            scrollIndicator.id = 'scroll-indicator';
            scrollIndicator.className = 'scroll-indicator hidden';
            scrollIndicator.innerHTML = `
                <button class="scroll-to-bottom-btn" aria-label="Scroll to bottom" title="Scroll to bottom">
                    <svg class="scroll-arrow-icon" xmlns="http://www.w3.org/2000/svg" version="1.1" viewBox="-5.0 -10.0 110.0 135.0">
                        <path d="m77.723 55.414c-2.2109-2.2031-5.7852-2.2031-7.9883 0l-14.086 14.086v-52.641c0-3.1172-2.5312-5.6484-5.6484-5.6484s-5.6484 2.5312-5.6484 5.6484v52.637l-14.086-14.086c-2.2109-2.2031-5.7852-2.2031-7.9883 0-2.2109 2.2109-2.2109 5.7852 0 7.9883l23.73 23.73c1.1016 1.1016 2.5469 1.6562 3.9961 1.6562 1.4453 0 2.8945-0.55469 3.9961-1.6562l23.73-23.73c2.2109-2.2109 2.2109-5.7852 0-7.9883z"/>
                    </svg>
                </button>
            `;
            
            // Add click handler for scroll to bottom
            const scrollBtn = scrollIndicator.querySelector('.scroll-to-bottom-btn');
            scrollBtn.addEventListener('click', () => {
                window.scrollTo({
                    top: document.body.scrollHeight,
                    behavior: 'smooth'
                });
            });
            
            // Insert before chat form
            const chatContainer = document.getElementById('chat-container');
            const chatForm = document.getElementById('chat-form');
            chatContainer.insertBefore(scrollIndicator, chatForm);
        }
    }

    // Update scroll indicator visibility
    function updateScrollIndicator() {
        createScrollIndicator();
        
        const overflowCheck = checkContentOverflow();
        const userNearBottom = isUserNearBottom();
        
        // Show indicator if content overflows AND user is not at bottom
        if (overflowCheck.overflows && !userNearBottom) {
            scrollIndicator.classList.remove('hidden');
        } else {
            scrollIndicator.classList.add('hidden');
        }
    }

    // Legacy function for backward compatibility - now uses smart repositioning
    function scrollToBottom() {
        repositionIfNeeded();
    }

    // Split long messages into multiple bubbles
    function splitLongMessage(text) {
        // Split at double line breaks first (natural paragraph breaks)
        const paragraphs = text.split('\n\n');
        const maxLength = 200; // Maximum characters per bubble
        const result = [];
        
        paragraphs.forEach(paragraph => {
            if (paragraph.length <= maxLength) {
                result.push(paragraph);
            } else {
                // Split long paragraphs at sentence boundaries
                const sentences = paragraph.split(/(?<=[.!?])\s+/);
                let currentChunk = '';
                
                sentences.forEach(sentence => {
                    if (currentChunk.length + sentence.length <= maxLength) {
                        currentChunk += (currentChunk ? ' ' : '') + sentence;
                    } else {
                        if (currentChunk) result.push(currentChunk);
                        currentChunk = sentence;
                    }
                });
                
                if (currentChunk) result.push(currentChunk);
            }
        });
        
        return result.filter(chunk => chunk.trim().length > 0);
    }

    // Message handling with smart splitting for long messages
    function appendMessage(sender, text) {
        if (sender === "bot" && text.length > 200) {
            // Split long bot messages into multiple bubbles
            const messageParts = splitLongMessage(text);
            messageParts.forEach((part, index) => {
                setTimeout(() => {
                    appendSingleMessage(sender, part);
                }, index * 800); // 800ms delay between message parts
            });
        } else {
            // Send short messages normally
            appendSingleMessage(sender, text);
        }
    }

    // Single message handling
    function appendSingleMessage(sender, text) {
        const msgWrapper = document.createElement("div");
        msgWrapper.className = sender === "user" ? "chat-message user" : "chat-message bot";

        const avatar = document.createElement("div");
        avatar.className = "chat-avatar";
        if (sender === "user") {
            setupCharacterAvatar(avatar, "boy", currentTheme);
        } else {
            setupCharacterAvatar(avatar, "bear", currentTheme);
        }

        const bubble = document.createElement("div");
        bubble.className = "chat-bubble";
        
        // Replace **word** with colored spans for vocabulary highlighting
        const processedText = text.replace(/\*\*(.*?)\*\*/g, '<span class="vocab-word">$1</span>');
        bubble.innerHTML = processedText;

        msgWrapper.appendChild(avatar);
        msgWrapper.appendChild(bubble);

        chatLog.appendChild(msgWrapper);
        
        // Scroll to bottom after avatar is set up
        scrollToBottom();
    }

    // Create vocabulary question UI
    function appendVocabQuestion(question, options, correctIndex) {
        const vocabContainer = document.createElement("div");
        vocabContainer.className = "vocab-question-container";

        // Question bubble
        const questionWrapper = document.createElement("div");
        questionWrapper.className = "chat-message bot";

        const avatar = document.createElement("div");
        avatar.className = "chat-avatar";
        setupCharacterAvatar(avatar, "bear", currentTheme);

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

        const kidAvatar = document.createElement("div");
        kidAvatar.className = "kid-avatar";
        setupCharacterAvatar(kidAvatar, "boy", currentTheme);

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
        
        // Scroll to bottom after avatars are set up
        scrollToBottom();
    }

    // Handle vocabulary answer
    function handleVocabAnswer(selectedIndex, correctIndex, selectedOption, buttonsContainer, vocabContainer) {
        // Disable all buttons
        Array.from(buttonsContainer.children).forEach(btn => btn.disabled = true);

        // Highlight selected button and maintain its styling
        const selectedButton = buttonsContainer.children[selectedIndex];
        selectedButton.classList.add("selected");

        // Add checkmark to correct answer
        const correctButton = buttonsContainer.children[correctIndex];
        if (selectedIndex === correctIndex) {
            // User selected correct answer - keep purple selected style
            const checkmark = document.createElement("span");
            checkmark.className = "checkmark";
            checkmark.textContent = "✔";
            selectedButton.appendChild(checkmark);
        } else {
            // User selected wrong answer - show correct answer in green
            const checkmark = document.createElement("span");
            checkmark.className = "checkmark";
            checkmark.textContent = "✔";
            correctButton.appendChild(checkmark);
            correctButton.classList.add("correct");
        }

        // Show user's selection
        appendMessage("user", selectedOption);

        // Show feedback
        const feedback = selectedIndex === correctIndex 
            ? "Correct! Great job! 🎉" 
            : `Nice try! The correct answer was ${buttonsContainer.children[correctIndex].textContent}. You'll get it next time! 💪`;
        
        appendMessage("bot", feedback);

        // Keep vocab container visible (don't remove it)
        
        // Apply smart repositioning after vocabulary feedback (same as regular user input)
        repositionIfNeeded();

        // Continue flow automatically after vocabulary answer
        setTimeout(() => {
            if (currentMode === 'funfacts') {
                continueAfterVocab();
            } else if (currentMode === 'storywriting') {
                // Update vocabulary phase tracking
                sessionData.storywriting.vocabularyPhase.questionsAsked++;
                
                // Check if we've reached max vocabulary questions
                if (sessionData.storywriting.vocabularyPhase.questionsAsked >= sessionData.storywriting.vocabularyPhase.maxQuestions) {
                    // Finish vocabulary phase and ask for new story
                    finishVocabularyPhase();
                } else {
                    // Request next vocabulary question
                    requestNextVocabulary();
                }
            }
        }, 2000);
    }


    // Start vocabulary phase after story completion
    async function startVocabularyPhase() {
        try {
            console.log("Starting vocabulary phase...");
            
            // Reset and activate vocabulary phase
            sessionData.storywriting.vocabularyPhase = {
                isActive: true,
                questionsAsked: 0,
                maxQuestions: 3,
                isComplete: false
            };
            
            const response = await fetch("/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ 
                    message: "start_vocabulary", // Explicit vocabulary start signal
                    mode: currentMode,
                    sessionData: sessionData[currentMode]
                })
            });

            const data = await response.json();
            
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
            console.error("Error starting vocabulary phase:", err);
            appendMessage("bot", "Let's move on to some vocabulary questions!");
        }
    }

    // Request next vocabulary question (with count validation)
    async function requestNextVocabulary() {
        try {
            console.log(`Requesting vocabulary question ${sessionData.storywriting.vocabularyPhase.questionsAsked + 1} of ${sessionData.storywriting.vocabularyPhase.maxQuestions}`);
            
            const response = await fetch("/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ 
                    message: "next_vocabulary", // Explicit next vocabulary signal
                    mode: currentMode,
                    sessionData: sessionData[currentMode]
                })
            });

            const data = await response.json();
            
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
            console.error("Error requesting next vocabulary:", err);
            appendMessage("bot", "Let me ask another vocabulary question...");
        }
    }

    // Finish vocabulary phase and ask for new story
    async function finishVocabularyPhase() {
        try {
            console.log("Finishing vocabulary phase, asking for new story...");
            
            // Mark vocabulary phase as complete
            sessionData.storywriting.vocabularyPhase.isComplete = true;
            sessionData.storywriting.vocabularyPhase.isActive = false;
            
            const response = await fetch("/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ 
                    message: "finish_vocabulary", // Explicit vocabulary finish signal
                    mode: currentMode,
                    sessionData: sessionData[currentMode]
                })
            });

            const data = await response.json();
            
            // Handle response (should ask if child wants to write another story)
            if (data.response) {
                appendMessage("bot", data.response);
            }
            
            // Update session data
            if (data.sessionData) {
                sessionData[currentMode] = data.sessionData;
            }

        } catch (err) {
            console.error("Error finishing vocabulary phase:", err);
            appendMessage("bot", "That was great! Would you like to write another story?");
        }
    }

    // Continue fun facts flow after vocabulary question
    async function continueAfterVocab() {
        try {
            // Show thinking message
            appendMessage("bot", "Let me share another cool fact...");

            // Send continue request to backend
            const response = await fetch("/chat", {
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
            
            // Theme switching now happens during "Thinking..." phase to prevent jarring UX
            // No longer handling backend theme suggestions here
            
            // Handle vocabulary questions
            if (data.vocabQuestion) {
                // Only show vocabulary questions when appropriate:
                // - In fun facts mode: always show them
                // - In storywriting mode: only show when story is complete
                const shouldShowVocabQuestion = 
                    currentMode === 'funfacts' || 
                    (currentMode === 'storywriting' && data.sessionData && data.sessionData.isComplete);
                
                console.log(`Vocab question received. Mode: ${currentMode}, Story complete: ${data.sessionData?.isComplete}, Should show: ${shouldShowVocabQuestion}`);
                
                if (shouldShowVocabQuestion) {
                    // Calculate dynamic delay based on content length to ensure content finishes rendering
                    const contentLength = data.response ? data.response.length : 0;
                    const baseDelay = 1000; // Base delay in milliseconds
                    const lengthMultiplier = 5; // Additional delay per character
                    const dynamicDelay = Math.min(baseDelay + (contentLength * lengthMultiplier), 8000); // Cap at 8 seconds
                    
                    console.log(`Scheduling vocabulary question with dynamic delay: ${dynamicDelay}ms (content length: ${contentLength})`);
                    
                    setTimeout(() => {
                        appendVocabQuestion(
                            data.vocabQuestion.question,
                            data.vocabQuestion.options,
                            data.vocabQuestion.correctIndex
                        );
                    }, dynamicDelay);
                } else {
                    console.log("Vocab question suppressed - story not complete yet");
                }
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

        // Check for topic in user message and switch theme smoothly (before backend response)
        // This prevents jarring simultaneous theme change + content scroll
        // ONLY detect topics during initial topic selection, NOT during story contributions
        const shouldDetectTopic = 
            (currentMode === 'funfacts' && !sessionData.funfacts.topic) || // Fun facts mode without topic
            (currentMode === 'storywriting' && !sessionData.storywriting.topic) || // Story mode without topic
            userMessage.toLowerCase().includes('write about') || // Explicit topic change request
            userMessage.toLowerCase().includes('story about'); // Explicit topic change request
            
        if (shouldDetectTopic) {
            const detectedTopic = extractTopicFromMessage(userMessage);
            if (detectedTopic) {
                const suggestedTheme = getThemeSuggestion(detectedTopic);
                if (suggestedTheme !== currentTheme) {
                    console.log(`Client-side topic "${detectedTopic}" detected, smoothly switching to ${suggestedTheme} theme during thinking phase`);
                    smoothThemeTransition(suggestedTheme); // Use smooth transition instead of immediate switch
                }
            }
        } else {
            console.log(`Skipping topic detection - mode: ${currentMode}, has topic: ${currentMode === 'funfacts' ? !!sessionData.funfacts.topic : !!sessionData.storywriting.topic}`);
        }

        try {
            // Send to backend
            const response = await fetch("/chat", {
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
                
                // Auto-trigger vocabulary phase when story is complete
                if (currentMode === 'storywriting' && data.sessionData.isComplete && !data.vocabQuestion) {
                    console.log("Story completed! Auto-starting vocabulary phase...");
                    // Wait a bit for user to read "The end!" then start vocab phase
                    setTimeout(() => {
                        startVocabularyPhase();
                    }, 2000);
                }
            }
            
            // Theme switching now happens during "Thinking..." phase to prevent jarring UX
            // No longer handling backend theme suggestions here
            
            // Handle vocabulary questions
            if (data.vocabQuestion) {
                // Only show vocabulary questions when appropriate:
                // - In fun facts mode: always show them
                // - In storywriting mode: only show when story is complete
                const shouldShowVocabQuestion = 
                    currentMode === 'funfacts' || 
                    (currentMode === 'storywriting' && data.sessionData && data.sessionData.isComplete);
                
                console.log(`Vocab question received. Mode: ${currentMode}, Story complete: ${data.sessionData?.isComplete}, Should show: ${shouldShowVocabQuestion}`);
                
                if (shouldShowVocabQuestion) {
                    // Calculate dynamic delay based on content length to ensure content finishes rendering
                    const contentLength = data.response ? data.response.length : 0;
                    const baseDelay = 1500; // Base delay in milliseconds
                    const lengthMultiplier = 1; // Additional delay per character
                    const dynamicDelay = Math.min(baseDelay + (contentLength * lengthMultiplier), 8000); // Cap at 8 seconds
                    
                    console.log(`Scheduling vocabulary question with dynamic delay: ${dynamicDelay}ms (content length: ${contentLength})`);
                    
                    setTimeout(() => {
                        appendVocabQuestion(
                            data.vocabQuestion.question,
                            data.vocabQuestion.options,
                            data.vocabQuestion.correctIndex
                        );
                    }, dynamicDelay);
                } else {
                    console.log("Vocab question suppressed - story not complete yet");
                }
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

    const body = document.body;

    // Character Avatar System with Individual Images
    function setupCharacterAvatar(avatarElement, characterType, theme) {
        // Use the character config system for easy image swapping
        const characterImage = getCharacterImage(characterType, theme);
        avatarElement.style.backgroundImage = `url('${characterImage}')`;
        
        // Set alt text for accessibility
        avatarElement.setAttribute('role', 'img');
        avatarElement.setAttribute('aria-label', characterType === "bear" ? "Bear Tutor" : "Kid");
    }

    // Unified Theme System
    let currentTheme = 'theme-space'; // Default theme
    let userManuallySelectedTheme = false; // Track if user manually chose a theme

    function switchTheme(themeName, isAutomatic = false, reason = 'manual') {
        // Only switch if it's actually a different theme
        if (currentTheme === themeName) return;
        
        // Smart auto-switching logic
        if (isAutomatic) {
            if (reason === 'topic') {
                // Always allow topic-based theme switching (when user chooses story topics)
                console.log(`Auto-switching to ${themeName} for topic selection - overriding manual preference`);
            } else if (userManuallySelectedTheme && localStorage.getItem('userSelectedTheme')) {
                // Block other automatic switching if user has manual preference
                console.log(`Auto-switch to ${themeName} skipped - user has manual preference (userManuallySelectedTheme: ${userManuallySelectedTheme}, localStorage: ${localStorage.getItem('userSelectedTheme')})`);
                return;
            }
        }
        
        // Remove all existing theme classes
        body.classList.remove('theme-space', 'theme-fantasy', 'theme-sports', 'theme-ocean', 'theme-whimsical', 'theme-fun', 'theme-food', 'theme-animals', 'theme-elegant', 'theme-creative');
        
        // Add new theme class
        body.classList.add(themeName);
        
        // Update theme button states (legacy - for any remaining theme buttons)
        updateThemeButtonStates(themeName);
        
        // Update dropdown active state
        updateActiveThemeOption(themeName);
        
        // Update all existing avatars to match the new theme
        updateAllAvatars(themeName);
        
        currentTheme = themeName;
        
        if (isAutomatic) {
            console.log(`Auto-switched to ${themeName} theme`);
        } else {
            console.log(`Manually switched to ${themeName} theme`);
            userManuallySelectedTheme = true;
            localStorage.setItem('userSelectedTheme', 'true');
            localStorage.setItem('preferredTheme', themeName);
        }
    }

    function updateThemeButtonStates(activeTheme) {
        // Remove active class from all theme buttons (legacy support)
        const themeButtons = document.querySelectorAll('.theme-btn');
        themeButtons.forEach(button => {
            button.classList.remove('active');
        });
        
        // Add active class to the current theme button
        const activeButton = document.querySelector(`.theme-btn[data-theme="${activeTheme}"]`);
        if (activeButton) {
            activeButton.classList.add('active');
        }
    }

    // Update active theme option in dropdown
    function updateActiveThemeOption(activeTheme) {
        // Remove active class from all theme options
        const themeOptions = document.querySelectorAll('.theme-option');
        themeOptions.forEach(option => {
            option.classList.remove('active');
        });
        
        // Add active class to the current theme option
        const activeOption = document.querySelector(`.theme-option[data-theme="${activeTheme}"]`);
        if (activeOption) {
            activeOption.classList.add('active');
        }
    }


    function updateAllAvatars(theme) {
        // Update all chat avatars (bot avatars)
        const chatAvatars = document.querySelectorAll('.chat-avatar');
        chatAvatars.forEach(avatar => {
            // Check if this is a bear avatar by looking at the aria-label or parent context
            const isBearAvatar = avatar.getAttribute('aria-label') === 'Bear Tutor' || 
                                avatar.closest('.chat-message.bot');
            setupCharacterAvatar(avatar, isBearAvatar ? "bear" : "boy", theme);
        });
        
        // Update all kid avatars (in vocab questions)
        const kidAvatars = document.querySelectorAll('.kid-avatar');
        kidAvatars.forEach(avatar => {
            setupCharacterAvatar(avatar, "boy", theme);
        });
    }

    // Random initial theme selection (Space or Ocean)
    function loadInitialTheme() {
        const savedTheme = localStorage.getItem('preferredTheme');
        const userHasPreference = localStorage.getItem('userSelectedTheme') === 'true';
        
        if (savedTheme && userHasPreference) {
            // User has manually selected a theme before, use it
            switchTheme(savedTheme);
            userManuallySelectedTheme = true;
        } else {
            // New user or no preference, randomly select Space or Ocean
            const initialThemes = ['theme-space', 'theme-ocean'];
            const randomTheme = initialThemes[Math.floor(Math.random() * initialThemes.length)];
            switchTheme(randomTheme, true, 'initial'); // Mark as automatic initial load
            console.log(`Welcome! Randomly selected ${randomTheme} as your starting theme`);
        }
    }

    // Subtle opacity cross-fade theme transition function
    function smoothThemeTransition(newTheme) {
        if (newTheme === currentTheme) return;
        
        console.log(`Starting subtle cross-fade transition to ${newTheme}`);
        
        // Add transition class for smooth background changes
        document.body.classList.add('theme-transitioning');
        
        // Add subtle opacity transition
        document.body.style.transition = 'opacity 0.2s ease-out';
        document.body.style.opacity = '0.95';
        
        // Switch theme during subtle fade (200ms delay)
        setTimeout(() => {
            // Switch theme using existing function
            switchTheme(newTheme, true, 'topic');
            
            // Return to full opacity
            document.body.style.opacity = '1';
            
            // Clean up after transition completes
            setTimeout(() => {
                document.body.classList.remove('theme-transitioning');
                document.body.style.transition = '';
                document.body.style.opacity = '';
                console.log(`Subtle cross-fade transition to ${newTheme} completed`);
            }, 200); // Match opacity transition duration
        }, 200); // Wait for subtle fade to complete
    }

    // Handle automatic theme switching based on story topics (can accept topic or full theme name)
    function handleTopicThemeSwitch(topicOrTheme) {
        if (!topicOrTheme) return;
        
        // If it's already a full theme name (theme-*), use it directly
        let suggestedTheme;
        if (topicOrTheme.startsWith('theme-')) {
            suggestedTheme = topicOrTheme;
        } else {
            // Map topic to theme
            const topicThemeMap = {
                'fantasy': 'theme-fantasy',
                'sports': 'theme-sports', 
                'food': 'theme-food',
                'animals': 'theme-animals',
                'ocean': 'theme-ocean',
                'space': 'theme-space',
                'creative': 'theme-creative',
                'mystery': 'theme-elegant',
                'adventure': 'theme-elegant',
                'fun': 'theme-fun',
                'whimsical': 'theme-whimsical',
                'magical': 'theme-whimsical',
                'inventions': 'theme-space' // Default technical topics to space
            };
            
            suggestedTheme = topicThemeMap[topicOrTheme.toLowerCase()] || 'theme-space';
        }
        
        if (suggestedTheme !== currentTheme) {
            console.log(`Topic/Theme "${topicOrTheme}" detected, switching to ${suggestedTheme} theme`);
            switchTheme(suggestedTheme, true, 'topic'); // Mark as automatic topic-based switch
        } else {
            console.log(`Topic/Theme "${topicOrTheme}" suggestion matches current theme ${currentTheme} - no switch needed`);
        }
    }

    // Client-side topic extraction (using centralized configuration)
    function extractTopicFromMessage(message) {
        const messageLower = message.toLowerCase();
        
        // Use loaded theme configuration
        const topicKeywords = themeConfig.topicKeywords;
        
        for (const [topic, keywords] of Object.entries(topicKeywords)) {
            if (keywords.some(keyword => messageLower.includes(keyword))) {
                return topic;
            }
        }
        
        // Default topic extraction - use first word that looks like a topic
        const words = message.split();
        return words[0] || "adventure";
    }

    // Client-side theme suggestion (using centralized configuration)
    function getThemeSuggestion(topic) {
        // Use loaded theme configuration
        const topicToTheme = themeConfig.themeMapping;
        
        return topicToTheme[topic.toLowerCase()] || themeConfig.defaultTheme;
    }

    // Make theme switching available globally
    window.switchTheme = switchTheme;


    // Settings dropdown functionality
    const settingsBtn = document.getElementById('settings-btn');
    const settingsDropdown = document.getElementById('settings-dropdown');
    const themeOptions = document.querySelectorAll('.theme-option');

    // Toggle dropdown
    settingsBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        settingsDropdown.classList.toggle('open');
    });

    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => {
        if (!settingsDropdown.contains(e.target) && !settingsBtn.contains(e.target)) {
            settingsDropdown.classList.remove('open');
        }
    });

    // Close dropdown with ESC key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            settingsDropdown.classList.remove('open');
        }
    });

    // Theme option selection
    themeOptions.forEach(option => {
        option.addEventListener('click', (e) => {
            e.stopPropagation();
            const themeName = option.getAttribute('data-theme');
            
            // Switch theme
            switchTheme(themeName);
            
            // Update active state
            updateActiveThemeOption(themeName);
            
            // Close dropdown
            settingsDropdown.classList.remove('open');
        });
    });


    // Add scroll event listener to update scroll indicator
    window.addEventListener('scroll', () => {
        updateScrollIndicator();
    });

    // Add resize event listener to handle window resizing
    window.addEventListener('resize', () => {
        updateScrollIndicator();
    });

    // Initialize the app
    loadInitialTheme(); // Load initial theme (random Space/Ocean for new users)
    updateActiveThemeOption(currentTheme); // Set initial active state in dropdown
    switchMode('funfacts');
});