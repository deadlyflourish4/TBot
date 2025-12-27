import json
import re
import time
import unicodedata
from typing import Any, Dict, List, Optional

import numpy as np

# Import các module hệ thống
from Agent.Answeragent import AnswerAgent
from Database.db import MultiDBManager
from sqlalchemy import text
from SystemPrompt.SemanticRouter import SemanticRouter
from Utils.Reflection import Reflection
from Utils.SessionMemory import SessionMemory


# ==========================================================
# 🛠️ DB WRAPPER
# ==========================================================
class DBWrapper:
    def __init__(self, engine):
        self.engine = engine

    def run_query(self, sql: str):
        with self.engine.connect() as conn:
            result = conn.execute(text(sql))
            return [dict(r._mapping) for r in result]


# ==========================================================
# 🎮 GRAPH ORCHESTRATOR
# ==========================================================


class GraphOrchestrator:
    def __init__(self):
        self.memory = SessionMemory()
        self.db_manager = MultiDBManager()

        # Hybrid Router (Regex + Embedding + Follow-up)
        self.router = SemanticRouter()

        # LLM Generator
        self.answer_agent = AnswerAgent(system_prompt="", memory=self.memory)
        self.reflection = Reflection(llm=self.answer_agent.llm)

    # ------------------------------------------------------
    # 🔥 CORE: SINH LỜI THOẠI AI
    # ------------------------------------------------------
    def synthesize_response(self, user_question, raw_data, intent_label):
        try:
            return self.answer_agent.run_synthesizer(
                user_question, raw_data, intent_label
            )
        except AttributeError:
            return str(raw_data)

    # ------------------------------------------------------
    # DB CANDIDATES
    # ------------------------------------------------------
    def get_db_candidates(self, project_id, region_id):
        engine = self.db_manager.get_engine(region_id)
        db = DBWrapper(engine)
        prefix = self.db_manager.DB_MAP[region_id]["prefix"]

        sql = f"""
        SELECT SubProjectID, SubProjectName, POI
        FROM {prefix}.SubProjects
        WHERE ProjectID = {project_id}
        """
        rows = db.run_query(sql)

        candidates = []
        for r in rows:
            if r.get("SubProjectName"):
                candidates.append(
                    {"id": r["SubProjectID"], "name": r["SubProjectName"]}
                )
            if r.get("POI"):
                candidates.append({"id": r["SubProjectID"], "name": r["POI"]})
        return candidates

    # ------------------------------------------------------
    # WORKERS
    # ------------------------------------------------------
    def run_count(self, ctx, target_place):
        if not target_place:
            return None

        engine = self.db_manager.get_engine(ctx["region_id"])
        db = DBWrapper(engine)
        prefix = self.db_manager.DB_MAP[ctx["region_id"]]["prefix"]

        sql = f"""
        SELECT COUNT(DISTINCT A.SubProjectAttractionID)
             + COUNT(DISTINCT D.SubProjectAttractionDetailID) AS Total
        FROM {prefix}.SubProjects AS S
        LEFT JOIN {prefix}.SubprojectAttractions AS A
            ON S.SubProjectID = A.SubProjectID
        LEFT JOIN {prefix}.SubprojectAttractionDetails AS D
            ON A.SubProjectAttractionID = D.SubProjectAttractionID
        WHERE S.SubProjectID = {target_place['id']}
        """
        rows = db.run_query(sql)
        return {
            "place_name": target_place["name"],
            "total_count": rows[0]["Total"] if rows else 0,
        }

    def run_info(self, ctx, target_place):
        if not target_place:
            return None

        engine = self.db_manager.get_engine(ctx["region_id"])
        db = DBWrapper(engine)
        prefix = self.db_manager.DB_MAP[ctx["region_id"]]["prefix"]

        sql = f"""
        SELECT SubProjectName, Introduction
        FROM {prefix}.SubProjects
        WHERE SubProjectID = {target_place['id']}
        """
        rows = db.run_query(sql)
        return rows[0] if rows else None

    def run_media(self, ctx, target_place):
        if not target_place:
            return None

        engine = self.db_manager.get_engine(ctx["region_id"])
        db = DBWrapper(engine)
        prefix = self.db_manager.DB_MAP[ctx["region_id"]]["prefix"]

        sql = f"""
        SELECT TOP 1
            COALESCE(MD.MediaURL, MA.MediaURL) AS URL,
            COALESCE(MD.MediaType, MA.MediaType) AS Type,
            S.SubProjectName,
            S.Introduction
        FROM {prefix}.SubProjects AS S
        LEFT JOIN {prefix}.SubprojectAttractions AS A
            ON S.SubProjectID = A.SubProjectID
        LEFT JOIN {prefix}.SubprojectAttractionMedia AS MA
            ON A.SubProjectAttractionID = MA.SubProjectAttractionID
        LEFT JOIN {prefix}.SubprojectAttractionDetails AS D
            ON A.SubProjectAttractionID = D.SubProjectAttractionID
        LEFT JOIN {prefix}.SubprojectAttractionDetailsMedia AS MD
            ON D.SubProjectAttractionDetailID = MD.SubProjectAttractionDetailID
        WHERE S.SubProjectID = {target_place['id']}
        AND COALESCE(MD.MediaType, MA.MediaType) IN ('video', 'audio')
        """
        rows = db.run_query(sql)

        if not rows:
            return {"status": "not_found"}

        return {
            "type": "media",
            "action": "play",
            "media_type": rows[0]["Type"],
            "url": rows[0]["URL"],
            "place_name": rows[0]["SubProjectName"],
        }

    def run_direction(self, ctx, target_place):
        engine = self.db_manager.get_engine(ctx["region_id"])
        db = DBWrapper(engine)
        prefix = self.db_manager.DB_MAP[ctx["region_id"]]["prefix"]

        if target_place:
            sql = f"""
            SELECT SubProjectName, Location, Introduction
            FROM {prefix}.SubProjects
            WHERE SubProjectID = {target_place['id']}
            """
        elif ctx["lat"]:
            sql = f"""
            SELECT TOP 1 SubProjectName, Location, Introduction
            FROM {prefix}.SubProjects
            WHERE ProjectID = {ctx['project_id']}
            AND Location IS NOT NULL
            """
        else:
            return None

        rows = db.run_query(sql)
        return rows[0] if rows else None

    def run_chitchat(self, ctx):
        return {"context": "social"}

    def _normalize(self, s: str) -> str:
        s = (s or "").lower().strip()
        s = unicodedata.normalize("NFKD", s)
        s = "".join(c for c in s if not unicodedata.combining(c))  # bỏ dấu
        s = re.sub(r"[^a-z0-9\s]", " ", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s

    def _mentions_place_explicitly(
        self, user_question: str, candidates: List[Dict[str, str]]
    ) -> bool:
        """
        True nếu câu có nhắc tên địa điểm (match substring đơn giản sau normalize).
        Cái này giúp chặn embedding đoán bừa khi user chỉ nói 'giới thiệu', 'thông tin', 'điểm đó'.
        """
        q = self._normalize(user_question)
        if not q:
            return False

        # nếu có các đại từ/ám chỉ -> coi là KHÔNG explicit (ưu tiên context)
        if re.search(
            r"\b(diem do|cho do|noi do|o do|do|nay|nay a|kia|o day|cho nay)\b", q
        ):
            return False

        # match nhanh theo substring (tối ưu: chỉ check tên dài >= 4 ký tự)
        for c in candidates:
            name = self._normalize(c.get("name", ""))
            if len(name) >= 4 and name in q:
                return True
        return False
    def format_public_response(
        self,
        final_message: str,
        raw_data: dict | None,
        intent_label: str,
        session_id: str
    ) -> dict:
        """
        Chuẩn hóa response trả về cho client.
        Chỉ dùng 4 field: Message, location, audio, session_id
        """

        location = None
        audio = None

        if intent_label == "direction" and raw_data:
            location = raw_data.get("Location"),

        if intent_label == "media" and raw_data and raw_data.get("media_type") == "audio":
            audio = raw_data.get("url"),

        return {
            "Message": final_message,
            "location": location,
            "audio": audio,
            "session_id": session_id,
        }
    # ======================================================
    # 🚀 MAIN PIPELINE
    # ======================================================
    def run(self, session_id, user_question, user_location, project_id, region_id=0):
        start_time = time.perf_counter()
        ctx = {
            "session_id": f"{session_id}_{region_id}",
            "lat": (
                user_location.split(",")[0].strip()
                if user_location and "," in user_location
                else None
            ),
            "lon": (
                user_location.split(",")[1].strip()
                if user_location and "," in user_location
                else None
            ),
            "project_id": project_id,
            "region_id": region_id,
        }

        # -------- 1️⃣ ROUTER --------
        self.memory.append_user(ctx["session_id"], user_question)

        # rewritten_question = self.reflection(self.memory, ctx["session_id"])
        # intent_res = self.router.classify_intent(rewritten_question)
        intent_res = self.router.classify_intent(user_question)

        intent_id = intent_res["id"]
        intent_label = intent_res["label"]

        print(f"🧠 Intent → {intent_label} | {intent_res.get('method')}")

        # -------- 2️⃣ FOLLOW-UP (STOP PIPELINE HERE) --------
        if intent_id == 5:
            follow_of = intent_res.get("follow_of")

            if follow_of == "direction":
                msg = "Bạn muốn hỏi khoảng cách hay thời gian di chuyển ạ?"
            elif follow_of == "info":
                msg = "Bạn muốn biết thêm thông tin gì? Ví dụ: lịch sử, giờ mở cửa?"
            elif follow_of == "media":
                msg = "Bạn muốn xem video hay nghe audio về địa điểm này?"
            elif follow_of == "count":
                msg = "Bạn muốn đếm số lượng hạng mục nào cụ thể?"
            else:
                msg = "Bạn có thể nói rõ hơn giúp mình được không?"

            self.memory.append_user(ctx["session_id"], user_question)
            self.memory.append_ai(ctx["session_id"], msg)

            return {
                "type": "follow_up",
                "confidence": intent_res["score"],
                "message": msg,
                "data": {"need_clarification": True},
            }

        # -------- 3️⃣ TARGET SEARCH --------
        target_place = None
        candidates = []
        if intent_id in [0, 1, 2, 4]:
            candidates = self.get_db_candidates(project_id, region_id)
            # 1) Nếu user KHÔNG nhắc địa điểm rõ ràng -> ưu tiên context
            has_explicit = self._mentions_place_explicitly(user_question, candidates)

            # target_place = self.router.find_target_place(user_question, candidates)
            # ✅ CONTEXT FALLBACK
            if not has_explicit and self.router.last_target_place:
                target_place = self.router.last_target_place
            else:
                # 2) Có nhắc địa điểm -> mới semantic match
                target_place = self.router.find_target_place(user_question, candidates)

                # 3) Nếu match fail -> fallback về context
                if not target_place and self.router.last_target_place:
                    target_place = self.router.last_target_place
        if target_place:
            self.router.last_target_place = target_place

        # -------- 4️⃣ DATA QUERY --------
        if intent_id == 0:
            raw_data = self.run_direction(ctx, target_place)
        elif intent_id == 1:
            raw_data = self.run_media(ctx, target_place)
        elif intent_id == 2:
            raw_data = self.run_info(ctx, target_place)
        elif intent_id == 4:
            raw_data = self.run_count(ctx, target_place)
        else:
            raw_data = self.run_chitchat(ctx)

        if not raw_data and intent_id != 3:
            raw_data = {"error": "no_data"}

        # -------- 5️⃣ LLM RESPONSE --------
        final_message = self.synthesize_response(user_question, raw_data, intent_label)

        # self.memory.append_user(ctx["session_id"], user_question)
        self.memory.append_ai(ctx["session_id"], final_message)
        total_ms = round((time.perf_counter() - start_time) * 1000, 2)

        public_response = self.format_public_response(
            final_message=final_message,
            raw_data=raw_data,
            intent_label=intent_label,
            session_id=ctx["session_id"],
        )
        return public_response

    
