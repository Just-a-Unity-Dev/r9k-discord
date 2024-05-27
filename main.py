import datetime # For timing out members
import discord # For the library
import hashlib # For hashing messages
import sqlite3 # For handling DB
import yaml # Config handling

config = {}
with open("config.yml") as stream:
    try:
        config = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        raise Exception(exc)

def is_silent(): return config['options']['silent_mode']

conn = sqlite3.connect("main.db")
cur = conn.cursor()

# Create DB tables
cur.execute("""CREATE TABLE IF NOT EXISTS r9k_posts (text BLOB NOT NULL UNIQUE);""")
conn.commit()
cur.execute("""CREATE TABLE IF NOT EXISTS r9k_infractions (id TEXT NOT NULL UNIQUE, infractions INT NOT NULL);""")
conn.commit()

intents = discord.Intents.all()

client = discord.Client(intents=intents)

def isascii(s):
    # Used to see whether text is in ASCII or not
    return len(s) == len(s.encode())

async def robot(message: discord.Message):
    if message.author == client.user: return # We don't want to strike the robot itself
    if not (message.channel.id in config['channels']): return # Not the channel we want
    if not isascii(message.content):
        if not is_silent(): await message.reply("No unicode is allowed.") # Ban unicode
        await message.delete()

    hex = hashlib.md5(message.content.encode()).hexdigest()
    hash = bin(int(hex,16)) # Turns this into a binary hash
    search_hash = f"{message.guild.id}-{hash}"

    try:
        cur.execute("insert into r9k_posts values(?);", (search_hash,))
        conn.commit()
    except sqlite3.IntegrityError: # I know there's probably a better way of doing this, but this is a really quick script, so whatever
        # Non-unique
        infraction_amount = cur.execute("select infractions from r9k_infractions where id=?;", (str(message.author.id),)).fetchone()
        if infraction_amount is None:
            # Put them in the database
            infraction_amount = (1,)
            cur.execute("insert into r9k_infractions values(?, ?);", (message.author.id,infraction_amount[0],))
        else:
            # Just update them
            cur.execute("UPDATE r9k_infractions SET infractions = infractions + 1 WHERE id = ?", (str(message.author.id),))
            infraction_amount = (infraction_amount[0] + 1,) # To update the infraction amount without doing a DB call
        conn.commit()
        punishment_time_seconds = 2 ** infraction_amount[0]

        time_now = datetime.datetime.now(datetime.timezone.utc)
        punishment_date_time = datetime.datetime.fromtimestamp(time_now.timestamp() + punishment_time_seconds, datetime.timezone.utc)

        await message.author.timeout(punishment_date_time, reason=f"ROBOT: {infraction_amount[0]}th infraction.")
        if not is_silent(): await message.channel.send(f"<@{message.author.id}> has been muted for **{punishment_time_seconds}** seconds.")
        await message.delete()

@client.event
async def on_message_edit(before: discord.Message, after: discord.Message):
    if before.content != after.content:
        await robot(after)

@client.event
async def on_message(message: discord.Message):
    if message.channel.id in config['channels']: return await robot(message)

    if not config["options"]['run_commands']: return # Commands are disabled.
    # Basic stats command
    if message.content == "-stats":
        await message.delete()
        most_infractions = cur.execute("select infractions from r9k_infractions where id=?;", (str(message.author.id),)).fetchone()
        if most_infractions is None:
            await message.channel.send(f"<@{message.author.id}>, you have no infractions.")
        else:
            await message.channel.send(f"<@{message.author.id}>, you have {most_infractions[0]} infractions, and will be muted for {2 ** (most_infractions[0] + 1)} seconds next time.")
        return
    
    # Leaderboard command, to get the top ten users with the most infractions.
    if message.content == "-lb":
        await message.delete()
        most_infractions = cur.execute("select id, infractions from r9k_infractions order by infractions desc;").fetchmany(10)

        most_leaderboard = "## Most Infractions\n\n"
        for x in most_infractions: most_leaderboard += f"<@{x[0]}>: {x[1]} infractions, next mute will be **{2 ** (x[1] + 1)}** seconds\n"
        await message.channel.send(most_leaderboard, allowed_mentions=discord.AllowedMentions.none())

        return

client.run(config['bot']['token'])