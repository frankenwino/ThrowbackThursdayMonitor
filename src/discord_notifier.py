from discord_webhook import DiscordEmbed, DiscordWebhook
import os
from dotenv import load_dotenv

class DiscordNotifier:
    """
    A class to send notifications to a Discord channel using a webhook.
    Methods
    -------
    __init__():
        Initializes the DiscordNotifier with the webhook URL from environment variables.
    send_message(message: str) -> None:
        Sends a message to the Discord channel using the webhook URL.
    """
    def __init__(self):
        load_dotenv()
        self.webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
        
    # def send_message(self, message: str) -> None:
    #     webhook = DiscordWebhook(url=self.webhook_url, content=message)
    #     webhook.execute()
        
        
    def send_message(self, embed: DiscordEmbed) -> None:
        webhook = DiscordWebhook(url=self.webhook_url)
        webhook.add_embed(embed)
        response = webhook.execute()

        if response.status_code == 200:
            print("Message sent successfully!")
        else:
            print(f"Failed to send message. Status code: {response.status_code}, Response: {response.text}")
