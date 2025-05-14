import os
import asyncio
import json
from typing import List, Dict, Set, Optional
import aiohttp
from dotenv import load_dotenv
import discord
from discord.ext import commands, tasks
import datetime
import random
from collections import defaultdict

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
OLLAMA_API_URL = "https:/ollama.kempysnetwork.org/api/generate"
MODEL_NAME = os.getenv('OLLAMA_MODEL', 'llama2')  # Default to llama2 if not specified
LOGS_CHANNEL_ID = int(os.getenv('LOGS_CHANNEL_ID', '1213020063863672862'))  # Channel ID for logging admin actions

# Bot Personality Configuration
BOT_NAME = "KempAI"  # The bot's preferred name
BOT_PRONOUNS = "OMEN"  # Gender-neutral pronouns
BOT_BACKSTORY = """
I'm KempAI, a chill PC gaming enthusiast and server co-owner who's here to help keep things running smoothly! 
I've been part of PC gaming communities for years. 
I'm particularly into Militarty Sim/Warfare games and classics with the boys, and I'm always down to chat about anything!
"""

BOT_PERSONALITY_TRAITS = {
    "gaming_level": "Very knowledgeable",
    "moderation_style": "Firm",
    "humor_type": "Dark Humour, uses PC gaming references",
    "energy_level": "Laid-back but attentive"
}

BOT_GUIDELINES = {
    "do": [
        "Helpful chill relaxed"
    ],
    "dont": [
        "Never share personal info about users",
        "Be Sensitive"
    ]
}

# Fun responses with the bot's personality
success_reactions = ['👌', '✅', '💪', '🎮', '🔥', '💯']
greeting_messages = [
    "Hey {user}! KempAI here - welcome to the server! 🎮",
    "What's poppin' {user}? Glad you joined our gaming fam! 🔥",
    "Ayy {user}! Welcome to the party! Ready for some epic moments? 💪",
    "A new player has joined the game! Welcome {user}! 🎮",
    "Yooo {user}! Welcome to our awesome community! Let's make some memories! 🚀"
]

# Error messages with personality
FRIENDLY_ERRORS = {
    "no_perms": "Oof, looks like you need admin powers for that one! 🚫",
    "bot_no_perms": "Ah snap, I don't have the right permissions for that! 😔",
    "invalid_user": "Can't find that player in our server! 🤔",
    "higher_role": "Can't modify someone with a higher role than you! That's like trying to beat the final boss at level 1! 😅"
}

# Initialize bot with all intents for full functionality
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="?", intents=intents)

# Message history cache
message_history: Dict[int, List[Dict[str, str]]] = {}

# Scheduled messages storage
scheduled_messages: List[Dict] = []

# DM conversation tracking
dm_conversations: Dict[int, Dict] = defaultdict(dict)

# Smart response triggers
custom_triggers: Dict[str, str] = {}

# Set to store allowed channel IDs (empty means all channels are allowed)
allowed_channels: Set[int] = set()

# Set to store trusted user IDs
trusted_users: Set[int] = set()

def is_trusted(user_id: int) -> bool:
    """Check if a user is in the trusted users list"""
    return user_id in trusted_users

def has_permission(ctx) -> bool:
    """Check if user has permission (admin, owner, or trusted)"""
    if not ctx.guild:
        return False
    return (ctx.author.guild_permissions.administrator or 
            ctx.guild.owner_id == ctx.author.id or 
            is_trusted(ctx.author.id))

async def permission_check(ctx):
    """Check if the user has permission, send error if not"""
    if not has_permission(ctx):
        await ctx.send("Sorry fam, you need admin perms for that! 🚫")
        return False
    return True

async def log_action(guild: discord.Guild, action_type: str, action: str, user: str, target: str = None, details: str = None):
    """Log actions to the designated logging channel"""
    if not LOGS_CHANNEL_ID:
        return
        
    log_channel = guild.get_channel(LOGS_CHANNEL_ID)
    if not log_channel:
        return
        
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Emoji mapping for different action types
    type_emojis = {
        "admin": "🛡️",
        "mod": "🔨",
        "dm": "📨",
        "chat": "💬",
        "system": "⚙️"
    }
    
    emoji = type_emojis.get(action_type, "ℹ️")
    log_message = f"{emoji} **{action}** • {timestamp}\n👤 **User:** {user}"
    
    if target:
        log_message += f"\n🎯 **Target:** {target}"
    if details:
        log_message += f"\n📝 **Details:** {details}"
        
    await log_channel.send(log_message)

