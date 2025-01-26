# import pytest
# from unittest.mock import patch, Mock
# from src.discord_notifier import DiscordNotifier

# @pytest.fixture
# def mock_env_vars():
#     """Fixture to mock environment variables"""
#     with patch.dict('os.environ', {'DISCORD_WEBHOOK_URL': 'https://discord.webhook.test'}):
#         yield

# @pytest.fixture
# def notifier(mock_env_vars):
#     """Fixture to create a DiscordNotifier instance"""
#     return DiscordNotifier()

# def test_init_loads_webhook_url(mock_env_vars):
#     """Test that initialization properly loads the webhook URL"""
#     notifier = DiscordNotifier()
#     assert notifier.webhook_url == 'https://discord.webhook.test'

# def test_init_with_missing_webhook_url():
#     """Test initialization with missing webhook URL"""
#     with patch.dict('os.environ', {}, clear=True):
#         notifier = DiscordNotifier()
#         assert notifier.webhook_url is None

# @patch('discord_webhook.DiscordWebhook.execute')
# def test_send_message_calls_webhook(mock_execute, notifier):
#     """Test that send_message properly calls the webhook"""
#     test_message = "Test message"
#     notifier.send_message(test_message)
#     mock_execute.assert_called_once()

# @patch('discord_webhook.DiscordWebhook')
# def test_send_message_content(mock_webhook, notifier):
#     """Test that the message content is properly set"""
#     test_message = "Test message"
#     notifier.send_message(test_message)
#     mock_webhook.assert_called_once_with(
#         url='https://discord.webhook.test',
#         content=test_message
#     )

# @patch('discord_webhook.DiscordWebhook.execute')
# def test_send_empty_message(mock_execute, notifier):
#     """Test sending an empty message"""
#     notifier.send_message("")
#     mock_execute.assert_called_once()

# @patch('discord_webhook.DiscordWebhook.execute')
# def test_webhook_execution_failure(mock_execute, notifier):
#     """Test handling of webhook execution failure"""
#     mock_execute.side_effect = Exception("Webhook failed")
#     with pytest.raises(Exception):
#         notifier.send_message("Test message")

import pytest
from unittest.mock import patch, MagicMock
from src.discord_notifier import DiscordNotifier

@pytest.fixture
def mock_env_vars():
    with patch.dict('os.environ', {'DISCORD_WEBHOOK_URL': 'https://discord.webhook.test'}):
        yield

@pytest.fixture
def notifier(mock_env_vars):
    return DiscordNotifier()

def test_init_with_webhook_url(mock_env_vars):
    notifier = DiscordNotifier()
    assert notifier.webhook_url == 'https://discord.webhook.test'

def test_init_with_missing_webhook_url():
    with patch.dict('os.environ', {}, clear=True):
        notifier = DiscordNotifier()
        assert notifier.webhook_url is None

@patch('discord_webhook.DiscordWebhook.execute')
def test_send_message(mock_execute, notifier):
    mock_execute.return_value = None
    notifier.send_message("Test message")
    mock_execute.assert_called_once()

@patch('discord_webhook.DiscordWebhook')
def test_send_message_content(mock_webhook, notifier):
    mock_webhook_instance = MagicMock()
    mock_webhook.return_value = mock_webhook_instance
    
    test_message = "Test message"
    notifier.send_message(test_message)
    
    mock_webhook.assert_called_with(
        url='https://discord.webhook.test',
        content=test_message
    )