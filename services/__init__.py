from services.console_service import ConsoleService
from services.discord_service import DiscordService
from services.slack_service import SlackService
from services.xmpp_service import XMPPService

SERVICE_NAMES = {
    "Console": ConsoleService,
    "Discord": DiscordService,
    "XMPP": XMPPService,
    "Slack": SlackService
}
