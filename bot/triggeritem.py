from disco.types.message import MessageEmbed
import re
import string


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
	def __init__(self, itemType, tokens, reminder, replacementTokens=None, cds=[], lang=None, logger=None):
		self.itemType = itemType
		self.patterns = []
		self.stemmer = None
		self.translatorPunctuation = None
		if itemType == 'regex':
			self.patterns = [re.compile(t) for t in tokens]
		elif itemType == 'equals_word_stem':
			from nltk.stem import SnowballStemmer
			self.language = lang
			# if not self.language:
			self.stemmer = SnowballStemmer(self.language)
			self.translatorPunctuation = str.maketrans('', '', string.punctuation)
			self.patterns = tokens
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

	def ensureLanguage(self, text):
		if not self.language:
			self.logMessage('WARNING: can not ensure language if current language is not set')
			return False
		else:
			from polyglot.detect import Detector
			detector = Detector(text)
			if detector.languages:
				#for l in detector.languages:
				#	self.logMessage(l.name)
				return self.language == detector.languages[0].name.lower()
			return False

	def areCooldownsSatisfied(self, e):
		satisfied = True
		for c in self.timeCooldowns:
			if (e.channel_id not in self.cooldownTSPerChannel or ((e.timestamp - self.cooldownTSPerChannel[e.channel_id]).total_seconds() >= c.cooldownParam)):
				self.cooldownTSPerChannel[e.channel_id] = e.timestamp
				satisfied = satisfied and True
			else:
				# update time cooldown even if we are below the threshold
				self.cooldownTSPerChannel[e.channel_id] = e.timestamp
				satisfied = satisfied and False
		for c in self.msgIntervalCooldowns:
			if e.channel_id not in self.cooldownMsgCounterPerChannel:
				self.cooldownMsgCounterPerChannel[e.channel_id] = c.cooldownParam
				satisfied = satisfied and True
			elif self.cooldownMsgCounterPerChannel[e.channel_id] <= 0:
				satisfied = satisfied and True
			else:
				satisfied = satisfied and False
		if satisfied:
			# reset the countdown for msg interval only if all cooldowns were satisfied
			for c in self.msgIntervalCooldowns:
				self.cooldownMsgCounterPerChannel[e.channel_id] = c.cooldownParam
		return satisfied

	def updateOnMsg(self, e):
		if e.channel_id in self.cooldownMsgCounterPerChannel and self.cooldownMsgCounterPerChannel[e.channel_id] > 0:
			self.cooldownMsgCounterPerChannel[e.channel_id] -= 1

	def craftReply(self, event, satisfiedPatternIndex):
		e = None
		# here, we check for None since empty string means "suppress embeds"
		if self.reminder.embed is not None:
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
				m = m.replace("$" + str(index + 1), t)
		return (m, e, atts)

	def satisfiesTrigger(self, event):
		text = event.content.lower()
		if self.itemType == 'equals_word_stem' and self.ensureLanguage(text) and any(p in text for p in self.patterns):
			words = text.translate(self.translatorPunctuation).split()
			for w in words:
				for index, p in enumerate(self.patterns):
					if p in w:  # preliminary match: pattern is in word
						# check if it matches also with the stem
						stemmed = self.stemmer.stem(w)
						if (p == stemmed) and (stemmed != w) and (self.areCooldownsSatisfied(event)):  # we exclude words that were already stems, they are usually false positives
							return self.craftReply(event, index)
		elif self.itemType == 'regex':
			for index, p in enumerate(self.patterns):
				if p.search(text) and self.areCooldownsSatisfied(event):
					return self.craftReply(event, index)
		return (None, None, [])

	def attachLogger(self, logger):
		self.logger = logger

	def logMessage(self, msg):
		if self.logger:
			self.logger.info(msg)
		else:
			print(msg)
