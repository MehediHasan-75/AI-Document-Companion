"""
LLM Service for Document Summarization and RAG Chain Generation.

This module provides LLM-powered chains for:
- Text and table summarization using Deepseek (via Ollama)
- Image summarization using Llava (via Ollama)
- RAG (Retrieval-Augmented Generation) chain construction

The service is designed for multi-modal document processing, supporting
text, tables, and images in a unified pipeline.

Architecture:
    - Uses Ollama as the local LLM inference server
    - Deepseek model for text/table summarization and RAG
    - Llava model for vision/image understanding

Integration Points:
    - REDIS_INTEGRATION: Cache LLM responses for repeated queries
    - WEBSOCKET_INTEGRATION: Stream LLM responses in real-time
    - MQ_INTEGRATION: Queue long-running summarization tasks

Configuration:
    - OLLAMA_BASE_URL: Base URL for Ollama server (default: http://localhost:11434)
    - TEXT_MODEL: Model for text processing (default: deepseek-r1:8b)
    - VISION_MODEL: Model for image processing (default: llava)

Example:
    >>> from src.services.llm_service import get_rag_chain, get_text_table_summarizer
    >>> summarizer = get_text_table_summarizer()
    >>> summary = summarizer.invoke("Long document text...")
"""

from __future__ import annotations

import logging
from base64 import b64decode
from typing import Any, Dict, List, Tuple, Union

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_ollama import ChatOllama

# Commented imports preserved for future provider flexibility
# from langchain_groq import ChatGroq
# from langchain_openai import ChatOpenAI


# =============================================================================
# Module Configuration
# =============================================================================

logger = logging.getLogger(__name__)

# LLM Configuration Constants
# NOTE: Consider moving to environment variables or config file for production
OLLAMA_BASE_URL: str = "http://localhost:11434"
TEXT_MODEL: str = "deepseek-r1:8b"
VISION_MODEL: str = "llava"
SUMMARIZATION_TEMPERATURE: float = 0.5
VISION_TEMPERATURE: float = 0.7


# =============================================================================
# Integration Placeholders (Future-Ready)
# =============================================================================

# REDIS_INTEGRATION: Cache LLM responses
# Example:
#   def get_cached_summary(content_hash: str) -> Optional[str]:
#       """Retrieve cached summary from Redis."""
#       return redis_client.get(f"summary:{content_hash}")
#
#   def cache_summary(content_hash: str, summary: str, ttl: int = 86400) -> None:
#       """Cache summary with 24-hour TTL."""
#       redis_client.setex(f"summary:{content_hash}", ttl, summary)

# WEBSOCKET_INTEGRATION: Stream LLM responses
# Example:
#   async def stream_llm_response(chain, input_data, websocket):
#       """Stream LLM response tokens via WebSocket."""
#       async for token in chain.astream(input_data):
#           await websocket.send_json({"type": "token", "content": token})

# MQ_INTEGRATION: Queue summarization tasks
# Example:
#   async def enqueue_summarization(content: str, content_type: str) -> str:
#       """Queue summarization task for async processing."""
#       return await message_queue.publish("summarization_queue", {
#           "content": content, "type": content_type
#       })


# =============================================================================
# Prompt Templates
# =============================================================================

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


# =============================================================================
# Text and Table Summarization
# =============================================================================

def get_text_table_summarizer() -> Any:
    """
    Create and return a chain for summarizing text and tables using Deepseek.
    
    This function constructs a LangChain pipeline that takes text or table
    content and produces a concise summary using the Deepseek LLM model.
    
    Returns:
        A LangChain runnable chain that accepts text/table content and
        returns a summary string.
    
    Integration Points:
        - REDIS_INTEGRATION: Cache summaries by content hash
        - MQ_INTEGRATION: Queue large batch summarizations
    
    Example:
        >>> summarizer = get_text_table_summarizer()
        >>> summary = summarizer.invoke("This is a long document about AI...")
        >>> print(summary)
    
    Note:
        Uses Ollama's Deepseek model locally. Ensure Ollama server is running
        at OLLAMA_BASE_URL with the deepseek-r1:8b model pulled.
    """
    logger.debug("Creating text/table summarizer chain")
    
    prompt = ChatPromptTemplate.from_template(TEXT_TABLE_SUMMARIZATION_PROMPT)
    
    model = ChatOllama(
        model=TEXT_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=SUMMARIZATION_TEMPERATURE
    )
    
    # Chain: input -> prompt formatting -> LLM -> string output
    summarize_chain = {"element": lambda x: x} | prompt | model | StrOutputParser()
    
    return summarize_chain


# =============================================================================
# Image Summarization
# =============================================================================

def get_image_summarizer() -> Any:
    """
    Create and return a chain for summarizing images using Llava.
    
    This function constructs a LangChain pipeline that takes a base64-encoded
    image and produces a detailed description using the Llava vision model.
    
    Returns:
        A LangChain runnable chain that accepts base64-encoded image data
        and returns a description string.
    
    Integration Points:
        - REDIS_INTEGRATION: Cache image descriptions by image hash
        - MQ_INTEGRATION: Queue batch image processing
    
    Example:
        >>> import base64
        >>> with open("image.jpg", "rb") as f:
        ...     img_b64 = base64.b64encode(f.read()).decode()
        >>> summarizer = get_image_summarizer()
        >>> description = summarizer.invoke(img_b64)
    
    Note:
        Uses Ollama's Llava model for vision tasks. Ensure the llava model
        is available on your Ollama server.
    """
    logger.debug("Creating image summarizer chain")
    
    messages = [
        (
            "user",
            [
                {"type": "text", "text": IMAGE_SUMMARIZATION_PROMPT},
                {
                    "type": "image_url",
                    "image_url": {"url": "data:image/jpeg;base64,{image}"},
                },
            ],
        )
    ]

    prompt = ChatPromptTemplate.from_messages(messages)
    
    chain = (
        prompt
        | ChatOllama(model=VISION_MODEL, base_url=OLLAMA_BASE_URL, temperature=VISION_TEMPERATURE)
        | StrOutputParser()
    )
    
    return chain


