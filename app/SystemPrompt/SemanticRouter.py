# import re
# from typing import Dict, List, Optional

# import numpy as np
# import torch
# from sentence_transformers import SentenceTransformer
# from sklearn.metrics.pairwise import cosine_similarity


# class SemanticRouter:
#     def __init__(self):
#         # Load Model e5-large (Model này "trâu bò" nhất cho tiếng Việt hiện nay)
#         model_name = "intfloat/multilingual-e5-large"
#         device = "cuda" if torch.cuda.is_available() else "cpu"
#         print(f"🚀 Loading Router Model: {model_name} on {device.upper()}...")

#         self.model = SentenceTransformer(model_name, device=device)

#         # ==============================================================================
#         # 🛡️ 1. RULE-BASED: KEYWORD (VÒNG KIM CÔ)
#         # ==============================================================================
#         self.keyword_rules = {
#             0: [  # DIRECTION
#                 r"chỉ đường",
#                 r"đường đi",
#                 r"bản đồ",
#                 r"map",
#                 r"route",
#                 r"vị trí",
#                 r"location",
#                 r"ở đâu",
#                 r"đi thế nào",
#                 r"cách đi",
#                 r"khoảng cách",
#                 r"bao xa",
#                 r"tọa độ",
#                 r"gps",
#                 r"google map",
#                 r"direction",
#                 r"lối nào",
#                 r"định vị",
#                 r"(?i)\b(chỉ đường|hướng dẫn đi|cách đi|đường đến|dẫn đường|route)\b",
#                 r"(?i)\b(map|bản đồ|vị trí|tọa độ|gps|location)\b",
#                 r"(?i)\b(ở đâu)(?!\s*(có bán|bán|ngon|đẹp))\b",  # Ở đâu (nhưng không phải hỏi mua bán/tính chất)
#                 r"(?i)\b(bao xa|khoảng cách|mất bao lâu để đi)\b",
#                 r"(?i)\b(hướng dẫn|hướng|đường|đi|làm thế nào để đến|làm sao đến|chỉ đường|địa điểm|vị trí|map|bản đồ|navigation|route|path|directions|location|where|how to get|di chuyển|từ.*đến)\b",
#                 r"(?i)\b(ở đâu|nằm ở đâu|gần đây|gần nhất|xung quanh|khoảng cách|distance|nearby|around|proximity)\b",
#                 r"(?i)\b(ga tàu|trạm xe bus|sân bay|điểm dừng|station|airport|bus stop|train station)\b",
#                 r"(?i)\b(lối đi|ngã tư|ngã ba|intersection|crossroad|turn left|turn right|rẽ trái|rẽ phải)\b",
#                 r"(?i)\b(google map|maps|GPS|navigate|lead me to|dẫn đến)\b",
#                 r"(?i)\b(địa chỉ|address|where is|ở chỗ nào|chỗ nào vậy)\b",
#                 r"(?i)\b(tìm đường|tìm vị trí|search route|find way|lost|迷路|mê lộ)\b",
#                 r"(?i)\b(đi bộ|đi xe|by foot|by car|driving|walking|biking|xe đạp|xe máy)\b",
#                 r"(?i)\b(chỉ dẫn|way to|path to|how to reach|đến nơi|arrive at)\b",
#                 r"(?i)\b(tọa độ|coordinates|lat long|latitude|longitude)\b",
#                 r"(?i)\b(định vị|locate|pin point|share location|gửi vị trí)\b",
#                 r"(?i)\b(lạc đường|got lost|help direction|trợ giúp đường đi)\b",
#                 r"(?i)\b(điểm đến|destination|target place|điểm tham quan gần)\b",
#                 r"(?i)\b(cách di chuyển|mode of transport|public transport|công cộng)\b",
#                 r"(?i)\b(taxi|grab|uber|book car|đặt xe)\b",
#                 r"(?i)\b(đỗ xe|parking|park car|chỗ đỗ)\b",
#                 r"(?i)\b(thời gian di chuyển|travel time|how long to get)\b",
#                 r"(?i)\b(đường tắt|shortcut|alternative route|đường khác)\b",
#                 r"(?i)\b(tránh kẹt xe|avoid traffic|best time to go)\b",
#                 r"(?i)\b(hướng đông|tây|nam|bắc|north|south|east|west)\b",
#                 r"(?i)\b(qua cầu|cross bridge|qua sông|across river)\b",
#                 r"(?i)\b(đi thẳng|go straight|turn around|quay đầu)\b",
#                 r"(?i)\b(sân ga|platform|departure|arrival)\b",
#                 r"(?i)\b(chuyến tàu|train schedule|lịch tàu)\b",
#                 r"(?i)\b(xe buýt số|bus number|line number|tuyến xe)\b",
#                 r"(?i)\b(điểm đón|pickup point|drop off|thả xuống)\b",
#                 r"(?i)\b(bãi biển gần|nearest beach|closest mountain|gần núi)\b",
#                 r"(?i)\b(hiking trail|đường mòn|path for hiking)\b",
#                 r"(?i)\b(tour guide map|bản đồ hướng dẫn|guided route)\b",
#                 r"(?i)\b(virtual tour|chuyến đi ảo|3d map)\b",
#                 r"(?i)\b(apple maps|waze|alternative maps)\b",
#                 r"(?i)\b(offline map|bản đồ ngoại tuyến|download map)\b",
#                 r"(?i)\b(real time location|vị trí thời gian thực|live tracking)\b",
#                 r"(?i)\b(share route|chia sẻ đường đi|send directions)\b",
#                 r"(?i)\b(avoid toll|tránh phí|free route)\b",
#                 r"(?i)\b(scenic route|đường đẹp|beautiful path)\b",
#                 r"(?i)\b(emergency route|đường khẩn cấp|safe way)\b",
#                 r"(?i)\b(accessible path|đường cho người khuyết tật|wheelchair access)\b",
#                 r"(?i)\b(pet friendly route|đường cho thú cưng|with pets)\b",
#                 r"(?i)\b(group travel|di chuyển nhóm|for groups)\b",
#             ],
#             1: [  # MEDIA
#                 r"mở audio",
#                 r"nghe",
#                 r"xem video",
#                 r"phát nhạc",
#                 r"play",
#                 r"listen",
#                 r"watch",
#                 r"mp3",
#                 r"mp4",
#                 r"giọng đọc",
#                 r"thuyết minh",
#                 r"poi",
#                 r"clip",
#                 r"media",
#                 r"bật file",
#                 r"âm thanh",
#                 r"(?i)\b(phát|play|listen|watch|xem|nghe|audio|video|media|clip|film|movie|song|bài hát|nhạc|music|podcast)\b",
#                 r"(?i)\b(youtube|spotify|zing|nhaccuatui|stream|streaming|broadcast|phát sóng)\b",
#                 r"(?i)\b(hình ảnh|photo|picture|gallery|album|video hướng dẫn|tutorial video)\b",
#                 r"(?i)\b(chơi nhạc|play music|turn on|turn off|bật|tắt|pause|stop|resume|tiếp tục)\b",
#                 r"(?i)\b(trailer|preview|teaser|short clip|reel|tik tok|shorts)\b",
#                 r"(?i)\b(nghe thử|watch this|xem cái này|play that|phát cái kia)\b",
#                 r"(?i)\b(live stream|trực tiếp|broadcast live|streaming now)\b",
#                 r"(?i)\b(download|tải về|save media|ghi âm|record)\b",
#                 r"(?i)\b(volume|loudness|âm lượng|mute|im lặng)\b",
#                 r"(?i)\b(subtitles|phụ đề|caption|dịch)\b",
#                 r"(?i)\b(full screen|toàn màn hình|zoom in|phóng to)\b",
#                 r"(?i)\b(rewind|tua lại|fast forward|tua nhanh)\b",
#                 r"(?i)\b(playlist|danh sách phát|queue|hàng đợi)\b",
#                 r"(?i)\b(shuffle|ngẫu nhiên|random play)\b",
#                 r"(?i)\b(repeat|lặp lại|loop)\b",
#                 r"(?i)\b(equalizer|cân bằng âm|sound settings)\b",
#                 r"(?i)\b(virtual reality|vr video|360 degree)\b",
#                 r"(?i)\b(augmented reality|ar filter|thực tế ảo)\b",
#                 r"(?i)\b(podcast episode|tập podcast|listen now)\b",
#                 r"(?i)\b(music video|mv|bài hát có hình)\b",
#                 r"(?i)\b(documentary|phim tài liệu|docu series)\b",
#                 r"(?i)\b(animation|hoạt hình|cartoon)\b",
#                 r"(?i)\b(live concert|buổi biểu diễn trực tiếp)\b",
#                 r"(?i)\b(webinar|hội thảo trực tuyến|online talk)\b",
#                 r"(?i)\b(audiobook|sách nói|read aloud)\b",
#                 r"(?i)\b(ringtone|nhạc chuông|set as ring)\b",
#                 r"(?i)\b(background music|nhạc nền|ambient sound)\b",
#                 r"(?i)\b(sound effect|hiệu ứng âm thanh|fx)\b",
#                 r"(?i)\b(voice over|giọng lồng tiếng|narrate)\b",
#                 r"(?i)\b(interview|phỏng vấn|talk show)\b",
#                 r"(?i)\b(news clip|đoạn tin tức|news video)\b",
#                 r"(?i)\b(tutorial|hướng dẫn video|how to video)\b",
#                 r"(?i)\b(unboxing|mở hộp|review video)\b",
#                 r"(?i)\b(vlog|nhật ký video|daily vlog)\b",
#                 r"(?i)\b(asMR|âm thanh thư giãn|relaxing sound)\b",
#                 r"(?i)\b(karaoke|hát theo|sing along)\b",
#                 r"(?i)\b(lyrics|lời bài hát|song words)\b",
#                 r"(?i)\b(album art|ảnh bìa|cover image)\b",
#                 r"(?i)\b(share media|chia sẻ video|send clip)\b",
#             ],
#             4: [  # COUNT
#                 r"bao nhiêu",
#                 r"số lượng",
#                 r"có mấy",
#                 r"liệt kê",
#                 r"how many",
#                 r"count",
#                 r"danh sách",
#                 r"tổng cộng",
#                 r"tổng số",
#                 r"đếm xem",
#                 r"thống kê",
#                 r"list",
#                 r"(?i)\b(bao nhiêu|how many)(?!\s*(tiền|giá|cost|price))\b",  # Bao nhiêu nhưng không đi kèm tiền/giá
#                 r"(?i)\b(số lượng|tổng số|có mấy|đếm|liệt kê|thống kê|list|danh sách)\b",
#                 r"(?i)\b(top \d+|xếp hạng|rank)\b",
#                 r"(?i)\b(bao nhiêu)(.*)(cái|con|người|địa điểm|tỉnh|thành phố)\b",  # Bao nhiêu + danh từ đếm được
#                 r"(?i)\b(bao nhiêu|how many|count|số lượng|list|danh sách|structure|cấu trúc|number|số)\b",
#                 r"(?i)\b(có bao nhiêu|total|tổng cộng|quantity|how much in numbers|đếm)\b",
#                 r"(?i)\b(các loại|types|kinds|categories|phân loại|classify|group|nhóm)\b",
#                 r"(?i)\b(top 10|top 5|best list|danh sách tốt nhất|rank|xếp hạng)\b",
#                 r"(?i)\b(đếm số|enumerate|itemized list|bullet points|liệt kê)\b",
#                 r"(?i)\b(cấu tạo|composition|made of|gồm những gì|components|thành phần)\b",
#                 r"(?i)\b(so sánh|compare|how many vs|so với|số lượng so sánh)\b",
#                 r"(?i)\b(statistics|thống kê|data|số liệu|figures|con số)\b",
#                 r"(?i)\b(percentage|tỷ lệ|percent|phần trăm)\b",
#                 r"(?i)\b(average|trung bình|mean|median)\b",
#                 r"(?i)\b(max|tối đa|minimum|tối thiểu)\b",
#                 r"(?i)\b(range|khoảng|from to|từ đến)\b",
#                 r"(?i)\b(tally|đếm tay|manual count)\b",
#                 r"(?i)\b(inventory|hàng tồn kho|stock count)\b",
#                 r"(?i)\b(population count|dân số|people count)\b",
#                 r"(?i)\b(vehicle count|xe cộ|số xe)\b",
#                 r"(?i)\b(room count|số phòng|floors|tầng)\b",
#                 r"(?i)\b(item list|danh sách vật phẩm|items)\b",
#                 r"(?i)\b(menu count|số món|dishes)\b",
#                 r"(?i)\b(event count|số sự kiện|events)\b",
#                 r"(?i)\b(member count|thành viên|members)\b",
#                 r"(?i)\b(score count|điểm số|scores)\b",
#                 r"(?i)\b(vote count|bầu cử|votes)\b",
#                 r"(?i)\b(step count|bước chân|steps)\b",
#                 r"(?i)\b(calorie count|calo|calories)\b",
#                 r"(?i)\b(time count|thời gian|times)\b",
#                 r"(?i)\b(frequency|tần suất|how often)\b",
#                 r"(?i)\b(distribution|phân bố|spread)\b",
#                 r"(?i)\b(hierarchy|cấp bậc|levels)\b",
#                 r"(?i)\b(breakdown|phân tích|details count)\b",
#                 r"(?i)\b(aggregate|tổng hợp|sum up)\b",
#                 r"(?i)\b(group by|nhóm theo|grouped)\b",
#                 r"(?i)\b(sort by|sắp xếp theo|ordered list)\b",
#                 r"(?i)\b(filter list|lọc danh sách|filtered)\b",
#                 r"(?i)\b(unique count|số duy nhất|uniques)\b",
#                 r"(?i)\b(duplicate count|trùng lặp|duplicates)\b",
#                 r"(?i)\b(data points|điểm dữ liệu|points)\b",
#                 r"(?i)\b(chart count|biểu đồ|charts)\b",
#                 r"(?i)\b(table rows|hàng bảng|rows)\b",
#             ],
#             2: [  # INFO
#                 r"thông tin",
#                 r"lịch sử",
#                 r"giá vé",
#                 r"chi tiết",
#                 r"info",
#                 r"description",
#                 r"what is",
#                 r"giới thiệu",
#                 r"kể về",
#                 r"biết về",
#                 r"là gì",
#                 r"review",
#                 r"mô tả",
#                 r"tìm hiểu",
#                 r"sự tích",
#                 r"nguồn gốc",
#                 r"(?i)\b(giá|chi phí|tốn bao nhiêu|tiền|price|cost|how much)\b",  # Đưa hỏi giá về INFO
#                 r"(?i)\b(thông tin|info|chi tiết|lịch sử|nguồn gốc|ý nghĩa|mô tả)\b",
#                 r"(?i)\b(là gì|what is|như thế nào|ra sao)\b",
#                 r"(?i)\b(review|đánh giá|có ngon không|có đẹp không)\b",
#                 r"(?i)\b(giờ mở cửa|thời gian hoạt động|open time)\b",
#                 r"(?i)\b(thông tin|info|details|chi tiết|lịch sử|history|giá|price|cost|how much|bao nhiêu|facts|sự kiện)\b",
#                 r"(?i)\b(mô tả|description|what is|gì vậy|giới thiệu|introduce|about|về)\b",
#                 r"(?i)\b(đánh giá|review|rating|opinion|ý kiến|best|tốt nhất|worst|xấu nhất)\b",
#                 r"(?i)\b(giờ mở cửa|opening hours|time|schedule|lịch trình|when open|mở lúc nào)\b",
#                 r"(?i)\b(lý do|reason why|why|at sao|tại sao|background|nền tảng)\b",
#                 r"(?i)\b(tips|mẹo|advice|lời khuyên|recommend|gợi ý|suggestion)\b",
#                 r"(?i)\b(có gì đặc biệt|special features|unique|độc đáo|highlights|nổi bật)\b",
#                 r"(?i)\b(update|cập nhật|latest news|tin mới|current status|tình hình hiện tại)\b",
#                 r"(?i)\b(kiến trúc|architecture|design|thiết kế)\b",
#                 r"(?i)\b(văn hóa|culture|tradition|truyền thống)\b",
#                 r"(?i)\b(ẩm thực|food|cuisine|dish|món ăn)\b",
#                 r"(?i)\b(lễ hội|festival|event|sự kiện)\b",
#                 r"(?i)\b(du lịch|travel|tourism|du khách)\b",
#                 r"(?i)\b(an toàn|safety|secure|an ninh)\b",
#                 r"(?i)\b(môi trường|environment|eco|sinh thái)\b",
#                 r"(?i)\b(kinh tế|economy|business|kinh doanh)\b",
#                 r"(?i)\b(giáo dục|education|school|học tập)\b",
#                 r"(?i)\b(y tế|health|medical|sức khỏe)\b",
#                 r"(?i)\b(thể thao|sports|activity|hoạt động)\b",
#                 r"(?i)\b(giải trí|entertainment|fun|vui chơi)\b",
#                 r"(?i)\b(mua sắm|shopping|buy|mua)\b",
#                 r"(?i)\b(visa|thị thực|entry|nhập cảnh)\b",
#                 r"(?i)\b(tiền tệ|currency|exchange|đổi tiền)\b",
#                 r"(?i)\b(ngôn ngữ|language|speak|nói)\b",
#                 r"(?i)\b(dân cư|population|people|dân số)\b",
#                 r"(?i)\b(khí hậu|climate|weather|thời tiết)\b",
#                 r"(?i)\b(địa lý|geography|terrain|địa hình)\b",
#                 r"(?i)\b(flora|thực vật|fauna|động vật)\b",
#                 r"(?i)\b(heritage|di sản|unesco)\b",
#                 r"(?i)\b(art|nghệ thuật|music|âm nhạc)\b",
#                 r"(?i)\b(religion|tôn giáo|faith|niềm tin)\b",
#                 r"(?i)\b(politics|chính trị|government|chính phủ)\b",
#                 r"(?i)\b(technology|công nghệ|tech)\b",
#                 r"(?i)\b(innovation|sáng tạo|new ideas)\b",
#                 r"(?i)\b(sustainability|bền vững|sustainable)\b",
#                 r"(?i)\b(community|cộng đồng|local people)\b",
#                 r"(?i)\b(transport|giao thông|traffic)\b",
#                 r"(?i)\b(accommodation|chỗ ở|hotel|khách sạn)\b",
#                 r"(?i)\b(ticket|vé|admission|nhập)\b",
#             ],
#             3: [  # CHITCHAT
#                 r"xin chào",
#                 r"chào",
#                 r"hello",
#                 r"hi",
#                 r"cảm ơn",
#                 r"thanks",
#                 r"bot",
#                 r"giúp gì",
#                 r"chức năng",
#                 r"tạm biệt",
#                 r"bye",
#                 r"ngủ ngon",
#                 r"khỏe không",
#                 # 🔥 FIX LỖI Ở DÒNG DƯỚI NÀY: Dùng "..." thay vì '...' để bao chuỗi có '
#                 r"(?i)\b(xin chào|hello|hi|hey|chào|yo|sup|what's up|có khỏe không|how are you|làm gì vậy)\b",
#                 r"(?i)\b(cảm ơn|thanks|thank you|tks|bye|tạm biệt|see you|gặp lại|good night|ngủ ngon)\b",
#                 r"(?i)\b(thời tiết|weather|today|hôm nay|chat|talk|nói chuyện|small talk)\b",
#                 r"(?i)\b(cuối tuần|weekend|plans|kế hoạch|funny story|câu chuyện vui|joke|đùa)\b",
#                 r"(?i)\b(ok|ừ|yeah|đúng rồi|no|không|sao cũng được|whatever)\b",
#                 r"(?i)\b(bạn tên gì|your name|tên bot|gọi là gì|who are you|bạn là ai)\b",
#                 r"(?i)\b(chém gió|buôn dưa lê|chat chit|trò chuyện linh tinh|gossip|tin đồn)\b",
#                 r"(?i)\b(mood|tâm trạng|feeling|cảm giác|haha|lol|cười|smile)\b",
#                 r"(?i)\b(ăn gì|food today|ăn sáng|breakfast)\b",
#                 r"(?i)\b(uống cà phê|coffee|tea|trà)\b",
#                 r"(?i)\b(phim hay|movie recommendation|gợi ý phim)\b",
#                 r"(?i)\b(sách hay|book|read|đọc)\b",
#                 r"(?i)\b(thể thao|sports|football|bóng đá)\b",
#                 r"(?i)\b(du lịch plan|travel plans|kế hoạch du lịch)\b",
#                 r"(?i)\b(công việc|work|job|làm việc)\b",
#                 r"(?i)\b(học tập|study|school|học)\b",
#                 r"(?i)\b(gia đình|family|home|nhà)\b",
#                 r"(?i)\b(bạn bè|friends|hang out|gặp gỡ)\b",
#                 r"(?i)\b(sở thích|hobby|interest|thích)\b",
#                 r"(?i)\b(âm nhạc|music|song|bài hát)\b",
#                 r"(?i)\b(trò chơi|game|play|chơi)\b",
#                 r"(?i)\b(mua sắm|shopping|buy|mua)\b",
#                 r"(?i)\b(sức khỏe|health|exercise|tập luyện)\b",
#                 r"(?i)\b(nghỉ ngơi|relax|rest|nghỉ)\b",
#                 r"(?i)\b(kỳ nghỉ|holiday|vacation|nghỉ phép)\b",
#                 r"(?i)\b(sinh nhật|birthday|celebrate|chúc mừng)\b",
#                 r"(?i)\b(lễ hội|festival|event|sự kiện)\b",
#                 r"(?i)\b(tin tức|news|update|cập nhật)\b",
#                 r"(?i)\b(thời trang|fashion|clothes|quần áo)\b",
#                 r"(?i)\b(động vật|animals|pet|thú cưng)\b",
#                 r"(?i)\b(cây cối|plants|garden|vườn)\b",
#                 r"(?i)\b(du lịch|travel|trip|chuyến đi)\b",
#                 r"(?i)\b(ảnh đẹp|photo|picture|hình ảnh)\b",
#                 r"(?i)\b(video hay|video|clip)\b",
#                 r"(?i)\b(meme vui|meme|funny|buồn cười)\b",
#                 r"(?i)\b(câu hỏi ngẫu nhiên|random question|hỏi vu vơ)\b",
#                 r"(?i)\b(chuyện phiếm|idle talk|nói linh tinh)\b",
#                 r"(?i)\b(how is the day|ngày hôm nay thế nào)\b",
#             ],
#         }