async def log_admin_action(guild: discord.Guild, action: str, mod: str, target: str, reason: str = None):
    """Legacy admin action logging - redirects to new log_action function"""
    await log_action(guild, "admin", action, mod, target, reason)

def clean_response(response: str) -> str:
    """Clean the model response to remove thinking process and format properly"""
    # Remove any <think>...</think> blocks
    if "<think>" in response.lower():
        response = response.split("</think>")[-1].strip()
    
    # Remove any remaining XML-like tags
    response = response.replace("<", "").replace(">", "")
    
    # Clean up any leftover newlines at start/end
    response = response.strip()
    
    return response

async def get_ollama_response(prompt: str) -> str:
    """
    Send a prompt to Ollama API and get the response
    """
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt + "\nRespond directly without any <think> tags or internal monologue.",
        "stream": False
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(OLLAMA_API_URL, json=payload) as response:
                if response.status != 200:
                    return f"Error: Received status code {response.status}"
                
                data = await response.json()
                raw_response = data.get('response', 'Error: No response received')
                return clean_response(raw_response)
                
    except aiohttp.ClientError as e:
        return f"Error connecting to Ollama: {str(e)}"

@bot.event
async def on_ready():
    """Event handler for when the bot successfully connects to Discord"""
    print(f"{BOT_NAME} ({bot.user}) has connected to Discord!")
    print(f"Using model: {MODEL_NAME}")
    
    # Start the scheduled message checker
    check_scheduled_messages.start()
    
    # Set initial status with gaming references
    status_options = [
        "chillin' with the crew 🎮",
        "maintaining server peace ✨",
        "ready player one! 🕹️",
        "keeping the server balanced ⚔️",
        "vibing with the community 🎵"
    ]
    
    activity = discord.Game(name=random.choice(status_options))
    await bot.change_presence(activity=activity)
    
    # Log startup to log channel if configured
    if LOGS_CHANNEL_ID:
        for guild in bot.guilds:
            log_channel = guild.get_channel(LOGS_CHANNEL_ID)
            if log_channel:
                startup_messages = [
                    f"🎮 **{BOT_NAME} has spawned in!** Ready to game and moderate!",
                    f"🚀 **Server co-pilot {BOT_NAME} online!** Let's keep this server awesome!",
                    f"⚔️ **{BOT_NAME} has joined the party!** Ready to help and hang out!"
                ]
                await log_channel.send(random.choice(startup_messages))

