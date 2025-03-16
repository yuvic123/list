import discord
import requests
import json
import base64
import re
import os  # To access environment variables
from keep_alive import keep_alive

# Initialize the bot
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# GitHub API URL for your new repository and file
GITHUB_API_URL = "https://api.github.com/repos/yuvic123/list/contents/list"

# Fetch tokens from environment variables (secrets)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # GitHub token from environment variables
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")  # Discord token from environment variables

# Allowed Discord IDs
ALLOWED_USERS = [
    1279868613628657860,
    598460565387476992,
    1272478153201422420,
    1197823319123165218
]

# Function to update the file on GitHub
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

# Function to get Roblox usernames
def get_roblox_usernames(user_ids):
    url = "https://users.roblox.com/v1/users"
    data = {"userIds": user_ids}

    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            return {user['id']: user['name'] for user in response.json()['data']}
        else:
            return {}
    except Exception as e:
        print(f"Error fetching usernames: {e}")
        return {}

# Listen for messages in Discord
@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    await client.change_presence(activity=discord.Game(name="Listening to Commands"))
    
@client.event
async def on_message(message):
    if not message.content.startswith((".add ", ".remove ", ".list", ".check", ".replace")):
        return

    # Check if the author is allowed or has the "Premium" role for `.replace`
    if message.content.startswith(".replace"):
        if not any(role.name == "Premium" for role in message.author.roles):
            await message.channel.send("❌ You need the **Premium** role to use this command.")
            return

    if message.author.id not in ALLOWED_USERS:
        await message.channel.send("❌ You don't have permission to use this command.")
        return

    # Fetch the current file content
    response = requests.get(GITHUB_API_URL, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    if response.status_code != 200:
        await message.channel.send(f"❌ Error fetching file: {response.status_code} - {response.text}")
        return

    file_data = response.json()
    file_content = base64.b64decode(file_data["content"]).decode('utf-8')

    # Extract existing IDs using regex
    existing_ids = re.findall(r'\d+', file_content)
    existing_ids = list(map(int, existing_ids))

    # .add Command
    if message.content.startswith(".add "):
        try:
            target_id = int(message.content.split(" ")[1].strip())
        except (ValueError, IndexError):
            await message.channel.send("❌ Invalid Roblox ID format. Please provide a numeric ID.")
            return

        if target_id in existing_ids:
            await message.channel.send(f"⚠️ Roblox ID `{target_id}` is already in the list.")
        else:
            existing_ids.append(target_id)
            await message.channel.send(f"✅ Added Roblox ID `{target_id}` to the list!")

    # .remove Command
    elif message.content.startswith(".remove "):
        try:
            target_id = int(message.content.split(" ")[1].strip())
        except (ValueError, IndexError):
            await message.channel.send("❌ Invalid Roblox ID format. Please provide a numeric ID.")
            return

        if target_id in existing_ids:
            existing_ids.remove(target_id)
            await message.channel.send(f"✅ Removed Roblox ID `{target_id}` from the list!")
        else:
            await message.channel.send(f"⚠️ Roblox ID `{target_id}` is not in the list.")

    # .replace Command
    elif message.content.startswith(".replace"):
        try:
            _, old_id, new_id = message.content.split(" ")
            old_id, new_id = int(old_id.strip()), int(new_id.strip())
        except (ValueError, IndexError):
            await message.channel.send("❌ Invalid format. Use `.replace <old_id> <new_id>`")
            return

        if old_id in existing_ids:
            existing_ids.remove(old_id)
            existing_ids.append(new_id)
            await message.channel.send(f"✅ Successfully replaced **{old_id}** with **{new_id}**.")
        else:
            await message.channel.send(f"⚠️ Roblox ID `{old_id}` not found in the list.")

    # .list Command
    elif message.content.startswith(".list"):
        if not existing_ids:
            embed = discord.Embed(
                title="❄️ Premium Roblox IDs",
                description="No premium Roblox IDs are currently listed.",
                color=discord.Color.blue()
            )
            embed.set_footer(text="Use .add <ID> to add new IDs")
        else:
            usernames = get_roblox_usernames(existing_ids)
            display_list = "\n".join(
                [f"`{uid}` - **{usernames.get(uid, 'Unknown User')}**" for uid in existing_ids]
            )

            embed = discord.Embed(
                title="💎 Premium Roblox Users",
                description=display_list,
                color=discord.Color.purple()
            )
            embed.set_footer(text=f"Total IDs: {len(existing_ids)} | Use .remove <ID> to delete")

        await message.channel.send(embed=embed)

    # .check Command
    elif message.content.startswith(".check"):
        try:
            target_id = int(message.content.split(" ")[1].strip())
        except (ValueError, IndexError):
            await message.channel.send("❌ Invalid Roblox ID format. Please provide a numeric ID.")
            return

        if target_id in existing_ids:
            await message.channel.send(f"✅ Roblox ID `{target_id}` **is premium**.")
        else:
            await message.channel.send(f"❌ Roblox ID `{target_id}` **is not premium**.")

    # Update the Lua content
    updated_lua_content = f"getgenv().ownerIDs = {{{', '.join(map(str, existing_ids))}}}\nreturn getgenv().ownerIDs"

    # Update the file on GitHub
    update_github_file(updated_lua_content, file_data["sha"])

# Run the Discord bot
keep_alive()
client.run(DISCORD_TOKEN)
