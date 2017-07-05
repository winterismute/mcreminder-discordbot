from disco.types.message import MessageEmbed
import re

class TriggerItemReminder(object):
	def __init__(self, content, embed=None, attachments=[]):
		self.content = content
		self.embed = embed
		self.attachments = attachments
		self.attachmentsData = [open(apath, 'rb') for apath in self.attachments]

class TriggerItemCooldown(object):
	def __init__(self, cooldowntype, cooldownparam):
		self.cooldownType = cooldowntype
		self.cooldownParam = cooldownparam

class TriggerItem(object):
	def __init__(self, itemType, tokens, reminder, replacementTokens=None, cds=[], logger=None):
		self.itemType = itemType
		self.patterns = []
		if itemType == 'regex':
			self.patterns = [re.compile(t) for t in tokens]
		self.reminder = reminder
		self.replacementTokens = replacementTokens
		self.timeCooldowns = []
		self.msgIntervalCooldowns = []
		for ci in cds:
			if ci.cooldownType == 'seconds':
				self.timeCooldowns.append(ci)
			elif ci.cooldownType == 'msg_interval':
				self.msgIntervalCooldowns.append(ci)
		self.cooldownTSPerChannel = {}
		self.cooldownMsgCounterPerChannel = {}
		self.logger = logger

	def areCooldownsSatisfied(self, e):
		satisfied = True
		for c in self.timeCooldowns:
			if c.cooldownParam <= 0:
				satisfied = satisfied and True
			elif (not e.channel_id in self.cooldownTSPerChannel or ((e.timestamp - self.cooldownTSPerChannel[e.channel_id]).total_seconds() > c.cooldownParam)):
				self.cooldownTSPerChannel[e.channel_id] = e.timestamp
				satisfied = satisfied and True
			else:
				# update time cooldown even if we are below the threshold
				self.cooldownTSPerChannel[e.channel_id] = e.timestamp
				satisfied = satisfied and False
		for c in self.msgIntervalCooldowns:
			if not e.channel_id in self.cooldownMsgCounterPerChannel:
				self.cooldownMsgCounterPerChannel[e.channel_id] = c.cooldownParam
				satisfied = satisfied & True
			elif self.cooldownMsgCounterPerChannel[e.channel_id] <= 0:
				print(c)
				satisfied = satisfied and True
			else:
				satisfied = satisfied and False
		if satisfied:
			# reset the countdown for msg interval only if we have satisfied everything
			for c in self.msgIntervalCooldowns:
				self.cooldownMsgCounterPerChannel[e.channel_id] = c.cooldownParam
		return satisfied

	def updateOnMsg(self, e):
		for cid, val in self.cooldownMsgCounterPerChannel.items():
			if val > 0:
				self.cooldownMsgCounterPerChannel[cid] -= 1

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
			if p.search(text) and self.areCooldownsSatisfied(event):
				return self.craftReply(event, index)
		return (None, None, [])

	def attachLogger(self, logger):
		self.logger = logger