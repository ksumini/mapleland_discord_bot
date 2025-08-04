import os

import discord
from discord.ext import commands
from supabase_storage import get_all_raids, get_raid_by_key, update_raid
from datetime import datetime

RAID_ANNOUNCEMENT_CHANNEL_ID = int(os.getenv("RAID_ANNOUNCEMENT_CHANNEL_ID"))


class EditRaidModal(discord.ui.Modal, title="자쿰 일정 수정"):
    date = discord.ui.TextInput(label="📅 날짜 (예: 2025-08-10)", placeholder="YYYY-MM-DD")
    time = discord.ui.TextInput(label="⏰ 시간 (예: 21:00)", placeholder="HH:MM")
    max_participants = discord.ui.TextInput(label="👥 최대 인원", placeholder="숫자만 입력", max_length=2)
    note = discord.ui.TextInput(label="📝 특이사항", required=False, style=discord.TextStyle.paragraph)

    def __init__(self, interaction: discord.Interaction, key: str):
        super().__init__()
        self.interaction = interaction
        self.key = key
        self.raid = get_raid_by_key(key) or {}

        # 기존 값 세팅
        if self.raid:
            dt = datetime.fromisoformat(self.raid["datetime"])
            self.date.default = dt.strftime("%Y-%m-%d")
            self.time.default = dt.strftime("%H:%M")
            self.max_participants.default = str(self.raid["max_participants"])
            self.note.default = self.raid.get("note", "")

    async def on_submit(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ 관리자만 수정할 수 있습니다.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            new_datetime = datetime.strptime(f"{self.date.value} {self.time.value}", "%Y-%m-%d %H:%M")
            max_participants = int(self.max_participants.value)
        except ValueError:
            await interaction.response.send_message("❌ 형식이 잘못되었습니다.", ephemeral=True)
            return

        if max_participants < 6:
            await interaction.response.send_message("❌ 최소 인원은 6명 이상이어야 합니다.", ephemeral=True)
            return

        raid = get_raid_by_key(self.key)
        if not raid:
            await interaction.response.send_message("❌ 해당 일정이 존재하지 않습니다.", ephemeral=True)
            return

        original_dt = datetime.fromisoformat(raid["datetime"])
        if new_datetime != original_dt:
            duplicate = get_raid_by_key(new_datetime.isoformat(timespec="seconds"))  # 또는 적절한 포맷
            if duplicate:
                await interaction.response.send_message("⚠️ 수정하려는 일정이 이미 존재합니다.", ephemeral=True)
                return

        # Supabase에서 업데이트
        update_raid(raid_id=raid["id"], new_datetime=new_datetime.isoformat(), max_participants=max_participants, note=self.note.value.strip())

        # 메시지 수정
        channel = interaction.guild.get_channel(RAID_ANNOUNCEMENT_CHANNEL_ID)
        if channel and "message_id" in raid:
            try:
                msg = await channel.fetch_message(raid["message_id"])

                for reaction in msg.reactions:
                    if str(reaction.emoji) == "✅":
                        async for user in reaction.users():
                            if not user.bot:
                                try:
                                    await user.send(f"🔔 `{new_datetime}` 일정에 변경 사항이 있습니다.\n변경된 내용을 확인해주세요!")
                                except:
                                    print(f"[WARN] {user.display_name}님에게 DM 전송 실패")

                old_content = msg.content
                old_embed = msg.embeds[0]

                new_description = (
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"📅 **일시:** {new_datetime.strftime('%Y-%m-%d (%a) %H:%M')}\n"
                    f"👥 **최대 인원:** {max_participants}명\n\n"
                    f"📝 **특이사항:**\n{self.note.value.strip() if self.note.value else '지금부터 참여 신청 받습니다!'}\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    "✅ 반응을 눌러 참여를 신청하세요!"
                )

                new_embed = discord.Embed(
                    title="🔔 변경사항이 있습니다!",
                    description=new_description,
                    color=discord.Color.orange()
                )
                for field in old_embed.fields:
                    if field.name.strip() != "✏️ 변경사항이 있습니다":
                        new_embed.add_field(name=field.name, value=field.value, inline=field.inline)

                new_embed.add_field(
                    name="✏️ 변경사항이 있습니다",
                    value=f"수정 시각: <t:{int(datetime.now().timestamp())}:f>",
                    inline=False
                )

                await msg.edit(content=old_content, embed=new_embed)
            except Exception as e:
                print(f"[ERROR] 메시지 수정 실패: {e}")

        await interaction.response.send_message(f"✅ `{new_datetime}` 일정이 성공적으로 수정되었습니다!", ephemeral=True)


class RaidDropdown(discord.ui.Select):
    def __init__(self, options, parent_interaction: discord.Interaction):
        super().__init__(placeholder="수정할 일정을 선택하세요", options=options)
        self.parent_interaction = parent_interaction

    async def callback(self, interaction: discord.Interaction):
        print(f"[DEBUG] Dropdown selected by {interaction.user.display_name}")
        try:
            await interaction.response.send_modal(EditRaidModal(interaction, self.values[0]))
        except Exception as e:
            print(f"[ERROR] Modal 호출 실패: {e}")
            await interaction.response.send_message("❌ 모달을 열 수 없습니다.", ephemeral=True)


class RaidSelect(discord.ui.View):
    def __init__(self, options, parent_interaction: discord.Interaction):
        super().__init__(timeout=60)
        self.add_item(RaidDropdown(options, parent_interaction))


def setup_edit_raid_command(bot: commands.Bot):
    @bot.tree.command(name="일정수정", description="자쿰 공대 일정을 수정합니다. (관리자 전용)")
    async def edit_raid(interaction: discord.Interaction):
        raids = get_all_raids()

        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ 관리자만 사용할 수 있습니다.", ephemeral=True)
            return

        if not raids:
            await interaction.response.send_message("⚠️ 수정할 일정이 없습니다.", ephemeral=True)
            return

        sorted_raids = sorted(raids, key=lambda r: r["datetime"], reverse=True)
        options = [
            discord.SelectOption(label=raid["datetime"], value=raid["datetime"])
            for raid in sorted_raids[:25]
        ]

        view = RaidSelect(options, interaction)
        await interaction.response.send_message("📋 수정할 일정을 선택하세요", view=view, ephemeral=True)
