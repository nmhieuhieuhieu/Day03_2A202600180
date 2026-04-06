import os
import re
import requests
from datetime import datetime
from ddgs import DDGS


ddgs = DDGS()
def web_search(query: str) -> str:
    """Search the web using Brave Search API. Returns top 3 snippets."""
    res = ddgs.text(query, max_results=5)
    return "\n".join(t['body'] for t in res)
    api_key = os.getenv("BRAVE_API_KEY")
    if not api_key:
        return "Error: BRAVE_API_KEY not set in .env"
    
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": api_key,
    }
    params = {"q": query, "count": 3}
    
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    
        results = []
        for item in data.get("web", {}).get("results", [])[:3]:
            title = item.get("title", "")
            snippet = item.get("description", "")
            results.append(f"- {title}: {snippet}")
    
        if not results:
            return "No results found."
        return "\n".join(results)
    
    except requests.RequestException as e:
        return f"Search error: {str(e)}"


def calculator(expression: str) -> str:
    """Evaluate a math expression safely. E.g., calculator[150000 * 2 + 50000]"""
    try:
        # Only allow safe math operations
        allowed = set("0123456789+-*/.() ")
        if not all(c in allowed for c in expression):
            return f"Error: Invalid characters in expression: {expression}"
        result = eval(expression)
        return str(result)
    except Exception as e:
        return f"Calculation error: {str(e)}"


def get_system_time() -> str:
    """Returns the current date and day of week."""
    now = datetime.now()
    return now.strftime("%A, %B %d, %Y")

def wikipedia_search(query: str) -> str:
    """
    Searches Wikipedia and returns a short summary of the top result.
    """
    url = os.getenv('WIKIPEDIA_URL')

    # ADDED: Custom User-Agent header required by Wikimedia API policies
    # Replace the email with your own contact info
    headers = {
        "User-Agent": f"MyReActAgent/1.0 ({os.getenv('WIKIPEDIA_USER_EMAIL')}) python-requests"
    }

    search_params = {
        "action": "query",
        "format": "json",
        "list": "search",
        "srsearch": query,
        "utf8": 1,
        "srlimit": 1,
    }

    try:
        # ADDED: Pass the headers to the GET request
        response = requests.get(url, headers=headers, params=search_params, timeout=5)
        response.raise_for_status()
        search_data = response.json()

        results = search_data.get("query", {}).get("search", [])
        if not results:
            return f"Observation: No Wikipedia results found for '{query}'."

        best_title = results[0]["title"]

        extract_params = {
            "action": "query",
            "format": "json",
            "prop": "extracts",
            "exchars": 400,
            "exintro": True,
            "explaintext": True,
            "titles": best_title,
        }

        # ADDED: Pass the headers to the second GET request as well
        extract_response = requests.get(
            url, headers=headers, params=extract_params, timeout=5
        )
        extract_response.raise_for_status()
        extract_data = extract_response.json()

        pages = extract_data.get("query", {}).get("pages", {})
        for page_id, page_info in pages.items():
            if page_id == "-1":
                return f"Observation: Could not retrieve summary for '{best_title}'."

            extract = page_info.get("extract", "").strip()
            extract_clean = extract.replace("\n", " ")
            return f"Observation: [Page: {best_title}] {extract_clean}"

    except requests.exceptions.RequestException as e:
        return f"Observation: Error connecting to Wikipedia API: {str(e)}"

    return "Observation: Unknown error occurred during Wikipedia search."

# Tool registry
TOOLS = [
    {
        "name": "web_search",
        "description": (
            "Search the web for real-time information using Brave Search API. "
            "Use this for weather forecasts, ticket prices, hotel prices, travel blogs, "
            "restaurant recommendations, and any current data. "
            "Input: a search query string. Output: top 3 result snippets."
        ),
        "function": web_search,
    },
    {
        "name": "calculator",
        "description": (
            "Evaluate a mathematical expression to get an exact numeric result. "
            "Use this for budget calculations, total cost estimates, unit conversions. "
            "Input: a math expression (e.g., '150000 * 2 + 50000'). Output: the result."
        ),
        "function": calculator,
    },
    {
        "name": "get_system_time",
        "description": (
            "Get today's date and day of the week. "
            "Use this to determine the current date for planning trips, "
            "calculating 'next weekend', or checking seasonal weather. "
            "Input: none. Output: current date string."
        ),
        "function": get_system_time,
    },
    {
        "name": "wikipedia_search",
        "description": "A wrapper around Wikipedia. Useful for when you need to answer general questions about people, places, companies, facts, historical events, or other subjects. Input should be a search query.",
        "function": wikipedia_search,
    },
]


def execute_tool(tool_name: str, args: str) -> str:
    """Execute a tool by name with the given arguments."""
    for tool in TOOLS:
        if tool["name"] == tool_name:
            fn = tool["function"]
            if tool_name == "get_system_time":
                return fn()
            return fn(args.strip())
    return f"Error: Tool '{tool_name}' not found. Available tools: {[t['name'] for t in TOOLS]}"

