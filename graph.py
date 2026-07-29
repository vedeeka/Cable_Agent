from langgraph.graph import StateGraph, END
from state import AgentState
from nodes import startup_node, welcome_node, sync_everything_node

# 1. Initialize State Graph
builder = StateGraph(AgentState)

# 2. Add Nodes
builder.add_node("startup", startup_node)
builder.add_node("welcome", welcome_node)
builder.add_node("sync", sync_everything_node)

# 3. Set Entry Point
builder.set_entry_point("startup")

# 4. Connect Workflow Edges (startup -> welcome -> sync -> END)
builder.add_edge("startup", "welcome")
builder.add_edge("welcome", "sync")       # <--- Route to sync node
builder.add_edge("sync", END)             # <--- End workflow after sync

# 5. Compile Graph
graph = builder.compile()