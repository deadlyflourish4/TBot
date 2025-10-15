import time 
import threading
import uuid
from Database.db import MultiDBManager

class ChatSession:
    def __init__(self, region_id: int, db_manager: MultiDBManager, session_id: str | None = None):
        self.session_id = session_id or str(uuid.uuid4())  
        self.region_id = region_id
        self.history = []
        self.last_used = time.time()
        self.db_session = db_manager.get_session(region_id)

    def add_message(self, role: str, content: str):
            self.history.append({"role": role, "content": content})
            self.last_used = time.time()

    def is_expired(self, timeout: int) -> bool:
            return (time.time() - self.last_used) > timeout
        
    def close_db(self):
            if self.db_session:
                try:
                    self.db_session.close()
                except Exception as e:
                    print(f"[ChatSession] Error closing DB session: {e}")
                self.db_session = None

class ChatManager:
    def __init__(self, db_manager: MultiDBManager, session_timeout: int = 3600):
        self.db_manager = db_manager
        self.sessions = {}
        self.session_timeout = session_timeout
        self.lock = threading.Lock()
        self.cleanup_thread = threading.Thread(target=self.cleanup_sessions, daemon=True)
        self.cleanup_thread.start()

    def create_session(self, region_id: int, session_id: str | None = None) -> ChatSession:
        with self.lock:
            session = ChatSession(region_id, self.db_manager, session_id=session_id)
            self.sessions[session.session_id] = session
            print(f"[ChatManager] Created session {session.session_id}")
            return session

    def get_session(self, session_id: str) -> ChatSession:
        with self.lock:
            session = self.sessions.get(session_id)
            if session:
                session.last_used = time.time()
            return session

    def cleanup_sessions(self):
        while True:
            time.sleep(300)  # Run cleanup every 5 minutes
            with self.lock:
                to_delete = [sid for sid, sess in self.sessions.items() if sess.is_expired(self.session_timeout)]
                for sid in to_delete:
                    sess = self.sessions.pop(sid)
                    sess.close_db()
                    print(f"[ChatManager] Session {sid} expired and removed.")