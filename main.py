from dotenv import load_dotenv
import discord
import requests
import json
import base64
import re
import os 
from keep_alive import keep_alive

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

GITHUB_API_URL = "https://api.github.com/repos/yuvic123/list/contents/list"

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

ALLOWED_USERS = [
    1279868613628657860,
    598460565387476992,
    1272478153201422420,
    1197823319123165218
]

def update_github_file(new_content, sha):
    updated_content = base64.b64encode(new_content.encode('utf-8')).decode('utf-8')

    data = {
        "message": "Update Roblox ID list",
        "content": updated_content,
        "sha": sha
    }

    response = requests.put(
        GITHUB_API_URL,
        headers={"Authorization": f"token {GITHUB_TOKEN}"},
        json=data
    )

    if response.status_code == 200:
        print("File updated successfully!")
    else:
        print(f"Failed to update file: {response.status_code} - {response.text}")

def get_roblox_user_info(user_ids):
    url = "https://users.roblox.com/v1/users"
    data = {"userIds": user_ids}

    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            return {user['id']: (user['name'], f"https://www.roblox.com/headshot-thumbnail/image?userId={user['id']}&width=420&height=420&format=png") for user in response.json()['data']}
        else:
            return {}
    except Exception as e:
        print(f"Error fetching user info: {e}")
        return {}

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    await client.change_presence(activity=discord.Game(name="Listening to Commands"))

@client.event
async def on_message(message):
    if not message.content.startswith(('.add', '.remove', '.list', '.check', '.replace')):
        return

    if message.author.id not in ALLOWED_USERS:
        await message.channel.send("❌ You don't have permission to use this command.")
        return

    response = requests.get(GITHUB_API_URL, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    if response.status_code != 200:
        await message.channel.send(f"❌ Error fetching file: {response.status_code} - {response.text}")
        return

    file_data = response.json()
    file_content = base64.b64decode(file_data["content"]).decode('utf-8')

    existing_ids = re.findall(r'\d+', file_content)
    existing_ids = list(map(int, existing_ids))

    if message.content.startswith(".add"):
        try:
            target_id = int(message.content.split(" ")[1].strip())
        except (ValueError, IndexError):
            await message.channel.send("❌ Invalid Roblox ID format. Please provide a numeric ID.")
            return

        if target_id in existing_ids:
            await message.channel.send(f"⚠️ Roblox ID {target_id} is already in the list.")
        else:
            existing_ids.append(target_id)
            user_info = get_roblox_user_info([target_id])
            username, profile_image = user_info.get(target_id, ("Unknown User", ""))

            embed = discord.Embed(
                title="✅ Successfully Added!",
                description=f"**{target_id}** - **{username}** has been added to the whitelist.",
                color=discord.Color.blue()
            )
            if profile_image:
                embed.set_thumbnail(url=profile_image)
            await message.channel.send(embed=embed)

    elif message.content.startswith(".remove"):
        try:
            target_id = int(message.content.split(" ")[1].strip())
        except (ValueError, IndexError):
            await message.channel.send("❌ Invalid Roblox ID format. Please provide a numeric ID.")
            return

        if target_id in existing_ids:
            existing_ids.remove(target_id)
            await message.channel.send(f"✅ Removed Roblox ID {target_id} from the list!")
        else:
            await message.channel.send(f"⚠️ Roblox ID {target_id} is not in the list.")

    updated_lua_content = f"getgenv().ownerIDs = {{{', '.join(map(str, existing_ids))}}}\nreturn getgenv().ownerIDs"

    update_github_file(updated_lua_content, file_data["sha"])

keep_alive()
client.run(DISCORD_TOKEN)
