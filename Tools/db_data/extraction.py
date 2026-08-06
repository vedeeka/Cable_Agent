from chromadb import PersistentClient
from state import AgentState
from datetime import datetime


client = PersistentClient(path="./vectordb")

collection = client.get_or_create_collection(
    "enterprise_ai_os"
)


def extraction(state: AgentState):

    print("========== EXTRACTION ==========")

    email = state["email"]

    print("User:", email)


    # Today's date
    today = datetime.now().strftime("%Y-%m-%d")


    # Fetch user's latest data
    results = collection.get(
        where={
            "email": email
        },
        include=[
            "documents",
            "metadatas"
        ]
    )


    if not results["metadatas"]:

        return {
            "latest_email": "NA",
            "latest_calendar": "NA",
            "latest_drive": "NA",
            "latest_sheets": "NA",

            "documents_synced": 0,
            "chunks_created": 0,

            "documents": []
        }



    documents = []
    metadata_list = results["metadatas"]



    # -----------------------------
    # Find latest metadata
    # -----------------------------

    latest_index = max(
        range(len(metadata_list)),
        key=lambda i:
        metadata_list[i].get(
            "timestamp",
            ""
        )
    )


    latest_metadata = metadata_list[latest_index]



    # -----------------------------
    # Pick only today's documents
    # -----------------------------

    for i, metadata in enumerate(metadata_list):

        doc_date = metadata.get(
            "timestamp",
            ""
        )


        if doc_date == today:

            documents.append(
                results["documents"][i]
            )



    # If nothing from today,
    # take latest 10 documents

    if not documents:

        docs_with_time = list(
            zip(
                results["documents"],
                metadata_list
            )
        )


        docs_with_time.sort(
            key=lambda x:
            x[1].get(
                "timestamp",
                ""
            ),
            reverse=True
        )


        documents = [
            item[0]
            for item in docs_with_time[:10]
        ]



    context = {

        "latest_email":
            latest_metadata.get(
                "latest_email",
                "NA"
            ),


        "latest_calendar":
            latest_metadata.get(
                "latest_calendar",
                "NA"
            ),


        "latest_drive":
            latest_metadata.get(
                "latest_drive",
                "NA"
            ),


        "latest_sheets":
            latest_metadata.get(
                "latest_sheets",
                "NA"
            ),


        "documents_synced":
            latest_metadata.get(
                "documents_synced",
                0
            ),


        "chunks_created":
            latest_metadata.get(
                "chunks_created",
                0
            ),


        # Only selected docs
        "documents": documents
    }



    print("========== SELECTED DOCUMENTS ==========")

    for doc in documents:
        print(doc[:200])
        print("--------------------")


    return context