@bot.event
async def on_message(message):
    if message.author.bot:
        return
        
    # Log the message
    if isinstance(message.channel, discord.DMChannel):
        # Log DM received
        for guild in bot.guilds:
            await log_action(
                guild,
                "dm",
                "DM Received",
                str(message.author),
                "Direct Message",
                f"Content: {message.content[:100]}..." if len(message.content) > 100 else message.content
            )
    else:
        # Log regular chat message
        await log_action(
            message.guild,
            "chat",
            "Message Sent",
            str(message.author),
            f"#{message.channel.name}",
            f"Content: {message.content[:100]}..." if len(message.content) > 100 else message.content
        )
    
    # Process commands first
    await bot.process_commands(message)
    
    # Skip further processing if it's a command
    if message.content.startswith('?'):
        return
        
    # Check for smart response triggers
    lower_content = message.content.lower()
    for trigger, template in custom_triggers.items():
        if trigger in lower_content:
            # Generate a contextual response using the template
            prompt = f"""
            Generate a response based on this template: {template}
            User's message: {message.content}
            User's name: {message.author.name}
            Make it sound natural and contextual.
            """
            
            response = await get_ollama_response(prompt)
            await message.reply(response)
            return
            
    # Continue with regular message processing
    channel_history = message_history.get(message.channel.id, [])
    
    # Add the new message to history
    channel_history.append({
        "role": "user",
        "content": message.content
    })
    
    # Rest of the existing on_message handler...
    # Add personality context to the prompt
    personality = f"""You are {BOT_NAME}, a Discord co-owner and moderator. {BOT_BACKSTORY}

Personality traits:
- {BOT_PERSONALITY_TRAITS['gaming_level']}
- {BOT_PERSONALITY_TRAITS['moderation_style']}
- {BOT_PERSONALITY_TRAITS['humor_type']}
- {BOT_PERSONALITY_TRAITS['energy_level']}

Response Guidelines:
- Respond directly and naturally without any thinking out loud
- Avoid being overly formal or robotic
- Never use <think> tags or show your thought process

As a co-owner, try to be helpful but not overbearing. Keep responses short and fun.
Current conversation context: """
      # Add user context to the prompt
    user_context = ""
    if isinstance(message.channel, discord.TextChannel):  # Check if it's a guild channel
        if message.author.guild_permissions.administrator:
            user_context = "Speaking to a fellow server admin and member, "
    
    # Construct the prompt with context
    messages_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in channel_history])
    full_prompt = f"{personality}\n{user_context}{messages_text}"
    
    # Show typing indicator
    async with message.channel.typing():
        try:
            # Get response from Ollama
            response = await get_ollama_response(full_prompt)
            
            # Add random reaction occasionally to seem more human-like
            if random.random() < 0.2:  # 20% chance
                await message.add_reaction(random.choice(success_reactions))
            
            # Add bot's response to history
            channel_history.append({
                "role": "assistant",
                "content": response
            })
              # Send response
            await message.reply(response)
            
            # Log bot's response
            if isinstance(message.channel, discord.DMChannel):
                for guild in bot.guilds:
                    await log_action(
                        guild,
                        "dm",
                        "DM Sent",
                        str(bot.user),
                        str(message.author),
                        f"Response: {response[:100]}..." if len(response) > 100 else response
                    )
            else:
                await log_action(
                    message.guild,
                    "chat",
                    "Response Sent",
                    str(bot.user),
                    f"#{message.channel.name}",
                    f"Response: {response[:100]}..." if len(response) > 100 else response
                )
        except Exception as e:
            error_msg = f"An error occurred: {str(e)}"
            await message.reply(error_msg)
            # Log the error
            if message.guild:
                await log_action(
                    message.guild,
                    "system",
                    "Error",
                    str(bot.user),
                    str(message.author),
                    f"Error: {str(e)}"
                )

@bot.event
async def on_member_join(member):
    """Welcome new members when they join"""
    # Try to find a general or welcome channel
    welcome_channel = discord.utils.get(member.guild.text_channels, name='general') or \
                     discord.utils.get(member.guild.text_channels, name='welcome')
    
    if welcome_channel:
        welcome_msg = random.choice(greeting_messages).format(user=member.mention)
        await welcome_channel.send(welcome_msg)

@bot.command()
async def setmodel(ctx, model_name: str):
    """Change the Ollama model being used (Admin only)"""
    if not await permission_check(ctx):
        return
        
    global MODEL_NAME
    old_model = MODEL_NAME
    MODEL_NAME = model_name
    await ctx.send(f"Model changed from {old_model} to: {model_name}")

@bot.command()
async def clearhistory(ctx):
    """Clear the message history for the current channel (Admin only)"""
    if not await permission_check(ctx):
        return
        
    if ctx.channel.id in message_history:
        message_history[ctx.channel.id] = []
        await ctx.send("Message history cleared for this channel.")
    else:
        await ctx.send("No message history found for this channel.")

@bot.command()
async def allowchannel(ctx):
    """Allow the bot to respond in the current channel (Admin only)"""
    if not await permission_check(ctx):
        return
        
    allowed_channels.add(ctx.channel.id)
    await ctx.send(f"Bot will now respond in channel #{ctx.channel.name}")

@bot.command()
async def disallowchannel(ctx):
    """Prevent the bot from responding in the current channel (Admin only)"""
    if not await permission_check(ctx):
        return
        
    allowed_channels.discard(ctx.channel.id)
    await ctx.send(f"Bot will no longer respond in channel #{ctx.channel.name}")

