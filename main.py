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
PAIDLIST_API_URL = "https://api.github.com/repos/yuvic123/paid/contents/paidlist"

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

def update_paidlist_file(new_content, sha):
    updated_content = base64.b64encode(new_content.encode('utf-8')).decode('utf-8')

    data = {
        "message": "Update HWID list",
        "content": updated_content,
        "sha": sha
    }

    response = requests.put(
        PAIDLIST_API_URL,
        headers={"Authorization": f"token {GITHUB_TOKEN}"},
        json=data
    )

    if response.status_code == 200:
        print("Paidlist file updated successfully!")
    else:
        print(f"Failed to update paidlist file: {response.status_code} - {response.text}")

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    await client.change_presence(activity=discord.Game(name="Listening to Commands"))

@client.event
async def on_message(message):
    if not message.content.startswith((".add ", ".remove ", ".list", ".check", ".replace", ".white")):
        return

    if message.author.id not in ALLOWED_USERS:
        await message.channel.send("❌ You don't have permission to use this command.")
        return

    if message.content.startswith(".white"):
        response = requests.get(PAIDLIST_API_URL, headers={"Authorization": f"token {GITHUB_TOKEN}"})
        if response.status_code != 200:
            await message.channel.send(f"❌ Error fetching paidlist file: {response.status_code} - {response.text}")
            return

        file_data = response.json()
        file_content = base64.b64decode(file_data["content"]).decode('utf-8')
        existing_hwids = re.findall(r'"(.*?)"', file_content)

        if ".add" in message.content:
            try:
                target_hwid = message.content.split(" ")[2].strip()
            except IndexError:
                await message.channel.send("❌ Invalid HWID format. Please provide a valid string.")
                return

            if target_hwid in existing_hwids:
                await message.channel.send(f"⚠️ HWID `{target_hwid}` is already in the list.")
            else:
                existing_hwids.append(target_hwid)
                await message.channel.send(f"✅ Added HWID `{target_hwid}` to the list!")

        elif ".remove" in message.content:
            try:
                target_hwid = message.content.split(" ")[2].strip()
            except IndexError:
                await message.channel.send("❌ Invalid HWID format. Please provide a valid string.")
                return

            if target_hwid in existing_hwids:
                existing_hwids.remove(target_hwid)
                await message.channel.send(f"✅ Removed HWID `{target_hwid}` from the list!")
            else:
                await message.channel.send(f"⚠️ HWID `{target_hwid}` is not in the list.")

        updated_hwid_content = "return {\n" + ",\n".join(f'"{hwid}"' for hwid in existing_hwids) + "\n}"
        update_paidlist_file(updated_hwid_content, file_data["sha"])

keep_alive()
client.run(DISCORD_TOKEN)
