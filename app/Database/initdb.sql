CREATE DATABASE Orpheo;
use Orpheo;

CREATE TABLE Tours (
    tour_id INT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(255) NOT NULL,
    destination NVARCHAR(255) NOT NULL,
    duration NVARCHAR(50),             -- ví dụ: 3N2Đ
    price DECIMAL(12,2) NOT NULL,
    discount_price DECIMAL(12,2) NULL,
    description NVARCHAR(MAX),
    includes_flight BIT DEFAULT 0,
    created_at DATETIME DEFAULT GETDATE()
);
CREATE TABLE Itineraries (
    itinerary_id INT IDENTITY(1,1) PRIMARY KEY,
    tour_id INT NOT NULL FOREIGN KEY REFERENCES Tours(tour_id),
    day_number INT NOT NULL,
    activity NVARCHAR(MAX) NOT NULL
);
CREATE TABLE Services (
    service_id INT IDENTITY(1,1) PRIMARY KEY,
    tour_id INT NOT NULL FOREIGN KEY REFERENCES Tours(tour_id),
    name NVARCHAR(255) NOT NULL,
    type NVARCHAR(100)  -- ví dụ: Khách sạn, Ăn uống, Di chuyển
);
CREATE TABLE Company_Info (
    company_id INT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(255) NOT NULL,
    description NVARCHAR(MAX),
    hotline NVARCHAR(50),
    email NVARCHAR(255),
    address NVARCHAR(255)
);
CREATE TABLE Company_Schedule (
    schedule_id INT IDENTITY(1,1) PRIMARY KEY,
    company_id INT NOT NULL FOREIGN KEY REFERENCES Company_Info(company_id),
    date_available DATE NOT NULL,
    status NVARCHAR(50) CHECK (status IN ('Available', 'Unavailable')),
    note NVARCHAR(255)
);
CREATE TABLE Customers (
    customer_id INT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(255) NOT NULL,
    phone NVARCHAR(50),
    email NVARCHAR(255),
    nationality NVARCHAR(100)
);

SET IDENTITY_INSERT Tours ON;

INSERT INTO Tours (tour_id, name, destination, duration, price, discount_price, description, includes_flight)
VALUES
(1, N'Đà Nẵng', N'Đà Nẵng', N'3N2Đ', 4500000, 4000000, N'Thăm Ngũ Hành Sơn, Bà Nà Hills, biển Mỹ Khê', 1),
(2, N'Hà Nội', N'Hà Nội', N'2N1Đ', 3000000, NULL, N'Thủ đô ngàn năm văn hiến, tham quan Lăng Bác, Văn Miếu', 0),
(3, N'Hạ Long', N'Hạ Long', N'2N1Đ', 3500000, 3200000, N'Du thuyền trên vịnh, ngủ tàu sang trọng', 1),
(4, N'Phú Quốc', N'Phú Quốc', N'4N3Đ', 7000000, 6500000, N'Thăm Vinpearl Safari, lặn ngắm san hô, check-in Sunset Sanato', 1),
(5, N'Huế', N'Huế', N'3N2Đ', 4000000, NULL, N'Thành phố di sản, tham quan Đại Nội, chùa Thiên Mụ', 0),
(6, N'Sa Pa', N'Sa Pa', N'3N2Đ', 5000000, 4500000, N'Thưởng ngoạn Fansipan, bản Cát Cát, Tả Van', 0),
(7, N'Ninh Bình', N'Ninh Bình', N'2N1Đ', 2800000, NULL, N'Tham quan Tràng An, Tam Cốc, chùa Bái Đính', 0),
(8, N'Đà Lạt', N'Đà Lạt', N'3N2Đ', 4200000, 3900000, N'Hồ Xuân Hương, Thung lũng Tình Yêu, Langbiang', 0),
(9, N'Cần Thơ', N'Cần Thơ', N'2N1Đ', 2500000, NULL, N'Chợ nổi Cái Răng, vườn trái cây miệt vườn', 0),
(10, N'Hội An', N'Hội An', N'2N1Đ', 3200000, 3000000, N'Phố cổ Hội An, chùa Cầu, đèn lồng lung linh', 0),
(11, N'Mũi Né', N'Mũi Né', N'3N2Đ', 3800000, 3500000, N'Đồi cát bay, Bãi biển Mũi Né, suối Tiên', 0),
(12, N'Côn Đảo', N'Côn Đảo', N'3N2Đ', 6000000, 5700000, N'Thăm nghĩa trang Hàng Dương, bãi Đầm Trầu', 1),
(13, N'Quy Nhơn', N'Quy Nhơn', N'3N2Đ', 5200000, NULL, N'Eo Gió, Kỳ Co, Tháp Đôi', 1),
(14, N'Nha Trang', N'Nha Trang', N'4N3Đ', 6500000, 6000000, N'VinWonders, tắm bùn, đảo Hòn Mun', 1),
(15, N'Buôn Ma Thuột', N'Buôn Ma Thuột', N'2N1Đ', 3100000, NULL, N'Thác Dray Nur, Buôn Đôn, thưởng thức cà phê', 0),
(16, N'Pleiku', N'Pleiku', N'2N1Đ', 3300000, NULL, N'Biển Hồ, chùa Minh Thành, núi Hàm Rồng', 0),
(17, N'Vũng Tàu', N'Vũng Tàu', N'2N1Đ', 2600000, 2400000, N'Tượng Chúa Kito, Bãi Sau, ngọn Hải Đăng', 0),
(18, N'Bình Định', N'Bình Định', N'4N3Đ', 5500000, 5200000, N'Tháp Bánh Ít, Hầm Hô, bãi biển Ghềnh Ráng', 0),
(19, N'Quảng Bình', N'Quảng Bình', N'3N2Đ', 4800000, 4500000, N'Động Phong Nha, hang Sơn Đoòng (tham quan ngoài)', 1),
(20, N'Cà Mau', N'Cà Mau', N'3N2Đ', 3700000, NULL, N'Mũi Cà Mau, vườn quốc gia U Minh Hạ', 0);