#         self.intents = {
#             0: [  # DIRECTION - Aim for ~100 total
#                 "passage: Đường nào ngắn nhất để đi tới chợ Bến Thành?",
#                 "passage: Từ đây ra sân bay đi lối nào nhanh?",
#                 "passage: Google map chỉ đường về nhà.",
#                 "passage: Check vị trí hiện tại của tôi.",
#                 "passage: Gửi định vị qua Zalo cho tôi.",
#                 "passage: Tránh đường cao tốc khi đi Vũng Tàu."
#                 "passage: Làm thế nào để đi từ Hà Nội đến Sapa?",
#                 "passage: Chỉ đường đến chùa Một Cột ở đâu?",
#                 "passage: Bản đồ đến chợ Đồng Xuân thế nào?",
#                 "passage: Vị trí của hồ Hoàn Kiếm nằm ở đâu vậy?",
#                 "passage: How to get to Halong Bay from Hanoi?",
#                 "passage: Đường đi ngắn nhất đến Phú Quốc là gì?",
#                 "passage: Gần đây có quán cà phê nào không?",
#                 "passage: Khoảng cách từ đây đến sân bay Tân Sơn Nhất bao xa?",
#                 "passage: Chỉ tôi lối đi đến bảo tàng Hồ Chí Minh.",
#                 "passage: Map to the nearest hotel please.",
#                 "passage: Làm sao để di chuyển bằng xe bus đến Đà Nẵng?",
#                 "passage: Where is the train station in Ho Chi Minh City?",
#                 "passage: Hướng dẫn rẽ trái hay phải để đến chợ Bến Thành?",
#                 "passage: Tìm đường đi bộ đến cầu Rồng ở Đà Nẵng.",
#                 "passage: GPS lead me to the beach in Nha Trang.",
#                 "passage: Ở chỗ nào có bãi đỗ xe gần nhất?",
#                 "passage: Ngã tư này đi hướng nào đến Huế?",
#                 "passage: Distance between Hanoi and Hoi An?",
#                 "passage: Dẫn đến địa chỉ 123 Nguyễn Huệ, Sài Gòn.",
#                 "passage: Mê lộ rồi, giúp chỉ đường về khách sạn.",
#                 "passage: Biking route to the mountains in Dalat.",
#                 "passage: Xe máy đi từ đây đến Vũng Tàu mất bao lâu?",
#                 "passage: Nearby attractions around my location.",
#                 "passage: Turn by turn directions to the temple.",
#                 "passage: Làm thế nào để tránh kẹt xe khi đi đến trung tâm?",
#                 "passage: Position of the famous bridge in Can Tho.",
#                 "passage: Search route on Google Maps for me.",
#                 "passage: Từ sân bay về trung tâm thành phố bằng gì nhanh nhất?",
#                 "passage: Hướng dẫn chi tiết đến hang Sơn Đoòng.",
#                 "passage: Where can I find the bus stop nearby?",
#                 "passage: Path to the waterfall in the national park.",
#                 "passage: Di chuyển từ đảo này sang đảo kia thế nào?",
#                 "passage: Lost in the city, need directions home.",
#                 "passage: Proximity to the nearest gas station.",
#                 "passage: Chỗ nào là điểm dừng xe buýt gần nhất?",
#                 "passage: Navigate to the market in the old quarter.",
#                 "passage: Cách đi đến làng nghề thủ công ở ngoại ô.",
#                 "passage: Around here, where's the best viewpoint?",
#                 "passage: Rẽ phải ở ngã ba rồi đi thẳng phải không?",
#                 "passage: Location of the cable car station in Sapa.",
#                 "passage: Help me find my way to the rice terraces.",
#                 "passage: Đi từ đây đến đó mất bao nhiêu km?",
#                 "passage: Bản đồ 3D đến địa điểm du lịch nổi tiếng.",
#                 "passage: Chỉ đường bằng tiếng Việt nhé, tôi không rành English.",
#                 "passage: Nearest ATM machine where?",
#                 "passage: Hướng dẫn đến chợ nổi Cái Răng từ khách sạn.",
#                 "passage: Walking directions to the pagoda.",
#                 "passage: Xe đạp thuê ở đâu gần đây?",
#                 "passage: Route planning for a road trip in Vietnam.",
#                 "passage: Ở đâu có trạm tàu điện ngầm?",
#                 "passage: Cách đi đến chùa Thiên Mụ từ Huế trung tâm.",
#                 "passage: Location of the War Remnants Museum in Saigon.",
#                 "passage: Hướng dẫn đường đến chợ đêm Đà Lạt nhé.",
#                 "passage: Từ Nha Trang đến Đà Lạt đi xe gì nhanh?",
#                 "passage: Where is the famous lighthouse in Phu Quoc?",
#                 "passage: Di chuyển bằng phà đến Côn Đảo thế nào?",
#                 "passage: Tìm đường đến vườn quốc gia Cát Tiên.",
#                 "passage: Khoảng cách từ Hội An đến Mỹ Sơn bao xa?",
#                 "passage: Chỉ đường đến bảo tàng Chứng tích Chiến tranh.",
#                 "passage: Map to the floating market in Mekong Delta.",
#                 "passage: Làm sao đến được tháp Chăm Ponagar?",
#                 "passage: Nearest pharmacy around here please.",
#                 "passage: Hướng dẫn đi bộ đến hồ Xuân Hương.",
#                 "passage: From airport to hotel in Hanoi, how?",
#                 "passage: Vị trí của cổng thành cổ Huế ở đâu?",
#                 "passage: Road to the sand dunes in Mui Ne.",
#                 "passage: Tìm vị trí quán ăn ngon gần nhất.",
#                 "passage: Directions to the Independence Palace.",
#                 "passage: Cách di chuyển đến đảo Lý Sơn từ Quảng Ngãi.",
#                 "passage: Where's the closest supermarket?",
#                 "passage: Navigate me to the French Quarter in Hanoi.",
#                 "passage: Đường đi đến hang Múa ở Ninh Bình.",
#                 "passage: Distance to the nearest hospital.",
#                 "passage: Hướng dẫn đến chợ hoa Quảng Bá.",
#                 "passage: Bike path to the countryside villages.",
#                 "passage: Làm thế nào đến được suối Tiên ở Bà Nà Hills?",
#                 "passage: Location of the Golden Bridge in Da Nang.",
#                 "passage: Tìm đường xe máy đến Hà Giang.",
#                 "passage: From Hoi An to Hue by bus.",
#                 "passage: Chỉ tôi cách đến bãi biển Mỹ Khê.",
#                 "passage: Map for trekking in Sapa.",
#                 "passage: Khoảng cách đến động Phong Nha.",
#                 "passage: Directions to the Cu Chi Tunnels.",
#                 "passage: Way to the marble mountains.",
#                 "passage: Vị trí trạm xăng gần nhất ở đâu?",
#                 "passage: Navigate to the night market in Hoi An.",
#                 "passage: Road trip from Saigon to Dalat.",
#                 "passage: Hướng dẫn đến làng gốm Bát Tràng.",
#                 "passage: Where is the bus terminal in Can Tho?",
#                 "passage: Tìm lối đi đến chùa Linh Ứng.",
#                 "passage: Distance from here to Vung Tau beach.",
#                 "passage: Chỉ đường đến bảo tàng Dân tộc học.",
#                 "passage: Map to the hot springs in Nha Trang.",
#                 "passage: Làm sao đến được đảo Bình Ba?",
#                 "passage: Nearest coffee shop location.",
#                 "passage: Hướng dẫn di chuyển đến Mũi Né.",
#                 "passage: Path to the ancient town in Hoi An.",
#                 "passage: Từ Đà Nẵng đến Hội An bao xa?",
#                 "passage: Directions for cycling tour in Hue.",
#                 "passage: Vị trí của hồ Tuyền Lâm ở Đà Lạt.",
#                 "passage: Navigate to the Cao Dai Temple.",
#                 "passage: Way to the Mekong River cruise starting point.",
#                 "passage: Tìm đường đến vườn quốc gia Bạch Mã.",
#             ],
#             1: [  # MEDIA - Aim for ~100 total
#                 "passage: Next bài giúp tôi.",
#                 "passage: Tua nhanh đoạn này đi.",
#                 "passage: Tăng âm lượng lên mức 50.",
#                 "passage: Mở bài hát đang hot trên Top Trending.",
#                 "passage: Dừng nhạc lại ngay.",
#                 "passage: Play nhạc không lời để học bài."
#                 "passage: Phát bài hát dân ca Việt Nam đi.",
#                 "passage: Xem video hướng dẫn du lịch Huế.",
#                 "passage: Nghe nhạc bolero hay nhất.",
#                 "passage: Play some Vietnamese pop music.",
#                 "passage: Bật video về vịnh Hạ Long.",
#                 "passage: Stream podcast về lịch sử Việt Nam.",
#                 "passage: Watch trailer of a Vietnamese movie.",
#                 "passage: Phát nhạc EDM remix đi bot.",
#                 "passage: Listen to the audio guide for Hanoi.",
#                 "passage: Xem clip ngắn về ẩm thực đường phố.",
#                 "passage: Play YouTube video on Vietnamese culture.",
#                 "passage: Bật radio địa phương nghe thử.",
#                 "passage: Show me pictures of Sapa rice fields.",
#                 "passage: Nghe bài hát 'Hello Vietnam' nhé.",
#                 "passage: Video tutorial cách mặc áo dài.",
#                 "passage: Pause the music for a second.",
#                 "passage: Resume playing the song.",
#                 "passage: Turn off the video now.",
#                 "passage: Phát live stream từ chợ đêm.",
#                 "passage: Download audio tour for the museum.",
#                 "passage: Xem ảnh gallery về Đà Lạt.",
#                 "passage: Play funny Vietnamese comedy clip.",
#                 "passage: Nghe podcast du lịch Việt Nam mới nhất.",
#                 "passage: Watch this TikTok about street food.",
#                 "passage: Bật nhạc chill cho buổi tối.",
#                 "passage: Show video of traditional dance.",
#                 "passage: Listen to English-Vietnamese language lessons.",
#                 "passage: Phát clip hướng dẫn nấu phở.",
#                 "passage: Stop the media playback.",
#                 "passage: Xem phim tài liệu về chiến tranh Việt Nam.",
#                 "passage: Play some karaoke songs.",
#                 "passage: Nghe truyện audio về thần thoại Việt.",
#                 "passage: Watch shorts on Instagram about travel tips.",
#                 "passage: Bật âm thanh hướng dẫn tham quan.",
#                 "passage: Show me the music video of Sơn Tùng.",
#                 "passage: Listen to relaxing sounds of nature in Vietnam.",
#                 "passage: Phát video 360 độ về hang động.",
#                 "passage: Turn on subtitles for the video.",
#                 "passage: Xem album ảnh du lịch Phú Quốc.",
#                 "passage: Play playlist of top Vietnamese hits.",
#                 "passage: Nghe radio tin tức du lịch.",
#                 "passage: Watch live concert from Hanoi.",
#                 "passage: Bật clip meme vui về du lịch.",
#                 "passage: Show photo slideshow of beaches.",
#                 "passage: Listen to audiobook on Vietnamese history.",
#                 "passage: Phát video ASMR về chợ Việt.",
#                 "passage: Stop and play something else.",
#                 "passage: Xem phim ngắn về làng quê.",
#                 "passage: Play background music for chatting.",
#                 "passage: Nghe voice note từ hướng dẫn viên.",
#                 "passage: Bật nhạc rap Việt hay nhất.",
#                 "passage: Watch video tour of Hanoi old quarter.",
#                 "passage: Nghe bài hát truyền thống dân tộc.",
#                 "passage: Play classical music from Vietnam.",
#                 "passage: Xem clip nấu ăn món bún chả.",
#                 "passage: Listen to podcast on Vietnamese festivals.",
#                 "passage: Phát video drone quay vịnh Hạ Long.",
#                 "passage: Show images of traditional costumes.",
#                 "passage: Nghe audio story about legends.",
#                 "passage: Watch travel vlog in Sapa.",
#                 "passage: Bật nhạc ballad tình cảm.",
#                 "passage: Play sound effects of city life.",
#                 "passage: Xem trailer phim Việt mới ra.",
#                 "passage: Listen to guided meditation in Vietnamese.",
#                 "passage: Phát clip hài hước về du khách.",
#                 "passage: Show gallery of street art in Saigon.",
#                 "passage: Nghe radio FM địa phương.",
#                 "passage: Watch live stream from temple festival.",
#                 "passage: Bật audio hướng dẫn yoga.",
#                 "passage: Play songs from My Tam.",
#                 "passage: Xem video 4K về Đà Nẵng.",
#                 "passage: Listen to bird sounds in national park.",
#                 "passage: Phát podcast về kinh nghiệm du lịch.",
#                 "passage: Show photos of lanterns in Hoi An.",
#                 "passage: Nghe truyện ngắn Việt Nam.",
#                 "passage: Watch cooking tutorial for spring rolls.",
#                 "passage: Bật nhạc dance cho party.",
#                 "passage: Play ambient sounds for sleep.",
#                 "passage: Xem clip phỏng vấn người dân địa phương.",
#                 "passage: Listen to Vietnamese rock music.",
#                 "passage: Phát video lịch sử ngắn gọn.",
#                 "passage: Show image collection of mountains.",
#                 "passage: Nghe audio book về văn hóa Việt.",
#                 "passage: Watch funny skits about travel mishaps.",
#                 "passage: Bật nhạc jazz Việt Nam.",
#                 "passage: Play playlist for road trips.",
#                 "passage: Xem video time-lapse của thành phố.",
#                 "passage: Listen to traditional instrument music.",
#                 "passage: Phát clip hướng dẫn nhảy múa dân gian.",
#                 "passage: Show photos of wildlife in Vietnam.",
#                 "passage: Nghe podcast phỏng vấn du lịch.",
#                 "passage: Watch virtual tour of museums.",
#                 "passage: Bật âm thanh sóng biển thư giãn.",
#                 "passage: Play songs about love in Vietnamese.",
#                 "passage: Xem album ảnh lễ hội.",
#                 "passage: Listen to news audio in Vietnamese.",
#                 "passage: Phát video hướng dẫn học tiếng Việt.",
#                 "passage: Show gallery of food dishes.",
#                 "passage: Nghe truyện ma Việt Nam.",
#                 "passage: Watch comedy show clips.",
#                 "passage: Bật nhạc hip hop mới.",
#                 "passage: Play relaxing piano covers.",
#             ],
#             2: [  # INFO - Aim for ~100 total
#                 "passage: Vé máy bay đi Đà Nẵng bao nhiêu tiền?",  # Có 'bao nhiêu' nhưng là INFO
#                 "passage: Chi phí ăn ở tại Sapa thế nào?",
#                 "passage: Món phở này làm từ nguyên liệu gì?",
#                 "passage: Tại sao Hội An lại nổi tiếng?",
#                 "passage: Chùa này xây dựng năm bao nhiêu?",  # Hỏi năm (thông tin), không phải đếm
#                 "passage: Thông tin về lịch sử chùa Thiên Mụ là gì?",
#                 "passage: Giá vé vào vịnh Hạ Long bao nhiêu?",
#                 "passage: Chi tiết về lễ hội ở Hội An.",
#                 "passage: What is the history of the Cu Chi tunnels?",
#                 "passage: Giới thiệu về ẩm thực Việt Nam.",
#                 "passage: Review về khách sạn ở Sài Gòn tốt nhất.",
#                 "passage: Giờ mở cửa của bảo tàng Dân tộc học.",
#                 "passage: Lý do nên thăm Đà Nẵng vào mùa hè.",
#                 "passage: Tips du lịch tiết kiệm ở Việt Nam.",
#                 "passage: Có gì đặc biệt ở chợ nổi Cái Bè?",
#                 "passage: Update tình hình thời tiết ở Phú Quốc.",
#                 "passage: Description of the Mekong Delta.",
#                 "passage: Ý kiến về tour kayak ở Hạ Long.",
#                 "passage: When is the best time to visit Sapa?",
#                 "passage: Chi phí ăn uống trung bình ở Hà Nội.",
#                 "passage: Background về văn hóa người dân tộc.",
#                 "passage: Recommend các món ăn phải thử ở Huế.",
#                 "passage: Facts thú vị về hồ Ba Bể.",
#                 "passage: Latest news về du lịch Việt Nam.",
#                 "passage: Mô tả chi tiết về cáp treo Fansipan.",
#                 "passage: Price for a visa to Vietnam?",
#                 "passage: Lịch sử ngắn gọn về triều Nguyễn.",
#                 "passage: Advice cho du khách lần đầu đến Việt Nam.",
#                 "passage: Current status của các di tích UNESCO.",
#                 "passage: What makes Phu Quoc unique?",
#                 "passage: Đánh giá về phương tiện giao thông công cộng.",
#                 "passage: Giới thiệu về festival âm nhạc ở Đà Nẵng.",
#                 "passage: How much does a sim card cost in Vietnam?",
#                 "passage: Thông tin về bảo hiểm du lịch cần thiết.",
#                 "passage: Special features of Vietnamese coffee.",
#                 "passage: Review homestay ở Mai Châu.",
#                 "passage: Lý do tại sao Hà Giang đẹp nhất mùa tam giác mạch.",
#                 "passage: Tips an toàn khi đi xe máy ở Việt Nam.",
#                 "passage: Description of the lantern festival in Hoi An.",
#                 "passage: Chi tiết về vườn quốc gia Cúc Phương.",
#                 "passage: Opinion on the best beaches in Vietnam.",
#                 "passage: Giờ cao điểm ở chợ Đồng Xuân.",
#                 "passage: Background on Vietnamese silk weaving.",
#                 "passage: Recommend sách về du lịch Việt Nam.",
#                 "passage: Facts về động vật hoang dã ở Việt Nam.",
#                 "passage: Update về quy định COVID cho du khách.",
#                 "passage: Mô tả về kiến trúc chùa ở Việt Nam.",
#                 "passage: Price range for street food.",
#                 "passage: Lịch sử của phố cổ Hà Nội.",
#                 "passage: Advice cho backpackers ở Việt Nam.",
#                 "passage: What is the currency exchange rate?",
#                 "passage: Thông tin về lễ hội Tết Nguyên Đán.",
#                 "passage: Review về tour thuyền ở Ninh Bình.",
#                 "passage: Lý do thăm hang động Phong Nha.",
#                 "passage: Chi tiết về bảo tàng Mỹ thuật Việt Nam.",
#                 "passage: Best time to visit Halong Bay.",
#                 "passage: Giới thiệu về làng nghề gốm Bát Tràng.",
#                 "passage: Facts about the Red River Delta.",
#                 "passage: Recommend restaurants in Hanoi.",
#                 "passage: History of the Cham Towers.",
#                 "passage: Tips for shopping in markets.",
#                 "passage: Description of Ba Na Hills.",
#                 "passage: Price of train tickets to Sapa.",
#                 "passage: Update on beach resorts in Nha Trang.",
#                 "passage: What is special about Con Dao islands?",
#                 "passage: Review of eco-tours in Mekong.",
#                 "passage: Lý do nên thử cà phê trứng Hà Nội.",
#                 "passage: Advice on avoiding scams in Vietnam.",
#                 "passage: Current weather in Dalat.",
#                 "passage: Mô tả về chợ nổi Cái Răng.",
#                 "passage: Facts about Vietnamese New Year.",
#                 "passage: Recommend hiking trails in Sapa.",
#                 "passage: History of the Imperial Citadel in Hue.",
#                 "passage: Tips for vegetarian food in Vietnam.",
#                 "passage: Description of My Son Sanctuary.",
#                 "passage: Price for boat tours in Halong.",
#                 "passage: Update about national parks.",
#                 "passage: What makes Hanoi unique?",
#                 "passage: Review of luxury hotels in Phu Quoc.",
#                 "passage: Lý do thăm Ninh Binh.",
#                 "passage: Advice for family travel in Vietnam.",
#                 "passage: Current events in Saigon.",
#                 "passage: Mô tả về ẩm thực đường phố.",
#                 "passage: Facts about Vietnamese tea.",
#                 "passage: Recommend spas in Hoi An.",
#                 "passage: History of French influence in Vietnam.",
#                 "passage: Tips for budget travel.",
#                 "passage: Description of Cat Ba Island.",
#                 "passage: Price of flights within Vietnam.",
#                 "passage: Update on visa extensions.",
#                 "passage: What is the best souvenir from Vietnam?",
#                 "passage: Review of adventure tours.",
#                 "passage: Lý do yêu thích Đà Nẵng.",
#                 "passage: Advice on learning Vietnamese.",
#                 "passage: Current trends in Vietnamese tourism.",
#                 "passage: Mô tả về làng chài ở Phú Quốc.",
#                 "passage: Facts about biodiversity in Vietnam.",
#                 "passage: Recommend cultural shows.",
#                 "passage: History of water puppetry.",
#                 "passage: Tips for photography in Vietnam.",
#                 "passage: Description of Fansipan mountain.",
#                 "passage: Price for cooking classes.",
#                 "passage: Update about festivals this year.",
#                 "passage: What to pack for Vietnam trip?",
#                 "passage: Review of homestays in Ha Giang.",
#             ],
#             3: [  # CHITCHAT - Aim for ~100 total
#                 "passage: Xin chào, hôm nay thế nào?",
#                 "passage: Cảm ơn bạn nhé!",
#                 "passage: Bye, hẹn gặp lại.",
#                 "passage: How are you doing today?",
#                 "passage: Thời tiết hôm nay đẹp quá.",
#                 "passage: Bạn tên gì vậy?",
#                 "passage: Kể chuyện vui đi.",
#                 "passage: Haha, cái đó buồn cười thật.",
#                 "passage: Cuối tuần bạn làm gì?",
#                 "passage: Ok, hiểu rồi.",
#                 "passage: Chém gió tí nào.",
#                 "passage: Buôn dưa lê về du lịch đi.",
#                 "passage: Mood hôm nay của bạn thế nào?",
#                 "passage: Yeah, đúng rồi đấy.",
#                 "passage: No, không phải vậy.",
#                 "passage: Sao cũng được, tùy bạn.",
#                 "passage: Good night, ngủ ngon nhé.",
#                 "passage: Hey, sup bro?",
#                 "passage: What's up in Vietnam these days?",
#                 "passage: Cười lol, meme hay quá.",
#                 "passage: Bạn là ai, bot à?",
#                 "passage: Trò chuyện linh tinh tí.",
#                 "passage: Gossip về celeb Việt Nam đi.",
#                 "passage: Feeling tired after traveling.",
#                 "passage: Smile, ngày mới vui vẻ.",
#                 "passage: Đùa thôi, đừng giận nhé.",
#                 "passage: Plans for the holiday?",
#                 "passage: Small talk about food?",
#                 "passage: Ừ, tao nghĩ vậy.",
#                 "passage: Yo, chào mày.",
#                 "passage: Thanks a lot, bro.",
#                 "passage: See you later, alligator.",
#                 "passage: How's life treating you?",
#                 "passage: Chat chit về phim Việt.",
#                 "passage: Haha, that's funny.",
#                 "passage: Bạn khỏe không, lâu rồi không gặp.",
#                 "passage: Tâm trạng buồn, an ủi đi.",
#                 "passage: Whatever, không quan trọng.",
#                 "passage: Joke of the day please.",
#                 "passage: Gặp lại sau nhé.",
#                 "passage: Sup, ready for adventure?",
#                 "passage: Cảm giác thế nào khi là bot?",
#                 "passage: Tin đồn mới nhất là gì?",
#                 "passage: Yeah, let's talk more.",
#                 "passage: No worries, it's fine.",
#                 "passage: Buổi sáng tốt lành.",
#                 "passage: Kể về bản thân đi.",
#                 "passage: Lol, couldn't stop laughing.",
#                 "passage: Plans du lịch sắp tới?",
#                 "passage: Ăn gì chưa, bot?",
#                 "passage: Hôm nay mệt quá.",
#                 "passage: Chào buổi tối vui vẻ.",
#                 "passage: Bạn thích màu gì?",
#                 "passage: Kể chuyện ma đi.",
#                 "passage: Haha, vui thật đấy.",
#                 "passage: Weekend plans gì không?",
#                 "passage: Ừm, có lẽ vậy.",
#                 "passage: Chém gió về thời tiết.",
#                 "passage: Buôn chuyện về sao Việt.",
#                 "passage: Mood buồn, nghe nhạc đi.",
#                 "passage: Yep, agree with you.",
#                 "passage: Nah, not really.",
#                 "passage: Anything goes, up to you.",
#                 "passage: Sweet dreams tonight.",
#                 "passage: Hey there, what's new?",
#                 "passage: What's happening around?",
#                 "passage: Lol, that's hilarious.",
#                 "passage: Are you a real person?",
#                 "passage: Let's chat randomly.",
#                 "passage: Rumors about travel spots.",
#                 "passage: Feeling excited for trip.",
#                 "passage: Grin, have a great day.",
#                 "passage: Just kidding, no offense.",
#                 "passage: Holiday ideas anyone?",
#                 "passage: Casual talk on movies.",
#                 "passage: Yeah, I think so too.",
#                 "passage: Yo dude, hello.",
#                 "passage: Appreciate it, man.",
#                 "passage: Catch you later.",
#                 "passage: How's everything going?",
#                 "passage: Chit chat about music.",
#                 "passage: Hehe, so amusing.",
#                 "passage: Long time no see, how are ya?",
#                 "passage: Cheer up, sad mood.",
#                 "passage: Doesn't matter, anyway.",
#                 "passage: Daily joke please.",
#                 "passage: See ya soon.",
#                 "passage: What's up, adventure time?",
#                 "passage: Being a bot feels like?",
#                 "passage: Latest gossip here?",
#                 "passage: Sure, continue chatting.",
#                 "passage: It's okay, don't worry.",
#                 "passage: Good morning sunshine.",
#                 "passage: Tell me about yourself.",
#                 "passage: ROFL, too funny.",
#                 "passage: Upcoming travel plans?",
#                 "passage: Had lunch yet?",
#                 "passage: Feeling lazy today.",
#                 "passage: Evening greetings.",
#                 "passage: What's your fave color?",
#             ],
#             4: [  # COUNT - Aim for ~100 total
#                 "passage: Có tất cả bao nhiêu dân tộc anh em?",
#                 "passage: Đếm xem có bao nhiêu cây cầu ở Đà Nẵng.",
#                 "passage: Liệt kê danh sách 5 ngọn núi cao nhất.",
#                 "passage: Tổng cộng có mấy chuyến bay một ngày?",
#                 "passage: Cho tôi danh sách các tỉnh miền Tây."
#                 "passage: Có bao nhiêu tỉnh ở Việt Nam?",
#                 "passage: List các di sản UNESCO ở Việt Nam.",
#                 "passage: Số lượng món ăn nổi tiếng ở Huế.",
#                 "passage: How many islands in Halong Bay?",
#                 "passage: Cấu trúc của tour du lịch 7 ngày.",
#                 "passage: Top 10 khách sạn ở Sài Gòn.",
#                 "passage: Đếm số loại trái cây ở miền Nam.",
#                 "passage: Các loại phương tiện giao thông ở Hà Nội.",
#                 "passage: Total dân số của Đà Nẵng.",
#                 "passage: Rank các bãi biển đẹp nhất Việt Nam.",
#                 "passage: Liệt kê các lễ hội lớn trong năm.",
#                 "passage: Số lượng chùa cổ ở Huế.",
#                 "passage: Compare số lượng du khách năm nay và năm ngoái.",
#                 "passage: Thống kê về du lịch Việt Nam.",
#                 "passage: How many steps to the top of the mountain?",
#                 "passage: Danh sách các hãng hàng không nội địa.",
#                 "passage: Cấu tạo của món phở truyền thống.",
#                 "passage: Số liệu về chiều dài sông Mekong.",
#                 "passage: Top 5 địa điểm trekking ở Việt Nam.",
#                 "passage: Enumerate các loại cà phê Việt.",
#                 "passage: Total number of national parks.",
#                 "passage: Count the famous bridges in Vietnam.",
#                 "passage: List all provinces in the North.",
#                 "passage: How many ethnic groups in Vietnam?",
#                 "passage: Structure of a typical Vietnamese meal.",
#                 "passage: Top 20 tourist attractions.",
#                 "passage: Đếm số đảo ở Phú Quốc.",
#                 "passage: Các loại rượu Việt Nam.",
#                 "passage: Population of Hanoi city.",
#                 "passage: Rank best street foods.",
#                 "passage: Liệt kê festival âm nhạc.",
#                 "passage: Number of temples in Hanoi.",
#                 "passage: Compare population North vs South.",
#                 "passage: Statistics on rice export.",
#                 "passage: How many caves in Phong Nha?",
#                 "passage: List domestic airports.",
#                 "passage: Composition of banh mi.",
#                 "passage: Data on Vietnam's coastline length.",
#                 "passage: Top 15 homestays in Sapa.",
#                 "passage: Enumerate types of transportation.",
#                 "passage: Total visitors to Halong last year.",
#                 "passage: Count the markets in Saigon.",
#                 "passage: List all UNESCO sites details.",
#                 "passage: How many dishes in royal cuisine?",
#                 "passage: Structure of Vietnamese family.",
#                 "passage: Top 10 waterfalls in Vietnam.",
#                 "passage: Đếm loại hoa ở Đà Lạt.",
#                 "passage: Các loại xe máy phổ biến.",
#                 "passage: Population growth rate.",
#                 "passage: Rank cities by size.",
#                 "passage: Liệt kê các món chay.",
#                 "passage: Number of rivers in Mekong Delta.",
#                 "passage: Compare tourism revenue.",
#                 "passage: Thống kê xe đạp ở Hà Nội.",
#                 "passage: How many pagodas in Hue?",
#                 "passage: Danh sách các bảo tàng.",
#                 "passage: Cấu tạo của áo dài.",
#                 "passage: Số liệu về núi cao nhất.",
#                 "passage: Top 5 coffee shops chains.",
#                 "passage: Enumerate festivals by month.",
#                 "passage: Total lakes in Vietnam.",
#                 "passage: Count the ethnic minorities.",
#                 "passage: List all beaches in Central.",
#                 "passage: How many trains daily to Sapa?",
#                 "passage: Structure of education system.",
#                 "passage: Top 25 must-see places.",
#                 "passage: Đếm số loại bia Việt.",
#                 "passage: Các loại trái cây nhiệt đới.",
#                 "passage: Population of ethnic groups.",
#                 "passage: Rank best hotels by stars.",
#                 "passage: Liệt kê các di tích lịch sử.",
#                 "passage: Number of islands in Nha Trang bay.",
#                 "passage: Compare flight prices.",
#                 "passage: Statistics on motorbikes.",
#                 "passage: How many hotels in Phu Quoc?",
#                 "passage: List international airports.",
#                 "passage: Composition of spring rolls.",
#                 "passage: Data on tourism growth.",
#                 "passage: Top 10 trekking routes.",
#                 "passage: Enumerate types of silk.",
#                 "passage: Total heritage sites.",
#                 "passage: Count the famous lakes.",
#                 "passage: List all mountains over 2000m.",
#                 "passage: How many types of pho?",
#                 "passage: Structure of a festival.",
#                 "passage: Top 20 food stalls.",
#                 "passage: Đếm loại rau củ ở chợ.",
#                 "passage: Các loại tàu thuyền.",
#                 "passage: Population density map.",
#                 "passage: Rank provinces by area.",
#                 "passage: Liệt kê các làng nghề.",
#                 "passage: Number of zoos in Vietnam.",
#                 "passage: Compare bus vs train.",
#                 "passage: Thống kê du thuyền.",
#                 "passage: How many cable cars?",
#                 "passage: Danh sách các suối nước nóng.",
#                 "passage: Cấu tạo của nón lá.",
#                 "passage: Số liệu về rừng quốc gia.",
#                 "passage: Top 5 bird watching spots.",
#             ],
#         }

