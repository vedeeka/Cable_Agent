from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver

from state import AgentState
from nodes import startup_node, welcome_node, sync_everything_node

checkpointer = InMemorySaver()

builder = StateGraph(AgentState)

builder.add_node("startup", startup_node)
builder.add_node("welcome", welcome_node)
builder.add_node("sync", sync_everything_node)

builder.set_entry_point("startup")

builder.add_edge("startup", "welcome")
builder.add_edge("welcome", "sync")
builder.add_edge("sync", END)

graph = builder.compile(checkpointer=checkpointer)