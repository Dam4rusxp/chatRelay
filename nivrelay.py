import argparse
import asyncio
import configparser

from services.console_service import ConsoleService
from services.discord_service import DiscordService
from services.service_handler import ConfigType
from services.slack_service import SlackService
from services.xmpp_service import XMPPService


def is_valid_section(section_config, name) -> bool:
    if name in ["yes", "no"]:
        print("Section has an invalid name '%s', skipping." % section_name)
        return False

    if not section_config.get("type", None):
        print("Section '%s' has no type, skipping." % section_name)
        return False

    return True


def grab_service_specific_config(service, section_config) -> dict:
    result = dict()

    for key, keytype in service.requested_config_values().items():
        if keytype is ConfigType.SINGLE_VALUE and key in section_config:
            result[key] = section_config[key]
        elif keytype is ConfigType.MULTI_VALUE and key in section_config:
            result[key] = section_config[key].strip().split("\n")
        else:
            continue

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="Chat Relay",
        description="A script for relaying messages between different chat services."
    )
    parser.add_argument("-c", help="Config file location", default="config.ini")
    args = parser.parse_args()

    config = configparser.ConfigParser()
    config.read(args.c)

    for section_name in config.sections():
        if not is_valid_section(config[section_name], section_name):
            continue

        section = config[section_name]

        service_config = dict()
        service_config["name"] = section_name
        service_config["receiver"] = section.get("receiver", "yes")
        service_config["broadcaster"] = section.get("broadcaster", "no")
        service_config["type"] = section["type"]

        service = None
        if section["type"] == "Discord":
            service = DiscordService
        elif section["type"] == "Console":
            service = ConsoleService
        elif section["type"] == "XMPP":
            service = XMPPService
        elif section["type"] == "Slack":
            service = SlackService
        else:
            print("Unknown service type '%s', skipping." % section["type"])
            continue

        service_config.update(grab_service_specific_config(service, section))

        # Initialize and start service
        service = service(service_config)
        asyncio.ensure_future(service.start())

    asyncio.get_event_loop().run_forever()
