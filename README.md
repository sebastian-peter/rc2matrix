# rc2matrix
Small script transferring Rocket.Chat json exports to Matrix using [matrix-nio](https://github.com/poljar/matrix-nio).

If the user has not joined the specified room before, we try to join the room.
This should work as long as the room is public _or_ the user is invited.

The used device can be verified by using [matrix-commander](https://github.com/8go/matrix-commander).
Unverified devices of others are ignored: all members of the room do not need to be verified.

## Getting Started

##### Exporting from Rocket.Chat
1. Export messages from Rocket.Chat. Use `Method: Export as file` and `Output format: JSON`. Only click `Export` _once_, it may take some time until the e-mail with the link to your export arrives.
2. Download and extract the archive. Copy the `*.json` and the `asset` directory to `input/` in your working directory.

##### Creat room in Matrix
3. Create a new room in Matrix. You may want to disable encryption (see known issues below).
4. If you enabled encryption, invite all users that you want to be able to access the imported messages.
5. Copy the room id (in Element: `Room options` - `Settings` - `Advanced`)
6. Provide `config.json` placed in the root working directory:
```
{
  "homeserver": "https://example.server:1234",
  "user": "@username:example.server",
  "password": "******",
  "device_name": "device_name",
  "room_id": "!abcdefghiABCDEFGHI:example.server",
  "input_file": "room_msgs.json"
}
```
7. If you are just logging in to a new session, you might want to verify the newly created device (e.g. with [matrix-commander](https://github.com/8go/matrix-commander)) and provide the `credentials.json` file.
8. Execute `main.py`

## Known issues

- Related to Matrix/Element: For rooms with E2E encryption enabled, message history cannot be accessed by users that join the room in the future.
  This is despite room settings in Element suggesting that message history will be available ([element-web#15965](https://github.com/vector-im/element-web/issues/15965), [element-web#13883](https://github.com/vector-im/element-web/issues/13883)).
  Currently, there are two possible workarounds:
  1. Invite all relevant users to a room _before_ running the import. This does not work for additional users that are invited in the future.
  2. Turn off encryption when _creating_ the room.
- Markdown parsing sometimes does not work as expected, e.g. using fenced code blocks with multiple consecutive line breaks inside. 
  This is because we use [python markdown](https://github.com/Python-Markdown/markdown) here, which might be different from the one used with RC.
- Remote images (e.g. by using the RC giphy plugin) are currently not displayed. It is possible to implement this though.
- Message threads are not preserved, as RC exports do not include any indications of threads. Instead, threads are flattened.

## Prerequisites
You need to have `olm` installed on your machine locally.
It is an implementation of the Double Ratchet cryptographic ratchet in C++.
For Ubuntu, e.g., you can get it via `sudo apt install libolm-dev`.
