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

def get_session_title(history):
    """Generate a title for the chat session based on first message"""
    if history and len(history) > 0:
        first_message = history[0][0]
        # Truncate to first 30 characters for display
        return first_message[:30] + "..." if len(first_message) > 30 else first_message
    return "New Chat"

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
    
    # Update chat list and return current session title as selected
    chat_list = update_chat_list()
    current_selection = get_session_title(history) if session_id else None
    
    return history, "", gr.update(choices=chat_list, value=current_selection)

def new_chat():
    """Start a new chat session"""
    global current_session_id
    current_session_id = generate_session_id()
    chat_list = update_chat_list()
    return [], current_session_id, gr.update(choices=chat_list, value=None)

def update_chat_list():
    """Return list of chat sessions for the dropdown"""
    if not chat_sessions:
        return []
    
    # Sort by timestamp, most recent first
    sorted_sessions = sorted(
        chat_sessions.items(), 
        key=lambda x: x[1]["timestamp"], 
        reverse=True
    )
    
    # Return only the titles, not the session IDs
    return [data['title'] for session_id, data in sorted_sessions]

def load_chat_session(selected_chat, current_session):
    """Load a selected chat session"""
    global current_session_id
    
    if not selected_chat or selected_chat == "":
        return [], current_session
    
    try:
        # Find the session by matching the title
        for session_id, data in chat_sessions.items():
            if data['title'] == selected_chat:
                current_session_id = session_id
                history = data["history"]
                return history, session_id
    except Exception as e:
        print(f"Error loading chat session: {e}")
    
    return [], current_session

def toggle_sidebar():
    """Toggle the visibility of the sidebar"""
    return gr.update(visible=True), gr.update(visible=False)

def hide_sidebar():
    """Hide the sidebar"""
    return gr.update(visible=False), gr.update(visible=True)

# Custom CSS for better styling
custom_css = """
footer {display: none !important}
.sidebar {
    border-right: 1px solid #e5e5e5;
    height: 100vh;
    padding: 1rem;
    min-width: 300px;
    max-width: 300px;
}
.chat-list {
    max-height: 400px;
    overflow-y: auto;
}
.toggle-btn {
    margin: 0 auto 15px auto;
    width: 30px;
    height: 30px;
    min-width: 30px !important;
    padding: 0 !important;
    display: block;
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
}
.main-content {
    flex: 1;
    padding: 0 1rem;
}
.chat-container {
    max-width: 1200px;
    margin: 0 auto;
}
"""

with gr.Blocks(title="Kusco", theme="soft", css=custom_css) as demo:
    # State variables
    session_state = gr.State(value=None)
    
    # Show sidebar button (when sidebar is hidden)
    show_btn = gr.Button("☰", size="sm", elem_classes="show-sidebar-btn", visible=False)
    
    with gr.Row():
        # Left sidebar
        with gr.Column(scale=1, elem_classes="sidebar") as sidebar:
            hide_btn = gr.Button("←", size="sm", elem_classes="toggle-btn")
            
            new_chat_btn = gr.Button("🗨️ New Chat", variant="primary", size="lg")
            
            chat_dropdown = gr.Dropdown(
                choices=[],
                interactive=True,
                elem_classes="chat-list",
                show_label=False
            )
        
        # Main chat area
        with gr.Column(scale=3, elem_classes="main-content") as main_area:
            with gr.Column(elem_classes="chat-container"):
                gr.Markdown("# 🦙 Kusco at your service!")
                
                chatbot = gr.Chatbot(
                    label="Chat History",
                    height=500,
                    show_copy_button=True
                )
                
                msg = gr.Textbox(
                    label="How may I serve you?", 
                    placeholder="Type your question here...",
                    lines=2
                )
                
                with gr.Row():
                    submit_btn = gr.Button("Send", variant="primary")
                    clear_btn = gr.Button("Clear", variant="secondary")
    
    # Event handlers
    def submit_message(message, history, session_id):
        if not message.strip():
            return history, "", update_chat_list()
        return chat_with_llama(message, history, session_id)
    
    # Message submission
    msg.submit(
        submit_message,
        inputs=[msg, chatbot, session_state],
        outputs=[chatbot, msg, chat_dropdown]
    )
    
    submit_btn.click(
        submit_message,
        inputs=[msg, chatbot, session_state],
        outputs=[chatbot, msg, chat_dropdown]
    )
    
    # New chat button
    new_chat_btn.click(
        new_chat,
        outputs=[chatbot, session_state, chat_dropdown]
    )
    
    # Load chat session
    chat_dropdown.change(
        load_chat_session,
        inputs=[chat_dropdown, session_state],
        outputs=[chatbot, session_state]
    )
    
    # Clear current chat
    clear_btn.click(
        lambda: ([], ""),
        outputs=[chatbot, msg]
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
        outputs=[chatbot, session_state, chat_dropdown]
    )

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0", 
        server_port=7860,
        show_api=False
    )