import discord
from discord.ext import commands
from utils.chatutils import SendMessage, SendChannelMessage
from datetime import datetime
from data.matchhistorydata import MatchResult, MatchHistoryData, MatchHistoryPlayerData
from enum import Enum
import random

class PlayerAlreadyQueued(commands.BadArgument):
	def __init__(self, argument):
		self.argument = argument
		super().__init__('Player {0.mention} is already queued.'.format(argument))

class PlayerNotQueued(commands.BadArgument):
	def __init__(self, argument):
		self.argument = argument
		super().__init__('Player {0.mention} is not currently queued.'.format(argument))

class InvalidMatchID(commands.BadArgument):
	def __init__(self, argument):
		self.argument = argument
		super().__init__('{} is not a valid match id.'.format(argument))

class Match(object):
	team1 = []
	team2 = []
	map = ''
	creationTime = ''
	uniqueID = 0

	def __init__(self, id, team1, team2, map, creationTime):
		self.uniqueID = id
		self.team1 = team1
		self.team2 = team2
		self.map = map
		self.creationTime = creationTime

	def GetTeamAndNames(self, result:MatchResult):
		team1Name = 'Blue :blue_square:'
		team2Name = 'Orange :orange_square:'

		if result == MatchResult.TEAM1VICTORY or result == MatchResult.CANCELLED:
			return (self.team1, team1Name, self.team2, team2Name)
		elif result == MatchResult.TEAM2VICTORY:
			return (self.team2, team2Name, self.team1, team1Name)
		else:
			return None
	
	def StoreMatchHistoryData(self, winnerTeamData, loserTeamData, result:MatchResult):
		data = MatchHistoryData()

		if (result == MatchResult.TEAM1VICTORY or result == MatchResult.CANCELLED):
			data.StoreData(winnerTeamData, loserTeamData, result, self.map, self.creationTime, self.uniqueID)
		elif (result == MatchResult.TEAM2VICTORY):
			data.StoreData(loserTeamData, winnerTeamData, result, self.map, self.creationTime, self.uniqueID)

def SumMMR(players):
	sum = 0
	for player in players:
		sum += player[1]
	return sum

class InvalidTeamResult(commands.BadArgument):
	def __init__(self, argument):
		self.argument = argument
		super().__init__('Team Result "{}" is not valid.'.format(argument))

class TeamResult(Enum):
	WIN = 0
	LOSE = 1
	CANCEL = 2
	INVALID = 3

	@classmethod
	async def convert(cls, ctx, argument):
		returnType = TeamResult.INVALID

		if (argument == TeamResult.WIN.value):
			returnType = TeamResult.WIN
		elif (argument == TeamResult.LOSE.value):
			returnType = TeamResult.LOSE
		elif (argument == TeamResult.CANCEL.value):
			returnType = TeamResult.CANCEL

		if (returnType is TeamResult.INVALID):
			raise InvalidTeamResult(argument)
		else:
			return returnType

