import argparse
import asyncio
import configparser

from services import SERVICE_NAMES
from services.service_handler import ServiceHandler
from util.config_type import Subtype


def _parse_requested_values(section_config, name, requested_values) -> dict:
    result = dict()
    for key, config_type in requested_values.items():
        # Handle missing values
        if key not in section_config:
            if config_type.required:
                print("Section '%s' is missing config key '%s', skipping." % (name, key))
                return None
            if config_type.default:
                result[key] = config_type.default
            continue

        # Handle service type
        if key == "type":
            if section_config[key] in SERVICE_NAMES:
                result[key] = SERVICE_NAMES.get(section_config[key])
                continue
            else:
                print("Section '%s' has an unknown type '%s', skipping." % (name, section_config[key]))
                return None

        # Handle multi-value values
        if config_type.multi_value:
            result[key] = section_config[key].strip().split("\n")
        else:
            result[key] = section_config[key]

        # Handle subtypes
        if config_type.subtype is Subtype.YES_NO:
            if result[key] not in ["yes", "no"]:
                print("Key '%s' in section '%s' must be either 'yes' or 'no', skipping." % (key, name))
                return None

        elif config_type.subtype is Subtype.RECEIVE_FILTER:
            real_receiver_channels = []
            for line in result[key]:
                if "->" in line:
                    if not result.get("receive_filter", None):
                        result["receive_filter"] = dict()
                    channel, target = line.split("->")
                    channel = channel.strip()
                    target = target.strip()
                    result["receive_filter"][channel] = target
                    real_receiver_channels.append(channel)
                else:
                    real_receiver_channels.append(line)

            result[key] = real_receiver_channels

    return result


def parse_config(section_config, name) -> dict:
    result = dict()

    if name in ["yes", "no"]:
        print("Section has an invalid name '%s', skipping." % section_name)
        return None

    result["name"] = name

    # Parse general config
    requested_values = ServiceHandler.requested_config_values()
    basic_parse = _parse_requested_values(section_config, name, requested_values)

    if not basic_parse:
        return None
    result.update(basic_parse)

    # Parse service-specific config
    requested_values = result["type"].requested_config_values()
    service_parse = _parse_requested_values(section_config, name, requested_values)

    if not service_parse:
        return None
    result.update(service_parse)

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
        section = config[section_name]

        service_config = parse_config(section, section_name)

        if not service_config:
            continue

        # Initialize and start service
        service = service_config["type"](service_config)
        asyncio.ensure_future(service.start())

    asyncio.get_event_loop().run_forever()
