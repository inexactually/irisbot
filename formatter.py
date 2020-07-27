import inspect
import itertools
import re

import discord

# This is all totally overkill, but if want markdown in our help text
# (rather than the giant code block discord.py uses by default) and
# still want pagination to work right this seems like the principled
# approach.


class Paginable:
    def size(self):
        raise NotImplementedError

    def split(self, max_size):
        if self.size() <= max_size:
            return self, None
        else:
            raise RuntimeError('Non-splittable item exceeds maximum size.')

    def paginate(self, max_size):
        current = self
        parts = []
        while current.size() >= max_size:
            first, rest = current.split(max_size)
            parts.append(first)
            current = rest
        parts.append(current)
        return parts

    def render_pages(self, max_size):
        return [part.render() for part in self.paginate(max_size)]


class Line(Paginable):
    def __init__(self, text):
        self._text = text

    def size(self):
        return len(self._text)

    def render(self):
        return self._text


class Compound(Paginable):
    def __init__(self, items=[]):
        self._size = 0
        self._items = []
        for item in items:
            self.append(item)

    def children(self, first, rest):
        return Compound(first), Compound(rest)

    def reserved_size(self):
        return 0

    def size(self):
        return self._size + self.reserved_size()

    def items(self):
        return self._items

    def append(self, item):
        self._size += item.size()
        self._items.append(item)

    def split(self, max_size):
        if self.size() <= max_size:
            return self, None

        allowed_size = max_size - self.reserved_size()

        # Splitting sub-items is undesirable, but we sometimes have to
        # to make progress if the first sub-item is too big.
        first = self._items[0]
        if first.size() > allowed_size:
            first_first, first_rest = first.split(allowed_size)
            return self.children([first_first], [first_rest] + self._items[1:])

        space_left = allowed_size
        i = 0
        while self._items[i].size() <= space_left:
            space_left -= self._items[i].size()
            i += 1

        return self.children(self._items[:i], self._items[i:])


class TextBlock(Compound):
    def __init__(self, items=[], *, prefix='', suffix=''):
        super().__init__(items)
        self._prefix = prefix
        self._suffix = suffix
        self._reserved_size = len(prefix) + len(suffix)

    @classmethod
    def from_text(cls, text, **kwargs):
        lines = [Line(s) for s in text.splitlines()]
        return cls(lines, **kwargs)

    def add_line(self, line='', *, empty=False):
        self.append(Line(line))
        if empty:
            self.append(Line(''))
        self._reserved_size += 2 if empty else 1

    def render(self):
        return self._prefix + '\n'.join(item.render() for item in self.items()) + self._suffix

    def reserved_size(self):
        return self._reserved_size

    def children(self, first, rest):
        opts = dict(prefix=self._prefix, suffix=self._suffix)
        return TextBlock(first, **opts), TextBlock(rest, **opts)


class HelpSection(TextBlock):
    def __init__(self, items=[], *, name=None, hint=None):
        self._name = name
        self._hint = hint

        prefix = '**{0._name}**'.format(self) if self._name else ''
        if self._hint:
            prefix += self._hint
        prefix += '\n'

        super().__init__(items, prefix=prefix)

    def children(self, first, rest):
        return (HelpSection(first, name=self._name, hint=self._hint),
                HelpSection(rest, name=self._name, hint="(cont'd)"))


class FancyFormatter(discord.ext.commands.HelpCommand):
    def is_command(self):
        return isinstance(self.context.command, discord.ext.commands.Command)

    def get_short_signature(self, cmd):
        """Retrives a command signature, ignoring aliases and defaults.
        """
        result = []
        prefix = self.clean_prefix
        parent = cmd.full_parent_name

        name = prefix + (parent + ' ' if parent else '') + cmd.name
        result.append(name)

        params = cmd.clean_params
        for name, param in params.items():
            if param.default is not param.empty:
                fmt = '[{}]'
            elif param.kind == param.VAR_POSITIONAL:
                fmt = '[{}\u2026]'
            else:
                fmt = '<{}>'
            result.append(fmt.format(name))

        return ' '.join(result)

    def format_command_short(self, command):
        sig = self.get_short_signature(command)
        doc = command.short_doc
        return Line('\u2002`{}`: {}'.format(sig, doc))

    def format_section(self, name, commands):
        section = HelpSection(name=name)
        for command in commands:
            section.append(self.format_command_short(command))
        section.add_line()
        return section

    def format_description(self, text):
        unwrapped = re.sub(r'(?<![\r\n])(\r?\n|\r)(?![\r\n])', ' ', text)
        return TextBlock.from_text(unwrapped)

    async def send_message(self, message):
        for page in message.render_pages(max_size=2000):
            await self.get_destination().send(content=page)

    def get_ending_note(self, has_categories=False):
        command_name = self.context.invoked_with
        template = "Type {0}{1} command for more info on a command."
        if has_categories:
            template += " You can also type {0}{1} category for more info on a category."
        return template.format(self.clean_prefix, command_name)

    async def command_not_found(self, name):
        message = TextBlock()
        message.add_line("Unknown command `{}`.".format(name))
        await self.send_message(message)

    async def subcommand_not_found(self, command, name):
        message = TextBlock()
        message.add_line("Unknown command option `{}` to command `{}`.".format(
            name, command.qualified_name))
        await self.send_message(message)

    async def send_bot_help(self, mapping):
        message = TextBlock()
        has_note = False

        for category in mapping:
            name = category.qualified_name if category else '\u200bOther'
            commands = await self.filter_commands(mapping[category], sort=True)
            if commands:
                message.append(self.format_section(name, commands))
                has_note = True

        if has_note:
            message.add_line(self.get_ending_note(has_categories=True))

        await self.send_message(message)

    async def send_cog_help(self, cog):
        message = TextBlock()

        description = cog.description
        if description:
            message.append(self.format_description(description))
            message.add_line()

        commands = await self.filter_commands(cog.get_commands(), sort=True)
        if commands:
            message.append(self.format_section('Commands', commands))
            message.add_line(self.get_ending_note())

        await self.send_message(message)

    async def send_group_help(self, group):
        message = TextBlock()

        description = group.description
        if description:
            message.append(self.format_description(description))
            message.add_line()

        usage = '**Usage:** `{}`'.format(self.get_command_signature(group))
        message.add_line(usage, empty=True)
        if group.help:
            message.append(self.format_description(group.help))
            message.add_line()

        subcommands = await self.filter_commands(group.commands, sort=True)
        if subcommands:
            message.append(self.format_section('Subcommands', subcommands))

        await self.send_message(message)

    async def send_command_help(self, command):
        message = TextBlock()

        description = command.description
        if description:
            message.append(self.format_description(description))
            message.add_line()

        usage = '**Usage:** `{}`'.format(self.get_command_signature(command))
        message.add_line(usage, empty=True)
        if command.help:
            message.append(self.format_description(command.help))
            message.add_line()

        await self.send_message(message)
