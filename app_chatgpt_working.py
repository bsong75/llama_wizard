import gradio as gr
import requests
import json
from datetime import datetime

LLAMA_URL = "http://llama-container:11434/v1/chat/completions"

# Global storage for chat sessions
chat_sessions = {}
current_session_id = None

def generate_session_id():
    return f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

def calculate_chatbot_height(history):
    """Calculate dynamic height based on number of messages"""
    if not history:
        return 150  # Minimum height when empty
    
    # Base height + height per message pair (user + assistant)
    base_height = 150
    height_per_message = 80
    max_height = 600
    
    message_count = len(history)
    calculated_height = base_height + (message_count * height_per_message)
    
    return min(calculated_height, max_height)

def get_session_title(history):
    """Generate a title for the chat session based on first message"""
    if history and len(history) > 0:
        first_message = history[0][0]
        # Truncate to first 40 characters for display
        return first_message[:40] + "..." if len(first_message) > 40 else first_message
    return "New Chat"

def format_timestamp(timestamp):
    """Format timestamp for display"""
    now = datetime.now()
    diff = now - timestamp
    
    if diff.days == 0:
        if diff.seconds < 3600:  # Less than 1 hour
            minutes = diff.seconds // 60
            return f"{minutes}m ago" if minutes > 0 else "Just now"
        else:  # Less than 24 hours
            hours = diff.seconds // 3600
            return f"{hours}h ago"
    elif diff.days == 1:
        return "Yesterday"
    elif diff.days < 7:
        return f"{diff.days}d ago"
    else:
        return timestamp.strftime("%m/%d")

def chat_with_llama(message, history, session_id):
    global chat_sessions, current_session_id
    
    messages = []
    for human_msg, ai_msg in history:
        messages.append({"role": "user", "content": human_msg})
        messages.append({"role": "assistant", "content": ai_msg})
    messages.append({"role": "user", "content": message})
    
    payload = {"messages": messages, 
               "max_tokens": 512,
               "temperature": 0.1, 
               "model": "llama3.2:3b"}
    
    try:
        response = requests.post(LLAMA_URL, json=payload)
        result = response.json()
        bot_response = result.get("choices", [{}])[0].get("message", {}).get("content", "No response")
    except Exception as e:
        bot_response = f"Error connecting to Llama: {str(e)}"
    
    history.append([message, bot_response])
    
    # Update session storage
    if session_id:
        chat_sessions[session_id] = {
            "history": history.copy(),
            "title": get_session_title(history),
            "timestamp": datetime.now()
        }
    
    # Update chat list
    chat_list_html = generate_chat_list_html()
    new_height = calculate_chatbot_height(history)
    
    return history, "", gr.update(value=chat_list_html), gr.update(height=new_height)

def new_chat():
    """Start a new chat session"""
    global current_session_id
    current_session_id = generate_session_id()
    chat_list_html = generate_chat_list_html()
    return [], current_session_id, gr.update(value=chat_list_html), gr.update(height=150)

def generate_chat_list_html():
    """Generate HTML for the chat list in Claude style"""
    if not chat_sessions:
        return "<div class='chat-list-empty'>No conversations yet</div>"
    
    # Sort by timestamp, most recent first
    sorted_sessions = sorted(
        chat_sessions.items(), 
        key=lambda x: x[1]["timestamp"], 
        reverse=True
    )
    
    html_items = []
    for session_id, data in sorted_sessions:
        title = data['title']
        timestamp = format_timestamp(data['timestamp'])
        is_current = session_id == current_session_id
        
        active_class = "active" if is_current else ""
        
        html_items.append(f"""
        <div class="chat-item {active_class}" data-session-id="{session_id}">
            <div class="chat-title">{title}</div>
            <div class="chat-timestamp">{timestamp}</div>
        </div>
        """)
    
    return f'<div class="chat-list">{"".join(html_items)}</div>'

def load_chat_from_click(session_id):
    """Load a chat session when clicked"""
    global current_session_id
    
    if not session_id or session_id not in chat_sessions:
        return [], None, gr.update(height=150), gr.update()
    
    current_session_id = session_id
    history = chat_sessions[session_id]["history"]
    new_height = calculate_chatbot_height(history)
    chat_list_html = generate_chat_list_html()
    
    return history, session_id, gr.update(height=new_height), gr.update(value=chat_list_html)

def toggle_sidebar():
    """Toggle the visibility of the sidebar"""
    return gr.update(visible=True), gr.update(visible=False)

def hide_sidebar():
    """Hide the sidebar"""
    return gr.update(visible=False), gr.update(visible=True)

