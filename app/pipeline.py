import time
import re
import unicodedata
from typing import Dict, List

from sqlalchemy import text

from Agent.Answeragent import AnswerAgent
from Database.db import MultiDBManager
from Project.Repo.TBot.app.Agent.SemanticRouter import SemanticRouter
from Utils.SessionMemory import SessionMemory
from Utils.Reflection import Reflection


# ==========================================================
# 🛠️ DB WRAPPER (DEBUG SQL)
# ==========================================================
class DBWrapper:
    def __init__(self, engine, debug: bool = False):
        self.engine = engine
        self.debug = debug

    def run_query(self, sql: str):
        if self.debug:
            print("🧾 [SQL] Executing:")
            print(sql.strip())

        with self.engine.connect() as conn:
            result = conn.execute(text(sql))
            rows = [dict(r._mapping) for r in result]

        if self.debug:
            print(f"📊 [SQL] Rows returned: {len(rows)}")

        return rows


# ==========================================================
# 🎮 GRAPH ORCHESTRATOR (FINAL)
# ==========================================================
class GraphOrchestrator:
    def __init__(self, debug: bool = True):
        self.debug = debug
        self.memory = SessionMemory()
        self.db_manager = MultiDBManager()
        self.router = SemanticRouter()

        self.answer_agent = AnswerAgent(system_prompt="", memory=self.memory)
        self.reflection = Reflection(llm=self.answer_agent.llm)

    # ---------------- DEBUG ----------------
    def dbg(self, *args):
        if self.debug:
            print(*args)

    # ---------------- LLM ----------------
    def synthesize_response(self, user_question, raw_data, intent_label):
        try:
            return self.answer_agent.run_synthesizer(
                user_question, raw_data, intent_label
            )
        except Exception as e:
            self.dbg("❌ LLM ERROR:", e)
            return str(raw_data)

    # ======================================================
    # DB CANDIDATES
    # ======================================================
    def get_db_candidates(self, project_id, region_id):
        engine = self.db_manager.get_engine(region_id)
        db = DBWrapper(engine, debug=self.debug)
        prefix = self.db_manager.DB_MAP[region_id]["prefix"]

        sql = f"""
        SELECT SubProjectID, SubProjectName, POI
        FROM {prefix}.SubProjects
        WHERE ProjectID = {project_id}
        """
        rows = db.run_query(sql)

        cands = []
        for r in rows:
            if r.get("SubProjectName"):
                cands.append({"id": r["SubProjectID"], "name": r["SubProjectName"]})
            if r.get("POI"):
                cands.append({"id": r["SubProjectID"], "name": r["POI"]})
        return cands

    # ======================================================
    # WORKERS (DEBUG HÀM + SQL)
    # ======================================================
    def run_direction(self, ctx, target_place):
        self.dbg("🛠️ [WORKER] run_direction")

        if not target_place:
            self.dbg("⚠️ run_direction: target_place=None")
            return None

        engine = self.db_manager.get_engine(ctx["region_id"])
        db = DBWrapper(engine, debug=self.debug)
        prefix = self.db_manager.DB_MAP[ctx["region_id"]]["prefix"]

        sql = f"""
        SELECT SubProjectName, Location, Introduction
        FROM {prefix}.SubProjects
        WHERE SubProjectID = {target_place['id']}
        """
        rows = db.run_query(sql)
        self.dbg("📦 run_direction rows =", rows)

        return rows[0] if rows else None

    def run_info(self, ctx, target_place):
        self.dbg("🛠️ [WORKER] run_info")

        if not target_place:
            return None

        engine = self.db_manager.get_engine(ctx["region_id"])
        db = DBWrapper(engine, debug=self.debug)
        prefix = self.db_manager.DB_MAP[ctx["region_id"]]["prefix"]

        sql = f"""
        SELECT SubProjectName, Introduction
        FROM {prefix}.SubProjects
        WHERE SubProjectID = {target_place['id']}
        """
        rows = db.run_query(sql)
        self.dbg("📦 run_info rows =", rows)

        return rows[0] if rows else None

    def run_media(self, ctx, target_place):
        self.dbg("🛠️ [WORKER] run_media")

        if not target_place:
            return None

        engine = self.db_manager.get_engine(ctx["region_id"])
        db = DBWrapper(engine, debug=self.debug)
        prefix = self.db_manager.DB_MAP[ctx["region_id"]]["prefix"]

        sql = f"""
        SELECT TOP 1
            COALESCE(MD.MediaURL, MA.MediaURL) AS URL,
            COALESCE(MD.MediaType, MA.MediaType) AS Type,
            S.SubProjectName
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
        """
        rows = db.run_query(sql)
        self.dbg("📦 run_media rows =", rows)

        if not rows:
            return {"status": "not_found"}

        return {
            "media_type": rows[0]["Type"],
            "url": rows[0]["URL"],
            "place_name": rows[0]["SubProjectName"],
        }

    def run_count(self, ctx, target_place):
        self.dbg("🛠️ [WORKER] run_count")
        return {"total": 0} if target_place else None

    def run_chitchat(self, ctx):
        self.dbg("🛠️ [WORKER] run_chitchat")
        return {"context": "social"}

    # ======================================================
    # NORMALIZE + EXPLICIT CHECK
    # ======================================================
    def _normalize(self, s: str) -> str:
        s = (s or "").lower().strip()
        s = unicodedata.normalize("NFKD", s)
        s = "".join(c for c in s if not unicodedata.combining(c))
        s = re.sub(r"[^a-z0-9\s]", " ", s)
        return re.sub(r"\s+", " ", s).strip()

    def _mentions_place_explicitly(
        self, user_question: str, candidates: List[Dict[str, str]]
    ) -> bool:
        q = self._normalize(user_question)
        if not q:
            return False

        if re.search(r"\b(o do|do|kia|nay|o day)\b", q):
            return False

        for c in candidates:
            name = self._normalize(c.get("name", ""))
            if len(name) >= 4 and name in q:
                return True
        return False

    # ======================================================
    # 🚀 MAIN PIPELINE
    # ======================================================
    def run(self, session_id, user_question, user_location, project_id, region_id=0):
        ctx = {
            "session_id": f"{session_id}_{region_id}",
            "project_id": project_id,
            "region_id": region_id,
        }

        self.dbg("\n================ REQUEST ================")
        self.dbg("👤 USER:", user_question)

        # 1️⃣ INTENT
        self.memory.append_user(ctx["session_id"], user_question)
        intent_res = self.router.classify_intent(user_question)

        intent_id = intent_res["id"]
        intent_label = intent_res["label"]
        self.memory.set_ctx(ctx["session_id"], "last_intent", intent_label)

        self.dbg("🧠 INTENT:", intent_label, intent_res.get("score"))

        # 2️⃣ FOLLOW-UP
        if intent_id == 5:
            follow_of = self.memory.get_ctx(ctx["session_id"], "last_intent")
            msg = f"Bạn muốn làm rõ thêm về {follow_of} không?"
            self.memory.append_ai(ctx["session_id"], msg)

            return {
                "Message": msg,
                "location": None,
                "audio": None,
                "session_id": ctx["session_id"],
            }

        # 3️⃣ TARGET PLACE
        target_place = None
        if intent_id in [0, 1, 2, 4]:
            candidates = self.get_db_candidates(project_id, region_id)
            has_explicit = self._mentions_place_explicitly(user_question, candidates)

            last_place = self.memory.get_ctx(ctx["session_id"], "last_target_place")

            if not has_explicit and last_place:
                target_place = last_place
            else:
                target_place = self.router.find_target_place(user_question, candidates)
                if not target_place and last_place:
                    target_place = last_place

        if target_place:
            self.memory.set_ctx(ctx["session_id"], "last_target_place", target_place)

        self.dbg("🎯 TARGET:", target_place)

        # 4️⃣ WORKER ROUTE
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

        self.dbg("🧪 raw_data =", raw_data)

        # 5️⃣ RESPONSE
        if intent_label == "direction" and raw_data and raw_data.get("Location"):
            final_message = (
                f"{raw_data.get('SubProjectName')} nằm tại "
                f"{raw_data.get('Location')}. "
                "Bạn có thể dùng Google Maps để chỉ đường chi tiết."
            )
        else:
            final_message = self.synthesize_response(
                user_question, raw_data, intent_label
            )

        self.memory.append_ai(ctx["session_id"], final_message)

        # 6️⃣ FORMAT OUTPUT
        location = None
        audio = None

        if intent_label == "direction" and raw_data:
            location = raw_data.get("Location")

        if (
            intent_label == "media"
            and raw_data
            and raw_data.get("media_type", "").lower() == "audio"
        ):
            audio = raw_data.get("url")

        return {
            "Message": final_message,
            "location": location,
            "audio": audio,
            "session_id": ctx["session_id"],
        }
