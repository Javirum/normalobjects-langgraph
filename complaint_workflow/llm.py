import os
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model=os.environ.get("OPENAI_MODEL", "gpt-4o"),
    temperature=0,
)
