from discord.ext import tasks
from datetime import datetime, time, timedelta
from discord import TextChannel
from src.services.leaderboard import LeaderboardService
from src.utils.embed_builder import LeaderboardEmbedBuilder

class LeaderboardScheduler:
    def __init__(self, channel: TextChannel, leaderboard_service: LeaderboardService):
        self.channel = channel
        self.leaderboard_service = leaderboard_service
        self.embed_builder = LeaderboardEmbedBuilder()

    @tasks.loop(time=[
        time(hour=20, minute=0),  # 8 PM UTC weekly
    ])
    async def check_and_send_leaderboards(self):
        now = datetime.now()
        
        # Weekly on Sundays
        if now.weekday() == 6:
            await self._send_leaderboard("Weekly", days=7)
            
        # Monthly on 1st
        if now.day == 1:
            await self._send_leaderboard("Monthly", days=30)
            
        # Yearly on Jan 1st
        if now.month == 1 and now.day == 1:
            await self._send_leaderboard("Yearly", days=365)

    async def _send_leaderboard(self, period: str, days: int):
        # TODO: write actual implementation
        return
        since = datetime.now() - timedelta(days=days)
        memes = await self.leaderboard_service.get_top_memes_since(since)
        users = await self.leaderboard_service.get_top_posters_since(since)
        
        embed = self.embed_builder.build_meme_leaderboard(
            f"{period} Meme Leaderboard 🎉", memes, users
        )
        await self.channel.send(embed=embed)

    def start(self):
        self.check_and_send_leaderboards.start()