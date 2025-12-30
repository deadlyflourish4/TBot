# Database/db_manager.py
import threading
import time
import urllib

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


class MultiDBManager:
    """
    Quản lý nhiều SQL Server region — tái sử dụng connection pool.
    Cho phép mỗi region có username/password riêng.
    """

    DB_MAP = {
        0: {
            "server": "212.95.42.77,784",
            "database": "guidepass_guidepassasia_cloud",
            "prefix": "guidepass_guidepassasia_cloud",
            "username": "guidepass_guidepassasia_cloud",
            "password": "Tinhyeu75@",
        },
        1: {
            "server": "112.78.2.94,1433",
            "database": "gui18554_guidepass",
            "prefix": "dbo",
            "username": "gui18554_guidepass",
            "password": "Tinhyeu75@",
        },
        2: {
            "server": "212.95.42.77,784",
            "database": "guidepass_cityguidepass_cloud",
            "prefix": "dbo",
            "username": "guidepass_cityguidepass_cloud",
            "password": "Tinhyeu75@",
        },
        3: {
            "server": "212.95.42.77,784",
            "database": "propass_proguidepass",
            "prefix": "propass_proguidepass",
            "username": "propass_proguidepass",
            "password": "Tinhyeu75@",
        },
        # 4: {...}
    }

    def __init__(
        self, default_driver="ODBC Driver 18 for SQL Server", idle_timeout=30 * 60
    ):
        """
        Args:
            default_driver (str): tên ODBC driver mặc định.
            idle_timeout (int): thời gian idle (giây) trước khi đóng connection pool.
        """
        self.default_driver = default_driver
        self.idle_timeout = idle_timeout
        self.engines = {}
        self.sessions = {}
        self.last_used = {}
        self.__start_cleanup_thread()

    # ----------------------------------------------------------------------

    def build_connection_string(self, cfg: dict) -> str:
        """Xây dựng chuỗi ODBC connect từ cấu hình"""
        driver = cfg.get("driver", self.default_driver)
        username = cfg.get("username")
        password = cfg.get("password")

        if not username or not password:
            raise ValueError(f"Thiếu username/password trong cấu hình DB: {cfg}")

        odbc_str = (
            f"DRIVER={{{driver}}};"
            f"SERVER={cfg['server']};"
            f"DATABASE={cfg['database']};"
            f"UID={username};PWD={password};"
            "Encrypt=yes;TrustServerCertificate=yes;"
        )
        return urllib.parse.quote_plus(odbc_str)

    # ----------------------------------------------------------------------

    def get_engine(self, region_id: int):
        """Trả về SQLAlchemy engine tương ứng với region, tạo nếu chưa có"""
        cfg = self.DB_MAP.get(region_id)
        if not cfg:
            raise ValueError(f"Invalid region_id: {region_id}")

        if region_id not in self.engines:
            params = self.build_connection_string(cfg)
            engine = create_engine(
                f"mssql+pyodbc:///?odbc_connect={params}",
                pool_size=100,
                max_overflow=20,
                pool_pre_ping=True,
                pool_recycle=1800,
            )
            self.engines[region_id] = engine
            self.sessions[region_id] = sessionmaker(bind=engine)
            print(
                f"[DBManager] ✅ Created engine for region {region_id}: {cfg['server']}"
            )

        self.last_used[region_id] = time.time()
        return self.engines[region_id]

    # ----------------------------------------------------------------------

    def get_session(self, region_id: int):
        """Tạo session tương ứng với vùng"""
        if region_id not in self.sessions:
            self.get_engine(region_id)
        self.last_used[region_id] = time.time()
        return self.sessions[region_id]()

    # ----------------------------------------------------------------------

    def __cleanup_idle_engines(self):
        """Tự động đóng engine sau khi idle quá lâu"""
        while True:
            now = time.time()
            for region_id, last in list(self.last_used.items()):
                if now - last > self.idle_timeout:
                    cfg = self.DB_MAP.get(region_id, {})
                    print(
                        f"[DBManager] 💤 Disposing idle engine for region {region_id} ({cfg.get('server')})"
                    )
                    try:
                        self.engines[region_id].dispose()
                    except Exception as e:
                        print(
                            f"[DBManager] ⚠️ Dispose failed for region {region_id}: {e}"
                        )
                    finally:
                        self.engines.pop(region_id, None)
                        self.sessions.pop(region_id, None)
                        self.last_used.pop(region_id, None)
            time.sleep(300)

    def __start_cleanup_thread(self):
        t = threading.Thread(target=self.__cleanup_idle_engines, daemon=True)
        t.start()
