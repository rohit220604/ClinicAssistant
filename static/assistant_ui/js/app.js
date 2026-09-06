/* Clinic Assistant - Minimal JavaScript for UI interactions */

(function () {
    'use strict';

    // Auto-scroll chat messages to the bottom
    function scrollChatToBottom() {
        const container = document.getElementById('chat-messages');
        if (container) {
            container.scrollTop = container.scrollHeight;
        }
    }

    // Clear chat input after sending
    function clearChatInput() {
        const input = document.getElementById('chat-message');
        if (input) {
            input.value = '';
            input.focus();
        }
    }

    // Initialize on DOM ready
    document.addEventListener('DOMContentLoaded', function () {
        scrollChatToBottom();

        const chatForm = document.getElementById('chat-form');
        if (chatForm) {
            chatForm.addEventListener('submit', function () {
                // Small delay to let the page render before scrolling
                setTimeout(scrollChatToBottom, 50);
            });
        }
    });
})();