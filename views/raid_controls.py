from collections import defaultdict
import discord
from discord.ui import View, button

from supabase_storage import get_raid_by_message_id, get_all_users


class RaidControlView(View):
    def __init__(self, raid_key: str):
        super().__init__(timeout=None)
        self.raid_key = raid_key

    @button(label="📋 참여자 명단 보기", style=discord.ButtonStyle.primary, custom_id="show_participants")
    async def show_participants(self, interaction: discord.Interaction, button: discord.ui.Button):
        message_id = interaction.message.id

        # 🔁 Supabase에서 일정 로드
        raid = get_raid_by_message_id(message_id)
        if not raid:
            await interaction.response.send_message("❌ 해당 일정 정보를 찾을 수 없습니다😭", ephemeral=True)
            return

        # 🔁 유저 정보 전체 로드
        users = get_all_users()

        participants = raid.get("participants", [])
        waitlist = raid.get("waitlist", [])
        max_participants = raid.get("max_participants", 0)
        raid_key = raid.get("datetime") or "알 수 없음"

        def group_by_job(user_ids):
            grouped = defaultdict(list)
            for uid in user_ids:
                user_info = users.get(str(uid))
                job = user_info["job"] if user_info else "기타"
                grouped[job].append(f"<@{uid}>")
            return grouped

        def format_grouped(grouped_dict):
            if not grouped_dict:
                return "없음"
            return "\n".join(f"- {job}: {', '.join(mentions)}" for job, mentions in grouped_dict.items())

        embed = discord.Embed(
            title="📋 자쿰 공대 참여 명단",
            description=f"**일정:** {raid_key}\n**최대 인원:** {max_participants}명",
            color=discord.Color.green()
        )
        embed.add_field(name="✅ 참여자", value=format_grouped(group_by_job(participants)), inline=False)
        embed.add_field(name="🕐 대기자", value=format_grouped(group_by_job(waitlist)), inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

