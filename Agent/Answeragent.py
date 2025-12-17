import json
import re
from typing import Any, Dict, List, Optional

from Agent.BaseAgent import BaseAgent
from Utils.SessionMemory import SessionMemory


class AnswerAgent(BaseAgent):
    """
    AnswerAgent: The Core Intelligence of the Travel Bot.
    Responsibilities:
    1. Intent Classification (Router)
    2. Response Synthesis (Generator)
    """

    def __init__(
        self,
        system_prompt: str = "",
        memory: Optional[SessionMemory] = None,
        model_name: str = "gpt-oss:20b",  # Model tối ưu cho 16GB VRAM
        temperature: float = 0.5,  # 0.5 để cân bằng giữa sáng tạo và chính xác
    ):
        # Thiết lập System Prompt mặc định nếu không có
        if not system_prompt:
            system_prompt = (
                "You are a smart, friendly, and helpful AI Travel Guide for Vietnam & Singapore. "
                "Always answer in Vietnamese unless requested otherwise."
            )

        super().__init__(
            system_prompt=system_prompt,
            model_name=model_name,
            temperature=temperature,
            memory=memory,
        )

    # =========================================================================
    # 🧠 TASK 1: CLASSIFY INTENT (PHÂN LOẠI Ý ĐỊNH)
    # =========================================================================
    def run_classifier(self, user_input: str) -> Dict[str, Any]:
        """
        Phân tích câu hỏi user -> Trả về ID intent (0-4) và Keyword.
        Luôn trả về Dict chuẩn, không bao giờ raise exception.
        """

        # 1. Prompt chuyên dụng cho Classification
        prompt = f"""
        [ROLE]
        You are an Intent Classifier. Analyze the input strictly.

        [INTENT DEFINITIONS]
        0: Direction (map, route, distance, location, "ở đâu", "đường đi")
        1: Media (audio, video, play, listen, "mở bài", "nghe", "poi")
        2: Info (history, details, description, price, "là gì", "giới thiệu", "cho biết về")
        3: Chitchat (hello, thanks, bye, unrelated)
        4: Count (quantity, structure, "bao nhiêu", "có mấy", "liệt kê", "danh sách")

        [STRICT RULES]
        - If input contains specific POI code (e.g. "poi 123"), classify as 1 (Media).
        - If input asks "how many" or "list", classify as 4 (Count).
        - If input asks about a place ("biết về", "kể về"), classify as 2 (Info).

        [USER INPUT]: "{user_input}"

        [OUTPUT FORMAT]
        Return JSON ONLY: {{"id": <int>, "keyword": "<extracted_entity_name_or_empty>"}}
        """

        try:
            # Gọi LLM (Sử dụng hàm invoke của BaseAgent hoặc gọi thẳng llm)
            # Lưu ý: BaseAgent thường có method run_llm hoặc invoke
            messages = [
                {
                    "role": "system",
                    "content": "You are a JSON generator. Output JSON only.",
                },
                {"role": "user", "content": prompt},
            ]
            response = self.llm.invoke(messages)
            raw_content = response.content.strip()

            # --- Parsing Logic (Siêu bền) ---
            # Dùng Regex để tìm JSON trong mớ hỗn độn text mà LLM có thể trả về
            match = re.search(r"\{.*\}", raw_content, re.DOTALL)

            if match:
                json_str = match.group()
                data = json.loads(json_str)

                # Validate ID
                intent_id = int(data.get("id", 3))
                if intent_id not in [0, 1, 2, 3, 4]:
                    intent_id = 3

                return {
                    "id": intent_id,
                    "keyword": str(data.get("keyword", "")).strip(),
                }

            # Fallback nếu không tìm thấy JSON
            print(f"⚠️ [Classifier] JSON not found in: {raw_content[:50]}...")
            return {"id": 3, "keyword": ""}

        except Exception as e:
            print(f"❌ [Classifier] Error: {e}")
            return {"id": 3, "keyword": ""}

    # =========================================================================
    # 🗣️ TASK 2: SYNTHESIZE RESPONSE (SINH LỜI THOẠI)
    # =========================================================================
    def run_synthesizer(
        self, user_question: str, raw_data: Any, intent_label: str
    ) -> str:
        """
        Biến dữ liệu thô (JSON/Text) thành lời văn tự nhiên, thân thiện.
        """

        # 1. Kiểm tra data rỗng
        if not raw_data or (isinstance(raw_data, dict) and raw_data.get("error")):
            return "Xin lỗi bạn nha, hiện tại mình chưa tìm thấy thông tin chi tiết về địa điểm này trong hệ thống. Bạn thử hỏi địa điểm khác xem sao nhé!"

        # 2. Nếu raw_data đã có sẵn message chuẩn (từ logic SQL), dùng luôn cho nhanh
        if (
            isinstance(raw_data, dict)
            and "message" in raw_data
            and intent_label in ["direction", "media"]
        ):
            return raw_data["message"]

        # 3. Prompt "Nhập vai" hướng dẫn viên
        prompt = f"""
        [NHIỆM VỤ]
        Bạn là AI Hướng dẫn viên du lịch (Travel Buddy) tên là "T-Bot".
        Tính cách: Thân thiện, Nhiệt tình, Am hiểu, Dùng ngôn ngữ tự nhiên (dạ, nhé, ạ).

        [CONTEXT]
        - Khách hỏi: "{user_question}"
        - Loại yêu cầu: {intent_label.upper()}
        - Dữ liệu tìm được: {raw_data}

        [YÊU CẦU TRẢ LỜI]
        1. Dựa CHÍNH XÁC vào dữ liệu trên. Không bịa đặt.
        2. Nếu là thông tin (Info): Tóm tắt ngắn gọn, hấp dẫn (tối đa 3 câu).
        3. Nếu là đếm (Count): Nói rõ con số.
        4. KHÔNG trả về JSON, chỉ trả về văn bản (Plain text).

        [CÂU TRẢ LỜI CỦA BẠN (Tiếng Việt)]:
        """

        try:
            messages = [
                {
                    "role": "system",
                    "content": "Bạn là trợ lý du lịch ảo chuyên nghiệp.",
                },
                {"role": "user", "content": prompt},
            ]
            response = self.llm.invoke(messages)

            # Làm sạch kết quả (đôi khi LLM để trong ngoặc kép)
            final_text = response.content.strip().strip('"')
            return final_text

        except Exception as e:
            print(f"❌ [Synthesizer] Error: {e}")
            # Fallback cùng lắm là trả về data thô
            return str(raw_data)

    # =========================================================================
    # 🔄 LEGACY RUN (Giữ lại để tương thích ngược nếu cần, nhưng khuyên dùng 2 hàm trên)
    # =========================================================================
    def run(self, prompt: str, *args, **kwargs):
        """
        Hàm Wrapper đa năng.
        Nếu args rỗng -> Chạy Synthesizer (Chat mode)
        Nếu có args -> Chạy tương thích code cũ
        """
        # Nếu gọi từ GraphOrchestrator.run_classifier (chỉ truyền prompt)
        if not args and not kwargs:
            # Đây là trick: nếu gọi run() mà không có tham số khác, ta coi như đang test
            return self.run_classifier(prompt)

        # Nếu gọi kiểu cũ (có dummy args)
        return self.llm.invoke(prompt).content
