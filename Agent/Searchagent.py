import requests
from bs4 import BeautifulSoup
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import Tool, AgentExecutor, initialize_agent, AgentType
from langchain.tools import DuckDuckGoSearchRun

class WebScraperTool:
    """Custom tool để scrape 1 URL."""
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
            text = "\n".join([line.strip() for line in text.splitlines() if line.strip()])

            return text[:4000] + ("...\n[Truncated]" if len(text) > 4000 else "")
        except Exception as e:
            return f"Error scraping {url}: {e}"

class SearchAgent:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.3,
            max_tokens=None,
            timeout=None,
            max_retries=2,
            google_api_key="AIzaSyBSHh_9Yd2-o8xjZsjzBqwnz24FAHR3GJU",
        )

        search_tool = DuckDuckGoSearchRun(name="Search", num_results=3)
        scraper_tool = WebScraperTool()

        self.tools = [
            Tool(
                name="Search",
                func=search_tool.run,
                description="Tìm kiếm nhanh thông tin từ web."
            ),
            Tool(
                name="WebScraper",
                func=scraper_tool.run,
                description="Lấy toàn văn nội dung từ một URL."
            ),
        ]

        self.agent = initialize_agent(
            tools=self.tools,
            llm=self.llm,
            agent=AgentType.CHAT_ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            handle_parsing_errors=True,
            early_stopping_method="generate",
        )

    def run(self, query: str) -> str:
        """Hỏi agent search."""
        return self.agent.run(query)
