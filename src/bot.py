import logging
import discord
from discord import Interaction
from discord.ext import commands
from src.services.leaderboard import LeaderboardService
from src.services.meme_tracking import MemeTrackingService
from src.scheduler import LeaderboardScheduler
from src.utils.embed_builder import LeaderboardEmbedBuilder
from src.database import verify_mongodb_connection, create_indexes

class HolgerBot(commands.Bot):
    # Setup
    def __init__(self, db, channel_id):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.reactions = True
        super().__init__(command_prefix=commands.when_mentioned, intents=intents)

        self.application_commands = True
        self.db = db
        self.channel_id = channel_id
        self.leaderboard_service = LeaderboardService(db)
        self.meme_service = MemeTrackingService(db)

    # Event Hooks
    async def on_ready(self):
        logger = logging.getLogger('holger')
        logger.info(f'{self.user} has connected to Discord!')
        await verify_mongodb_connection(self.db)
        await create_indexes(self.db)

    async def on_message(self, message: discord.Message):
        logger = logging.getLogger("holger")
        logger.info("ON MESSAGE TRIGGERED")
        if message.channel.id != self.channel_id:
            return
            
        if message.attachments or any(embed.type in ['video', 'image', 'gifv', 'link'] for embed in message.embeds):    
            await self.meme_service.track_meme(message.id, message.author.id)
            
        await self.process_commands(message)

    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        logger = logging.getLogger("holger")
        logger.info("ON reaction add TRIGGERED")
        if payload.channel_id != self.channel_id:
            return
            
        await self.meme_service.track_reaction(
            payload.message_id,
            payload.user_id,
            add=True
        )

    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        logger = logging.getLogger("holger")
        logger.info("ON reaction removed TRIGGERED")
        if payload.channel_id != self.channel_id:
            return
            
        await self.meme_service.track_reaction(
            payload.message_id,
            payload.user_id,
            add=False
        )

    async def setup_hook(self):
        logger = logging.getLogger('holger')
        logger.info('SETUP HOOK RAN')
        self.channel = await self.fetch_channel(self.channel_id)
        self.scheduler = LeaderboardScheduler(self.channel, self.leaderboard_service)
        self.scheduler.start()
        
        self.tree.clear_commands(guild=None)

        @self.tree.command(description="Sync slash commands")
        async def sync_commands(interaction: Interaction) -> None:
            logger = logging.getLogger('holger')
            logger.info("RUNNING SYNC COMMAND")
            if interaction.user.guild_permissions.administrator:
                logger.info('IS admin')
                await interaction.response.defer()
                await self.tree.sync()
                await interaction.followup.send("Commands synced!")
            else:
                await interaction.response.send_message("You need admin permissions to sync commands.")

        @self.tree.command(name="stats", description="Show your meme statistics")
        async def stats(interaction: Interaction) -> None:
            logger = logging.getLogger('holger')
            logger.info("TRIGGERED STATS COMMAND")
            user_stats = await self.leaderboard_service.get_user_stats(interaction.user.id)
            embed = discord.Embed(
                title=f"Meme Stats for {interaction.user.name}",
                color=discord.Color.blue()
            )
            embed.add_field(name="Memes Posted", value=str(len(user_stats['memes_posted'])))
            embed.add_field(name="Reactions Given", value=str(len(user_stats['reactions_given'])))
            await interaction.response.send_message(embed=embed)

        @self.tree.command(name="leaderboard", description="Show current meme leaderboard")
        async def leaderboard(interaction: Interaction) -> None:
            logger = logging.getLogger('holger')
            logger.info("TRIGGERED leaderboard COMMAND")
            memes = await self.leaderboard_service.get_top_memes()
            users = await self.leaderboard_service.get_top_posters()
            embed = LeaderboardEmbedBuilder.build_meme_leaderboard(
                "Current Meme Leaderboard 🏆", memes, users
            )
            await interaction.response.send_message(embed=embed)

        await self.tree.sync()
    