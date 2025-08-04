from discord.ext import tasks
from datetime import datetime
from supabase_storage import get_all_raids

bot = None  # 전역 변수로 봇 인스턴스 저장


def set_bot_instance(bot_instance):
    global bot
    bot = bot_instance


async def send_raid_reminder(raid, message_type):
    participants = raid.get("participants", [])
    if not participants:
        return

    for uid in participants:
        user = bot.get_user(int(uid))
        if user:
            try:
                await user.send(f"🔔 **{message_type}** 알림입니다!\n자쿰 공대({raid['datetime']})에 참여 예정이에요!")
            except Exception as e:
                print(f"❌ {uid}님에게 DM 보내기 실패: {e}")
        else:
            print(f"❌ 유저 {uid} 찾을 수 없음")


@tasks.loop(minutes=5)
async def check_upcoming_raids():
    raids = get_all_raids()
    now = datetime.now()

    for raid in raids:
        try:
            raid_time = datetime.strptime(raid["datetime"], "%Y-%m-%d %H:%M")
        except ValueError:
            continue

        # 1시간 전 알림 (±2.5분)
        if abs((raid_time - now).total_seconds() - 3600) < 150:
            await send_raid_reminder(raid, "공대 시작 1시간 전")

        # 전날 오후 8시 알림
        if now.hour == 20 and (raid_time.date() - now.date()).days == 1:
            await send_raid_reminder(raid, "내일 공대 참여 확인")
