"""
ToolExecutor: Execute tools based on LLM decisions.
Handles multi-region database queries with fallback to vector search.
"""
import logging
from typing import Any, Dict, Optional

from sqlalchemy import text

logger = logging.getLogger(__name__)


class ToolExecutor:
    """Execute travel-related tools for TravelAgent."""

    def __init__(self, db_manager, vector_store=None):
        """
        Args:
            db_manager: MultiDBManager instance for SQL queries
            vector_store: Optional TravelVectorStore for search_places
        """
        self.db = db_manager
        self.vector_store = vector_store
        
        self.registry = {
            "get_place_info": self._get_place_info,
            "get_place_location": self._get_place_location,
            "get_place_media": self._get_place_media,
            "get_attractions": self._get_attractions,
            "search_places": self._search_places,
        }

    async def execute(
        self, 
        tool_name: str, 
        args: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a tool with given arguments and context.
        
        Args:
            tool_name: Name of tool to execute
            args: Tool arguments from LLM
            context: {region_id, project_id, user_location}
            
        Returns:
            Tool execution result as dict
        """
        if tool_name not in self.registry:
            logger.error(f"Unknown tool: {tool_name}")
            return {"error": f"Unknown tool: {tool_name}"}
        
        try:
            handler = self.registry[tool_name]
            result = await handler(args, context)
            logger.info(f"Tool {tool_name} executed successfully")
            return result
        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}")
            return {"error": str(e)}

    # =========================================================================
    # TOOL IMPLEMENTATIONS
    # =========================================================================

    async def _get_place_info(self, args: Dict, ctx: Dict) -> Dict:
        """Get place introduction from database."""
        region_id = ctx.get("region_id", 0)
        project_id = ctx.get("project_id", 1)
        place_name = args["place_name"]
        
        prefix = self.db.DB_MAP[region_id]["prefix"]
        engine = self.db.get_engine(region_id)
        
        sql = f"""
        SELECT SubProjectName, Introduction 
        FROM {prefix}.SubProjects 
        WHERE SubProjectName LIKE :place_name 
        AND ProjectID = :project_id
        """
        
        with engine.connect() as conn:
            row = conn.execute(
                text(sql),
                {"place_name": f"%{place_name}%", "project_id": project_id}
            ).fetchone()
        
        if row:
            return {
                "found": True,
                "name": row.SubProjectName,
                "introduction": row.Introduction or "Không có thông tin",
                "source": "database"
            }
        
        # Fallback to vector search if available
        if self.vector_store:
            logger.info(f"SQL miss for '{place_name}', trying vector search")
            return await self._search_places({"query": place_name, "top_k": 1}, ctx)
        
        return {"found": False, "message": f"Không tìm thấy thông tin về {place_name}"}

    async def _get_place_location(self, args: Dict, ctx: Dict) -> Dict:
        """Get place location from database."""
        region_id = ctx.get("region_id", 0)
        project_id = ctx.get("project_id", 1)
        place_name = args["place_name"]
        
        prefix = self.db.DB_MAP[region_id]["prefix"]
        engine = self.db.get_engine(region_id)
        
        sql = f"""
        SELECT SubProjectName, Location 
        FROM {prefix}.SubProjects 
        WHERE SubProjectName LIKE :place_name 
        AND ProjectID = :project_id
        """
        
        with engine.connect() as conn:
            row = conn.execute(
                text(sql),
                {"place_name": f"%{place_name}%", "project_id": project_id}
            ).fetchone()
        
        if row:
            return {
                "found": True,
                "name": row.SubProjectName,
                "location": row.Location or "Không có thông tin địa chỉ",
                "source": "database"
            }
        
        return {"found": False, "message": f"Không tìm thấy vị trí của {place_name}"}

    async def _get_place_media(self, args: Dict, ctx: Dict) -> Dict:
        """Get media files for a place."""
        region_id = ctx.get("region_id", 0)
        project_id = ctx.get("project_id", 1)
        place_name = args["place_name"]
        media_type = args.get("media_type", "video")
        
        prefix = self.db.DB_MAP[region_id]["prefix"]
        engine = self.db.get_engine(region_id)
        
        # Build media type filter
        media_filter = ""
        if media_type != "all":
            media_filter = "AND am.MediaType = :media_type"
        
        sql = f"""
        SELECT TOP 5
            sp.SubProjectName, 
            a.AttractionName, 
            am.MediaType, 
            am.MediaURL 
        FROM {prefix}.SubProjects sp 
        JOIN {prefix}.SubProjectAttractions a ON sp.SubProjectID = a.SubProjectID 
        JOIN {prefix}.SubProjectAttractionMedia am ON a.SubProjectAttractionID = am.SubProjectAttractionID 
        WHERE sp.SubProjectName LIKE :place_name 
        AND sp.ProjectID = :project_id
        {media_filter}
        """
        
        params = {
            "place_name": f"%{place_name}%",
            "project_id": project_id,
        }
        if media_type != "all":
            params["media_type"] = media_type
        
        with engine.connect() as conn:
            rows = conn.execute(text(sql), params).fetchall()
        
        if rows:
            media_list = [
                {
                    "attraction": r.AttractionName,
                    "type": r.MediaType,
                    "url": r.MediaURL
                }
                for r in rows
            ]
            return {
                "found": True,
                "name": rows[0].SubProjectName,
                "media": media_list,
                "count": len(media_list),
                "source": "database"
            }
        
        return {"found": False, "message": f"Không tìm thấy media của {place_name}"}

    async def _get_attractions(self, args: Dict, ctx: Dict) -> Dict:
        """Get attractions within a place."""
        region_id = ctx.get("region_id", 0)
        project_id = ctx.get("project_id", 1)
        place_name = args["place_name"]
        limit = args.get("limit", 5)
        
        prefix = self.db.DB_MAP[region_id]["prefix"]
        engine = self.db.get_engine(region_id)
        
        sql = f"""
        SELECT TOP {limit} 
            sp.SubProjectName, 
            a.AttractionName, 
            a.Introduction 
        FROM {prefix}.SubProjects sp 
        JOIN {prefix}.SubProjectAttractions a ON sp.SubProjectID = a.SubProjectID 
        WHERE sp.SubProjectName LIKE :place_name 
        AND sp.ProjectID = :project_id 
        ORDER BY a.SortOrder
        """
        
        with engine.connect() as conn:
            rows = conn.execute(
                text(sql),
                {"place_name": f"%{place_name}%", "project_id": project_id}
            ).fetchall()
        
        if rows:
            attractions = [
                {
                    "name": r.AttractionName,
                    "description": (r.Introduction or "")[:200]
                }
                for r in rows
            ]
            return {
                "found": True,
                "place": rows[0].SubProjectName,
                "attractions": attractions,
                "count": len(attractions),
                "source": "database"
            }
        
        # Fallback to vector search
        if self.vector_store:
            logger.info(f"No attractions found for '{place_name}', trying vector search")
            return await self._search_places({"query": f"điểm tham quan {place_name}", "top_k": 3}, ctx)
        
        return {"found": False, "message": f"Không tìm thấy điểm tham quan tại {place_name}"}

    async def _search_places(self, args: Dict, ctx: Dict) -> Dict:
        """Search places using vector store."""
        query = args["query"]
        top_k = args.get("top_k", 5)
        
        if not self.vector_store:
            # Placeholder until Qdrant is setup in Phase 2
            logger.warning("Vector store not configured, returning empty results")
            return {
                "found": False,
                "message": "Tìm kiếm vector chưa được cấu hình. Vui lòng thử lại với tên địa điểm cụ thể.",
                "source": "vector_store"
            }
        
        results = await self.vector_store.search(
            query=query,
            region_id=ctx.get("region_id"),
            project_id=ctx.get("project_id"),
            top_k=top_k
        )
        
        if results:
            return {
                "found": True,
                "places": results,
                "count": len(results),
                "source": "vector_store"
            }
        
        return {"found": False, "message": f"Không tìm thấy kết quả cho '{query}'"}
