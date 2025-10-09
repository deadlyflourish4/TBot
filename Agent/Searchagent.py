import requests
from bs4 import BeautifulSoup
from langchain.agents import Tool, initialize_agent, AgentType
from langchain_community.tools import DuckDuckGoSearchRun
from .BaseAgent import BaseAgent
from ..Utils.SessionMemory import SessionMemory


class WebScraperTool:
    """Extract readable text from a URL by removing HTML noise."""

    def run(self, url: str) -> str:
        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/91.0.4472.124 Safari/537.36"
                )
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            for tag in soup(["script", "style", "footer", "nav", "aside"]):
                tag.extract()

            text = soup.get_text(separator="\n", strip=True)
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            text = "\n".join(lines)

            return text[:1000] + ("...\n[Truncated]" if len(text) > 1000 else "")
        except Exception as e:
            return f"[Error scraping {url}: {e}]"


class SearchAgent(BaseAgent):
    """
    SearchAgent:
      - Performs factual web searches (DuckDuckGo + Gemini).
      - Logs user query + LLM result into shared SessionMemory.
      - Returns unified JSON response for downstream AnswerAgent.
    """

    def __init__(
        self,
        system_prompt: str = None,
        api_key: str = "",
        memory: SessionMemory = None,
    ):
        super().__init__(
            system_prompt=system_prompt
            or "You are a helpful travel search assistant.",
            api_key=api_key,
            temperature=0.3,
            memory=memory,
        )

        search_tool = DuckDuckGoSearchRun(name="Search", num_results=3)
        scraper_tool = WebScraperTool()

        self.tools = [
            Tool(
                name="Search",
                func=search_tool.run,
                description="Perform web searches for travel destinations, attractions, or events.",
            ),
            Tool(
                name="WebScraper",
                func=scraper_tool.run,
                description="Extract clean text content from a webpage.",
            ),
        ]

        self.agent = initialize_agent(
            tools=self.tools,
            llm=self.llm,
            agent=AgentType.CHAT_ZERO_SHOT_REACT_DESCRIPTION,
            verbose=False,
            handle_parsing_errors=True,
            early_stopping_method="generate",
        )

    def run(self, session_id: str, query: str) -> dict:
        """Perform search, log to memory, and return structured output."""
        try:
            # Log user query to memory
            # if self.memory:
            #     self.memory.append_user(session_id, query)

            # Perform search
            raw_text = self.agent.run(query)
            message_text = raw_text.strip() if raw_text else ""

            # Log AI response
            # if self.memory:
            #     self.memory.append_ai(session_id, message_text)

            # Extract audio links
            audio_links = [
                token for token in message_text.split()
                if token.lower().endswith(".mp3")
            ]

            # Trim long output for readability
            message = (
                f"According to recent web information:\n\n{message_text[:1500]}"
                + ("..." if len(message_text) > 1500 else "")
            )

            # Unified structured output
            return self.format_json(
                question_old=self.memory.get_history_list(session_id)
                if self.memory else [query],
                message=message,
                audio=list(set(audio_links)),
                location={},
            )

        except Exception as e:
            error_msg = f"Search failed: {e}"
            # if self.memory:
            #     self.memory.append_ai(session_id, error_msg)

            return self.format_json(
                question_old=self.memory.get_history_list(session_id)
                if self.memory else [query],
                message=error_msg,
                audio=[],
                location={},
            )
