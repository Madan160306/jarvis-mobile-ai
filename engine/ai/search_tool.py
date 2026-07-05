import urllib.request
import urllib.parse
import json
import yaml
import os

def load_tavily_key():
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "jk_config.yaml")
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            return config.get("tavily_api_key", "")
    except Exception:
        return ""

def search_tavily(query: str, max_results: int = 3) -> str:
    api_key = load_tavily_key()
    if not api_key:
        return None
        
    url = "https://api.tavily.com/search"
    headers = {
        "Content-Type": "application/json",
    }
    data = json.dumps({
        "api_key": api_key,
        "query": query,
        "search_depth": "basic",
        "include_answer": True,
        "max_results": max_results
    }).encode('utf-8')
    
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            res_json = json.loads(response.read().decode('utf-8'))
            results = res_json.get("results", [])
            
            formatted = []
            
            # Include the AI-synthesized answer if available
            answer = res_json.get("answer", "")
            if answer:
                formatted.append(f"DIRECT ANSWER: {answer}")
            
            for i, r in enumerate(results):
                title = r.get("title", "No Title")
                content = r.get("content", "No Content")
                link = r.get("url", "No URL")
                formatted.append(f"[{i+1}] Title: {title}\n    Snippet: {content}\n    URL: {link}")
                
            if formatted:
                return "\n\n".join(formatted)
    except Exception as e:
        print(f"[Search Tool] Tavily request failed: {e}")
    return None

def search_web(query: str, max_results: int = 3) -> str:
    """Find real-time up-to-date data for a query using Tavily with Google/DDG fallback."""
    
    # Try Tavily first
    res = search_tavily(query, max_results)
    if res:
        return res
        
    # Fallback to DuckDuckGo/Google HTML parsing could be added here
    # For now, if Tavily is configured it will be the primary search.
    return "No search results found or Tavily API key is missing."
