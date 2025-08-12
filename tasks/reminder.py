from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from discord.ext import tasks

from supabase_storage import get_all_raids

bot = None  # 전역 변수로 봇 인스턴스 저장
KST = ZoneInfo("Asia/Seoul")

# 직전 루프 시각(알림 중복/누락 방지용)
_last_tick: datetime | None = None

# 디버그 로그 토글 (원하면 환경변수로도 제어 가능)
DEBUG = True


def set_bot_instance(bot_instance):
    global bot
    bot = bot_instance


async def _get_user(uid: int):
    """유저 캐시 미스 보완."""
    user = bot.get_user(uid)
    if user is None:
        try:
            user = await bot.fetch_user(uid)
        except Exception:
            return None
    return user


async def send_raid_reminder(raid, message_type):
    participants = raid.get("participants", [])
    if not participants:
        if DEBUG:
            print(f"[reminder] skip: participants empty for {raid.get('datetime')}")
        return

    for uid in participants:
        try:
            user = await _get_user(int(uid))
            if not user:
                print(f"[reminder] 유저 {uid}를 찾을 수 없음")
                continue
            await user.send(
                f"🔔 **{message_type}**\n"
                f"자쿰 공대 **{raid['datetime']}** 에 참여 예정이에요!"
            )
            if DEBUG:
                print(f"[reminder] DM sent to {uid} ({message_type})")

        except Exception as e:
            print(f"[reminder] DM 실패 uid={uid}: {e}")


@tasks.loop(minutes=5)
async def check_upcoming_raids():
    """지난 루프~이번 루프 사이에 '목표시각을 통과'했으면 알림 발송."""
    global _last_tick

    now = datetime.now(KST)

    # 첫 루프에서는 기준점만 잡고 종료 (다음 루프부터 판정)
    if _last_tick is None:
        _last_tick = now
        if DEBUG:
            print(f"[reminder] first tick; anchor set to {now.isoformat()}")
        return

    window_start = _last_tick
    window_end = now
    _last_tick = now

    if DEBUG:
        print(f"[reminder] window {window_start.isoformat()} → {window_end.isoformat()}")

    # 최신 일정 조회
    try:
        raids = get_all_raids()
    except Exception as e:
        print(f"[reminder] 일정 조회 실패: {e}")
        return

    for raid in raids:
        try:
            raid_time = datetime.strptime(raid["datetime"], "%Y-%m-%d %H:%M").replace(tzinfo=KST)
        except Exception as e:
            print(f"[reminder] bad datetime ({raid.get('datetime')}): {e}")
            continue

        t1h = raid_time - timedelta(hours=1)
        t24h = raid_time - timedelta(hours=24)

        if DEBUG:
            print(f"[reminder] raid={raid['datetime']} t-1h={t1h.time()} t-24h={t24h.time()} participants={len(raid.get('participants', []))}")

        # 지난 루프~이번 루프 사이를 '통과'했는지로 판정 (루프 타이밍/지연 무관)
        if window_start <= t1h < window_end:
            await send_raid_reminder(raid, "공대 시작 1시간 전")

        if window_start <= t24h < window_end:
            await send_raid_reminder(raid, "공대 시작 24시간 전")


# 루프 에러 핸들러(예외로 루프 정지 방지)
@check_upcoming_raids.error
async def _reminder_error(e):
    print(f"[reminder] loop error: {e}")