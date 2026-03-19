"""Prompt templates for LLM interactions."""

TEXT_TABLE_SUMMARIZATION_PROMPT: str = """
You are an assistant tasked with summarizing tables and text for use as a search index.
Give a concise summary (under 200 words) that preserves all key entities, names, numbers, dates, and technical terms.
The summary should be findable by someone searching for any specific fact in the original.

Do not include any thinking, reasoning process, or chain-of-thought.
Do not start your message by saying "Here is a summary" or anything like that.
Respond only with the final summary.

Table or text chunk: {element}

"""

IMAGE_SUMMARIZATION_PROMPT: str = """Describe this image in detail. Include all visible text, labels, data values, and structural elements.
If it is a chart or graph, describe the axes, trends, and key data points.
If it is a diagram, describe the components and their relationships.
Do not include any thinking or reasoning process. Output only the description."""
