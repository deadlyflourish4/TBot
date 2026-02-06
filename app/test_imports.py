# test_imports.py
"""Test để kiểm tra các import trong project hoạt động đúng."""

import sys
sys.path.insert(0, ".")

def test_imports():
    """Kiểm tra tất cả imports."""
    errors = []
    
    # ===== Core imports =====
    try:
        from database.db import MultiDBManager
        print("✅ database.db.MultiDBManager")
    except Exception as e:
        errors.append(f"❌ database.db.MultiDBManager: {e}")
    
    try:
        from services.chat_manager import ChatManager
        print("✅ services.chat_manager.ChatManager")
    except Exception as e:
        errors.append(f"❌ services.chat_manager.ChatManager: {e}")
    
    try:
        from services.storage import GCStorage
        print("✅ services.storage.GCStorage")
    except Exception as e:
        errors.append(f"❌ services.storage.GCStorage: {e}")
    
    try:
        from pipeline import GraphOrchestrator
        print("✅ pipeline.GraphOrchestrator")
    except Exception as e:
        errors.append(f"❌ pipeline.GraphOrchestrator: {e}")
    
    try:
        from security.middleware import jwt_middleware
        print("✅ security.middleware.jwt_middleware")
    except Exception as e:
        errors.append(f"❌ security.middleware.jwt_middleware: {e}")
    
    # ===== NEW: Tools module =====
    try:
        from tools.definitions import TRAVEL_TOOLS
        print(f"✅ tools.definitions.TRAVEL_TOOLS ({len(TRAVEL_TOOLS)} tools)")
    except Exception as e:
        errors.append(f"❌ tools.definitions.TRAVEL_TOOLS: {e}")
    
    try:
        from tools.executor import ToolExecutor
        print("✅ tools.executor.ToolExecutor")
    except Exception as e:
        errors.append(f"❌ tools.executor.ToolExecutor: {e}")
    
    # ===== NEW: Agents module =====
    try:
        from agents.travel_agent import TravelAgent
        print("✅ agents.travel_agent.TravelAgent")
    except Exception as e:
        errors.append(f"❌ agents.travel_agent.TravelAgent: {e}")
    
    # ===== NEW: Tasks module =====
    try:
        from tasks import celery_app
        print("✅ tasks.celery_app")
    except Exception as e:
        errors.append(f"❌ tasks.celery_app: {e}")
    
    # Summary
    print("\n" + "="*50)
    if errors:
        print(f"❌ FAILED: {len(errors)} import error(s)")
        for err in errors:
            print(f"  {err}")
        return False
    else:
        print("✅ ALL IMPORTS PASSED!")
        return True

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