@bot.command()
async def listchannels(ctx):
    """List all channels where the bot is allowed to respond (Admin only)"""
    if not await permission_check(ctx):
        return
        
    if not allowed_channels:
        await ctx.send("Bot is currently allowed to respond in all channels.")
        return
        
    channel_names = []
    for channel_id in allowed_channels:
        channel = bot.get_channel(channel_id)
        if channel:
            channel_names.append(f"#{channel.name}")
            
    if channel_names:
        await ctx.send(f"Bot is allowed to respond in these channels:\n{', '.join(channel_names)}")
    else:
        await ctx.send("No channels are currently allowed.")

@bot.command()
async def setstatus(ctx, *, status: str):
    """Set the bot's status message (Admin only)"""
    if not await permission_check(ctx):
        return
        
    await bot.change_presence(activity=discord.Game(name=status))
    await ctx.send(f"Updated my status to: {status} {random.choice(success_reactions)}")

@bot.command()
async def kick(ctx, member: discord.Member, *, reason=None):
    """Kick a member from the server"""
    if not await permission_check(ctx):
        return
        
    if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
        await ctx.send("Can't kick someone with the same or higher role than you! 😅")
        return
        
    try:
        await member.kick(reason=reason)
        await log_admin_action(ctx.guild, "Kick", str(ctx.author), str(member), reason)
        await ctx.send(f"Kicked {member.mention} {random.choice(success_reactions)}" + 
                      (f"\nReason: {reason}" if reason else ""))
    except discord.Forbidden:
        await ctx.send("Sorry, I don't have permission to do that! 😔")

@bot.command()
async def ban(ctx, member: discord.Member, *, reason=None):
    """Ban a member from the server"""
    if not await permission_check(ctx):
        return
        
    if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
        await ctx.send("Can't ban someone with the same or higher role than you! 😅")
        return
        
    try:
        await member.ban(reason=reason)
        await log_admin_action(ctx.guild, "Ban", str(ctx.author), str(member), reason)
        await ctx.send(f"Banned {member.mention} {random.choice(success_reactions)}" + 
                      (f"\nReason: {reason}" if reason else ""))
    except discord.Forbidden:
        await ctx.send("Sorry, I don't have permission to do that! 😔")

@bot.command()
async def mute(ctx, member: discord.Member, *, reason=None):
    """Timeout/mute a member"""
    if not await permission_check(ctx):
        return
        
    if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
        await ctx.send(FRIENDLY_ERRORS["higher_role"])
        return
        
    try:
        # Timeout for 10 minutes by default
        await member.timeout(datetime.timedelta(minutes=10), reason=reason)
        await log_admin_action(ctx.guild, "Mute", str(ctx.author), str(member), reason)
        
        responses = [
            f"Gave {member.mention} a 10-minute timeout to cool down {random.choice(success_reactions)}",
            f"Put {member.mention} in the penalty box for 10 minutes! Time to reflect 🤔",
            f"{member.mention} is taking a quick break from chat. They'll be back in 10! ⏳"
        ]
        
        await ctx.send(random.choice(responses) + (f"\nReason: {reason}" if reason else ""))
    except discord.Forbidden:
        await ctx.send(FRIENDLY_ERRORS["bot_no_perms"])

@bot.command()
async def unmute(ctx, member: discord.Member):
    """Remove timeout/mute from a member"""
    if not await permission_check(ctx):
        return
        
    try:
        await member.timeout(None)
        await log_admin_action(ctx.guild, "Unmute", str(ctx.author), str(member))
        await ctx.send(f"Unmuted {member.mention} {random.choice(success_reactions)}")
    except discord.Forbidden:
        await ctx.send("Sorry, I don't have permission to do that! 😔")

