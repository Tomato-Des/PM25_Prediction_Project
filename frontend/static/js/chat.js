// Chatbot JavaScript

async function sendMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();
    
    if (!message) return;
    
    // Add user message to chat
    addMessage(message, 'user');
    input.value = '';
    
    // Show loading message
    const loadingId = addMessage('Thinking...', 'bot', true);
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message: message })
        });
        
        const data = await response.json();
        
        // Remove loading message
        removeMessage(loadingId);
        
        // Add bot response
        if (data.response) {
            addMessage(data.response, 'bot');
        } else if (data.error) {
            addMessage('Sorry, I encountered an error. Please try again.', 'bot');
        }
        
    } catch (error) {
        console.error('Chat error:', error);
        removeMessage(loadingId);
        addMessage('Sorry, I couldn\'t connect to the server. Please try again later.', 'bot');
    }
}

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