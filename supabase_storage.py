from supabase_client import supabase


# 유저 등록 / 조회
def register_user(discord_id: str, nickname: str, level: int, job: str):
    data = {
        "discord_id": discord_id,
        "nickname": nickname,
        "level": level,
        "job": job
    }
    print(data)
    return supabase.table("users").upsert(data, on_conflict=["discord_id"]).execute()


def get_user(discord_id: str):
    result = supabase.table("users").select("*").eq("discord_id", discord_id).execute()
    return result.data[0] if result.data else None


# 공대 일정 생성 / 전체 조회
def create_raid(datetime_str: str, max_participants: int, note: str):
    from uuid import uuid4
    new_id = str(uuid4())
    data = {
        "id": new_id,
        "datetime": datetime_str,
        "max_participants": max_participants,
        "note": note,
        "participants": [],
        "waitlist": []
    }
    response = supabase.table("raids").insert(data).execute()
    print("📦 Insert Response:", response.data)
    return new_id


def get_all_raids():
    result = supabase.table("raids").select("*").execute()
    return result.data if result.data else []


def get_raid_by_key(key: str):
    # key는 "YYYY-MM-DD HH:MM" 형식의 문자열
    result = supabase.table("raids").select("*").eq("datetime", key).execute()
    return result.data[0] if result.data else None


def delete_raid_by_key(key: str):
    supabase.table("raids").delete().eq("datetime", key).execute()


def update_raid(raid_id: str, new_datetime: str, max_participants: int, note: str):
    supabase.table("raids").update({
        "datetime": new_datetime,
        "max_participants": max_participants,
        "note": note
    }).eq("id", raid_id).execute()


def get_raid_by_message_id(message_id: int):
    result = supabase.table("raids").select("*").eq("message_id", message_id).execute()
    if result.data:
        return result.data[0]
    return None


def update_raid_participants(raid_id: int, participants: list, waitlist: list):
    supabase.table("raids").update({
        "participants": participants,
        "waitlist": waitlist
    }).eq("id", raid_id).execute()


def get_all_users():
    result = supabase.table("users").select("*").execute()
    return {str(user["discord_id"]): user for user in result.data}