class MatchService(object):
	queuedPlayers = []
	matchesStarted = {}
	bot = None
	botSettings = None

	def Init(self, bot, botSettings):
		self.bot = bot
		self.botSettings = botSettings

	async def JoinQueue(self, ctx, user:discord.Member):
		mmr = self.botSettings.GetMMR(user)

		self.queuedPlayers.append((user, mmr))

		numPlayers = len(self.queuedPlayers)

		if (numPlayers == 10):
			description = '{0.mention} [{1}] joined the queue.\nThe queue is now full, starting a match...'.format(user, mmr)
		else:
			description = '**[{0}/10]** {1.mention} [{2}] joined the queue.'.format(len(self.queuedPlayers), user, mmr)
		
		await SendMessage(ctx, description=description, color=discord.Color.blue())

		if (numPlayers == 10):
			await self.StartMatch(ctx)
		

	async def LeaveQueue(self, ctx, user:discord.Member):
		mmr = self.botSettings.GetMMR(user)

		self.queuedPlayers.remove((user, mmr))

		numPlayers = len(self.queuedPlayers)

		if (numPlayers == 0):
			description = '{0.mention} [{1}] left the queue.\nThe queue is now empty.'.format(user, mmr)
		else:
			description = '**[{0}/10]** {1.mention} [{2}] left the queue.'.format(numPlayers, user, mmr)

		await SendMessage(ctx, description=description, color=discord.Color.blue())

	async def ShowQueue(self, ctx):
		numPlayers = len(self.queuedPlayers)

		if (numPlayers == 0):
			description = 'The queue is empty.'
			await SendMessage(ctx, description=description, color=discord.Color.blue())
		else:
			title = 'Lobby [{0}/10]'.format(numPlayers)
			description = ''

			for player in self.queuedPlayers:
				description += '[{1}] {0.mention}'.format(player[0], player[1])

			await SendMessage(ctx, title=title, description=description, color=discord.Color.blue())

	async def StartMatch(self, ctx):
		# Check for PMCC override
		enablePMCCOverride = False

		for player in self.queuedPlayers:
			if (player[0].id == int('90342358620573696')):
				enablePMCCOverride = True
				break

		id = self.botSettings.GetNextUniqueMatchID()
		selectedMap = self.botSettings.GetRandomMap(enablePMCCOverride).name
		creationTime = datetime.strftime(datetime.now(), '%d %b %Y %H:%M')

		title = 'Game #{} Started'.format(id)
		description = '**Creation Time:** {}\n**Map:** {}'.format(creationTime, selectedMap)

		team1Field = {}
		team1Field['name'] = 'Team Blue :blue_square:'
		team1Field['value'] = ''
		team1Field['inline'] = False
		
		team2Field = {}
		team2Field['name'] = 'Team Orange :orange_square:'
		team2Field['value'] = ''
		team2Field['inline'] = False

		numPlayers = len(self.queuedPlayers)
		team1Size = int(numPlayers / 2)
		team2Size = int(numPlayers - team1Size)
		minDiff = 2147483647

		team1 = []
		team2 = []

		for i in range(5):
			tempList = self.queuedPlayers.copy()
			random.shuffle(tempList) 

			tempT1 = tempList[:team1Size]
			tempT2 = tempList[team1Size:]

			team1Sum = SumMMR(tempT1)
			team2Sum = SumMMR(tempT2)

			diff = abs(team1Sum - team2Sum)
			if (diff < minDiff):
				team1 = tempT1
				team2 = tempT2
				minDiff = diff

		if (len(team1) > 0):
			isFirst = True
			for player in team1:
				if (isFirst):
					isFirst = False
				else:
					team1Field['value'] += '\n'

				team1Field['value'] += '{0.mention}'.format(player[0])
		else:
			team1Field['value'] = 'Empty'

		if (len(team2) > 0):
			isFirst = True
			for player in team2:
				if (isFirst):
					isFirst = False
				else:
					team2Field['value'] += '\n'

				team2Field['value'] += '{0.mention}'.format(player[0])
		else:
			team2Field['value'] = 'Empty'

		self.matchesStarted[id] = Match(id, team1, team2, selectedMap, creationTime)
		self.queuedPlayers.clear()

		adminField = {}
		adminField['name'] = 'Report the result!'
		adminField['value'] = 'Team Blue Win :blue_square:\nTeam Orange Win :orange_square:\nCancelled :negative_squared_cross_mark:'
		adminField['inline'] = False

		# To get these to work, you need to get the <:emoji_name:emoji_id>. The easiest way to do that is to type this into discord
		# and copy what it gives you in the message: \:YourEmoji:
		reactions = ['🟦', '🟧', '❎']

		await SendChannelMessage(self.botSettings.lobbyChannel, title=title, description=description, fields=[team1Field, team2Field], color=discord.Color.blue())
		message = await SendChannelMessage(self.botSettings.reportChannel, title=title, description=description, fields=[team1Field, team2Field, adminField], reactions=reactions)

		def IsValidAdminAndEmoji(reaction, user):
			return self.botSettings.IsUserAdmin(user) and str(reaction.emoji) in reactions

		# Wait for an admin to report the results
		reaction, user = await self.bot.wait_for('reaction_add', check=IsValidAdminAndEmoji)

		# Team 1 Win
		emoji = str(reaction.emoji)
		if (emoji == reactions[0]):
			await self.CallMatch(ctx, user, id, MatchResult.TEAM1VICTORY)
		# Team 2 Win
		elif (emoji == reactions[1]):
			await self.CallMatch(ctx, user, id, MatchResult.TEAM2VICTORY)
		# Match Cancelled
		elif (emoji == reactions[2]):
			await self.CallMatch(ctx, user, id, MatchResult.CANCELLED)
		else:
			print('Something has gone very wrong here')

	async def UpdateRoles(self, ctx, member:discord.Member, oldRole, newRole):
		if (oldRole is not None):
			try:
				await member.remove_roles(oldRole.role, reason='Match service is updating MMR Role for {}'.format(member))
			except discord.HTTPException:
				await SendMessage(ctx, description='Failed to remove previous rank. Please try again.', color=discord.Color.red())

		if (newRole is not None):
			try:
				await member.add_roles(newRole.role, reason='Match service is updating MMR Role for {}'.format(member))
			except discord.HTTPException:
				await SendMessage(ctx, description='Failed to add new rank. Please try again.', color=discord.Color.red())

	async def GetTeamData(self, ctx, team, teamName, result:TeamResult):
		teamData = []
		teamField = {}
		teamField['name'] = '{}: Team {}'.format('Winner' if result == TeamResult.WIN else 'Loser', teamName)
		teamField['value'] = ''
		teamField['inline'] = False

		if (len(team) > 0):
			isFirst = True

			for player in team:
				oldMMR = 0
				newMMR = 0
				oldRole = None
				newRole = None
				mmrDelta = None

				if (result == TeamResult.WIN):
					oldMMR, newMMR, oldRole, newRole = self.botSettings.DeclareWinner(player[0])
				elif (result == TeamResult.LOSE):
					oldMMR, newMMR, oldRole, newRole = self.botSettings.DeclareLoser(player[0])
				else:
					oldMMR, newMMR, mmrDelta = self.botSettings.DeclareCancel(player[0])

				delta = int(abs(newMMR - oldMMR)) if mmrDelta is None else mmrDelta
				teamData.append(MatchHistoryPlayerData(_id=player[0].id, _prevMMR=oldMMR, _newMMR=newMMR, _mmrDelta=delta))

				if (isFirst):
					isFirst = False
				else:
					teamField['value'] += '\n'

				sign = '+' if result == TeamResult.WIN else '-'

				teamField['value'] += '[{}] **MMR:** {} {} {} = {}'.format(self.botSettings.GetUserName(player[0]), oldMMR, sign, delta, newMMR)

				if (oldRole is not None and newRole is not None):
					teamField['value'] += ' **Rank:** {0.mention} -> {1.mention}'.format(oldRole.role, newRole.role)

				# No point in updating roles if the match was cancelled
				if (result != TeamResult.CANCEL):
					await self.UpdateRoles(ctx, player[0], oldRole, newRole)
		else:
			teamField['value'] = 'Empty'

		return teamData, teamField

	async def CallMatch(self, ctx, user:discord.Member, id:int, matchResult:MatchResult):
		print('Match {} has been called as {}'.format(id, matchResult))

		if (id not in self.matchesStarted):
			raise InvalidMatchID(id)

		title = 'Match Results: Game #{}'.format(id)
		footer = 'This match was called by {}'.format(user)

		winnerTeam, winnerName, loserTeam, loserName = self.matchesStarted[id].GetTeamAndNames(matchResult)

		if (matchResult == MatchResult.CANCELLED):
			description = 'This match has been cancelled.'

			team1Data, team1Field = await self.GetTeamData(ctx, winnerTeam, winnerName, TeamResult.CANCEL)
			team2Data, team2Field = await self.GetTeamData(ctx, loserTeam, loserName, TeamResult.CANCEL)

			self.matchesStarted[id].StoreMatchHistoryData(team1Data, team2Data, matchResult)
			del self.matchesStarted[id]

			await SendChannelMessage(self.botSettings.resultsChannel, title=title, description=description, footer=footer, color=discord.Color.blue())
			return

		winnerTeamData, winnerField = await self.GetTeamData(ctx, winnerTeam, winnerName, TeamResult.WIN)
		loserTeamData, loserField = await self.GetTeamData(ctx, loserTeam, loserName, TeamResult.LOSE)

		self.botSettings.DeclareMapPlayed(self.matchesStarted[id].map)

		self.matchesStarted[id].StoreMatchHistoryData(winnerTeamData, loserTeamData, matchResult)
		del self.matchesStarted[id]

		await SendChannelMessage(self.botSettings.resultsChannel, title=title, fields=[winnerField, loserField], footer=footer, color=discord.Color.blue())

	def IsPlayerQueued(self, user:discord.User):
		return user in self.queuedPlayers
