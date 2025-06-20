document.addEventListener("DOMContentLoaded", function () {
    const chatForm = document.getElementById("chat-form");
    const chatInput = document.getElementById("chat-input");
    const chatLog = document.getElementById("chat-log");

    function appendMessage(sender, text) {
        const msgDiv = document.createElement("div");
        msgDiv.className = sender === "user" ? "user-message" : "bot-message";
        msgDiv.textContent = text;
        chatLog.appendChild(msgDiv);
        chatLog.scrollTop = chatLog.scrollHeight;
    }

    chatForm.addEventListener("submit", async function (e) {
        e.preventDefault();
        const userMessage = chatInput.value.trim();
        if (!userMessage) return;

        appendMessage("user", userMessage);
        chatInput.value = "";
        appendMessage("bot", "Thinking...");

        try {
            const response = await fetch("http://localhost:8000/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ message: userMessage })
            });
            const data = await response.json();
            // Remove the "Thinking..." message
            chatLog.removeChild(chatLog.lastChild);
            appendMessage("bot", data.response);
        } catch (err) {
            chatLog.removeChild(chatLog.lastChild);
            appendMessage("bot", "Sorry, there was an error connecting to the server.");
        }
    });
});
