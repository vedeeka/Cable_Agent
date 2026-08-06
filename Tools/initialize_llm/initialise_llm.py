from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv
import os
# Load environment variables
load_dotenv()


def initialise_llm(system_prompt):
    model = init_chat_model(
        "gemini-3-flash-preview",
        model_provider="google_genai",
        api_key=os.getenv("YOUR_GOOGLE_API_KEY"),
        temperature=0.5,
        timeout=600,
        max_tokens=25000,
        streaming=True,
    )

    response = model.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content="Please answer based on the provided context.")
    ])

    return response