#         # Cache Vector (Chạy 1 lần khi khởi động)
#         # Việc này sẽ tốn khoảng 5-10s lúc khởi động app nhưng bù lại lúc chạy cực nhanh
#         self.intent_vectors = {}
#         for k, v in self.intents.items():
#             self.intent_vectors[k] = self.model.encode(v, normalize_embeddings=True)

#         print(
#             f"✅ Hybrid Router Ready with {sum(len(v) for v in self.intents.values())} examples!"
#         )

#     # --------------------------------------------------------------------------
#     # CLASSIFY FUNCTION (GIỮ NGUYÊN LOGIC CŨ VÌ ĐÃ TỐI ƯU)
#     # --------------------------------------------------------------------------
#     def classify_intent(self, text: str, threshold=0.65) -> dict:
#         if not text:
#             return {"id": 3, "label": "chitchat", "score": 0}

#         text_lower = text.lower()
#         labels = {0: "direction", 1: "media", 2: "info", 3: "chitchat", 4: "count"}

#         # 1. Regex (Ưu tiên tuyệt đối)
#         for intent_id, keywords in self.keyword_rules.items():
#             for kw in keywords:
#                 if re.search(kw, text_lower):
#                     return {
#                         "id": intent_id,
#                         "label": labels[intent_id],
#                         "score": 1.0,
#                         "method": "keyword",
#                     }

