# 🐷Holger - Discord Meme Leaderboard Bot🐷

A discord bot that sends weekly, monthly, and yearly leaderboards in your Discord server's meme channel. 🥇

Leaderboard currently includes:

- Top memes 🐸 (Memes with the most number of reactions)
- Top meme posters ✉️ (# of images, videos, and gifs posted)
- Top meme enjoyers 🤣 (# of reactions made to memes posted by other people)

## Running the bot locally

1. Create and activate a Python venv (optional)
   1. `python -m venv venv`
   2. `source venv/bin/activate`
2. Install dependencies. `pip install -r requirements.txt`
3. Create a `.env` file with the following variables: (Syntax: `VARIABLE_NAME=value`)
   1. `CHANNEL_ID` - Discord meme channel ID
   2. `BOT_TOKEN` - Discord Bot token
   3. `MONGO_URI` - MongoDB connection string (default: `mongodb://localhost:27017/`)
   4. `DB_NAME` - MongoDB database name (default: `holger_db`)
   5. `LOG_LEVEL` - At what log level to log information (INFO, DEBUG, WARN, ERROR)
4. Run `docker-compose up -d` to start the bot locally, this will start the bot along side a MongoDB database.
