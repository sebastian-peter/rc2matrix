# rc2matrix
Small script transferring Rocket.Chat json exports to Matrix using [matrix-nio](https://github.com/poljar/matrix-nio).

If the user has not joined the specified room before, we try to join the room.
This should work as long as the room is public _or_ the user is invited.

The used device can be verified by using [matrix-commander](https://github.com/8go/matrix-commander).
Unverified devices of others are ignored: all members of the room do not need to be verified.

Import is configured by providing `config.json` placed in the root working directory:
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

The input file needs to be placed in `input/` and all corresponding attachments in `input/assets/`.

## Known issues

- Markdown parsing sometimes does not work as expected, e.g. using fenced code blocks with multiple consecutive line breaks inside. 
  This is because we use [python markdown](https://github.com/Python-Markdown/markdown) here, which might be different from the one used with RC.
- Remote images (e.g. by using the RC giphy plugin) are currently not displayed. It is possible to implement this though.
- Message threads are not preserved, as RC exports do not include any indications of threads. Instead, threads are flattened.
- Related to Element: Despite room settings in Element suggesting that sent messages can be read by users that join the room in the future, this seems to not work.
  Thus, it is recommended to invite all relevant users to a room _before_ running the import.