#         # 2. Embedding (Dự phòng cho câu phức tạp)
#         query_vec = self.model.encode([f"query: {text}"], normalize_embeddings=True)
#         scores = {}
#         for intent, vectors in self.intent_vectors.items():
#             scores[intent] = np.max(cosine_similarity(query_vec, vectors))

#         best_id = max(scores, key=scores.get)
#         best_score = float(scores[best_id])

#         # Threshold chặn rác
#         if best_score < threshold:
#             return {
#                 "id": 3,
#                 "label": "fallback",
#                 "score": best_score,
#                 "method": "fallback",
#             }

#         return {
#             "id": best_id,
#             "label": labels[best_id],
#             "score": best_score,
#             "method": "embedding",
#         }

#     # --------------------------------------------------------------------------
#     # FIND TARGET PLACE (SEMANTIC SEARCH)
#     # --------------------------------------------------------------------------
#     def find_target_place(
#         self, user_query: str, candidates: List[Dict[str, str]]
#     ) -> Optional[Dict]:
#         if not candidates:
#             return None

#         # Prefix 'passage:' cho tên địa điểm trong DB
#         candidate_texts = [f"passage: {c['name']}" for c in candidates]

#         query_vec = self.model.encode(
#             [f"query: {user_query}"], normalize_embeddings=True
#         )
#         candidate_vecs = self.model.encode(candidate_texts, normalize_embeddings=True)

