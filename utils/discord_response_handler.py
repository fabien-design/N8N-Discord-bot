"""
Discord Response Handler Utility
Handles long responses by splitting them or sending as text files.
"""

import discord
import io
from typing import Union


async def send_long_response(
    channel: discord.TextChannel,
    content: str,
    max_length: int = 2000,
    as_file_threshold: int = 4000,
    filename: str = "response.txt"
) -> None:
    """
    Send a response to Discord, handling long content appropriately.

    Args:
        channel: Discord channel to send to
        content: The content to send
        max_length: Maximum length for a single Discord message (default: 2000)
        as_file_threshold: If content exceeds this, send as file (default: 4000)
        filename: Name of the file if sent as attachment (default: response.txt)

    Behavior:
        - If content <= 2000 chars: Send as single message
        - If 2000 < content <= 4000 chars: Split into multiple messages
        - If content > 4000 chars: Send as text file
    """
    if not content:
        await channel.send("✅ Action effectuée avec succès")
        return

    content_length = len(content)

    # Short enough to send as single message
    if content_length <= max_length:
        await channel.send(content)
        return

    # Long content - send as file
    if content_length > as_file_threshold:
        await _send_as_file(channel, content, filename)
        return

    # Medium length - split into multiple messages
    await _send_split_messages(channel, content, max_length)


async def _send_as_file(
    channel: discord.TextChannel,
    content: str,
    filename: str
) -> None:
    """
    Send content as a text file attachment.

    Args:
        channel: Discord channel to send to
        content: The content to send
        filename: Name of the file
    """
    # Create a file-like object from the string
    file_content = io.BytesIO(content.encode('utf-8'))
    discord_file = discord.File(fp=file_content, filename=filename)

    # Send the file with a message
    await channel.send(
        "📄 La réponse est trop longue, voici le fichier:",
        file=discord_file
    )


async def _send_split_messages(
    channel: discord.TextChannel,
    content: str,
    max_length: int
) -> None:
    """
    Split content into multiple messages and send them.

    Args:
        channel: Discord channel to send to
        content: The content to split and send
        max_length: Maximum length for each message
    """
    # Split by newlines first to avoid breaking mid-line
    lines = content.split('\n')
    current_chunk = ""
    message_count = 1

    for line in lines:
        # If adding this line would exceed max_length
        if len(current_chunk) + len(line) + 1 > max_length:
            # Send current chunk if not empty
            if current_chunk:
                await channel.send(current_chunk)
                message_count += 1
                current_chunk = ""

        # Add line to current chunk
        if current_chunk:
            current_chunk += "\n" + line
        else:
            current_chunk = line

    # Send remaining content
    if current_chunk:
        await channel.send(current_chunk)
