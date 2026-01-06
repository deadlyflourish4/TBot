# services/chat_manager.py
"""
ChatManager: Quản lý phiên chat với session timeout và lưu trữ lịch sử.
"""

import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class ChatMessage:
    """Đại diện cho một tin nhắn trong phiên chat."""
    role: str  # "user" hoặc "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ChatSession:
    """Đại diện cho một phiên chat."""
    session_id: str
    region_id: int
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    messages: List[ChatMessage] = field(default_factory=list)

    def add_message(self, role: str, content: str) -> ChatMessage:
        """Thêm tin nhắn vào phiên chat."""
        message = ChatMessage(role=role, content=content)
        self.messages.append(message)
        self.last_activity = datetime.utcnow()
        return message

    def get_history(self, limit: Optional[int] = None) -> List[Dict]:
        """Lấy lịch sử chat dạng dict."""
        messages = self.messages[-limit:] if limit else self.messages
        return [
            {"role": m.role, "content": m.content, "timestamp": m.timestamp.isoformat()}
            for m in messages
        ]


class ChatManager:
    """
    Quản lý nhiều phiên chat với tự động timeout.
    
    Args:
        db_manager: Database manager instance (để lưu trữ nếu cần).
        session_timeout: Thời gian timeout phiên (giây), mặc định 30 phút.
    """

    def __init__(self, db_manager=None, session_timeout: int = 1800):
        self.db_manager = db_manager
        self.session_timeout = session_timeout
        self._sessions: Dict[str, ChatSession] = {}
        self._lock = threading.Lock()
        self._start_cleanup_thread()

    def create_session(
        self, region_id: int, session_id: Optional[str] = None
    ) -> ChatSession:
        """
        Tạo phiên chat mới.
        
        Args:
            region_id: ID vùng/region.
            session_id: ID phiên tùy chọn, tự động tạo nếu không có.
        
        Returns:
            ChatSession mới được tạo.
        """
        with self._lock:
            if session_id is None:
                session_id = str(uuid.uuid4())
            
            session = ChatSession(session_id=session_id, region_id=region_id)
            self._sessions[session_id] = session
            print(f"[ChatManager] ✅ Created session: {session_id[:8]}...")
            return session

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """
        Lấy phiên chat theo ID.
        
        Args:
            session_id: ID phiên cần tìm.
        
        Returns:
            ChatSession nếu tìm thấy và chưa hết hạn, None nếu không.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                # Cập nhật thời gian hoạt động cuối
                session.last_activity = datetime.utcnow()
            return session

    def delete_session(self, session_id: str) -> bool:
        """
        Xóa phiên chat.
        
        Args:
            session_id: ID phiên cần xóa.
        
        Returns:
            True nếu xóa thành công, False nếu không tìm thấy.
        """
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                print(f"[ChatManager] 🗑️ Deleted session: {session_id[:8]}...")
                return True
            return False

    def get_active_sessions_count(self) -> int:
        """Trả về số phiên đang hoạt động."""
        with self._lock:
            return len(self._sessions)

    def _cleanup_expired_sessions(self):
        """Dọn dẹp các phiên đã hết hạn."""
        while True:
            time.sleep(60)  # Kiểm tra mỗi phút
            now = datetime.utcnow()
            expired = []

            with self._lock:
                for session_id, session in self._sessions.items():
                    elapsed = (now - session.last_activity).total_seconds()
                    if elapsed > self.session_timeout:
                        expired.append(session_id)

                for session_id in expired:
                    del self._sessions[session_id]
                    print(f"[ChatManager] 💤 Expired session: {session_id[:8]}...")

    def _start_cleanup_thread(self):
        """Khởi động thread dọn dẹp phiên hết hạn."""
        t = threading.Thread(target=self._cleanup_expired_sessions, daemon=True)
        t.start()
