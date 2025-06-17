import gradio as gr
import requests
import json

LLAMA_URL = "http://llama-container:11434/v1/chat/completions"


def chat_with_llama(message, history):
    messages = []
    for human_msg, ai_msg in history:
        messages.append({"role": "user", "content": human_msg})
        messages.append({"role": "assistant", "content": ai_msg})
    messages.append({"role": "user", "content": message})
    
    payload = {"messages": messages, 
               "max_tokens": 512, #512
               "temperature": 0.1, 
               "model": "llama3.2:3b"}
    response = requests.post(LLAMA_URL, json=payload)
    result = response.json()
    bot_response = result.get("choices", [{}])[0].get("message", {}).get("content", "No response")
    
    history.append([message, bot_response])
    return history, ""

with gr.Blocks(title="Kusco", theme="soft", css="footer {display: none ! important}") as demo:
    chatbot = gr.Chatbot(label="Chat History",
                         height=500)
    gr.Markdown("# Kusco at your service!")
    msg = gr.Textbox(label="How many I serve you?", 
                     placeholder="Type your question here."
                     )
    
    msg.submit(chat_with_llama, [msg, chatbot], [chatbot, msg])

demo.launch(server_name="0.0.0.0", 
            server_port=7860,
            show_api=False)