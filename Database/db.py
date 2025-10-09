from sqlalchemy import create_engine, text
import urllib


class DatabaseConnector:
    def __init__(self):
        # Connection string Windows Authentication
        odbc_str = (
            "DRIVER={ODBC Driver 18 for SQL Server};"
            "SERVER=34.142.157.56,1433;"
            "DATABASE=vie44364_guidepassasia_cloud;"
            "UID=sqlserver;"
            "PWD=Tinhyeu75@;"
            "Encrypt=yes;"
            "TrustServerCertificate=yes;"
        )
        params = urllib.parse.quote_plus(odbc_str)
        self.engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")

    def run_query(self, sql: str):
        with self.engine.connect() as conn:
            try:
                result = conn.execute(text(sql))
                rows = [dict(row._mapping) for row in result]
                return rows
            except Exception as e:
                return {"error": str(e)}


def main():
    server = "localhost"  # hoặc "localhost\\SQLEXPRESS" nếu là bản express
    database = "Orpheo"  # thay bằng tên DB của bạn

    db = DatabaseConnector(server, database)

    res = db.run_query(
        "SELECT i.day_number, i.activity FROM .Itineraries i JOIN Tours t ON i.tour_id = t.tour_id WHERE t.destination = N'Huế' AND i.day_number IN (2, 3) ORDER BY i.day_number;"
    )
    print(res)


if __name__ == "__main__":
    main()