SET IDENTITY_INSERT Tours OFF;

select * from Tours

-- Lịch trình cho 20 tours
INSERT INTO Itineraries (tour_id, day_number, activity) VALUES
-- Đà Nẵng
(1,1,N'Đón khách tại sân bay, tham quan Ngũ Hành Sơn, biển Mỹ Khê'),
(1,2,N'Trải nghiệm Bà Nà Hills, Cầu Vàng, Fantasy Park'),
(1,3,N'Tự do mua sắm chợ Hàn, tiễn sân bay'),

-- Hà Nội
(2,1,N'Thăm Lăng Bác, Văn Miếu Quốc Tử Giám'),
(2,2,N'Hồ Hoàn Kiếm, phố cổ, thưởng thức ẩm thực Hà Nội'),

-- Hạ Long
(3,1,N'Du thuyền trên vịnh, tham quan hang Sửng Sốt'),
(3,2,N'Ngắm bình minh, chèo kayak, trả khách'),

-- Phú Quốc
(4,1,N'Đón khách, tham quan Dinh Cậu, chợ đêm'),
(4,2,N'Thăm Vinpearl Safari, tắm biển Bãi Sao'),
(4,3,N'Lặn ngắm san hô, cáp treo Hòn Thơm'),
(4,4,N'Mua sắm đặc sản, tiễn sân bay'),

-- Huế
(5,1,N'Thăm Đại Nội, chùa Thiên Mụ'),
(5,2,N'Du thuyền sông Hương, nghe ca Huế'),
(5,3,N'Tự do mua sắm, trả khách'),

-- Sa Pa
(6,1,N'Tham quan bản Cát Cát, Tả Phìn'),
(6,2,N'Chinh phục Fansipan bằng cáp treo'),
(6,3,N'Tự do dạo chợ Sa Pa, mua đặc sản'),

-- Ninh Bình
(7,1,N'Tham quan Tràng An, Tam Cốc'),
(7,2,N'Chùa Bái Đính, thưởng thức dê núi Ninh Bình'),

-- Đà Lạt
(8,1,N'Hồ Xuân Hương, quảng trường Lâm Viên'),
(8,2,N'Thung lũng Tình Yêu, Langbiang'),
(8,3,N'Chợ Đà Lạt, mua đặc sản'),

-- Cần Thơ
(9,1,N'Chợ nổi Cái Răng, tham quan vườn trái cây'),
(9,2,N'Nhà cổ Bình Thủy, thưởng thức đờn ca tài tử'),

-- Hội An
(10,1,N'Thăm phố cổ, chùa Cầu, thưởng thức Cao Lầu'),
(10,2,N'Chụp ảnh đèn lồng, mua sắm đặc sản'),

-- Mũi Né
(11,1,N'Đồi cát bay, Bãi biển Mũi Né'),
(11,2,N'Suối Tiên, Làng chài Mũi Né'),
(11,3,N'Tự do nghỉ dưỡng, trả khách'),

