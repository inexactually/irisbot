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
        raise NotImplemented

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
            prefix += (' ' if header else '') + self._hint
        prefix += '\n'

        super().__init__(items, prefix=prefix)


    def children(self, first, rest):
        return (HelpSection(first, name=self._name, hint=self._hint),
                HelpSection(rest, name=self._name, hint="(cont'd)"))


class FancyFormatter(discord.ext.commands.HelpFormatter):
    def is_command(self):
        return isinstance(self.command, discord.ext.commands.Command)

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
        for name, command in commands:
            if name not in command.aliases:
                section.append(self.format_command_short(command))
        section.add_line()
        return section

    def format_description(self, text):
        unwrapped = re.sub(r'(?<![\r\n])(\r?\n|\r)(?![\r\n])', ' ', text)
        return TextBlock.from_text(unwrapped)

    def get_ending_note(self, has_categories=False):
        command_name = self.context.invoked_with
        template = "Type {0}{1} command for more info on a command."
        if has_categories:
            template += " You can also type {0}{1} category for more info on a category."
        return template.format(self.clean_prefix, command_name)

    def format(self):
        message = TextBlock()
        show_ending_note = False

        description = self.command.description if not self.is_cog() else inspect.getdoc(self.command)
        if description:
            message.append(self.format_description(description))
            message.add_line()

        if self.is_command():
            usage = '**Usage:** `{}`'.format(self.get_command_signature())
            message.add_line(usage, empty=True)
            if self.command.help:
                message.append(self.format_description(self.command.help))
                message.add_line()
            if self.has_subcommands():
                subcommands = list(self.filter_command_list())
                if subcommands:
                    message.append(self.format_section('Subcommands', subcommands))
                    show_ending_note = True

        elif self.is_cog():
            commands = list(self.filter_command_list())
            if commands:
                message.append(self.format_section('Commands', commands))
                show_ending_note = True

        elif self.is_bot():
            category = lambda tup: tup[1].cog_name or '\u200bOther'
            data = sorted(self.filter_command_list(), key=category)
            for category, commands in itertools.groupby(data, key=category):
                commands = list(commands)
                if commands:
                    message.append(self.format_section(category, commands))
                    show_ending_note = True

        if show_ending_note:
            message.add_line(self.get_ending_note(has_categories=self.is_bot()))

        return message.render_pages(max_size=2000)


