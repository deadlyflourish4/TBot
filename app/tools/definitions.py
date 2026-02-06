"""
Tool definitions for TravelAgent.
LLM sẽ dựa vào schema này để quyết định tool nào cần gọi.
"""

TRAVEL_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_place_info",
            "description": "Lấy thông tin giới thiệu về một địa điểm du lịch. Dùng khi user hỏi 'giới thiệu về X', 'X là gì', 'kể về X'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "place_name": {
                        "type": "string",
                        "description": "Tên địa điểm cần tra cứu"
                    }
                },
                "required": ["place_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_place_location",
            "description": "Lấy vị trí, địa chỉ của một địa điểm. Dùng khi user hỏi 'X ở đâu', 'địa chỉ của X', 'cách đi đến X'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "place_name": {
                        "type": "string",
                        "description": "Tên địa điểm"
                    }
                },
                "required": ["place_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_place_media",
            "description": "Lấy video, audio về một địa điểm. Dùng khi user hỏi 'video về X', 'có clip X không'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "place_name": {
                        "type": "string",
                        "description": "Tên địa điểm"
                    },
                    "media_type": {
                        "type": "string",
                        "enum": ["video", "audio", "all"],
                        "description": "Loại media cần lấy",
                        "default": "video"
                    }
                },
                "required": ["place_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_attractions",
            "description": "Lấy danh sách điểm tham quan trong một địa điểm. Dùng khi user hỏi 'X có gì', 'có gì vui ở X'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "place_name": {
                        "type": "string",
                        "description": "Tên địa điểm"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Số lượng kết quả tối đa",
                        "default": 5
                    }
                },
                "required": ["place_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_places",
            "description": "Tìm kiếm địa điểm theo từ khóa. Dùng khi không biết chính xác tên địa điểm hoặc user hỏi 'có gì ở thành phố Y'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Từ khóa tìm kiếm"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Số kết quả trả về",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }
    }
]
