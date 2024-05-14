import datetime # For timing out members
import discord # For the library
import hashlib # For hashing messages
import sqlite3 # For handling DB
import os # Env
from dotenv import load_dotenv # Env
load_dotenv()

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

@client.event
async def on_message(message):
    if message.author == client.user: # We don't want to strike the robot itself
        return

    if message.channel.id != int(os.getenv("CHANNEL")): # This isn't the channel we want
        return # Not the channel we want

    if not isascii(message.content):
        await message.reply("No unicode is allowed.") # Ban unicode
        await message.delete()

    hex = hashlib.md5(message.content.encode()).hexdigest()
    hash = bin(int(hex,16)) # Turns this into a binary hash
    try:
        cur.execute("insert into r9k_posts values(?);", (hash,))
        conn.commit()
    except sqlite3.IntegrityError: # I know there's probably a better way of doing this, but this is a really quick script, so whatever
        # Non-unique
        await message.reply("You can only post unique text here.")
        await message.delete()

        infraction_amount = cur.execute("select infractions from r9k_infractions where id=?;", (str(message.author.id),)).fetchone()
        if infraction_amount == None:
            # Put them in the database
            infraction_amount = (1,)
            cur.execute("insert into r9k_infractions values(?, ?);", (message.author.id,infraction_amount,))
        else:
            # Just update them
            cur.execute("UPDATE r9k_infractions SET infractions = infractions + 1 WHERE id = ?", (str(message.author.id),))
        conn.commit()
        punishment_time = 2 ** infraction_amount[0]

        time_now = datetime.datetime.now(datetime.timezone.utc)
        punish_time = datetime.datetime.fromtimestamp(time_now.timestamp() + punishment_time, datetime.timezone.utc)

        await message.author.timeout(punish_time)

client.run(os.getenv("TOKEN"))