import os
import sys
import json
from typing import Optional

from nio import (AsyncClient, LoginResponse, AsyncClientConfig)

SESSION_FILE = "credentials.json"


class EncryptedClient(AsyncClient):
    def __init__(
            self,
            homeserver: str,
            user: str = "",
            device_id: Optional[str] = "",
            store_path: Optional[str] = "",
            config: Optional[AsyncClientConfig] = None,
            ssl: Optional[bool] = None,
            proxy: Optional[str] = None
    ):
        super().__init__(homeserver, user=user, device_id=device_id, store_path=store_path, config=config, ssl=ssl,
                         proxy=proxy)

        # if the store location doesn't exist, create it
        if store_path and not os.path.isdir(store_path):
            os.mkdir(store_path)

    async def re_login(self,
                       password: Optional[str] = None,
                       device_name: Optional[str] = None
                       ) -> None:
        """Log in either using the global variables or (if possible) using the session file.
        """
        # Restore the previous session if we can
        if os.path.isfile(SESSION_FILE):
            try:
                with open(SESSION_FILE, "r") as f:
                    cfg = json.load(f)

                    self.restore_login(
                        user_id=cfg['user_id'],
                        device_id=cfg['device_id'],
                        access_token=cfg['access_token']
                    )
                    print(f"Logged in using credentials from previous session: {self.user_id} on {self.device_id}")

            except IOError as err:
                print(f"Couldn't load session from file: {err}")
            except json.JSONDecodeError:
                print("Couldn't read JSON file")

        # We didn't restore a previous session, so we'll log in with a password
        if not self.user_id or not self.access_token or not self.device_id:
            # this calls the login method defined in AsyncClient from nio
            resp = await super().login(password=password, device_name=device_name)

            if isinstance(resp, LoginResponse):
                print("Logged in using a password. Saving session to disk.")
                self.__write_details_to_disk(resp)
            else:
                print(f"Failed to log in: {resp}")
                sys.exit(1)

    def trust_devices(self, user_id: str) -> None:
        """Marks all devices of a user as trusted.
        Client has to be synced before this.
        """

        # device_store requires a sync before executing this
        for device_id, olm_device in self.device_store[user_id].items():
            if user_id == self.user_id and device_id == self.device_id:
                # We cannot explicitly trust our own device
                continue

            self.verify_device(olm_device)
            print(f"Trusting {device_id} from user {user_id}")

    async def send_msg(self, room_id: str, content: dict) -> None:
        await self.room_send(
            room_id=room_id,
            message_type="m.room.message",
            content=content
        )

    @staticmethod
    def __write_details_to_disk(resp: LoginResponse) -> None:
        """Writes login details to disk so that we can restore our session later
        without logging in again and creating a new device ID.

        Arguments:
            resp {LoginResponse} -- the successful client login response.
        """
        with open(SESSION_FILE, "w") as f:
            json.dump({
                "access_token": resp.access_token,
                "device_id": resp.device_id,
                "user_id": resp.user_id
            }, f)
