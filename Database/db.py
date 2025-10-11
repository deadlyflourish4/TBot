# Database/db_manager.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import urllib
from sqlalchemy import text

class MultiDBManager:
    """Quản lý nhiều SQL Server region — tái sử dụng connection pool."""

    DB_MAP = {
        0: {"region": "VN", "server": "34.142.157.56", "database": "vie44364_guidepassasia", "prefix": "vie44364_vietnampass"},
        1: {"region": "SG", "server": "35.200.111.23", "database": "guidepass_singapore", "prefix": "vie44364_vietnampass"},
        2: {"region": "FR", "server": "51.83.210.45", "database": "guidepass_france", "prefix": "vie44364_vietnampass"},
        3: {"region": "US", "server": "23.94.80.12", "database": "guidepass_usa", "prefix": "vie44364_vietnampass"},
        4: {"region": "AU", "server": "45.76.123.99", "database": "guidepass_australia", "prefix": "vie44364_vietnampass"},
    }

    def __init__(self, username="sqlserver", password="Tinhyeu75@", driver="ODBC Driver 18 for SQL Server"):
        self.username = username
        self.password = password
        self.driver = driver
        self.engines = {}
        self.sessions = {}

    def get_engine(self, region_id: int):
        """Trả về SQLAlchemy engine tương ứng với region, tạo nếu chưa có"""
        cfg = self.DB_MAP.get(region_id)
        if not cfg:
            raise ValueError(f"Invalid region_id: {region_id}")

        if region_id not in self.engines:
            odbc_str = (
                f"DRIVER={{{self.driver}}};"
                f"SERVER={cfg['server']},1433;"
                f"DATABASE={cfg['database']}_cloud;"
                f"UID={self.username};PWD={self.password};"
                "Encrypt=yes;TrustServerCertificate=yes;"
            )
            params = urllib.parse.quote_plus(odbc_str)
            engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}", pool_pre_ping=True)
            self.engines[region_id] = engine
            self.sessions[region_id] = sessionmaker(bind=engine)
        return self.engines[region_id]

    def get_session(self, region_id: int):
        """Tạo session tương ứng vùng"""
        if region_id not in self.sessions:
            self.get_engine(region_id)
        return self.sessions[region_id]()
