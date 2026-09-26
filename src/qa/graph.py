from typing import Literal

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import END, START, MessagesState, StateGraph

from .titlesummary import TitleSummarizer


class QAState(MessagesState):
    needs_title: bool
    title: str


def build_qa_graph(
    model: BaseChatModel,
    title_summarizer: TitleSummarizer,
):
    def answer(state: QAState):
        return {"messages": [model.invoke(state["messages"])]}

    def route_after_answer(state: QAState) -> Literal["title", "__end__"]:
        return "title" if state.get("needs_title") else END

    def title(state: QAState):
        history = [
            {"role": message.type, "content": message.content}
            for message in state["messages"]
            if message.type in {"human", "ai"}
        ]
        return {"title": title_summarizer.summarize(history)}

    builder = StateGraph(QAState)
    builder.add_node("answer", answer)
    builder.add_node("title", title)
    builder.add_edge(START, "answer")
    builder.add_conditional_edges("answer", route_after_answer)
    builder.add_edge("title", END)
    return builder.compile()
