import os
import json
import streamlit as st
from dotenv import load_dotenv
from groq import Groq
from duckduckgo_search import DDGS
from streamlit_mic_recorder import mic_recorder
from gtts import gTTS
import base64

# 🚀 Environment Setup
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key)

HISTORY_FILE = "chat_history.json"
# 🏎️ Super Fast aur low token consuming model lagaya taake Rate Limit na aaye
MODEL_NAME = "llama-3.1-8b-instant"

# 🔄 History load karne ka function
def load_chat_memory():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return [
        {
            "role": "system",
            "content": (
                "Aapka naam LIA hai. Aap ek nihayat samajhdar aur friendly AI assistant hain. "
                "Aap Mateen bhai ke har sawaal ka jawab Roman Urdu ya Hindi mein bohot hi tameez aur gehrayi ke sath denge. "
                "CRITICAL RULE: Jab bhi user mausam, temperature, news, ya kisi live facts ke baare mein pooche, "
                "to aapne LAZMI 'search_internet' tool chalana hai. Apni taraf se andaza nahi lagana."
            )
        }
    ]

def save_chat_memory(memory):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(memory, f, indent=4, ensure_ascii=False)
    except:
        pass

# 🌐 Super Fast Internet Search
def search_internet(query):
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=2)) # Sirf top 2 taake tokens bach skein
            if results:
                search_text = ""
                for r in results:
                    search_text += f"Source: {r.get('title', '')}\nInfo: {r.get('body', '')}\n\n"
                return search_text
    except:
        pass
    return "Internet par taza maloomat nahi mili."

tools = [
    {
        "type": "function",
        "function": {
            "name": "search_internet",
            "description": "Use this tool ONLY for live data, weather, temperature, news, or factual info.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query."}
                },
                "required": ["query"]
            }
        }
    }
]

# 🔊 Text to Audio Player Function
def play_audio(text):
    try:
        tts = gTTS(text=text, lang='hi', slow=False)
        tts.save("reply.mp3")
        with open("reply.mp3", "rb") as f:
            audio_bytes = f.read()
        audio_base64 = base64.b64encode(audio_bytes).decode()
        audio_html = f'<audio src="data:audio/mp3;base64,{audio_base64}" autoplay="true" />'
        st.markdown(audio_html, unsafe_allow_html=True)
        os.remove("reply.mp3")
    except:
        pass

# 🎨 Streamlit UI
st.set_page_config(page_title="LIA AI Assistant", page_icon="🤖", layout="centered")
st.title("🤖 LIA AI Assistant")
st.caption("Advanced Brain + Live Search + Voice Reply 🔊")

if "messages" not in st.session_state:
    raw_memory = load_chat_memory()
    st.session_state.messages = [m for m in raw_memory if m["role"] != "system"]
    st.session_state.full_history = raw_memory
else:
    st.session_state.full_history = load_chat_memory()

# 💬 Chat Display
for message in st.session_state.messages:
    if message.get("role") in ["user", "assistant"] and message.get("content"):
        with st.chat_message(message.get("role")):
            st.markdown(message.get("content"))

# --- 🎤 VOICE INPUT SECTION ---
st.write("---")
st.write("🎤 **Bol kar sawaal poochein:**")

# State variables to handle audio click bug
if "last_audio" not in st.session_state:
    st.session_state.last_audio = None

audio_input = mic_recorder(start_prompt="🔴 Recording Shuru", stop_prompt="⏹️ Bhejein", key='recorder')

user_input = None

# Audio Process with safety check
if audio_input and audio_input != st.session_state.last_audio:
    st.session_state.last_audio = audio_input
    with st.spinner("🎙️ Aapki awaaz ko suna ja raha hai..."):
        try:
            with open("user_voice.wav", "wb") as f:
                f.write(audio_input['bytes'])
            
            with open("user_voice.wav", "rb") as audio_file:
                transcription = client.audio.transcriptions.create(
                    model="whisper-large-v3", 
                    file=audio_file,
                    language="ur"
                )
            if transcription.text.strip():
                user_input = transcription.text
            os.remove("user_voice.wav")
        except:
            pass

# --- 📥 TEXT INPUT SECTION ---
text_input = st.chat_input("Ya yahan type kijiye...")
if text_input:
    user_input = text_input

# --- 🧠 PROCESSING RESPONSE ---
if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)
        
    st.session_state.full_history.append({"role": "user", "content": user_input})
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=st.session_state.full_history,
                tools=tools,
                tool_choice="auto",
                temperature=0.1,
            )
            response_message = response.choices[0].message
            
            if response_message.tool_calls:
                message_placeholder.markdown("🔍 *LIA internet par check kar rahi hai...*")
                
                st.session_state.full_history.append({
                    "role": "assistant",
                    "content": response_message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                        } for tc in response_message.tool_calls
                    ]
                })
                
                for tool_call in response_message.tool_calls:
                    if tool_call.function.name == "search_internet":
                        tool_args = json.loads(tool_call.function.arguments)
                        search_result = search_internet(tool_args.get("query"))
                        
                        st.session_state.full_history.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": "search_internet",
                            "content": search_result
                        })
                
                stream = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=st.session_state.full_history,
                    temperature=0.2,
                    stream=True,
                )
            else:
                stream = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=st.session_state.full_history,
                    temperature=0.5,
                    stream=True,
                )
            
            lia_reply = ""
            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    lia_reply += content
                    message_placeholder.markdown(lia_reply + "▌")
                    
            message_placeholder.markdown(lia_reply)
            
            # 🔊 Voice Out
            play_audio(lia_reply)
            
            # Save History
            clean_history = load_chat_memory()
            clean_history.append({"role": "user", "content": user_input})
            clean_history.append({"role": "assistant", "content": lia_reply})
            save_chat_memory(clean_history)
            
            st.session_state.messages.append({"role": "assistant", "content": lia_reply})
            st.rerun() # Page refresh to clear audio states
            
        except Exception as e:
            message_placeholder.markdown(f"Maaf kijiyega, koi masla hai. (Error: {e})")