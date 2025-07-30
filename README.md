# Project: API for AI Agent Queries with Web Search and Analysis

This project provides an API for asynchronous processing of user queries using the **Yandex GPT API** and **Yandex Search API**. The API receives user queries, searches the web, analyzes the information, and returns an answer with reasoning and source links.

The project was developed as part of the **ITMO MegOlympiad 2025** under the **AI Talent Hub** track.

## Functionality

**Input:** A POST request with JSON `{id: int, query: str}`
**Output:** JSON `{id: int, answer: int / None, reasoning: str, sources: list(urls)}`

## Core Workflow

1. The question (in multiple forms) is sent to the **Yandex Search API**. Only the most relevant sources (top results) are collected.
2. Key information is extracted from the web pages using **BeautifulSoup**.
3. The sources are filtered via **Yandex GPT API** based on the principle: *"Is this information useful for answering the question?"*
4. A concise answer and an explanation are generated using the **Yandex GPT API**, leveraging the filtered useful sources.

## Key Features

1. Accepts queries with or without answer choices.
2. Searches for relevant sources online.
3. Parses web sources.
4. Uses Yandex GPT to analyze sources and choose the most appropriate answer.
5. Returns the answer, reasoning, and source links.

### Requirements

* Python 3.8+
* Docker (for running in containers)

## Installing Dependencies

1. Clone the repository:

   ```bash
   git clone https://github.com/cvvcvccvvcvc/mega.git
   cd repository-name
   ```
2. Create a `.env` file in the root directory and add your API keys:

   ```
   FOLDER_ID=your_folder_id
   YANDEXGPT_KEY=your_yandex_gpt_api_key
   YANDEX_SEARCH_KEY=your_yandex_search_api_key
   ```
3. Build and run the container:

   ```bash
   docker-compose up -d
   ```
