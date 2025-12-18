// Chatbot JavaScript

async function sendMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    const chatMessages = document.getElementById('chat-messages');

    if (!message) return;

    // 1. Immediately add YOUR message to the right
    appendMessage('user', message);
    
    // Clear input
    input.value = '';

    // 2. Add a temporary "Thinking..." bubble to the left
    const loadingBubble = appendMessage('bot', 'Thinking...', true);

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: message })
        });
        
        const data = await response.json();

        // 3. Remove "Thinking..." and add real response
        loadingBubble.remove(); 
        appendMessage('bot', data.response);

    } catch (error) {
        loadingBubble.remove();
        appendMessage('bot', 'Error: Could not reach AI.');
        console.error('Error:', error);
    }
}

// Helper function to create the HTML elements
function appendMessage(sender, text, isLoading = false) {
    const chatMessages = document.getElementById('chat-messages');
    
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', sender);
    if (isLoading) messageDiv.classList.add('loading');

    const bubbleDiv = document.createElement('div');
    bubbleDiv.classList.add('bubble');
    bubbleDiv.textContent = text;

    messageDiv.appendChild(bubbleDiv);
    chatMessages.appendChild(messageDiv);

    // Auto-scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;

    return messageDiv; // Return div so we can remove it later if needed
}

// Make sure Enter key works
document.getElementById('chat-input').addEventListener('keypress', function (e) {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

function addMessage(text, sender, isLoading = false) {
    const container = document.getElementById('chatMessages');
    const messageId = 'msg-' + Date.now();
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${sender}`;
    messageDiv.id = messageId;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.textContent = text;
    
    messageDiv.appendChild(contentDiv);
    container.appendChild(messageDiv);
    
    // Scroll to bottom
    container.scrollTop = container.scrollHeight;
    
    return messageId;
}

function removeMessage(messageId) {
    const message = document.getElementById(messageId);
    if (message) {
        message.remove();
    }
}