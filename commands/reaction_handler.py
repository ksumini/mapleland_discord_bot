import discord
from discord.ext import commands
from supabase_storage import get_raid_by_message_id, update_raid_participants


def setup_reaction_handler(bot: commands.Bot):
    @bot.event
    async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
        if payload.user_id == bot.user.id:
            return
        if str(payload.emoji) != "✅":
            return

        raid = get_raid_by_message_id(payload.message_id)
        if not raid:
            return

        user_id = str(payload.user_id)
        participants = raid.get("participants") or []
        waitlist = raid.get("waitlist") or []
        max_participants = raid.get("max_participants", 0)

        if user_id in participants or user_id in waitlist:
            return  # 이미 신청됨

        if len(participants) < max_participants:
            participants.append(user_id)
        else:
            waitlist.append(user_id)

        update_raid_participants(raid["id"], participants, waitlist)

    @bot.event
    async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
        if str(payload.emoji) != "✅":
            return

        raid = get_raid_by_message_id(payload.message_id)
        if not raid:
            return

        user_id = str(payload.user_id)
        participants = raid.get("participants") or []
        waitlist = raid.get("waitlist") or []

        changed = False

        if user_id in participants:
            participants.remove(user_id)
            if waitlist:
                next_user = waitlist.pop(0)
                participants.append(next_user)
            changed = True

        elif user_id in waitlist:
            waitlist.remove(user_id)
            changed = True

        if changed:
            update_raid_participants(raid["id"], participants, waitlist)