-- Côn Đảo
(12,1,N'Thăm nghĩa trang Hàng Dương, mộ chị Võ Thị Sáu'),
(12,2,N'Tham quan bảo tàng Côn Đảo, chùa Núi Một'),
(12,3,N'Tắm biển Đầm Trầu, mua đặc sản hải sản khô'),

-- Quy Nhơn
(13,1,N'Tham quan Eo Gió, Kỳ Co'),
(13,2,N'Tháp Đôi, Ghềnh Ráng'),
(13,3,N'Tự do tắm biển, thưởng thức hải sản'),

-- Nha Trang
(14,1,N'Tham quan VinWonders, biển Trần Phú'),
(14,2,N'Tắm bùn, hải sản Nha Trang'),
(14,3,N'Đi đảo Hòn Mun, lặn ngắm san hô'),
(14,4,N'Mua sắm quà lưu niệm, trả khách'),

-- Buôn Ma Thuột
(15,1,N'Thăm thác Dray Nur, Buôn Đôn'),
(15,2,N'Thưởng thức cà phê Tây Nguyên, bảo tàng Cà phê'),

-- Pleiku
(16,1,N'Tham quan Biển Hồ, chùa Minh Thành'),
(16,2,N'Leo núi Hàm Rồng, thưởng thức ẩm thực Pleiku'),

-- Vũng Tàu
(17,1,N'Tượng Chúa Kito, Bãi Sau'),
(17,2,N'Ngọn hải đăng, chợ hải sản Vũng Tàu'),

-- Bình Định
(18,1,N'Tháp Bánh Ít, bảo tàng Quang Trung'),
(18,2,N'Hầm Hô, thưởng thức bánh xèo tôm nhảy'),
(18,3,N'Ghềnh Ráng, bãi biển Hoàng Hậu'),
(18,4,N'Mua đặc sản tré Bình Định, trả khách'),

-- Quảng Bình
(19,1,N'Tham quan Động Phong Nha'),
(19,2,N'Khám phá hang Thiên Đường'),
(19,3,N'Tham quan vườn quốc gia Phong Nha - Kẻ Bàng'),

-- Cà Mau
(20,1,N'Tham quan Mũi Cà Mau, cột mốc tọa độ quốc gia'),
(20,2,N'Vườn quốc gia U Minh Hạ, thưởng thức cá lóc nướng'),
(20,3,N'Chợ nổi Cà Mau, mua đặc sản khô cá');

select * from Itineraries

SELECT activity
FROM Itineraries
WHERE tour_id = 1 AND day_number = 2;

-- Dịch vụ cho 20 tours
INSERT INTO Services (tour_id, name, type) VALUES
-- Đà Nẵng
(1,N'Khách sạn 4 sao ven biển',N'Khách sạn'),
(1,N'Buffet Bà Nà Hills',N'Ăn uống'),
(1,N'Xe đưa đón sân bay',N'Di chuyển'),

-- Hà Nội
(2,N'Khách sạn 3 sao trung tâm',N'Khách sạn'),
(2,N'Bún chả Hà Nội',N'Ăn uống'),

-- Hạ Long
(3,N'Du thuyền ngủ đêm 4 sao',N'Khách sạn'),
(3,N'Hải sản trên tàu',N'Ăn uống'),
(3,N'Thuyền kayak miễn phí',N'Di chuyển'),

-- Phú Quốc
(4,N'Resort 5 sao ven biển',N'Khách sạn'),
(4,N'Buffet hải sản',N'Ăn uống'),
(4,N'Xe điện tham quan đảo',N'Di chuyển'),

-- Huế
(5,N'Khách sạn 3 sao gần sông Hương',N'Khách sạn'),
(5,N'Cơm hến Huế',N'Ăn uống'),

-- Sa Pa
(6,N'Khách sạn view núi',N'Khách sạn'),
(6,N'Thắng cố, rượu ngô bản địa',N'Ăn uống'),
(6,N'Xe ô tô giường nằm khứ hồi Hà Nội – Sa Pa',N'Di chuyển'),

-- Ninh Bình
(7,N'Khách sạn mini 2 sao',N'Khách sạn'),
(7,N'Cơm cháy dê núi',N'Ăn uống'),
(7,N'Thuyền tham quan Tràng An',N'Di chuyển'),

-- Đà Lạt
(8,N'Khách sạn 3 sao trung tâm',N'Khách sạn'),
(8,N'Lẩu gà lá é',N'Ăn uống'),

-- Cần Thơ
(9,N'Nhà nghỉ miệt vườn',N'Khách sạn'),
(9,N'Cá lóc nướng trui',N'Ăn uống'),
(9,N'Thuyền tham quan chợ nổi',N'Di chuyển'),

