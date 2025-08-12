from datetime import datetime
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")


def parse_kst(dt_str: str) -> datetime:
    """
    ISO 문자열을 KST로 파싱 (naive면 KST tz 부여)
    예) "2025-08-12 13:30" 또는 "2025-08-12T13:30:00"
    """
    dt = datetime.fromisoformat(dt_str)
    # 타임존이 있으면 KST로 변환, 없으면 KST 부여
    dt = dt.astimezone(KST) if dt.tzinfo else dt.replace(tzinfo=KST)
    return dt