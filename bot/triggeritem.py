from disco.types.message import MessageEmbed
import re

class TriggerItemReminder(object):
	def __init__(self, content, embed=None, attachments=[]):
		self.content = content
		self.embed = embed
		self.attachments = attachments
		self.attachmentsData = [open(apath, 'rb') for apath in self.attachments]

class TriggerItem(object):
	def __init__(self, itemType, tokens, reminder, replacementTokens=None, cooldownTime=0):
		self.itemType = itemType
		self.patterns = []
		if itemType == 'regex':
			self.patterns = [re.compile(t) for t in tokens]
		self.reminder = reminder
		self.replacementTokens = replacementTokens
		self.cooldownTime = cooldownTime
		self.cooldowns = {}

	def isCooldownSatisfied(self, e):
		if self.cooldownTime <= 0:
			return True
		if not e.channel_id in self.cooldowns:
			self.cooldowns[e.channel_id] = e.timestamp
			return True
		if (e.timestamp - self.cooldowns[e.channel_id]).total_seconds() > self.cooldownTime:
			self.cooldowns[e.channel_id] = e.timestamp
			return True
		# update cooldown even if we are below the threshold
		self.cooldowns[e.channel_id] = e.timestamp
		return False

	def craftReply(self, event, satisfiedPatternIndex):
		e = None
		# here, we check for None since empty string means "suppress embeds"
		if not self.reminder.embed is None:
			e = MessageEmbed()
			e.set_image(url=self.reminder.embed)
		atts = []
		if self.reminder.attachments:
			atts = [(self.reminder.attachments[i], self.reminder.attachmentsData[i]) for i in range(len(self.reminder.attachments))]
		m = self.reminder.content
		m = m.replace(u'$AUTHOR', u'<@' + str(event.author.id) + '>')
		# chech if we have tokens to substitute for this satisfied pattern
		if satisfiedPatternIndex < len(self.replacementTokens):
			for index, t in enumerate(self.replacementTokens[satisfiedPatternIndex]):
				m = m.replace("$" + str(index+1), t)
		return (m, e, atts)

	def satisfiesTrigger(self, event):
		text = event.content.lower()
		for index, p in enumerate(self.patterns):
			if p.search(text) and self.isCooldownSatisfied(event):
				return self.craftReply(event, index)
		return (None, None, [])