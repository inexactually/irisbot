## Requirements

Python 3.5 or above, `discord.py`, and [`Wand`](http://wand-py.org/) for color swatches.

Wand in turn requires ImageMagick. You may find its
[install guide](http://docs.wand-py.org/en/0.4.4/guide/install.html)
helpful.

## Installation

Create a virtual environment, activate it, and install dependencies with:

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Edit `config.py` to include your Discord bot API token:

```
TOKEN = '<your token goes here>'
```

You may also want to change a few settings in `settings.py` to suit
your server, most notably the admin/moderator role names and the
allowed channels settings.

## Running

Just activate the virtual environment and run `python main.py`.