-- Hội An
(10,N'Khách sạn boutique phố cổ',N'Khách sạn'),
(10,N'Cao Lầu, Mì Quảng',N'Ăn uống'),

-- Mũi Né
(11,N'Khách sạn 3 sao ven biển',N'Khách sạn'),
(11,N'Hải sản nướng Mũi Né',N'Ăn uống'),

-- Côn Đảo
(12,N'Khách sạn 4 sao view biển',N'Khách sạn'),
(12,N'Hải sản Côn Đảo',N'Ăn uống'),
(12,N'Xe đưa đón sân bay',N'Di chuyển'),

-- Quy Nhơn
(13,N'Khách sạn 4 sao ven biển',N'Khách sạn'),
(13,N'Bánh xèo tôm nhảy',N'Ăn uống'),

-- Nha Trang
(14,N'Khách sạn 4 sao trung tâm',N'Khách sạn'),
(14,N'Buffet hải sản Nha Trang',N'Ăn uống'),
(14,N'Tàu cao tốc ra đảo',N'Di chuyển'),

-- Buôn Ma Thuột
(15,N'Khách sạn 3 sao nội thành',N'Khách sạn'),
(15,N'Cà phê Tây Nguyên',N'Ăn uống'),

-- Pleiku
(16,N'Khách sạn 2 sao trung tâm',N'Khách sạn'),
(16,N'Phở khô Gia Lai',N'Ăn uống'),

-- Vũng Tàu
(17,N'Khách sạn 3 sao gần biển',N'Khách sạn'),
(17,N'Lẩu cá đuối Vũng Tàu',N'Ăn uống'),

-- Bình Định
(18,N'Khách sạn 3 sao Quy Nhơn',N'Khách sạn'),
(18,N'Trẻ Bình Định, bánh ít lá gai',N'Ăn uống'),

-- Quảng Bình
(19,N'Khách sạn 3 sao trung tâm Đồng Hới',N'Khách sạn'),
(19,N'Hải sản Quảng Bình',N'Ăn uống'),

-- Cà Mau
(20,N'Nhà nghỉ Cà Mau',N'Khách sạn'),
(20,N'Cua Cà Mau, cá thòi lòi nướng',N'Ăn uống'),
(20,N'Thuyền tham quan Mũi Cà Mau',N'Di chuyển');

INSERT INTO Company_Info (name, description, hotline, email, address)
VALUES
(N'Orpheo Travel', 
 N'Công ty du lịch Orpheo với hơn 10 năm kinh nghiệm, cung cấp tour trong và ngoài nước với chất lượng dịch vụ hàng đầu.', 
 N'1900-9999',
 N'contact@orpheo.com',
 N'123 Lê Lợi, Quận 1, TP.HCM');

-- Tháng 10/2025
DECLARE @d DATE = '2025-10-01';
WHILE @d <= '2025-10-31'
BEGIN
    INSERT INTO Company_Schedule (company_id, date_available, status, note)
    VALUES
    (1, @d,
     CASE 
        WHEN DAY(@d) IN (2,5,8,11,15,25) THEN 'Unavailable'
        ELSE 'Available'
     END,
     CASE 
        WHEN DAY(@d) = 2 THEN N'Quá tải đoàn khách'
        WHEN DAY(@d) = 5 THEN N'Nghỉ lễ nội bộ'
        WHEN DAY(@d) = 8 THEN N'Bảo trì hệ thống'
        WHEN DAY(@d) = 11 THEN N'Full booking đoàn 200 khách'
        WHEN DAY(@d) = 15 THEN N'Tour đoàn công ty lớn'
        WHEN DAY(@d) = 25 THEN N'Nghỉ lễ'
        ELSE N'Lịch bình thường'
     END);
    SET @d = DATEADD(DAY,1,@d);
END;

-- Tháng 11/2025
SET @d = '2025-11-01';
WHILE @d <= '2025-11-30'
BEGIN
    INSERT INTO Company_Schedule (company_id, date_available, status, note)
    VALUES
    (1, @d,
     CASE 
        WHEN DAY(@d) IN (3,9,15,25) THEN 'Unavailable'
        ELSE 'Available'
     END,
     CASE 
        WHEN DAY(@d) = 3 THEN N'Bảo trì định kỳ'
        WHEN DAY(@d) = 9 THEN N'Full booking đoàn'
        WHEN DAY(@d) = 15 THEN N'Nghỉ lễ địa phương'
        WHEN DAY(@d) = 25 THEN N'Sự kiện công ty'
        ELSE N'Lịch bình thường'
     END);
    SET @d = DATEADD(DAY,1,@d);