#         similarities = cosine_similarity(query_vec, candidate_vecs)[0]
#         best_idx = np.argmax(similarities)
#         best_score = similarities[best_idx]

#         # print(f"🔎 Match: '{user_query}' ~= '{candidates[best_idx]['name']}' ({best_score:.3f})")

#         if best_score > 0.78:
#             return candidates[best_idx]
#         return None


import re
from typing import Dict, List, Optional

import numpy as np
import torch

# from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# =========================================================
# INTENT DEFINITIONS (GIỮ ID CŨ)
# =========================================================
INTENT_LABELS = {
    0: "direction",
    1: "media",
    2: "info",
    3: "chitchat",
    4: "count",
    5: "follow_up",
}

# Priority resolve khi hòa điểm
INTENT_PRIORITY = [5, 0, 4, 2, 1, 3]  # direction > count > info > media > chitchat

# Scoring config
HARD_SCORE = 3
SOFT_SCORE = 1
MIN_RULE_SCORE = 3  # đủ mạnh để KHÔNG cần embedding


# =========================================================
# KEYWORD RULES (ĐÃ LỌC – KHÔNG THAM)
# =========================================================
INTENT_RULES = {
    5: {  # DIRECTION
        "hard": [
            r"\b(xa không|gần không)\b",
            r"\b(bao lâu|mất bao lâu)\b",
            r"\b(còn không|vẫn không)\b",
            r"\b(thế còn|còn nữa)\b",
            r"\b(ở gần đây không)\b",
        ],
        "soft": ["xa", "gần", "lâu", "còn", "nữa"],
    },
    0: {  # DIRECTION
        "hard": [
            r"\b(chỉ đường|how to get|map to|đường đi đến)\b",
            r"\b(từ .* đến)\b",
            r"\b(turn left|turn right|rẽ trái|rẽ phải)\b",
            r"\b(gps|google map|navigate to|lead me to)\b",
        ],
        "soft": ["đường", "map", "route", "vị trí", "ở đâu", "đi thế nào"],
    },
    1: {  # MEDIA
        "hard": [
            r"\b(play|listen|watch|xem video|nghe audio|phát nhạc)\b",
        ],
        "soft": ["audio", "video", "nhạc", "clip", "mp3", "mp4"],
    },
    2: {  # INFO
        "hard": [
            r"\b(là gì|what is|lịch sử|history|giới thiệu)\b",
            r"\b(giờ mở cửa|opening hours)\b",
        ],
        "soft": ["giá", "chi tiết", "review", "thông tin", "mô tả"],
    },
    4: {  # COUNT
        "hard": [
            r"\b(có bao nhiêu|how many|total number)\b",
        ],
        "soft": ["bao nhiêu", "số lượng", "liệt kê", "danh sách", "đếm"],
    },
    3: {  # CHITCHAT
        "hard": [
            r"\b(xin chào|hello|hi|bye|thanks)\b",
        ],
        "soft": ["haha", "lol", "ok", "uhm"],
    },
}


