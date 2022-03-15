#!/usr/bin/env python3

import sys
import asyncio

import json
import markdown
import aiofiles.os
import magic
from PIL import Image
from datetime import datetime

from nio import AsyncClientConfig, UploadResponse, JoinedRoomsResponse, JoinError

from encrypted_client import EncryptedClient

CONFIG_FILE = "config.json"
STORE_DIR = "store/"

INPUT_DIR = "input/"


class RcImporter:

    def __init__(self, cfg: dict):
        self.config = cfg

        homeserver = self.config['homeserver']
        user = self.config['user']

        client_config = AsyncClientConfig(encryption_enabled=True, store_sync_tokens=True)

        self.client = EncryptedClient(
            homeserver=homeserver,
            user=user,
            config=client_config,
            store_path=STORE_DIR)

    async def run(self, data: dict) -> None:
        try:
            password = self.config['password']
            device_name = self.config['device_name']
            room_id = self.config['room_id']

            await self.client.re_login(password, device_name)

            # sync to get rooms etc.
            await self.client.sync(full_state=True)

            # retrieve all rooms that we've joined
            joined_rooms_resp = await self.client.joined_rooms()
            if isinstance(joined_rooms_resp, JoinedRoomsResponse):
                joined_rooms = joined_rooms_resp.rooms
            else:
                print("Could not retrieve joined rooms. Exiting.")
                sys.exit(1)

            # if we're not in the desired room, try to join it
            if room_id not in joined_rooms:
                print("User has not joined room, trying to join now.")
                join_resp = await self.client.join(room_id)

                if isinstance(join_resp, JoinError):
                    print(f"Failed to join room: {join_resp.message} ({join_resp.status_code})")
                    sys.exit(1)
                else:
                    print("Join successful.")
                    # important: sync again so that the room join is known to us
                    await self.client.sync()

            # trust all devices of all users of room
            for user in self.client.rooms[room_id].users:
                self.client.trust_devices(user)

            # import all messages
            await self.__transfer_msgs(data)
        finally:
            await self.client.close()

    async def __transfer_msgs(self, data: dict) -> None:
        room_id = self.config['room_id']

        for d in data:
            msg = d['msg']

            if d.get('type') is not None:
                # special messages (user removed/added etc.)
                msg = ''.join(['_', msg, '_'])

            # first, send header as separate text msg
            (header_plain, header_html) = self.__create_msg_header(d)
            await self.__send_text_msg(header_plain, header_html, msg)

            attachments = d.get('attachments')

            if attachments is not None:
                # there are attachments, send them in new msgs
                # process and upload each attachment on its own
                for attach in attachments:
                    # we ignore message_link because it is not a real attachment in our sense
                    if attach.get('message_link') is None and not attach['remote']:
                        # either image or other file

                        if attach.get('fileName') is not None:
                            clean_file_name = attach['fileName'].replace(':', '-')
                        else:
                            # if fileName not defined, there is still an attachment file
                            clean_file_name = 'undefined'

                        full_file_name = ''.join([attach['fileId'], '-', clean_file_name])
                        file_path = ''.join([INPUT_DIR, 'assets/', full_file_name])
                        mime_type = magic.from_file(file_path, mime=True)

                        file_stat = await aiofiles.os.stat(file_path)

                        # first upload, then send URI of upload to room
                        async with aiofiles.open(file_path, "r+b") as file:
                            resp, maybe_keys = await self.client.upload(
                                file,
                                content_type=mime_type,
                                filename=full_file_name,
                                filesize=file_stat.st_size)

                        if not isinstance(resp, UploadResponse):
                            print(f"Failed to upload image. Failure response: {resp}")
                            continue

                        if mime_type.startswith("image/svg"):
                            # svg image

                            # it's not trivial to figure out the dimensions of svgs, thus for now hardcoded to 100x100
                            content = {
                                "body": clean_file_name,
                                "info": {
                                    "mimetype": mime_type,
                                    "size": file_stat.st_size,
                                    "w": 100,
                                    "h": 100
                                },
                                "msgtype": "m.image",
                                "url": resp.content_uri
                            }
                        elif mime_type.startswith("image/"):
                            # other image

                            im = Image.open(file_path)
                            (width, height) = im.size  # im.size returns (width,height) tuple

                            content = {
                                "body": clean_file_name,
                                "info": {
                                    "h": height,
                                    "mimetype": mime_type,
                                    "size": file_stat.st_size,
                                    "w": width
                                },
                                "msgtype": "m.image",
                                "url": resp.content_uri
                            }
                        else:
                            # file

                            content = {
                                "body": clean_file_name,
                                "filename": full_file_name,
                                "info": {
                                    "mimetype": mime_type,
                                    "size": file_stat.st_size
                                },
                                "msgtype": "m.file",
                                "url": resp.content_uri
                            }

                        await self.client.send_msg(room_id, content)

    @staticmethod
    def __create_msg_header(d: dict) -> (str, str):
        user = d['username']
        date_parsed = datetime.strptime(d['ts'], '%Y-%m-%dT%H:%M:%S.%fZ')
        date_formatted = date_parsed.strftime('%Y-%m-%d %H:%M:%S')

        header_additions_plain = []
        header_additions_html = []

        if d.get("type") is not None:
            type_ = d['type']
            if type_ == 'uj':
                type_title = 'User joined'
            elif type_ == 'ru':
                type_title = 'User removed'
            elif type_ == 'au':
                type_title = 'User added'
            elif type_ == 'message_pinned':
                type_title = 'Message pinned'
            elif type_ == 'subscription-role-added':
                type_title = 'Subscription role added'
            elif type_ == 'room_changed_privacy':
                type_title = 'Room privacy changed'
            elif type_ == 'discussion-created':
                type_title = 'Discussion created'
            else:
                type_title = 'Other'

            header_additions_plain.append(''.join(['action: ', type_title]))
            header_additions_html.append(''.join(['<em>action:</em> ', type_title]))

        attachments = d.get('attachments')
        if attachments is not None:
            # attachments usually mean we want to extend our header

            def header_addition_plain(a):
                if a.get('fileName') is not None:
                    return a['fileName']
                if a.get('message_link') is not None:
                    return a['message_link']
                if a.get('remote') and a.get('title'):
                    return ''.join(['external: ', a['title']])
                return ''

            def header_addition_html(a):
                if a.get('fileName') is not None:
                    return a['fileName']
                if a.get('message_link') is not None:
                    return ''.join(['<a href="', a['message_link'], '">link</a>'])
                if a.get('remote') and a.get('title'):
                    return ''.join(['<a href="', a['url'], '">', a['title'], '</a>'])
                return ''

            header_additions_plain.extend(map(header_addition_plain, attachments))
            header_additions_html.extend(map(header_addition_html, attachments))

        header_add_plain = ', '.join(header_additions_plain)
        header_add_html = ', '.join(header_additions_html)

        if header_add_plain:
            # there is an addition to the header, add it
            msg_header_plain = ''.join([user, ' // ', date_formatted, ' // ', header_add_plain])
            msg_header_html = ''.join(['<sub>', user, ' // ', date_formatted, ' // ', header_add_html, '</sub>'])

            return msg_header_plain, msg_header_html

        # no attachments, thus simple header
        msg_header_plain = ''.join([user, ' // ', date_formatted])
        msg_header_html = ''.join(['<sub>', msg_header_plain, '</sub>'])

        return msg_header_plain, msg_header_html

    async def __send_text_msg(
            self,
            msg_header_plain: str,
            msg_header_html: str,
            msg: str
    ) -> None:
        if msg.strip():
            # msg neither empty nor just spaces
            msg_html = markdown.markdown(msg)

            msg_combined_plain = ''.join([msg_header_plain, '\n', msg])
            msg_combined_html = ''.join([msg_header_html, '<br>', msg_html])
        else:
            # msg empty or just spaces
            msg_combined_plain = msg_header_plain
            msg_combined_html = msg_header_html

        content = {
            "msgtype": "m.text",
            "body": msg_combined_plain,
            "format": "org.matrix.custom.html",
            "formatted_body": msg_combined_html
        }

        room_id = self.config['room_id']
        await self.client.send_msg(room_id, content)


def __load_msgs(input_file_path: str) -> dict:
    with open(input_file_path) as input_file:
        # turn separate json dicts into list of dicts
        return json.loads("[" +
                          input_file.read().replace("}\n{", "},\n{") +
                          "]")


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    try:
        with open(CONFIG_FILE, "r") as conf_file:
            config = json.load(conf_file)
    except IOError as err:
        print(f"Couldn't load configs from file. Error: {err}")
        sys.exit(1)
    except json.JSONDecodeError:
        print("Couldn't read JSON file; overwriting")
        sys.exit(1)

    msgs = __load_msgs(INPUT_DIR + config['input_file'])

    importer = RcImporter(config)
    asyncio.get_event_loop().run_until_complete(importer.run(msgs))
