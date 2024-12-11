from langchain.llms import Ollama

ollama_client = Ollama(base_url="http://localhost:11434")
CREATIVE_MODEL = "llama2"
CREATIVE_SYSTEM_PROMPT = "You are a creative writing assistant." 