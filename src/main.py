# pylint: disable=missing-module-docstring, missing-function-docstring, too-many-locals, too-many-branches, too-many-statements, line-too-long
import datetime
import sys
import os

import discord
from dateutil.relativedelta import relativedelta
from pymongo import MongoClient
import jsonpickle

AUTH_TOKEN = os.environ["AUTH_TOKEN"]
CHANNEL_ID = int(os.environ["MEME_CHANNEL_ID"])
if not (AUTH_TOKEN and CHANNEL_ID):
    import config
    AUTH_TOKEN = config.AUTH_TOKEN
    CHANNEL_ID = config.MEME_CHANNEL_ID

discord_intents = discord.Intents.default()
discord_client = discord.Client(intents=discord_intents)

mongodb_client = MongoClient("localhost", 27017)
mongodb_db = mongodb_client["weekly-leaderboards"]
top_memes_collection = mongodb_db["top-memes"]
user_stats_collection = mongodb_db["user-stats"]

def sort_order(item):
    return item['reactions']

async def save_leaderboard_data(number_of_days: int, channel):
    for i in range(0, number_of_days):
        # Read posts from last day ish 00:00-00:00
        start_time = (datetime.datetime.now() - datetime.timedelta(days=i)) - datetime.timedelta(days=1)
        date_entry = str(datetime.datetime.now() - datetime.timedelta(days=i))[:10].replace('-', '')
        messages = [
            message async for message in channel.history(after=start_time, limit=None)
        ]

        user_stats = {}
        meme_leaderboard = {}
        for message in messages:
            if (
                message.embeds == [] and message.attachments == []
            ) or message.author == discord_client.user or message.author.bot:
                continue

            reactions = 0
            for reaction in message.reactions:
                reaction_users = [user async for user in reaction.users()]
                user_posted = message.author.name
                reaction_count = reaction.count
                if user_posted in reaction_users:
                    reaction_count = reaction_count - 1

                reactions = reactions + reaction_count

                for reaction_user in reaction_users:
                    if reaction_user.bot:
                        continue
                    if reaction_user in user_stats:
                        user_stats[reaction_user]["reactions_sent"] = user_stats[reaction_user]["reactions_sent"] + 1
                    else:
                        user_stats[reaction_user] = {
                            "posts": 0,
                            "reactions_sent": 1,
                            "reactions_recieved": 0
                        }

            if message.author in user_stats:
                user_stats[message.author]["posts"] = user_stats[message.author]["posts"] + 1
                user_stats[message.author]["reactions_recieved"] = user_stats[message.author]["reactions_recieved"] + reactions
            else:
                user_stats[message.author] = {
                    "posts": 1,
                    "reactions_sent": 0,
                    "reactions_recieved": reactions
                }
            meme_leaderboard[message] = reactions
        meme_leaderboard = sorted(meme_leaderboard.items(), key=lambda x:x[1])
        formatted_meme_leaderboard = {
            "day": date_entry,
            "leaderboard": {}
        }
        for meme_message, nr_of_reactions in meme_leaderboard:
            if meme_message.attachments != []:
                meme = await meme_message.attachments[0].to_file()
                meme_type = "attachment"
            else:
                meme = meme_message.embeds[0]
                meme_type = "embed"

            formatted_meme_leaderboard["leaderboard"][meme_message.id] = jsonpickle.encode({
                "mention": meme_message.author.mention,
                "reactions": nr_of_reactions,
                "meme": meme,
                "memeType": meme_type,
                "reference": meme_message
            })

        top_memes_collection.insert_one(formatted_meme_leaderboard)
        user_stats_collection.insert_one(jsonpickle.encode({
            "day": date_entry,
            "user_stats": user_stats
        }))

