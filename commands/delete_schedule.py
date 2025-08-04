import os
from dotenv import load_dotenv

import discord
from discord.ext import commands
from supabase_storage import get_all_raids, get_raid_by_key, delete_raid_by_key

load_dotenv()
RAID_ANNOUNCEMENT_CHANNEL_ID = int(os.getenv("RAID_ANNOUNCEMENT_CHANNEL_ID"))


def setup_delete_raid_command(bot: commands.Bot):
    @bot.tree.command(name="일정삭제", description="자쿰 공대 일정을 삭제합니다. (관리자 전용)")
    async def delete_raid(interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ 관리자만 사용할 수 있습니다.", ephemeral=True)
            return

        raids = get_all_raids()
        if not raids:
            await interaction.response.send_message("⚠️ 삭제할 일정이 없습니다.", ephemeral=True)
            return

        sorted_raids = sorted(raids, key=lambda r: r["datetime"], reverse=True)
        options = [discord.SelectOption(label=raid["datetime"], value=raid["datetime"]) for raid in sorted_raids[:25]]

        class DeleteDropdown(discord.ui.Select):
            def __init__(self):
                super().__init__(placeholder="삭제할 일정을 선택하세요", options=options)

            async def callback(self, select_interaction: discord.Interaction):
                key = self.values[0]
                raid = get_raid_by_key(key)
                if not raid:
                    await select_interaction.response.send_message("❌ 해당 일정이 존재하지 않습니다.", ephemeral=True)
                    return

                channel = interaction.guild.get_channel(RAID_ANNOUNCEMENT_CHANNEL_ID)
                if channel and "message_id" in raid:
                    try:
                        msg = await channel.fetch_message(raid["message_id"])

                        for reaction in msg.reactions:
                            if str(reaction.emoji) == "✅":
                                users = [user async for user in reaction.users()]
                                for user in users:
                                    if user.bot:
                                        continue
                                    try:
                                        await user.send(f"⚠️ `{key}` 일정이 취소되었습니다.")
                                    except:
                                        print(f"[WARN] {user.name}님에게 DM 전송 실패")

                        cancelled_embed = discord.Embed(
                            title="❌ 일정이 취소되었습니다",
                            description=f"해당 일정 ({raid['datetime']})은 취소되었습니다.",
                            color=discord.Color.red()
                        )
                        await msg.edit(embed=cancelled_embed)

                    except Exception as e:
                        print(f"[ERROR] 메시지 수정 실패: {e}")

                # Supabase에서 삭제
                delete_raid_by_key(key)
                await select_interaction.response.send_message(f"✅ `{key}` 일정이 삭제되었습니다.", ephemeral=True)

        class DeleteView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=60)
                self.add_item(DeleteDropdown())

        await interaction.response.send_message("🗑 삭제할 일정을 선택하세요", view=DeleteView(), ephemeral=True)
