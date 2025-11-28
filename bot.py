"""
Discord Bot - Assistant Personnel
Écoute les messages textuels et vocaux et répond en écho.
"""

import platform
import discord
from discord.ext import commands
import requests
import jwt
import json
from datetime import datetime, timedelta, timezone

from utils import TOKEN, PREFIX, ENABLE_MESSAGE_CONTENT, ALLOWED_USER_IDS, JWT_SECRET, N8N_WEBHOOK
from utils import setup_logger, transcribe_audio_from_url

logger = setup_logger()

intents = discord.Intents.default()
if ENABLE_MESSAGE_CONTENT:
    intents.message_content = True


class DiscordBot(commands.Bot):
    """Main Discord bot class."""

    def __init__(self) -> None:
        super().__init__(
            command_prefix=PREFIX,
            intents=intents,
            help_command=None,
        )
        self.logger = logger

    async def setup_hook(self) -> None:
        """Executed when the bot starts."""
        self.logger.info(f"Logged in as {self.user.name}")
        self.logger.info(f"discord.py API version: {discord.__version__}")
        self.logger.info(f"Python version: {platform.python_version()}")
        self.logger.info(f"Running on: {platform.system()} {platform.release()}")
        self.logger.info("-------------------")
        self.logger.info("Bot is ready to listen to messages!")

    async def on_message(self, message: discord.Message) -> None:
        """
        Handles incoming messages (text and voice).
        """
        try:
            if message.author == self.user or message.author.bot:
                self.logger.debug(f"Ignoring message from bot/self: {message.author}")
                return

            self.logger.info(f"Received message from {message.author} (ID: {message.author.id})")

            if ALLOWED_USER_IDS:
                allowed_ids = [int(uid.strip()) for uid in ALLOWED_USER_IDS.split(",")]
                self.logger.debug(f"Allowed user IDs: {allowed_ids}")

                if message.author.id not in allowed_ids:
                    self.logger.warning(f"Unauthorized user {message.author} (ID: {message.author.id}) attempted to interact.")
                    return
                else:
                    self.logger.info(f"User {message.author.id} is authorized")

            if message.attachments:
                self.logger.info(f"Message has {len(message.attachments)} attachment(s)")
                await self._handle_audio_attachments(message)
                return

            if message.content:
                self.logger.info(f"Processing text message: {message.content[:50]}...")
                await self._handle_text_message(message)
            else:
                self.logger.warning("Message has no content and no attachments")

        except Exception as e:
            self.logger.error(f"Error in on_message: {e}", exc_info=True)
            try:
                await message.channel.send(f"❌ Erreur interne: {str(e)}")
            except:
                pass

    async def _handle_audio_attachments(self, message: discord.Message) -> None:
        """
        Process audio attachments and transcribe them.
        """
        try:
            for attachment in message.attachments:
                self.logger.info(f"Processing attachment: {attachment.filename} (type: {attachment.content_type})")

                if attachment.content_type and attachment.content_type.startswith('audio/'):
                    self.logger.info(f"Audio attachment detected from {message.author}: {attachment.url}")

                    processing_msg = await message.channel.send("🎤 Transcription en cours...")

                    try:
                        self.logger.info("Starting audio transcription...")
                        transcription = await transcribe_audio_from_url(attachment.url)
                        self.logger.info(f"Transcription completed: {transcription}")

                        if transcription:
                            await processing_msg.delete()
                            self.logger.info("Sending transcription to webhook...")

                            response = await self._call_webhook(transcription)

                            if response and response.status_code == 200:
                                self.logger.info("Webhook call successful, formatting response...")
                                formatted_message = self._format_webhook_response(response)
                                await message.channel.send(formatted_message)
                                self.logger.info("Response sent to Discord")
                            else:
                                status = response.status_code if response else "None"
                                self.logger.error(f"Webhook call failed with status: {status}")
                                await message.channel.send(f"❌ Erreur lors de l'envoi au webhook (status: {status})")

                        else:
                            self.logger.error("Transcription returned empty/None")
                            await processing_msg.edit(content="❌ Erreur lors de la transcription")

                    except Exception as e:
                        self.logger.error(f"Error during audio processing: {e}", exc_info=True)
                        await processing_msg.edit(content=f"❌ Erreur: {str(e)}")

                else:
                    self.logger.info(f"Non-audio attachment: {attachment.content_type}")

        except Exception as e:
            self.logger.error(f"Error in _handle_audio_attachments: {e}", exc_info=True)
            await message.channel.send(f"❌ Erreur lors du traitement de l'audio: {str(e)}")

    async def _handle_text_message(self, message: discord.Message) -> None:
        """Handle text messages and send to webhook."""
        try:
            self.logger.info(f"Text message from {message.author}: {message.content}")
            self.logger.info("Sending text message to webhook...")

            response = await self._call_webhook(message.content)

            if response and response.status_code == 200:
                self.logger.info(f"Webhook response received: {response.status_code}")
                self.logger.debug(f"Response content: {response.text[:200]}")

                formatted_message = self._format_webhook_response(response)
                await message.channel.send(formatted_message)
                self.logger.info("Response sent to Discord")
            else:
                status = response.status_code if response else "None"
                self.logger.error(f"Webhook call failed with status: {status}")
                if response:
                    self.logger.error(f"Response content: {response.text}")
                await message.channel.send(f"❌ Erreur lors de l'envoi au webhook (status: {status})")

        except Exception as e:
            self.logger.error(f"Error in _handle_text_message: {e}", exc_info=True)
            await message.channel.send(f"❌ Erreur lors du traitement du message: {str(e)}")

    def _format_webhook_response(self, response) -> str:
        """
        Format webhook response for Discord display.
        Handles all action types: email, calendar, notes, tasks, etc.
        """
        try:
            data = response.json()
            self.logger.debug(f"Parsing webhook response, type: {type(data)}")

            # Handle list response (N8N can return arrays)
            if isinstance(data, list):
                self.logger.info(f"Response is a list with {len(data)} items")
                if len(data) == 0:
                    return "✅ Action effectuée avec succès"
                # Use first item if it's a list
                data = data[0]
                self.logger.debug(f"Using first item from list: {data}")

            # Handle dict response
            if not isinstance(data, dict):
                self.logger.warning(f"Unexpected response type: {type(data)}")
                return f"✅ Réponse:\n```\n{str(data)}\n```"

            action = data.get('action')
            output = data.get('output', {})

            self.logger.debug(f"Action: {action}, Output type: {type(output)}")

            if not output:
                return "✅ Action effectuée avec succès"

            output_type = output.get('type', '')
            content = output.get('content', '')
            items = output.get('items', [])

            self.logger.debug(f"Output type: {output_type}, Content length: {len(content) if content else 0}, Items: {len(items)}")

            # Map actions to emojis
            action_emojis = {
                'get_email': '📧',
                'send_email': '📨',
                'get_calendar': '📅',
                'send_calendar': '🗓️',
                'note': '📝',
                'task': '✅',
                'other': '💡'
            }

            emoji = action_emojis.get(action, '✅')

            # Format based on action type
            if action == 'get_email' or output_type == 'email_summary':
                self.logger.info("Formatting as email list")
                return self._format_email_list(emoji, content, items)

            elif action == 'send_email' or output_type == 'email_sent':
                self.logger.info("Formatting as email sent")
                return f"{emoji} **{content}**"

            elif action == 'get_calendar' or output_type == 'calendar_events':
                self.logger.info("Formatting as calendar events")
                return self._format_calendar_events(emoji, content, items)

            elif action == 'send_calendar' or output_type == 'calendar_event_created':
                self.logger.info("Formatting as calendar event created")
                return f"{emoji} **{content}**"

            elif action == 'note' or output_type in ['note_created', 'note_updated', 'note_list']:
                self.logger.info("Formatting as notes")
                return self._format_notes(emoji, content, items)

            elif action == 'task' or output_type in ['task_created', 'task_updated', 'task_list']:
                self.logger.info("Formatting as tasks")
                return self._format_tasks(emoji, content, items)

            # Generic format with items
            elif items:
                self.logger.info("Formatting as generic list")
                return self._format_generic_list(emoji, content, items)

            # Simple content response
            elif content:
                self.logger.info("Formatting as simple content")
                return f"{emoji} **{content}**"

            # Fallback to JSON
            self.logger.warning("Using JSON fallback formatting")
            return f"{emoji} Réponse:\n```json\n{json.dumps(data, indent=2, ensure_ascii=False)}\n```"

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error: {e}")
            return f"✅ Réponse:\n```\n{response.text}\n```"
        except Exception as e:
            self.logger.error(f"Error formatting response: {e}", exc_info=True)
            return "✅ Action effectuée"

    def _format_email_list(self, emoji: str, content: str, items: list) -> str:
        """Format email list with details."""
        formatted = f"{emoji} **{content}**\n\n"

        for idx, item in enumerate(items, 1):
            sender = item.get('sender', item.get('from', 'Inconnu'))
            subject = item.get('subject', 'Sans objet')
            date_str = item.get('date', item.get('received', ''))
            preview = item.get('preview', item.get('snippet', ''))

            formatted += f"**{idx}.** {subject}\n"
            formatted += f"   📨 De: {sender}\n"

            if date_str:
                formatted += f"   📅 {self._format_date(date_str)}\n"

            if preview:
                preview_text = preview[:100] + '...' if len(preview) > 100 else preview
                formatted += f"   💬 {preview_text}\n"

            formatted += "\n"

        return formatted

    def _format_calendar_events(self, emoji: str, content: str, items: list) -> str:
        """Format calendar events with details."""
        formatted = f"{emoji} **{content}**\n\n"

        for idx, item in enumerate(items, 1):
            title = item.get('title', item.get('summary', 'Sans titre'))
            start = item.get('start', item.get('start_time', ''))
            end = item.get('end', item.get('end_time', ''))
            location = item.get('location', '')
            description = item.get('description', '')

            formatted += f"**{idx}.** {title}\n"

            if start:
                formatted += f"   🕐 Début: {self._format_date(start)}\n"
            if end:
                formatted += f"   🕐 Fin: {self._format_date(end)}\n"
            if location:
                formatted += f"   📍 Lieu: {location}\n"
            if description:
                desc_text = description[:100] + '...' if len(description) > 100 else description
                formatted += f"   📄 {desc_text}\n"

            formatted += "\n"

        return formatted

    def _format_notes(self, emoji: str, content: str, items: list) -> str:
        """Format notes with details."""
        if not items:
            return f"{emoji} **{content}**"

        formatted = f"{emoji} **{content}**\n\n"

        for idx, item in enumerate(items, 1):
            title = item.get('title', 'Sans titre')
            body = item.get('body', item.get('content', ''))
            created = item.get('created', item.get('created_at', ''))

            formatted += f"**{idx}.** {title}\n"

            if body:
                body_text = body[:150] + '...' if len(body) > 150 else body
                formatted += f"   {body_text}\n"

            if created:
                formatted += f"   🕐 {self._format_date(created)}\n"

            formatted += "\n"

        return formatted

    def _format_tasks(self, emoji: str, content: str, items: list) -> str:
        """Format tasks with details."""
        if not items:
            return f"{emoji} **{content}**"

        formatted = f"{emoji} **{content}**\n\n"

        for idx, item in enumerate(items, 1):
            title = item.get('title', item.get('name', 'Sans titre'))
            status = item.get('status', item.get('completed', False))
            due_date = item.get('due_date', item.get('due', ''))
            priority = item.get('priority', '')

            status_icon = '✅' if status in [True, 'completed', 'done'] else '⬜'
            formatted += f"{status_icon} **{idx}.** {title}\n"

            if priority:
                priority_icons = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}
                priority_icon = priority_icons.get(str(priority).lower(), '⚪')
                formatted += f"   {priority_icon} Priorité: {priority}\n"

            if due_date:
                formatted += f"   📅 Échéance: {self._format_date(due_date)}\n"

            formatted += "\n"

        return formatted

    def _format_generic_list(self, emoji: str, content: str, items: list) -> str:
        """Format generic list of items."""
        formatted = f"{emoji} **{content}**\n\n"

        for idx, item in enumerate(items, 1):
            if isinstance(item, str):
                formatted += f"**{idx}.** {item}\n"
            elif isinstance(item, dict):
                title = item.get('title', item.get('name', item.get('text', str(item))))
                formatted += f"**{idx}.** {title}\n"

                for key, value in item.items():
                    if key not in ['title', 'name', 'text'] and value:
                        formatted += f"   • {key}: {value}\n"

            formatted += "\n"

        return formatted

    def _format_date(self, date_str: str) -> str:
        """Format date string to readable format."""
        try:
            date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return date_obj.strftime('%d/%m/%Y à %H:%M')
        except:
            return date_str

    async def _call_webhook(self, message: str):
        try:
            payload = {
                'message': message,
                'exp': datetime.now(timezone.utc) + timedelta(hours=1)
            }
            token = jwt.encode(payload, JWT_SECRET, algorithm='HS256')

            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            self.logger.info(f"Message : {message}")
            data = {'message': message}

            self.logger.info(f"Sending message to N8N webhook: {N8N_WEBHOOK}")
            response = requests.post(N8N_WEBHOOK, json=data, headers=headers)

            self.logger.info(f"Webhook response status: {response.status_code}")
            return response
        except Exception as e:
            self.logger.error(f"Error calling webhook: {e}")
            return None


def main():
    """Main entry point for the bot."""
    if not TOKEN:
        logger.error("TOKEN not found in environment variables!")
        return

    bot = DiscordBot()
    bot.run(TOKEN)


if __name__ == "__main__":
    main()