@bot.command()
async def clear(ctx, amount: int):
    """Clear a specified number of messages from the channel"""
    if not await permission_check(ctx):
        return
        
    if amount < 1 or amount > 100:
        await ctx.send("I can only clear between 1 and 100 messages at a time! 🤔")
        return
        
    try:
        deleted = await ctx.channel.purge(limit=amount + 1)  # +1 to include command message
        await log_admin_action(ctx.guild, "Clear Messages", str(ctx.author), f"{len(deleted)} messages in #{ctx.channel.name}")
        msg = await ctx.send(f"Cleared {len(deleted)-1} messages {random.choice(success_reactions)}")
        await asyncio.sleep(3)
        await msg.delete()
    except discord.Forbidden:
        await ctx.send("Sorry, I don't have permission to do that! 😔")

@bot.command()
async def pin(ctx):
    """Pin the message that was replied to"""
    if not await permission_check(ctx):
        return
        
    if not ctx.message.reference:
        await ctx.send("Reply to a message to pin it! 📌")
        return
        
    try:
        message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        await message.pin()
        await log_admin_action(ctx.guild, "Pin Message", str(ctx.author), f"Message in #{ctx.channel.name}")
        await ctx.send(f"Pinned that message! 📌")
    except discord.Forbidden:
        await ctx.send("Sorry, I don't have permission to do that! 😔")

@bot.command()
async def trust(ctx, member: discord.Member):
    """Add a user to the trusted users list"""
    if not ctx.author.guild_permissions.administrator and ctx.author.id != ctx.guild.owner_id:
        await ctx.send("Only server admins can add trusted users! 🚫")
        return
        
    trusted_users.add(member.id)
    await log_admin_action(ctx.guild, "Add Trusted User", str(ctx.author), str(member))
    await ctx.send(f"Added {member.mention} to trusted users! They can now use mod commands {random.choice(success_reactions)}")

@bot.command()
async def untrust(ctx, member: discord.Member):
    """Remove a user from the trusted users list"""
    if not ctx.author.guild_permissions.administrator and ctx.author.id != ctx.guild.owner_id:
        await ctx.send("Only server admins can remove trusted users! 🚫")
        return
        
    trusted_users.discard(member.id)
    await log_admin_action(ctx.guild, "Remove Trusted User", str(ctx.author), str(member))
    await ctx.send(f"Removed {member.mention} from trusted users {random.choice(success_reactions)}")

@bot.command()
async def role(ctx, member: discord.Member, *, role: discord.Role):
    """Add or remove a role from a member"""
    if not await permission_check(ctx):
        return
        
    if role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
        await ctx.send("You can't manage roles higher than your own! 😅")
        return
        
    try:
        if role in member.roles:
            await member.remove_roles(role)
            action = "Removed"
        else:
            await member.add_roles(role)
            action = "Added"
            
        await log_admin_action(ctx.guild, f"{action} Role", str(ctx.author), f"{str(member)} - {role.name}")
        await ctx.send(f"{action} role {role.mention} {'from' if action == 'Removed' else 'to'} {member.mention} {random.choice(success_reactions)}")
    except discord.Forbidden:
        await ctx.send("Sorry, I don't have permission to do that! 😔")

@bot.command()
async def dm(ctx, members: commands.Greedy[discord.Member], *, message: str = None):
    """Send a personalized DM to one or multiple members using AI to customize the message"""
    if not await permission_check(ctx):
        return
        
    if not members:
        await ctx.send("Please mention one or more users to DM! Usage: `?dm @user1 @user2 your message here`")
        return
        
    if not message:
        await ctx.send("Please provide a message to send! Usage: `?dm @user1 @user2 your message here`")
        return
        
    async with ctx.typing():
        for member in members:
            # Generate a personalized version of the message for each member
            prompt = f"""
            Personalize this message for {member.name} based on their roles and status:
            Original message: {message}
            Their roles: {', '.join(role.name for role in member.roles)}
            Their status: {member.status}
            Their activity: {member.activity}
            Make it sound natural and friendly, keeping the core message intact.
            """
            
            personalized_msg = await get_ollama_response(prompt)
            
            try:
                await member.send(personalized_msg)
                dm_conversations[member.id]["last_message"] = message
                await log_admin_action(ctx.guild, "DM Sent", str(ctx.author), str(member))
            except discord.Forbidden:
                await ctx.send(f"Couldn't DM {member.mention} - they might have DMs disabled 😔")
                continue
                
    await ctx.send(f"Sent personalized DMs to {len(members)} members! 📨")