END;

-- Tháng 12/2025
SET @d = '2025-12-01';
WHILE @d <= '2025-12-31'
BEGIN
    INSERT INTO Company_Schedule (company_id, date_available, status, note)
    VALUES
    (1, @d,
     CASE 
        WHEN DAY(@d) IN (5,10,15,24,25,30) THEN 'Unavailable'
        ELSE 'Available'
     END,
     CASE 
        WHEN DAY(@d) = 5 THEN N'Tour công ty lớn'
        WHEN DAY(@d) = 10 THEN N'Bảo trì hệ thống'
        WHEN DAY(@d) = 15 THEN N'Nghỉ lễ nội bộ'
        WHEN DAY(@d) = 24 THEN N'Full booking Giáng Sinh'
        WHEN DAY(@d) = 25 THEN N'Đóng tour Giáng Sinh'
        WHEN DAY(@d) = 30 THEN N'Tour cuối năm'
        ELSE N'Lịch bình thường'
     END);
    SET @d = DATEADD(DAY,1,@d);
END;

INSERT INTO Customers (name, phone, email, nationality) VALUES
(N'Nguyễn Văn A','0901234567','a.nguyen@example.com',N'Việt Nam'),
(N'Trần Thị B','0907654321','b.tran@example.com',N'Việt Nam'),
(N'John Smith','0123456789','john.smith@example.com',N'Mỹ'),
(N'Lê Văn C','0988888888','c.le@example.com',N'Việt Nam'),
(N'Nguyễn Hoàng D','0911111111','d.nguyen@example.com',N'Việt Nam'),
(N'Maria Garcia','0999999999','maria.garcia@example.com',N'Tây Ban Nha'),
(N'Phạm Minh E','0902222333','e.pham@example.com',N'Việt Nam'),
(N'Lê Thị F','0903333444','f.le@example.com',N'Việt Nam'),
(N'William Brown','0904444555','will.brown@example.com',N'Anh'),
(N'Hồ Văn G','0905555666','g.ho@example.com',N'Việt Nam'),
(N'Nguyễn Thị H','0906666777','h.nguyen@example.com',N'Việt Nam'),
(N'David Lee','0907777888','david.lee@example.com',N'Hàn Quốc'),
(N'Phan Văn I','0908888999','i.phan@example.com',N'Việt Nam'),
(N'Trần Văn J','0910000001','j.tran@example.com',N'Việt Nam'),
(N'Lê Thị K','0910000002','k.le@example.com',N'Việt Nam'),
(N'Jessica Wang','0910000003','jess.wang@example.com',N'Trung Quốc'),
(N'Mai Thị L','0910000004','l.mai@example.com',N'Việt Nam'),
(N'Nguyễn Văn M','0910000005','m.nguyen@example.com',N'Việt Nam'),
(N'Anderson Silva','0910000006','anderson.silva@example.com',N'Brazil'),
(N'Phạm Thị N','0910000007','n.pham@example.com',N'Việt Nam');

CREATE TABLE Customer_History (
    history_id INT IDENTITY(1,1) PRIMARY KEY,
    customer_id INT NOT NULL FOREIGN KEY REFERENCES Customers(customer_id),
    tour_id INT NOT NULL FOREIGN KEY REFERENCES Tours(tour_id),
    booking_date DATE NOT NULL DEFAULT GETDATE(),
    travel_date DATE NOT NULL,
    feedback NVARCHAR(MAX)
);

DECLARE @i INT = 1;
WHILE @i <= 100
BEGIN
    INSERT INTO Customer_History (customer_id, tour_id, booking_date, travel_date, feedback)
    SELECT 
        ABS(CHECKSUM(NEWID()) % 20) + 1,   -- random customer 1-20
        ABS(CHECKSUM(NEWID()) % 20) + 1,   -- random tour 1-20
        DATEADD(DAY, -ABS(CHECKSUM(NEWID()) % 200), GETDATE()),  -- booking random 200 ngày gần đây
        DATEADD(DAY, -ABS(CHECKSUM(NEWID()) % 180), GETDATE()),  -- travel random 180 ngày gần đây
        N'Chuyến đi thú vị';
    SET @i = @i + 1;
END;

select * from Customer_History

SELECT tour_id, name, duration, price, discount_price 
FROM Tours 
WHERE destination = N'Phú Quốc';

SELECT s.name, s.type 
FROM Services s 
JOIN Tours t ON s.tour_id = t.tour_id 
WHERE t.destination = N'Phú Quốc';