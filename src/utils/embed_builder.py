import discord
from datetime import datetime
from typing import List, Dict

class LeaderboardEmbedBuilder:
    @staticmethod
    def build_meme_leaderboard(title: str, memes: List[Dict], users: List[Dict]) -> discord.Embed:
        embed = discord.Embed(
            title=title,
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )

        # TODO: Update this implementation, currently untested.
        # Top Memes Section
        memes_value = "\n".join(
            f"🏆 {i+1}. {meme['reactions']} reactions"
            for i, meme in enumerate(memes[:5])
        )
        embed.add_field(name="Top Memes 🐸", value=memes_value or "No memes yet!", inline=False)
        
        # Top Posters Section
        posters_value = "\n".join(
            f"🏆 {i+1}. <@{user['user_id']}> - {user['memes_posted']} posts"
            for i, user in enumerate(users[:5])
        )
        embed.add_field(name="Top Posters ✉️", value=posters_value or "No posters yet!", inline=False)
        
        return embed
