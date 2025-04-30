import discord
from discord import app_commands
from dotenv import load_dotenv
import requests
import json
import base64
import re
import os
from keep_alive import keep_alive

load_dotenv()

intents = discord.Intents.default()
intents.members = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

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
    await tree.sync()

@tree.command(name="add", description="Add a Roblox ID to the whitelist.")
@app_commands.describe(discord_user="Mention the Discord user", roblox_id="Roblox ID to whitelist")
async def add(interaction: discord.Interaction, discord_user: discord.User, roblox_id: int):
    if interaction.user.id not in ALLOWED_USERS:
        await interaction.response.send_message("❌ You don't have permission to use this command.")
        return

    # Load file from GitHub
    response = requests.get(GITHUB_API_URL, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    if response.status_code != 200:
        await interaction.response.send_message(f"❌ Could not fetch whitelist file.")
        return

    file_data = response.json()
    file_content = base64.b64decode(file_data["content"]).decode("utf-8")

    # Parse Lua dictionary
    id_map = {int(k): int(v) for k, v in re.findall(r"\[(\d+)]\s*=\s*(\d+)", file_content)}

    if roblox_id in id_map:
        await interaction.response.send_message(f"⚠️ Roblox ID `{roblox_id}` is already added by <@{id_map[roblox_id]}>.")
        return

    id_map[roblox_id] = discord_user.id
    usernames = get_roblox_usernames([roblox_id])
    username = usernames.get(roblox_id, "Unknown User")

    embed = discord.Embed(
        title="✅ Successfully Added!",
        description=f"Roblox ID `{roblox_id}` - **{username}** has been added under <@{discord_user.id}>.",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)

    # Write back to GitHub
    update_github_file(id_map, file_data["sha"])

@tree.command(name="replace", description="Replace an existing Roblox ID with a new one.")
@app_commands.describe(old_id="Old Roblox ID", new_id="New Roblox ID")
async def replace(interaction: discord.Interaction, old_id: int, new_id: int):
    # Load file from GitHub
    response = requests.get(GITHUB_API_URL, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    if response.status_code != 200:
        await interaction.response.send_message(f"❌ Could not fetch whitelist file.")
        return

    file_data = response.json()
    file_content = base64.b64decode(file_data["content"]).decode("utf-8")

    # Parse Lua dictionary
    id_map = {int(k): int(v) for k, v in re.findall(r"\[(\d+)]\s*=\s*(\d+)", file_content)}

    if old_id not in id_map:
        await interaction.response.send_message(f"⚠️ Roblox ID `{old_id}` is not in the list.")
        return
    if id_map[old_id] != interaction.user.id:
        await interaction.response.send_message("❌ You can only replace your own Roblox ID.")
        return
    if new_id in id_map:
        await interaction.response.send_message(f"⚠️ Roblox ID `{new_id}` is already whitelisted.")
        return

    del id_map[old_id]
    id_map[new_id] = interaction.user.id
    await interaction.response.send_message(f"✅ Replaced `{old_id}` with `{new_id}`.")

    # Write back to GitHub
    update_github_file(id_map, file_data["sha"])

@tree.command(name="premiumcheck", description="Check your whitelisted Roblox IDs.")
async def premiumcheck(interaction: discord.Interaction):
    user_id = interaction.user.id

    # Load file from GitHub
    response = requests.get(GITHUB_API_URL, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    if response.status_code != 200:
        await interaction.response.send_message(f"❌ Could not fetch whitelist file.")
        return

    file_data = response.json()
    file_content = base64.b64decode(file_data["content"]).decode("utf-8")

    # Parse Lua dictionary
    id_map = {int(k): int(v) for k, v in re.findall(r"\[(\d+)]\s*=\s*(\d+)", file_content)}

    owned_ids = [rid for rid, did in id_map.items() if did == user_id]

    if not owned_ids:
        await interaction.response.send_message("🔍 You don't have any whitelisted Roblox IDs.")
    else:
        usernames = get_roblox_usernames(owned_ids)
        display = "\n".join(f"`{rid}` - **{usernames.get(rid, 'Unknown')}**" for rid in owned_ids)
        embed = discord.Embed(
            title="💼 Your Whitelisted Roblox Accounts",
            description=display,
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed)

@tree.command(name="check", description="Check if a Roblox ID is whitelisted.")
@app_commands.describe(roblox_id="Roblox ID to check")
async def check(interaction: discord.Interaction, roblox_id: int):
    # Load file from GitHub
    response = requests.get(GITHUB_API_URL, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    if response.status_code != 200:
        await interaction.response.send_message(f"❌ Could not fetch whitelist file.")
        return

    file_data = response.json()
    file_content = base64.b64decode(file_data["content"]).decode("utf-8")

    # Parse Lua dictionary
    id_map = {int(k): int(v) for k, v in re.findall(r"\[(\d+)]\s*=\s*(\d+)", file_content)}

    if roblox_id in id_map:
        await interaction.response.send_message(f"✅ Roblox ID `{roblox_id}` is whitelisted under <@{id_map[roblox_id]}>.")
    else:
        await interaction.response.send_message(f"❌ Roblox ID `{roblox_id}` is not whitelisted.")

@tree.command(name="list", description="List all whitelisted Roblox IDs.")
async def list(interaction: discord.Interaction):
    # Load file from GitHub
    response = requests.get(GITHUB_API_URL, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    if response.status_code != 200:
        await interaction.response.send_message(f"❌ Could not fetch whitelist file.")
        return

    file_data = response.json()
    file_content = base64.b64decode(file_data["content"]).decode("utf-8")

    # Parse Lua dictionary
    id_map = {int(k): int(v) for k, v in re.findall(r"\[(\d+)]\s*=\s*(\d+)", file_content)}

    if not id_map:
        await interaction.response.send_message("📃 The whitelist is empty.")
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
    await interaction.response.send_message(embed=embed)

keep_alive()
client.run(DISCORD_TOKEN)
