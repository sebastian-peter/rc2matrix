# rc2matrix
Small script transferring Rocket.Chat json exports to Matrix using [matrix-nio](https://github.com/poljar/matrix-nio).

If the user has not joined the specified room before, we try to join the room.
This should work as long as the room is public _or_ the user is invited.
The used device can be verified by using [matrix-commander](https://github.com/8go/matrix-commander).

Import is configured by providing `config.json`:
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