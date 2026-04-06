# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Nguyễn Minh Hiếu
- **Student ID**: 2A202600180
- **Date**: April 6, 2026

---

## I. Technical Contribution (15 Points)

*   **Modules Implemented**: `src/tools/tools.py` & `tests/test_bug3.py`

*   **Code Highlights**:
    - **Collaborative Toolset**: I participated in the development of the core toolset, including `web_search` (leveraging Brave Search API for real-time data), `calculator` (a safe mathematical evaluator), and `get_system_time` (providing essential temporal context).
    - **Tool Dispatcher**: Contributed to the design of the `execute_tool` function, which serves as a centralized dispatcher to enable dynamic tool selection based on the agent's reasoning.
    - **Sanitization & Testing**: I implemented a critical input sanitization layer for tool arguments and developed `tests/test_bug3.py`, an automated test suite to validate search query formatting.

*   **Documentation**:
    - The tools were registered in the `TOOLS` registry with detailed descriptions to guide the Agent's decision-making process. My specific contribution focused on ensuring the reliability of these tools by addressing data retrieval failures. 
    - I identified that the search API often failed when LLM-generated queries contained unnecessary quotes (the "Quoted Query" bug). To resolve this, I implemented a robust sanitization layer in `tools.py` that strips problematic characters from inputs before they reach the API. Furthermore, I formalized this fix by creating an automated test suite (`tests/test_bug3.py`) to simulate various query edge cases. This ensured that the Agent’s search reliability transitioned from experimental to production-ready, guaranteeing consistent data retrieval regardless of the LLM’s output formatting.


---

## II. Debugging Case Study (10 Points)

*   **Problem Description**: During the testing phase, I encountered two major integration issues: an OpenAI `401 Authentication Error` that halted the agent, and a persistent "No results found" error from the external search API despite the Agent querying valid topics.

*   **Log Source**: Terminal stack trace & `tests/test_brave_search.py` test outputs.

*   **Diagnosis**:
    - 1. **Authentication Error**: The system failed to authenticate with the LLM provider because the `OPENAI_API_KEY` was either missing from the environment or improperly loaded during runtime.
    - 2. **The "Quoted Query" Bug**: I traced the search failure to how the LLM formatted tool arguments. The LLM often generated queries wrapped in double or single quotes (e.g., `web_search["'thời tiết Đà Nẵng'"]`). The search API interpreted these quotes as strict "exact phrase" constraints, causing normal and highly relevant searches to return empty results.

*   **Solution**:
    - 1. **Environment Configuration**: Reconfigured the `.env` file, ensured the key was active, and verified that `load_dotenv()` was executed at the very beginning of the application entry point to guarantee all modules had access to the credentials.
    - 2. **Input Sanitization**: I implemented a robust string-cleaning mechanism inside the tool logic (`.strip('"\'').replace('"', '').replace("'", '')`) to strip all quotes before the query is sent to the API. To ensure this bug was permanently resolved, I wrote a dedicated test script (`tests/test_brave_search.py`) that simulates edge-case quoted inputs, successfully verifying that the search tool now handles LLM formatting anomalies gracefully.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

1.  **Reasoning**: - The `Thought` block enables deliberation before action. Unlike standard Chatbots, ReAct allows the Agent to decide when to seek new information, significantly reducing hallucinations.
2.  **Reliability**: Agents are less reliable than Chatbots during network failures. While Chatbots generate generic text regardless of accuracy, Agents may loop infinitely if error handling is insufficient.
3.  **Observation**: Environment feedback acts as a compass. If a search fails, the Agent dynamically adjusts its query—a capability impossible for static Chatbots.
---

## IV. Future Improvements (5 Points)

*How would you scale this for a production-level AI agent system?*

- **Scalability**: Implement asynchronous tool calling (`asyncio`) to prevent blocking the Agent loop during slow API request
- **Safety**: Add a "Supervisor LLM" layer to audit Agent actions and prevent misuse of tools
- **Performance**: Integrate a Vector Database to cache search results, reducing API overhead and improving overall response time

---