# =========================================================
# SEMANTIC ROUTER CLASS
# =========================================================
class SemanticRouter:
    def __init__(self):
        from sentence_transformers import SentenceTransformer

        model_name = "anansupercuteeeee/multilingual-travelling"
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"🚀 Loading Semantic Router Model: {model_name} on {device.upper()}")
        self.last_intent_id = None
        self.last_target_place = None
        self.model = SentenceTransformer(model_name, device=device)

        # -------------------------------------------------
        # INTENT EXAMPLES (EMBEDDING FALLBACK)
        # -------------------------------------------------
        self.intent_examples = {
            0: [
                "passage: chỉ đường đến chợ Bến Thành",
                "passage: how to get to the airport",
                "passage: map to the nearest hotel",
                "passage: từ Hà Nội đến Sapa đi thế nào",
            ],
            1: [
                "passage: play music",
                "passage: nghe audio guide",
                "passage: xem video du lịch",
                "passage: bật nhạc thư giãn",
                "passage: có audio Dinh Độc Lập không",
                "passage: mở audio về Dinh Độc Lập",
            ],
            2: [
                "passage: giá vé bao nhiêu",
                "passage: lịch sử chùa Thiên Mụ",
                "passage: thông tin về địa đạo Củ Chi",
                "passage: giờ mở cửa bảo tàng",
                "passage: giới thiệu Dinh Độc Lập",
                "passage: thông tin về Dinh Độc Lập",
            ],
            3: [
                "passage: xin chào",
                "passage: cảm ơn bạn",
                "passage: hôm nay thế nào",
                "passage: nói chuyện chút nhé",
            ],
            4: [
                "passage: có bao nhiêu tỉnh ở Việt Nam",
                "passage: liệt kê các di sản UNESCO",
                "passage: số lượng chùa ở Huế",
                "passage: how many islands in Halong Bay",
            ],
        }

        # Encode intent vectors (chạy 1 lần khi khởi động)
        self.intent_vectors = {
            k: self.model.encode(v, normalize_embeddings=True)
            for k, v in self.intent_examples.items()
        }

        print("✅ SemanticRouter ready (rule + embedding + priority)")

    # =====================================================
    # INTERNAL: SCORE ONE INTENT
    # =====================================================
    def _score_intent(self, text: str, intent_id: int) -> int:
        rules = INTENT_RULES[intent_id]
        score = 0

        for pattern in rules["hard"]:
            if re.search(pattern, text, re.IGNORECASE):
                score += HARD_SCORE

        for kw in rules["soft"]:
            if kw in text:
                score += SOFT_SCORE

        return score

    # =====================================================
    # MAIN CLASSIFIER
    # =====================================================
    def classify_intent(self, text: str, threshold: float = 0.65) -> Dict:
        if not text or not text.strip():
            return {
                "id": 3,
                "label": "chitchat",
                "score": 0.0,
                "method": "empty",
            }

        text = text.lower()

        # =====================================================
        # FOLLOW-UP CHECK (CÂU NGẮN, KHÔNG ĐỦ NGHĨA)
        # =====================================================
        tokens = text.split()

        if len(tokens) <= 4 and self.last_intent_id is not None:
            follow_score = self._score_intent(text, 5)
            if follow_score >= HARD_SCORE:
                return {
                    "id": 5,
                    "label": "follow_up",
                    "score": float(follow_score),
                    "method": "context",
                    "follow_of": INTENT_LABELS[self.last_intent_id],
                }

        # -----------------------------
        # 1️⃣ RULE-BASED SCORING
        # -----------------------------
        scores = {
            intent_id: self._score_intent(text, intent_id)
            for intent_id in INTENT_RULES
            if intent_id != 5
        }

        max_score = max(scores.values())

        if max_score >= MIN_RULE_SCORE:
            candidates = [k for k, v in scores.items() if v == max_score]

            for intent_id in INTENT_PRIORITY:
                if intent_id in candidates:
                    self.last_intent_id = intent_id
                    return {
                        "id": intent_id,
                        "label": INTENT_LABELS[intent_id],
                        "score": float(max_score),
                        "method": "rule",
                    }

        # -----------------------------
        # 2️⃣ EMBEDDING FALLBACK
        # -----------------------------
        query_vec = self.model.encode([f"query: {text}"], normalize_embeddings=True)

        sim_scores = {}
        for intent_id, vectors in self.intent_vectors.items():
            sim_scores[intent_id] = float(np.max(cosine_similarity(query_vec, vectors)))

        best_intent = max(sim_scores, key=sim_scores.get)
        best_score = sim_scores[best_intent]

        if best_score < threshold:
            self.last_intent_id = 3
            return {
                "id": 3,
                "label": "fallback",
                "score": best_score,
                "method": "fallback",
            }
        self.last_intent_id = best_intent
        return {
            "id": best_intent,
            "label": INTENT_LABELS[best_intent],
            "score": best_score,
            "method": "embedding",
        }

    # =====================================================
    # OPTIONAL: DEBUG TOOL
    # =====================================================
    def debug_scores(self, text: str) -> Dict[int, int]:
        text = text.lower()
        return {
            intent_id: self._score_intent(text, intent_id) for intent_id in INTENT_RULES
        }

    def find_target_place(
        self, user_query: str, candidates: List[Dict[str, str]]
    ) -> Optional[Dict]:
        if not candidates:
            return None

        # Prefix 'passage:' cho tên địa điểm trong DB
        candidate_texts = [f"passage: {c['name']}" for c in candidates]

        query_vec = self.model.encode(
            [f"query: {user_query}"], normalize_embeddings=True
        )
        candidate_vecs = self.model.encode(candidate_texts, normalize_embeddings=True)

        similarities = cosine_similarity(query_vec, candidate_vecs)[0]
        best_idx = np.argmax(similarities)
        best_score = similarities[best_idx]

        # print(f"🔎 Match: '{user_query}' ~= '{candidates[best_idx]['name']}' ({best_score:.3f})")

        if best_score > 0.78:
            return candidates[best_idx]
        return None
