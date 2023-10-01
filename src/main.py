# pylint: disable=missing-module-docstring, missing-function-docstring, too-many-locals, too-many-branches, too-many-statements, line-too-long
import datetime
import sys

import discord
import config

intents = discord.Intents.default()
client = discord.Client(intents=intents)

def sort_order(item):
    return item[1]


@client.event
async def on_ready():
    print(f"We have logged in as {client.user}")
    # meme_channel = client.get_channel(config.DEBUG_CHANNEL_ID) # TESTING SERVER
    meme_channel = client.get_channel(
        config.MEME_CHANNEL_ID
    )  # MEMES CHANNEL IN CRINGE GANG
    now = datetime.datetime.now()
    if sys.argv[1] == "day":
        start_date = now - datetime.timedelta(days=1)
    if sys.argv[1] == "week":
        start_date = now - datetime.timedelta(days=7)
    elif sys.argv[1] == "month":
        start_date = now - datetime.timedelta(weeks=4)
    elif sys.argv[1] == "year":
        start_date = now - datetime.timedelta(days=365)

    messages = [
        message async for message in meme_channel.history(after=start_date, limit=None)
    ]

    top_reactors = {}
    top_posters = {}
    meme_leaderboard = []
    for message in messages:
        if (
            message.embeds == [] and message.attachments == []
        ) or message.author == client.user:
            continue

        if message.author not in top_posters:
            top_posters[message.author] = 1
        else:
            top_posters[message.author] = top_posters[message.author] + 1

        reactions = 0
        for reaction in message.reactions:
            reaction_users = [user async for user in reaction.users()]
            reaction_user_names = [user.name for user in reaction_users]
            user_posted = message.author.name
            reaction_count = reaction.count
            if user_posted in reaction_user_names:
                reaction_count = reaction_count - 1

            reactions = reactions + reaction_count

            for user in reaction_users:
                if user not in top_reactors:
                    top_reactors[user] = 1
                else:
                    top_reactors[user] = top_reactors[user] + 1

        meme_leaderboard.append([message, reactions])

    meme_leaderboard.sort(reverse=True, key=sort_order)

    winners = []
    for item in meme_leaderboard[:3]:
        if item[0].attachments != []:
            meme = await item[0].attachments[0].to_file()
            meme_type = "attachment"
        else:
            meme = item[0].embeds[0]
            meme_type = "embed"

        winners.append(
            {
                "mention": item[0].author.mention,
                "reactions": item[1],
                "meme": meme,
                "memeType": meme_type,
                "reference": item[0],
            }
        )

    announcemen_string = f":trophy: Top memes of the {sys.argv[1]} :trophy:"
    first_place_string = f':first_place: {winners[0]["mention"]} with {winners[0]["reactions"]} reactions :clap::clap:\n'
    second_place_string = f':second_place: {winners[1]["mention"]} with {winners[1]["reactions"]} reactions :raised_hands:\n'
    third_place_string = f':third_place: {winners[2]["mention"]} with {winners[2]["reactions"]} reactions :+1:\n'

    top_posters_string = f"Top meme posters of the {sys.argv[1]} :rofl:\n"
    i = 0
    for u in sorted(top_posters, key=top_posters.get, reverse=True):
        if i == 0:
            top_posters_string = (
                top_posters_string
                + f":first_place: {u.mention} with {top_posters[u]} memes posted :joy:\n"
            )
        elif i == 1:
            top_posters_string = (
                top_posters_string
                + f":second_place: {u.mention} with {top_posters[u]} memes posted :smile:\n"
            )
        elif i == 2:
            top_posters_string = (
                top_posters_string
                + f":third_place: {u.mention} with {top_posters[u]} memes posted :upside_down:"
            )
        else:
            break
        i = i + 1

    top_reactor_string = f"Top meme enjoyers of the {sys.argv[1]} :rofl:\n"
    i = 0
    for u in sorted(top_reactors, key=top_reactors.get, reverse=True):
        if i == 0:
            top_reactor_string = (
                top_reactor_string
                + f":first_place: {u.mention} with {top_reactors[u]} reactions to memes :joy:\n"
            )
        elif i == 1:
            top_reactor_string = (
                top_reactor_string
                + f":second_place: {u.mention} with {top_reactors[u]} reactions to memes :smile:\n"
            )
        elif i == 2:
            top_reactor_string = (
                top_reactor_string
                + f":third_place: {u.mention} with {top_reactors[u]} reactions to memes :upside_down:"
            )
        else:
            break
        i = i + 1

    await meme_channel.send(content=announcemen_string)
    if winners[0]["memeType"] == "attachment":
        await meme_channel.send(
            content=first_place_string,
            file=winners[0]["meme"],
            reference=winners[0]["reference"],
        )
    else:
        await meme_channel.send(
            content=first_place_string,
            embed=winners[0]["meme"],
            reference=winners[0]["reference"],
        )

    if winners[1]["memeType"] == "attachment":
        await meme_channel.send(
            content=second_place_string,
            file=winners[1]["meme"],
            reference=winners[1]["reference"],
        )
    else:
        await meme_channel.send(
            content=second_place_string,
            embed=winners[1]["meme"],
            reference=winners[1]["reference"],
        )

    if winners[2]["memeType"] == "attachment":
        await meme_channel.send(
            content=third_place_string,
            file=winners[2]["meme"],
            reference=winners[2]["reference"],
        )
    else:
        await meme_channel.send(
            content=third_place_string,
            embed=winners[2]["meme"],
            reference=winners[2]["reference"],
        )

    await meme_channel.send(content=top_posters_string)
    await meme_channel.send(content=top_reactor_string)
    await client.close()
    sys.exit()


client.run(config.AUTH_TOKEN)