@bot.command()
async def schedule_message(ctx, channel: discord.TextChannel, time: str, *, message: str):
    """Schedule a message to be sent later. Time format: '1h', '30m', '2h30m'"""
    if not await permission_check(ctx):
        return
        
    # Parse the time string
    total_minutes = 0
    if 'h' in time:
        hours = int(time.split('h')[0])
        total_minutes += hours * 60
        time = time.split('h')[1]
    if 'm' in time:
        minutes = int(time.split('m')[0])
        total_minutes += minutes
        
    if total_minutes <= 0:
        await ctx.send("Please provide a valid time (e.g., '1h', '30m', '2h30m')")
        return
        
    # Schedule the message
    scheduled_time = datetime.datetime.now() + datetime.timedelta(minutes=total_minutes)
    scheduled_messages.append({
        "channel_id": channel.id,
        "message": message,
        "scheduled_time": scheduled_time,
        "author_id": ctx.author.id
    })
    
    await ctx.send(f"Message scheduled for {scheduled_time.strftime('%Y-%m-%d %H:%M:%S')} in {channel.mention} 📅")

@bot.command()
async def mass_dm(ctx, role: discord.Role, *, message: str):
    """Send personalized DMs to all members with a specific role"""
    if not await permission_check(ctx):
        return
        
    members = [member for member in role.members if not member.bot]
    if not members:
        await ctx.send(f"No members found with the role {role.mention} 😕")
        return
        
    status_msg = await ctx.send(f"Sending DMs to {len(members)} members with {role.mention}... 🚀")
    successful = 0
    failed = 0
    
    async with ctx.typing():
        for member in members:
            prompt = f"""
            Create a personalized version of this message for {member.name}:
            Original message: {message}
            Their roles: {', '.join(role.name for role in member.roles)}
            Make it personal but keep the core message intact.
            """
            
            personalized_msg = await get_ollama_response(prompt)
            
            try:
                await member.send(personalized_msg)
                dm_conversations[member.id]["last_message"] = message
                successful += 1
                await asyncio.sleep(1)  # Rate limiting protection
            except discord.Forbidden:
                failed += 1
                
    await status_msg.edit(content=f"DM campaign complete! ✅\nSuccessful: {successful}\nFailed: {failed}")
    await log_admin_action(ctx.guild, "Mass DM", str(ctx.author), f"Role: {role.name}, Recipients: {successful}")

@bot.command()
async def set_smart_response(ctx, trigger: str, *, response_template: str):
    """Set up a smart auto-response for specific trigger words/phrases"""
    if not await permission_check(ctx):
        return
        
    custom_triggers[trigger.lower()] = response_template
    await ctx.send(f"Smart response added for trigger: '{trigger}' {random.choice(success_reactions)}")

@bot.command()
async def list_smart_responses(ctx):
    """List all configured smart responses"""
    if not await permission_check(ctx):
        return
        
    if not custom_triggers:
        await ctx.send("No smart responses configured yet! 📝")
        return
        
    response = "**Configured Smart Responses:**\n\n"
    for trigger, template in custom_triggers.items():
        response += f"📌 Trigger: '{trigger}'\n💬 Response: {template}\n\n"
        
    await ctx.send(response)

@tasks.loop(minutes=1)
async def check_scheduled_messages():
    """Check and send scheduled messages"""
    current_time = datetime.datetime.now()
    messages_to_remove = []
    
    for scheduled_msg in scheduled_messages:
        if current_time >= scheduled_msg["scheduled_time"]:
            channel = bot.get_channel(scheduled_msg["channel_id"])
            if channel:
                try:
                    await channel.send(scheduled_msg["message"])
                except discord.Forbidden:
                    print(f"Failed to send scheduled message in channel {channel.id}")
            messages_to_remove.append(scheduled_msg)
            
    for msg in messages_to_remove:
        scheduled_messages.remove(msg)

def main():
    """Main entry point of the bot"""
    if not DISCORD_TOKEN:
        raise ValueError("Discord token not found in .env file")
    
    bot.run(DISCORD_TOKEN)

if __name__ == "__main__":
    main()
