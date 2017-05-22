## Requirements

Python 3.5 (for the `async`/`await` sugar), `discord.py`,
and [`Wand`](http://wand-py.org/) (for color swatches).

Wand in turn requires ImageMagick. You may find its
[install guide](http://docs.wand-py.org/en/0.4.4/guide/install.html)
helpful.

## Setup

Edit `config.py` to include your Discord bot API token:

```
TOKEN = '<your token goes here>'
```

You may also want to change a few settings in `settings.py` to suit
your server, most notably the role names for adults/minors and the
allowed channels settings (whitelist, blacklist, and/or regex).

## Running

Just run `python main.py`.
