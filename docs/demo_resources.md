# RAG Demo Resources & Questions

A curated collection of documents and questions to showcase the full capabilities of the RAG pipeline across all supported file types.

---

## 1. PDF — "Attention Is All You Need"

> The foundational Transformer paper. Dense with technical content, equations, tables, and figures — a perfect stress test.

**Download:** [attention_is_all_you_need.pdf](https://arxiv.org/pdf/1706.03762)

| # | Question | What It Showcases |
|---|---|---|
| 1 | What problem does the Transformer solve that RNNs couldn't? | Conceptual retrieval |
| 2 | How does scaled dot-product attention work? | Technical detail extraction |
| 3 | What are the dimensions of the model and why were they chosen? | Number/table retrieval |
| 4 | Why did the authors use positional encoding instead of recurrence? | Reasoning over design decisions |
| 5 | Summarize the results from the WMT translation benchmarks. | Table summarization |

---

## 2. PDF — "Retrieval-Augmented Generation (RAG) Original Paper"

> The paper that defines RAG — testing your system with questions about itself is the best possible demo.

**Download:** [rag_paper.pdf](https://arxiv.org/pdf/2005.11401)

| # | Question | What It Showcases |
|---|---|---|
| 1 | What is the difference between RAG-Sequence and RAG-Token? | Multi-concept comparison |
| 2 | What retriever does the original RAG paper use? | Fact lookup |
| 3 | How does RAG perform compared to closed-book GPT-2? | Benchmark comparison |
| 4 | What datasets were used to evaluate RAG? | List extraction |

> **Pro tip:** This is the "wow" moment of the demo — your RAG system answering questions about RAG using RAG.

---

## 3. PDF — "BERT: Pre-training of Deep Bidirectional Transformers"

> Long, multi-section NLP paper. Great for testing chunking and multi-hop retrieval.

**Download:** [bert_paper.pdf](https://arxiv.org/pdf/1810.04805)

| # | Question | What It Showcases |
|---|---|---|
| 1 | What does bidirectional mean in the context of BERT? | Conceptual explanation |
| 2 | How is BERT pre-trained? What are the two tasks? | Multi-part fact retrieval |
| 3 | How does BERT compare to GPT on the GLUE benchmark? | Benchmark table retrieval |
| 4 | What is the difference between BERT-Base and BERT-Large? | Comparative extraction |

---

## 4. PDF — "A Survey of Large Language Models"

> A broad survey paper — tests the system's ability to synthesize information across many sections.

**Download:** [llm_survey.pdf](https://arxiv.org/pdf/2303.18223)

| # | Question | What It Showcases |
|---|---|---|
| 1 | What are the key capabilities of large language models? | High-level summarization |
| 2 | How do LLMs handle reasoning tasks? | Concept extraction |
| 3 | What alignment techniques are discussed in the paper? | Section-level retrieval |
| 4 | What are the main challenges and limitations of LLMs? | Multi-point synthesis |

---

## 5. CSV — Titanic Dataset

> Structured tabular data. Tests the pipeline's ability to reason over rows, columns, and numeric aggregations.

**Download:** [titanic.csv](https://raw.githubusercontent.com/datasciencedojo/datasets/master/titanic.csv)

| # | Question | What It Showcases |
|---|---|---|
| 1 | What was the overall survival rate? | Aggregation over tabular data |
| 2 | Did passenger class affect survival chances? | Cross-column reasoning |
| 3 | What was the average age of survivors vs non-survivors? | Numeric comparison |
| 4 | How many passengers embarked from each port? | Group-by style retrieval |
| 5 | Who was the oldest passenger on board? | Row-level lookup |

---

## 6. CSV — World Population Data

> Long time-series dataset. Good for trend and comparison questions.

**Download:** [population.csv](https://raw.githubusercontent.com/datasets/population/master/data/population.csv)

| # | Question | What It Showcases |
|---|---|---|
| 1 | Which country had the highest population in 2020? | Filtered row lookup |
| 2 | How has the population of India changed over the last 30 years? | Time-series retrieval |
| 3 | What is the difference in population between China and the USA? | Numeric comparison |

---

## 7. Markdown — React README

> Official React README from GitHub. Tests Markdown parsing, code block handling, and instruction extraction.

**Download:** [react_readme.md](https://raw.githubusercontent.com/facebook/react/main/README.md)

| # | Question | What It Showcases |
|---|---|---|
| 1 | How do I install React? | Instruction extraction |
| 2 | What is the purpose of React? | Summary generation |
| 3 | What examples are provided in the repo? | List extraction from Markdown |

---

## 8. Markdown — Node.js Changelog

> Large, structured changelog file. Tests chunking of repetitive structured content.

**Download:** [node_changelog.md](https://raw.githubusercontent.com/nodejs/node/main/CHANGELOG.md)

| # | Question | What It Showcases |
|---|---|---|
| 1 | What was changed in the most recent release? | Latest-entry retrieval |
| 2 | Were there any security fixes in recent versions? | Keyword-based retrieval |
| 3 | Which versions introduced breaking changes? | Cross-chunk synthesis |

---

## 9. JSON — LangChain GitHub Repository Metadata

> A real GitHub API JSON response. Tests JSON parsing and nested key extraction.

**Download:** [langchain_repo.json](https://api.github.com/repos/langchain-ai/langchain)

| # | Question | What It Showcases |
|---|---|---|
| 1 | How many stars does the LangChain repo have? | JSON key extraction |
| 2 | When was the repository created? | Metadata retrieval |
| 3 | What is the primary programming language of the project? | Nested JSON parsing |
| 4 | Is the repository archived or still active? | Boolean field retrieval |

---

## 10. HTML — Wikipedia: Transformer Architecture

> Save this page as `.html` from your browser (File → Save As). Rich content with sections, tables, and links.

**Page URL:** [Transformer (deep learning architecture) — Wikipedia](https://en.wikipedia.org/wiki/Transformer_(deep_learning_architecture))

| # | Question | What It Showcases |
|---|---|---|
| 1 | What is the Transformer architecture used for? | High-level summary |
| 2 | Who introduced the Transformer and when? | Fact retrieval |
| 3 | What are the main components of a Transformer model? | List/section extraction |
| 4 | How does self-attention differ from traditional attention? | Conceptual comparison |

---

## Best Single Demo Flow

Upload these two files together, then ask questions in order:

```
Files:   attention_is_all_you_need.pdf  +  titanic.csv

Ask:  1. "Explain multi-head attention like I'm a junior developer."
      2. "What percentage of women survived vs men on the Titanic?"
      3. "What hardware did the Transformer authors train on and for how long?"
      4. "What were the limitations the authors acknowledged in the Attention paper?"
```

---

## Multi-turn Conversation Demo

Upload `attention_is_all_you_need.pdf` and ask these **in sequence** to showcase chat history and the sliding window memory:

```
1. "What is the Transformer architecture?"
2. "How does it handle sequential data without recurrence?"
3. "Can you compare that to what an RNN does?"
4. "Which approach is faster to train and why?"
5. "What were the limitations the authors acknowledged?"
```

Each answer should reference context from the previous exchange — this demonstrates your 20-message sliding window working correctly.

---

## Cross-Document Edge Case

After uploading both the Attention paper and the Titanic CSV, ask:

> *"Based on the documents you have, which is more complex — the Transformer model or the Titanic dataset?"*

This intentionally crosses document boundaries and is a great stress test for your retriever's ability to reason across sources.