# Custom CSS for Claude-style interface
custom_css = """
footer {display: none !important}

.sidebar {
    border-right: 1px solid #374151;
    height: 100vh;
    padding: 0;
    min-width: 180px;
    max-width: 180px;
    background-color: rgb(6 16 30);
}

.sidebar-header {
    padding: 16px;
    border-bottom: 1px solid #374151;
    background-color: rgb(6 16 30);
}

.toggle-btn {
    margin: 0 0 16px 0;
    width: 100%;
    height: 36px;
    font-size: 14px;
    font-weight: 500;
    background-color: #374151 !important;
    color: #f9fafb !important;
    border: 1px solid #4b5563 !important;
}

.new-chat-btn {
    width: 100%;
    height: 40px;
    font-size: 14px;
    font-weight: 500;
    background-color: #3b82f6 !important;
    border: none !important;
    color: white !important;
}

.show-sidebar-btn {
    position: fixed;
    top: 20px;
    left: 20px;
    z-index: 1000;
    width: 40px;
    height: 40px;
    min-width: 40px !important;
    padding: 0 !important;
    border-radius: 50%;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    background-color: #374151 !important;
    color: #f9fafb !important;
}

.chat-list {
    padding: 8px 0;
    max-height: calc(100vh - 140px);
    overflow-y: auto;
    background-color: #1f2937;
}

.chat-list-empty {
    padding: 20px 16px;
    text-align: center;
    color: #9ca3af;
    font-size: 14px;
}

.chat-item {
    padding: 12px 16px;
    cursor: pointer;
    border-left: 3px solid transparent;
    transition: all 0.2s ease;
    margin: 2px 0;
    background-color: #1f2937;
}

.chat-item:hover {
    background-color: #374151;
}

.chat-item.active {
    background-color: #1e3a8a;
    border-left-color: #3b82f6;
}

.chat-title {
    font-size: 14px;
    font-weight: 500;
    color: #f9fafb;
    line-height: 1.4;
    margin-bottom: 4px;
    word-wrap: break-word;
}

.chat-timestamp {
    font-size: 12px;
    color: #9ca3af;
}

.main-content {
    flex: 1;
    padding: 0 1rem;
    background-color: transparent;
}

.chat-container {
    max-width: 1200px;
    margin: 0 auto;
}

.dynamic-chatbot {
    transition: height 0.3s ease-in-out;
    border: 1px solid #374151;
    border-radius: 8px;
}

.chatbot-container {
    min-height: 150px;
    max-height: 600px;
}

/* Scrollbar styling for chat list */
.chat-list::-webkit-scrollbar {
    width: 6px;
}

.chat-list::-webkit-scrollbar-track {
    background: transparent;
}

.chat-list::-webkit-scrollbar-thumb {
    background: #4b5563;
    border-radius: 3px;
}

.chat-list::-webkit-scrollbar-thumb:hover {
    background: #6b7280;
}
"""

# JavaScript for handling chat item clicks
chat_click_js = """
function(html_content) {
    // Add click event listeners to chat items
    setTimeout(() => {
        const chatItems = document.querySelectorAll('.chat-item');
        chatItems.forEach(item => {
            item.addEventListener('click', function() {
                const sessionId = this.getAttribute('data-session-id');
                if (sessionId) {
                    // Trigger the load_chat function through a hidden button
                    const hiddenInput = document.querySelector('#hidden-session-input textarea');
                    const hiddenButton = document.querySelector('#hidden-load-button');
                    if (hiddenInput && hiddenButton) {
                        hiddenInput.value = sessionId;
                        hiddenButton.click();
                    }
                }
            });
        });
    }, 100);
    return html_content;
}
"""

with gr.Blocks(title="Llama-Wizard", theme="soft", css=custom_css) as demo:
    # State variables
    session_state = gr.State(value=None)
    
    # Hidden components for chat loading
    hidden_session_input = gr.Textbox(visible=False, elem_id="hidden-session-input")
    hidden_load_button = gr.Button(visible=False, elem_id="hidden-load-button")
    
    # Show sidebar button (when sidebar is hidden)
    show_btn = gr.Button("☰", size="sm", elem_classes="show-sidebar-btn", visible=False)
    
    with gr.Row():
        # Left sidebar
        with gr.Column(scale=1, elem_classes="sidebar") as sidebar:
            with gr.Column(elem_classes="sidebar-header"):
                hide_btn = gr.Button("← Hide Sidebar", size="sm", elem_classes="toggle-btn")
                new_chat_btn = gr.Button("🗨️ New Chat", variant="secondary", size="sm", elem_classes="new-chat-btn")
            
            chat_list_display = gr.HTML(
                value="<div class='chat-list-empty'>No conversations yet</div>",
                elem_classes="chat-list-container"
            )
        
        # Main chat area
        with gr.Column(scale=3, elem_classes="main-content") as main_area:
            with gr.Column(elem_classes="chat-container"):
                gr.Markdown("# 🦙 Llama-Wizard at your service!")
                
                chatbot = gr.Chatbot(
                    label="Chat",
                    height=300,
                    show_copy_button=True,
                    elem_classes="dynamic-chatbot"
                )
                
                msg = gr.Textbox(
                    label=None, 
                    placeholder="Type your question here...",
                    lines=2,
                    interactive=True
                )
                
                with gr.Row():
                    submit_btn = gr.Button("Send", variant="primary")
    
    # Event handlers
    def submit_message(message, history, session_id):
        if not message.strip():
            return history, "", gr.update(), gr.update()
        return chat_with_llama(message, history, session_id)
    
    # Message submission
    msg.submit(
        submit_message,
        inputs=[msg, chatbot, session_state],
        outputs=[chatbot, msg, chat_list_display, chatbot]
    )
    
    submit_btn.click(
        submit_message,
        inputs=[msg, chatbot, session_state],
        outputs=[chatbot, msg, chat_list_display, chatbot]
    )
    
    # New chat button
    new_chat_btn.click(
        new_chat,
        outputs=[chatbot, session_state, chat_list_display, chatbot]
    )
    
    # Hidden button for loading chats (triggered by JavaScript)
    hidden_load_button.click(
        lambda session_id: load_chat_from_click(session_id),
        inputs=[hidden_session_input],
        outputs=[chatbot, session_state, chatbot, chat_list_display]
    )
    
    # Add JavaScript event handling for chat list
    chat_list_display.change(
        None,
        inputs=[chat_list_display],
        outputs=[chat_list_display],
        js=chat_click_js
    )
    
    # Sidebar toggle functionality
    hide_btn.click(
        hide_sidebar,
        outputs=[sidebar, show_btn]
    )
    
    show_btn.click(
        toggle_sidebar,
        outputs=[sidebar, show_btn]
    )
    
    # Initialize with a new chat session
    demo.load(
        new_chat,
        outputs=[chatbot, session_state, chat_list_display, chatbot]
    )

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0", 
        server_port=7860,
        show_api=False
    )