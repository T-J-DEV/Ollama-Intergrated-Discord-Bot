# KempAI Discord Bot

A powerful Discord bot that uses Ollama's API to provide AI-powered interactions, moderation, and server management features. The bot maintains a gaming-themed personality while offering comprehensive moderation tools and AI-enhanced communication.

## Features

### AI Integration
- Responds to messages using local Ollama models
- Maintains conversation context (last 3 messages)
- AI-powered personalized DM system
- Smart auto-responses with context awareness
- Customizable response templates

### Administration
- Scheduled message system
- Mass DM capabilities with rate limiting
- Comprehensive moderation tools
- Role-based permissions system
- Admin action logging

### User Experience
- Shows typing indicator while generating responses
- Configurable model selection
- Personalized responses based on user roles and status
- Gaming-themed responses and emojis
- Error handling for API issues

### Channel Management
- Selective channel activation
- Message history management
- Pinning system

## Prerequisites

- Python 3.8 or higher
- Ollama installed and running locally
- A Discord bot token

## Setup

1. Install the required Python packages:
```bash
pip install -r requirements.txt
```

2. Create a Discord application and bot at https://discord.com/developers/applications
   - Enable the "Message Content Intent" in the Bot settings

3. Copy your bot token and add it to the `.env` file:
```env
DISCORD_TOKEN=your_token_here
OLLAMA_MODEL=llama2
LOGS_CHANNEL_ID=channel_id_for_admin_logs  # Optional: For admin action logging
```

4. Make sure Ollama is running locally with your chosen model

5. Run the bot:
```bash
python bot.py
```

## Available Commands

### General Commands
- `?setmodel <model_name>` - Change the Ollama model being used
- `?clearhistory` - Clear the message history for the current channel
- `?setstatus <status>` - Set the bot's status message

### Admin Commands
- `?dm @user1 @user2 <message>` - Send personalized AI-generated DMs to specific users
- `?mass_dm @Role <message>` - Send personalized DMs to all members with a specific role
- `?schedule_message #channel <time> <message>` - Schedule a message to be sent later (time format: 1h, 30m, 2h30m)
- `?set_smart_response <trigger> <template>` - Set up AI-powered auto-responses for specific triggers
- `?list_smart_responses` - List all configured smart auto-responses

### Moderation Commands
- `?kick @user [reason]` - Kick a member from the server
- `?ban @user [reason]` - Ban a member from the server
- `?mute @user [reason]` - Timeout/mute a member (10 minutes)
- `?unmute @user` - Remove timeout/mute from a member
- `?clear <amount>` - Clear specified number of messages from the channel
- `?pin` - Pin the message that was replied to

### Channel Management
- `?allowchannel` - Allow the bot to respond in the current channel
- `?disallowchannel` - Prevent the bot from responding in the current channel
- `?listchannels` - List all channels where the bot is allowed to respond

### Role Management
- `?role @user @role` - Add or remove a role from a member
- `?trust @user` - Add a user to the trusted users list (admin only)
- `?untrust @user` - Remove a user from the trusted users list (admin only)

## Features

### AI Integration
- Responds to messages using local Ollama models
- Maintains conversation context (last 3 messages)
- AI-powered personalized DM system
- Smart auto-responses with context awareness
- Customizable response templates

### Administration
- Scheduled message system
- Mass DM capabilities with rate limiting
- Comprehensive moderation tools
- Role-based permissions system
- Admin action logging

### User Experience
- Shows typing indicator while generating responses
- Configurable model selection
- Personalized responses based on user roles and status
- Gaming-themed responses and emojis
- Error handling for API issues
- Ignores messages from other bots

### Channel Management
- Selective channel activation
- Message history management
- Pinning system
