from discord.ext import commands
from utils.chatutils import SendChannelMessage
from globals import *
import discord
import itertools

class HelpCommand(commands.DefaultHelpCommand):

	def get_command_signature(self, command):
		"""Retrieves the signature portion of the help page.

		Parameters
		------------
		command: :class:`Command`
			The command to get the signature of.

		Returns
		--------
		:class:`str`
			The signature for the command.
		"""

		field = {}
		field['name'] = command.name
		field['value'] = '**Usage:** '
		field['inline'] = False


		parent = command.parent
		entries = []
		while parent is not None:
			if not parent.signature or parent.invoke_without_command:
				entries.append(parent.name)
			else:
				entries.append(parent.name + ' ' + parent.signature)
			parent = parent.parent
		parent_sig = ' '.join(reversed(entries))

		name = command.name if not parent_sig else parent_sig + ' ' + command.name
		field['value'] += '{}{} {}'.format(self.clean_prefix, name, command.signature)

		if len(command.aliases) > 0:
			aliases = '|'.join(command.aliases)
			field['value'] += '\n**Aliases:** {}'.format(aliases)

		#return '%s%s %s' % (self.clean_prefix, alias, command.signature)
		return field

	def add_command_formatting(self, command):
		"""A utility function to format the non-indented block of commands and groups.

		Parameters
		------------
		command: :class:`Command`
			The command to format.
		"""

		field = self.get_command_signature(command)

		if command.help:
			field['value'] += '\n{}'.format(command.help)
		return field

	def add_indented_commands(self, commands, *, heading, max_size=None):
		"""Indents a list of commands after the specified heading.

		The formatting is added to the :attr:`paginator`.

		The default implementation is the command name indented by
		:attr:`indent` spaces, padded to ``max_size`` followed by
		the command's :attr:`Command.short_doc` and then shortened
		to fit into the :attr:`width`.

		Parameters
		-----------
		commands: Sequence[:class:`Command`]
			A list of commands to indent for output.
		heading: :class:`str`
			The heading to add to the output. This is only added
			if the list of commands is greater than 0.
		max_size: Optional[:class:`int`]
			The max size to use for the gap between indents.
			If unspecified, calls :meth:`get_max_size` on the
			commands parameter.
		"""

		field = {}
		field['name'] = heading 
		field['value'] = ''
		field['inline'] = False

		if not commands:
			return field

		field['value'] = '```'
		isFirst = False

		max_size = max_size or self.get_max_size(commands)

		get_width = discord.utils._string_width

		for command in commands:
			name = command.name
			width = max_size - (get_width(name) - len(name))
			field['value'] += '\n{0:<{width}} {1}'.format(name, command.short_doc, width=width)

		field['value'] += '```'

		return field

	async def send_bot_help(self, mapping):
		ctx = self.context
		bot = ctx.bot

		description = None

		if bot.description:
			description = bot.description

		no_category = '\u200b{0.no_category}'.format(self)
		def get_category(command, *, no_category=no_category):
			cog = command.cog
			return cog.qualified_name + '' if cog is not None else no_category

		filtered = await self.filter_commands(bot.commands, sort=True, key=get_category)
		to_iterate = itertools.groupby(filtered, key=get_category)

		fields = []

		# Now we can add the commands to the page.
		for category, commands in to_iterate:
			if (category == 'AdminCommands' and not botSettings.IsUserAdmin(ctx.author)):
				continue

			commands = sorted(commands, key=lambda c: c.name) if self.sort_commands else list(commands)
			field = self.add_indented_commands(commands, heading=category)
			fields.append(field)

		footer = self.get_ending_note()

		await SendChannelMessage(self.get_destination(), description=description, footer=footer, fields=fields, color=discord.Color.blue())

	async def send_command_help(self, command):
		field = self.add_command_formatting(command)
		await SendChannelMessage(self.get_destination(), fields=[field], color=discord.Color.blue())

	async def send_group_help(self, group):
		self.add_command_formatting(group)

		filtered = await self.filter_commands(group.commands, sort=self.sort_commands)
		self.add_indented_commands(filtered, heading=self.commands_heading)

		if filtered:
			note = self.get_ending_note()
			if note:
				self.paginator.add_line()
				self.paginator.add_line(note)

		await self.send_pages()

	async def send_cog_help(self, cog):
		filtered = await self.filter_commands(cog.get_commands(), sort=self.sort_commands)
		field = self.add_indented_commands(filtered, heading=self.commands_heading)

		footer = self.get_ending_note()

		await SendChannelMessage(self.get_destination(), footer=footer, fields=[field], color=discord.Color.blue())

	async def send_pages(self):
		pass
