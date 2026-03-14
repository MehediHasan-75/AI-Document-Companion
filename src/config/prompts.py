"""Prompt templates for LLM interactions."""

TEXT_TABLE_SUMMARIZATION_PROMPT: str = """
You are an assistant tasked with summarizing tables and text.
Give a concise summary of the table or text.

Respond only with the summary, no additionnal comment.
Do not start your message by saying "Here is a summary" or anything like that.
Just give the summary as it is.

Table or text chunk: {element}

"""

IMAGE_SUMMARIZATION_PROMPT: str = """Describe the image in detail. For context,
the image is part of a research paper explaining the transformers
architecture. Be specific about graphs, such as bar plots."""

RAG_PROMPT_TEMPLATE: str = """
Answer the question based only on the following context, which can include text, tables, and the below image.
Context: {context}
Question: {question}
"""
