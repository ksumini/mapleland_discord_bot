from datetime import datetime, date
import discord
from discord import app_commands
from discord.ext import commands
from notion_client import Client
import os

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DB_ID = os.getenv("NOTION_DISTRIBUTION_DB_ID")

notion = Client(auth=NOTION_API_KEY)


def parse_number(prop):
    return prop.get("number")


def parse_date(prop):
    if prop.get("date") and prop["date"].get("start"):
        return datetime.fromisoformat(prop["date"]["start"]).date()
    return None


def parse_text(prop):
    arr = prop.get("title") or prop.get("rich_text", [])
    return "".join([x.get("plain_text", "") for x in arr]) if arr else ""


def query_by_date(target_date: date):
    res = notion.databases.query(
        database_id=NOTION_DB_ID,
        filter={"property": "날짜", "date": {
            "on_or_after": target_date.isoformat(),
            "on_or_before": target_date.isoformat()
        }},
        page_size=1
    )
    return res.get("results", [])


def extract_page_info(page):
    props = page["properties"]
    return {
        "date": parse_date(props["날짜"]),
        "title": parse_text(props["정산 세부 페이지"]),
        "status": props["정산진행 여부"]["status"]["name"] if props.get("정산진행 여부") else "",
        "participants": parse_number(props["참여자 수"]),
        "total": parse_number(props["총 수익"]),
        "per_person": parse_number(props["인당 분배금"]),
        "url": page.get("url")
    }


def setup_distribution_command(bot: commands.Bot):
    @bot.tree.command(name="분배금정산", description="노션 DB에서 정산 정보를 불러옵니다.")
    @app_commands.describe(날짜="YYYY-MM-DD 형식 (예: 2025-07-27)")
    async def distribution(interaction: discord.Interaction, 날짜: str):
        await interaction.response.defer(ephemeral=True)

        try:
            y, m, d = map(int, 날짜.split("-"))
            target_date = date(y, m, d)
        except ValueError:
            await interaction.followup.send("날짜 형식이 올바르지 않습니다. (YYYY-MM-DD)", ephemeral=True)
            return

        pages = query_by_date(target_date)
        if not pages:
            await interaction.followup.send("해당 날짜의 정산 정보를 찾을 수 없습니다.", ephemeral=True)
            return

        page_info = extract_page_info(pages[0])

        embed = discord.Embed(
            title=f"정산 — {page_info['title']}",
            url=page_info["url"],
            color=discord.Color.green()
        )
        embed.add_field(name="날짜", value=str(page_info["date"]), inline=True)
        embed.add_field(name="정산 상태", value=page_info["status"], inline=True)
        embed.add_field(name="참여자 수", value=str(page_info["participants"]), inline=True)
        embed.add_field(name="총 수익", value=f"{page_info['total']:,}원", inline=True)
        embed.add_field(name="인당 분배금", value=f"{page_info['per_person']:,}원", inline=True)

        await interaction.followup.send(embed=embed, ephemeral=True)