# =============================================================================
# Document Parsing Utilities
# =============================================================================

def parse_docs(docs: List[Any]) -> Dict[str, List[Any]]:
    """
    Split retrieved documents into base64-encoded images and text documents.
    
    This utility function categorizes documents based on whether they are
    base64-encoded images or text content, enabling separate processing
    in the RAG pipeline.
    
    Args:
        docs: List of documents from the retriever. Can contain Document
            objects or base64-encoded image strings.
    
    Returns:
        Dictionary with two keys:
            - "images": List of base64-encoded image strings
            - "texts": List of text Document objects
    
    Example:
        >>> docs = [Document(page_content="text"), "base64string=="]
        >>> result = parse_docs(docs)
        >>> print(result["texts"])  # [Document(...)]
        >>> print(result["images"])  # ["base64string=="]
    """
    b64_images: List[str] = []
    text_docs: List[Any] = []
    
    for doc in docs:
        try:
            # Attempt to decode as base64 - if successful, it's an image
            b64decode(doc)
            b64_images.append(doc)
        except Exception:
            # Not valid base64, treat as text document
            text_docs.append(doc)
    
    return {"images": b64_images, "texts": text_docs}


def build_prompt(kwargs: Dict[str, Any]) -> ChatPromptTemplate:
    """
    Build a multi-modal prompt from context documents and user question.
    
    Constructs a ChatPromptTemplate that includes text context and optionally
    base64-encoded images for multi-modal RAG queries.
    
    Args:
        kwargs: Dictionary containing:
            - context: Dict with "texts" and "images" lists (from parse_docs)
            - question: The user's question string
    
    Returns:
        ChatPromptTemplate ready for LLM invocation with text and image content.
    
    Note:
        Images are embedded as data URIs in the prompt for vision-capable models.
        Text content is extracted from Document objects using page_content attribute.
    """
    docs_by_type = kwargs["context"]
    user_question = kwargs["question"]

    # Concatenate all text content from Document objects
    context_text = ""
    if len(docs_by_type["texts"]) > 0:
        for text_element in docs_by_type["texts"]:
            # Use page_content here as Document objects are passed
            context_text += text_element.page_content

    # Construct prompt with context (including images)
    prompt_template = f"""
    Answer the question based only on the following context, which can include text, tables, and the below image.
    Context: {context_text}
    Question: {user_question}
    """

    prompt_content: List[Dict[str, Any]] = [{"type": "text", "text": prompt_template}]

    # Append base64 images as image_url content
    if len(docs_by_type["images"]) > 0:
        for image in docs_by_type["images"]:
            prompt_content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image}"},
                }
            )

    return ChatPromptTemplate.from_messages(
        [
            HumanMessage(content=prompt_content),
        ]
    )


# =============================================================================
# RAG Chain Construction
# =============================================================================

def get_rag_chain(retriever: Any) -> Tuple[Any, Any]:
    """
    Construct and return RAG chains for question answering.
    
    Creates two variants of the RAG pipeline:
    1. Standard chain: Returns only the answer
    2. Chain with sources: Returns answer along with source context
    
    Args:
        retriever: A LangChain retriever instance configured to search
            the vector store for relevant documents.
    
    Returns:
        Tuple containing:
            - chain: Standard RAG chain (question -> answer)
            - chain_with_sources: RAG chain that includes source context
    
    Integration Points:
        - REDIS_INTEGRATION: Cache responses by question hash
        - WEBSOCKET_INTEGRATION: Stream response tokens in real-time
        - MQ_INTEGRATION: Queue complex queries for async processing
    
    Example:
        >>> retriever = vectorstore.as_retriever()
        >>> chain, chain_with_sources = get_rag_chain(retriever)
        >>> answer = chain.invoke("What is machine learning?")
        >>> result = chain_with_sources.invoke("Explain neural networks")
    
    Note:
        Both chains use the same Deepseek model. The chain_with_sources
        variant preserves context for citation and debugging purposes.
    """
    logger.debug("Creating RAG chain with retriever")
    
    # Standard RAG chain: retriever -> parse -> prompt -> LLM -> output
    chain = (
        {
            "context": retriever | RunnableLambda(parse_docs),
            "question": RunnablePassthrough(),
        }
        | RunnableLambda(build_prompt)
        | ChatOllama(model=TEXT_MODEL, base_url=OLLAMA_BASE_URL)
        | StrOutputParser()
    )

    # RAG chain with sources: preserves context alongside response
    chain_with_sources = {
        "context": retriever | RunnableLambda(parse_docs),
        "question": RunnablePassthrough(),
    } | RunnablePassthrough().assign(
        response=(
            RunnableLambda(build_prompt)
            | ChatOllama(model=TEXT_MODEL, base_url=OLLAMA_BASE_URL)
            | StrOutputParser()
        )
    )
    
    logger.debug("RAG chains created successfully")
    
    return chain, chain_with_sources
