from chromadb import PersistentClient
from state import AgentState

client = PersistentClient(path="./vectordb")
collection = client.get_or_create_collection("enterprise_ai_os")

def extraction(state: AgentState):
    results = collection.get(
        where={"email": state["email"]},
        include=["documents", "metadatas"]
    )

    metadata = results["metadatas"][0]

    print(metadata["latest_sheets"])
    print(metadata["latest_email"])
    print(metadata["documents_synced"])
    print(metadata["chunks_created"])