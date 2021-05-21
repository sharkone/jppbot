from mongoengine import Document, IntField, StringField
import discord

class PlayerData(Document):
    # Database fields.  Dont modify or access directly, use the non underscore versions
    _mmr = IntField(default=0)
    _matchesPlayed = IntField(default=0)
    _wins = IntField(default=0)
    _loses = IntField(default=0)
    _name = StringField(default='')
    _user = IntField(default=-1)

    # Settings
    mmr = 0
    matchesPlayed = 0
    wins = 0
    loses = 0
    name = '' # The name choosen by the user when registering
    user = None # discord.User

    async def Init(self, bot):
        self.mmr = self._mmr
        self.matchesPlayed = self._matchesPlayed
        self.wins = self._wins
        self.loses = self._loses
        self.name = self._name
        self.user = await bot.fetch_user(self._user)

    def UpdateData(mmrDelta:int, isWin:bool):
        # Update cache
        self.mmr += mmrDelta

        if (isWin):
            self.wins += 1
        else:
            self.loses += 1

        self.matchesPlayed += 1

        # Update database
        self._mmr = self.mmr
        self._wins = self.wins
        self._loses = self.loses
        self._matchesPlayed = self.matchesPlayed
        self.save()
	
    def SetUser(self, user:discord.User, name:str):
        self.user = user
        self._user = user.id
        self.name = name
        self._name = name
        self.save()

