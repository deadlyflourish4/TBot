from Agent.BaseAgent import BaseAgent
from Utils.SessionMemory import SessionMemory
from bs4 import BeautifulSoup
import requests


# ==========================================================
# DuckDuckGo search (no API key)
# ==========================================================
def duckduckgo_search(query: str, max_results: int = 3):
    url = "https://duckduckgo.com/html/"
    params = {"q": query}
    headers = {"User-Agent": "Mozilla/5.0"}

    resp = requests.post(url, data=params, headers=headers, timeout=10)
    resp.raise_for_status()

    results = []
    soup = BeautifulSoup(resp.text, "html.parser")

    for a in soup.select("a.result__a", limit=max_results):
        href = a.get("href")
        if href:
            results.append(href)

    return results


# ==========================================================
# Web scraper
# ==========================================================
class WebScraper:
    def scrape(self, url: str, limit: int = 1200) -> str:
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            r = requests.get(url, headers=headers, timeout=10)
            r.raise_for_status()

            soup = BeautifulSoup(r.text, "html.parser")
            for tag in soup(["script", "style", "footer", "nav", "aside"]):
                tag.decompose()

            text = soup.get_text(separator="\n", strip=True)
            lines = [l.strip() for l in text.splitlines() if len(l.strip()) > 40]
            return "\n".join(lines)[:limit]

        except Exception as e:
            return f"[Scrape error: {e}]"


# ==========================================================
# SearchAgent
# ==========================================================
class SearchAgent(BaseAgent):
    """
    SearchAgent:
      - Performs web search (DuckDuckGo)
      - Scrapes top pages
      - Summarizes with Ollama (ChatOllama)
      - Returns unified JSON for AnswerAgent
    """

    def __init__(
        self,
        system_prompt: str = None,
        memory: SessionMemory = None,
        model_name: str = "deepseek-r1:8b",
    ):
        super().__init__(
            system_prompt=system_prompt
            or (
                "You are a helpful travel search assistant. "
                "Summarize factual web information clearly and concisely."
            ),
            model_name=model_name,
            temperature=0.3,
            memory=memory,
        )

        self.scraper = WebScraper()

    # ======================================================
    def run(self, session_id: str, query: str) -> dict:
        try:
            # 1️⃣ Search URLs
            urls = duckduckgo_search(query, max_results=3)

            # 2️⃣ Scrape content
            contents = []
            for url in urls:
                text = self.scraper.scrape(url)
                if text:
                    contents.append(text)

            # 3️⃣ Build LLM prompt
            joined_content = "\n\n".join(contents[:3])
            user_prompt = (
                f"User question: {query}\n\n"
                f"Web information:\n{joined_content}\n\n"
                "Based only on the information above, "
                "provide a clear, factual, and helpful answer. "
                "Do not invent facts."
            )

            # 4️⃣ Summarize via LLM
            answer = self.run_llm(session_id, user_prompt)

            # 5️⃣ Extract audio links (simple heuristic)
            audio_links = [
                token for token in answer.split()
                if token.lower().endswith(".mp3")
            ]

            return self.format_json(
                question_old=(
                    self.memory.get_history_list(session_id)
                    if self.memory else [query]
                ),
                message=answer,
                audio=list(set(audio_links)),
                location={},
            )

        except Exception as e:
            return self.format_json(
                question_old=(
                    self.memory.get_history_list(session_id)
                    if self.memory else [query]
                ),
                message=f"Search failed: {e}",
                audio=[],
                location={},
            )
