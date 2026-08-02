from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver
from state import AgentState
from nodes import startup_node, welcome_node, sync_everything_node
from Tools.db_data.extraction import extraction
# Create checkpointer
checkpointer = InMemorySaver()

# 1. Initialize State Graph
builder = StateGraph(AgentState)

# 2. Add Nodes
builder.add_node("startup", startup_node)
builder.add_node("welcome", welcome_node)
builder.add_node("sync", sync_everything_node)
builder.add_node("extraction",extraction)

# 3. Set Entry Point
builder.set_entry_point("startup")

# 4. Connect Workflow Edges
builder.add_edge("startup", "welcome")
builder.add_edge("welcome", "sync")
builder.add_edge("sync", "extraction")
builder.add_edge("extraction",END)

# 5. Compile Graph with Checkpointer
graph = builder.compile(checkpointer=checkpointer)