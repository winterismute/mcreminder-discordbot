from disco.types.message import MessageEmbed
import re
import string
from abc import ABC, abstractmethod
import gevent


class TriggerItemReminder(object):
	def __init__(self, content, embed=None, attachments=[]):
		self.content = content
		self.embed = embed
		self.attachments = attachments
		self.attachmentsData = [open(apath, 'rb') for apath in self.attachments]


class TriggerCooldown(ABC):
	@abstractmethod
	def isSatisfied(self, event):
		pass

	def onReply(self, event, msg):
		pass

	def onMessageUpdate(self, event):
		pass


class TriggerCooldownTimeInterval(TriggerCooldown):
	def __init__(self, secs):
		self.seconds = secs
		self.timeStampPerChannel = {}

	def isSatisfied(self, event):
		return event.channel_id not in self.timeStampPerChannel or ((event.timestamp - self.timeStampPerChannel[event.channel_id]).total_seconds() >= self.seconds)

	def onReply(self, event, msg):
		self.timeStampPerChannel[event.channel_id] = event.timestamp


class TriggerCooldownMsgInterval(TriggerCooldown):
	def __init__(self, interval):
		self.msgInterval = interval
		self.msgCounterPerChannel = {}

	def isSatisfied(self, event):
		if event.channel_id not in self.msgCounterPerChannel:
			self.msgCounterPerChannel[event.channel_id] = self.msgInterval
			return True
		elif self.msgCounterPerChannel[event.channel_id] <= 0:
			return True
		else:
			return False

	def onReply(self, event, msg):
		self.msgCounterPerChannel[event.channel_id] = self.msgInterval

	def onMessageUpdate(self, event):
		if event.channel_id in self.msgCounterPerChannel and self.msgCounterPerChannel[event.channel_id] > 0:
			self.msgCounterPerChannel[event.channel_id] -= 1

class TriggerItemBase(object):
	def __init__(self, tokens, reminder, replacementTokens=None, cds=[], messageDuration=None, logger=None):
		self.patterns = tokens
		self.reminder = reminder
		self.replacementTokens = replacementTokens
		self.cooldowns = cds
		self.messageDuration = messageDuration
		self.logger = logger

	def attachLogger(self, logger):
		self.logger = logger

	def logMessage(self, msg):
		if self.logger:
			self.logger.info(msg)
		else:
			print(msg)

	def onMessageUpdate(self, e):
		for c in self.cooldowns:
			c.onMessageUpdate(e)

	def delete_message_task(self, msg):
		gevent.sleep(self.messageDuration)
		msg.delete()

	def onReply(self, event, msg):
		for c in self.cooldowns:
			c.onReply(event, msg)
		if self.messageDuration is not None:
			gevent.spawn(self.delete_message_task, msg)

	def areCooldownsSatisfied(self, e):
		for c in self.cooldowns:
			if not c.isSatisfied(e):
				return False
		# Here all cooldowns are satisfied
		return True

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

	def satisfies(self, event):
		pass


class TriggerItemRegex(TriggerItemBase):
	def __init__(self, tokens, reminder, replacementTokens=None, cds=[], messageDuration=None, logger=None):
		TriggerItemBase.__init__(self, tokens, reminder, replacementTokens, cds, messageDuration, logger)
		self.patterns = [re.compile(t) for t in tokens]

	def satisfies(self, event):
		text = event.content.lower()
		for index, p in enumerate(self.patterns):
			if p.search(text) and self.areCooldownsSatisfied(event):
				return self.craftReply(event, index)
		return (None, None, [])


class TriggerItemEqualStems(TriggerItemBase):
	def __init__(self, tokens, reminder, lang=None, replacementTokens=None, cds=[], messageDuration=None, logger=None):
		TriggerItemBase.__init__(self, tokens, reminder, replacementTokens, cds, messageDuration, logger)
		from nltk.stem import SnowballStemmer
		self.language = "english" if not lang else lang
		self.stemmer = SnowballStemmer(self.language)
		self.translatorPunctuation = str.maketrans('', '', string.punctuation)
		self.patterns = tokens

	def ensureLanguage(self, text):
		if not self.language:
			self.logMessage('WARNING: can not ensure language if current language is not set')
			return False
		else:
			from polyglot.detect import Detector
			detector = Detector(text)
			if detector.languages:
				# for l in detector.languages:
				#	self.logMessage(l.name)
				return self.language == detector.languages[0].name.lower()

	def satisfies(self, event):
		text = event.content.lower()
		if self.ensureLanguage(text) and any(p in text for p in self.patterns):
			words = text.translate(self.translatorPunctuation).split()
			for w in words:
				for index, p in enumerate(self.patterns):
					if p in w:  # preliminary match: pattern is in word
						# check if it matches also with the stem
						stemmed = self.stemmer.stem(w)
						if (p == stemmed) and (stemmed != w) and (self.areCooldownsSatisfied(event)):  # we exclude words that were already stems, they are usually false positives
							return self.craftReply(event, index)
		return (None, None, [])