def build_strings(meme_leaderboard, user_stats):

    announcemen_string = f":trophy: Meme Leaderboard for the {sys.argv[1]} :trophy:"
    first_place_string = f':first_place: {meme_leaderboard[0]["mention"]}: {meme_leaderboard[0]["reactions"]} reactions\n'
    second_place_string = f':second_place: {meme_leaderboard[1]["mention"]}: {meme_leaderboard[1]["reactions"]} reactions\n'
    third_place_string = f':third_place: {meme_leaderboard[2]["mention"]}: {meme_leaderboard[2]["reactions"]} reactions\n'

    top_posters_string = f"Most memes posted this {sys.argv[1]} :rofl:\n"
    i = 0
    for user in sorted(user_stats, key=user_stats["posts"], reverse=True):
        if i == 0:
            top_posters_string = (
                top_posters_string
                + f":first_place: {user.mention}: {user_stats[user]}\n"
            )
        elif i == 1:
            top_posters_string = (
                top_posters_string
                + f":second_place: {user.mention}: {user_stats[user]}\n"
            )
        elif i == 2:
            top_posters_string = (
                top_posters_string
                + f":third_place: {user.mention}: {user_stats[user]}"
            )
        else:
            break
        i = i + 1

    top_reactor_string = f"Most reactions sent this {sys.argv[1]} :rofl:\n"
    i = 0
    for user in sorted(user_stats, key=user_stats['reactions_sent'], reverse=True):
        if i == 0:
            top_reactor_string = (
                top_reactor_string
                + f":first_place: {user.mention}: {user_stats[user]}\n"
            )
        elif i == 1:
            top_reactor_string = (
                top_reactor_string
                + f":second_place: {user.mention}: {user_stats[user]}\n"
            )
        elif i == 2:
            top_reactor_string = (
                top_reactor_string
                + f":third_place: {user.mention}: {user_stats[user]}"
            )
        else:
            break
        i = i + 1

        return {
            "announcement": announcemen_string,
            "placements": [first_place_string, second_place_string, third_place_string],
            "top_posters": top_posters_string,
            "top_reactions": top_reactor_string,
        }

async def send_top_meme(channel, meme_data, text_content):
    if meme_data["memeType"] == "attachment":
        await channel.send(
            content=text_content,
            file=meme_data["meme"],
            reference=meme_data["reference"],
        )
    else:
        await channel.send(
            content=text_content,
            embed=meme_data["meme"],
            reference=meme_data["reference"],
        )

@discord_client.event
async def on_ready():
    print("running")
    channel = discord_client.get_channel(
        CHANNEL_ID
    )  # MEMES CHANNEL IN CRINGE GANG
    if sys.argv[1] == "day":
        await save_leaderboard_data(1, channel)
        # Send message

    now = datetime.datetime.now()
    start_date = None
    if sys.argv[1] == "week":
        start_date = str(now - datetime.timedelta(days=7))[:10].replace('-', '')
    elif sys.argv[1] == "month":
        start_date = str(now - relativedelta(months=4))[:10].replace('-', '')
    elif sys.argv[1] == "year":
        start_date = str(now - datetime.timedelta(days=365))[:10].replace('-', '')
    elif sys.argv[1] == "customSave":
        await save_leaderboard_data(sys.argv[2], channel)

    if start_date is None:
        await discord_client.close()
        sys.exit()

    meme_leaderboards_dict = top_memes_collection.find({"day": {"$gte": start_date}})
    meme_leaderboards = list(meme_leaderboards_dict["leaderboard"].keys())
    user_stats = user_stats_collection.find({"day": {"$gte": start_date}})

    # Send message

    strings = build_strings(meme_leaderboards, user_stats)
    if sys.argv[2] == "debug":
        print(strings)
    else:
        await channel.send(content=strings["announcement"])
        for meme_data in meme_leaderboards[:3]:
            placement = 0
            await send_top_meme(channel, meme_data, strings["placements"][placement])
            placement += 1

        await channel.send(content=strings["top_posters"])
        await channel.send(content=strings["top_reactions"])
    await discord_client.close()
    sys.exit()

discord_client.run(AUTH_TOKEN)
