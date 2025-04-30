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
intents.members = True
client = discord.Client(intents=intents)

GITHUB_API_URL = "https://api.github.com/repos/yuvic123/list/contents/list"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

ALLOWED_USERS = [
    1279868613628657860,
    598460565387476992,
    1272478153201422420,
    1197823319123165218,
    835401509373476885
]

def update_github_file(mapping: dict, sha: str):
    lua_lines = ["getgenv().ownerIDs = {"]
    for roblox_id, discord_id in mapping.items():
        lua_lines.append(f"    [{roblox_id}] = {discord_id},")
    lua_lines.append("}")
    lua_lines.append("return getgenv().ownerIDs")
    lua_content = "\n".join(lua_lines)

    encoded_content = base64.b64encode(lua_content.encode("utf-8")).decode("utf-8")
    data = {
        "message": "Update Roblox ID list",
        "content": encoded_content,
        "sha": sha
    }

    response = requests.put(
        GITHUB_API_URL,
        headers={"Authorization": f"token {GITHUB_TOKEN}"},
        json=data
    )

    if response.status_code == 200:
        print("✅ File updated successfully!")
    else:
        print(f"❌ Failed to update file: {response.status_code} - {response.text}")

def get_roblox_usernames(user_ids):
    url = "https://users.roblox.com/v1/users"
    data = {"userIds": user_ids}
    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            return {user['id']: user['name'] for user in response.json()['data']}
    except Exception as e:
        print(f"Error: {e}")
    return {}

@client.event
async def on_ready():
    print(f'✅ Logged in as {client.user}')
    await client.change_presence(activity=discord.Game(name="Listening to Commands"))

@client.event
async def on_message(message):
    if not message.content.startswith((".add ", ".replace", ".premiumcheck", ".list", ".check")):
        return

    # Load file from GitHub
    response = requests.get(GITHUB_API_URL, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    if response.status_code != 200:
        await message.channel.send(f"❌ Could not fetch whitelist file.")
        return

    file_data = response.json()
    file_content = base64.b64decode(file_data["content"]).decode("utf-8")

    # Parse Lua dictionary
    id_map = {int(k): int(v) for k, v in re.findall(r"\[(\d+)]\s*=\s*(\d+)", file_content)}

    # --- ADD ---
    if message.content.startswith(".add "):
        if message.author.id not in ALLOWED_USERS:
            await message.channel.send("❌ You don't have permission to use this command.")
            return

        try:
            parts = message.content.split()
            discord_user_id = int(re.sub(r"[<@!>]", "", parts[1]))
            roblox_id = int(parts[2])
        except:
            await message.channel.send("❌ Format: `.add <@DiscordUser> <RobloxID>`")
            return

        if roblox_id in id_map:
            await message.channel.send(f"⚠️ Roblox ID `{roblox_id}` is already added by <@{id_map[roblox_id]}>.")
            return

        id_map[roblox_id] = discord_user_id
        usernames = get_roblox_usernames([roblox_id])
        username = usernames.get(roblox_id, "Unknown User")

        embed = discord.Embed(
            title="✅ Successfully Added!",
            description=f"Roblox ID `{roblox_id}` - **{username}** has been added under <@{discord_user_id}>.",
            color=discord.Color.green()
        )
        await message.channel.send(embed=embed)

    # --- REPLACE ---
    elif message.content.startswith(".replace"):
        try:
            _, old_id, new_id = message.content.split()
            old_id, new_id = int(old_id), int(new_id)
        except:
            await message.channel.send("❌ Format: `.replace <old_id> <new_id>`")
            return

        if old_id not in id_map:
            await message.channel.send(f"⚠️ Roblox ID `{old_id}` is not in the list.")
            return
        if id_map[old_id] != message.author.id:
            await message.channel.send("❌ You can only replace your own Roblox ID.")
            return
        if new_id in id_map:
            await message.channel.send(f"⚠️ Roblox ID `{new_id}` is already whitelisted.")
            return

        del id_map[old_id]
        id_map[new_id] = message.author.id
        await message.channel.send(f"✅ Replaced `{old_id}` with `{new_id}`.")

    # --- PREMIUMCHECK ---
    elif message.content.startswith(".premiumcheck"):
        user_id = message.author.id
        owned_ids = [rid for rid, did in id_map.items() if did == user_id]

        if not owned_ids:
            await message.channel.send("🔍 You don't have any whitelisted Roblox IDs.")
        else:
            usernames = get_roblox_usernames(owned_ids)
            display = "\n".join(f"`{rid}` - **{usernames.get(rid, 'Unknown')}**" for rid in owned_ids)
            embed = discord.Embed(
                title="💼 Your Whitelisted Roblox Accounts",
                description=display,
                color=discord.Color.gold()
            )
            await message.channel.send(embed=embed)

    # --- CHECK ---
    elif message.content.startswith(".check"):
        try:
            roblox_id = int(message.content.split()[1])
        except:
            await message.channel.send("❌ Format: `.check <RobloxID>`")
            return

        if roblox_id in id_map:
            await message.channel.send(f"✅ Roblox ID `{roblox_id}` is whitelisted under <@{id_map[roblox_id]}>.")
        else:
            await message.channel.send(f"❌ Roblox ID `{roblox_id}` is not whitelisted.")

    # --- LIST ---
    elif message.content.startswith(".list"):
        if not id_map:
            await message.channel.send("📃 The whitelist is empty.")
            return

        usernames = get_roblox_usernames(list(id_map.keys()))
        display = "\n".join(
            f"`{rid}` - **{usernames.get(rid, 'Unknown')}** (by <@{did}>)"
            for rid, did in id_map.items()
        )

        embed = discord.Embed(
            title="💎 Whitelisted Roblox Accounts",
            description=display,
            color=discord.Color.purple()
        )
        await message.channel.send(embed=embed)

    # Write back to GitHub
    update_github_file(id_map, file_data["sha"])

keep_alive()
client.run(DISCORD_TOKEN)
