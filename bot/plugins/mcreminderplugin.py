from disco.bot import Bot, Plugin
from triggeritem import TriggerItemReminder, TriggerItemRegex, TriggerItemEqualStems, TriggerCooldownTimeInterval, TriggerCooldownMsgInterval
import json
import sys


def toTriggerItemReminder(dct):
	return TriggerItemReminder(dct['content'], dct.get('embed', None), dct.get('attachments', []))


def toTriggerItemCooldown(dct):
	cdType = dct['cooldown_type']
	if cdType == 'seconds':
		return TriggerCooldownTimeInterval(dct['cooldown_value'])
	elif cdType == 'msg_interval':
		return TriggerCooldownMsgInterval(dct['cooldown_value'])
	raise ValueError('Error: can not parse cooldown item with type: ' + str(cdType))


def toTriggerItem(dct):
	itemType = dct.get('type')
	if itemType == 'regex':
		return TriggerItemRegex(dct['tokens'], (dct['reminder']), dct.get('replacementTokens', []), dct.get('cooldowns', []), dct.get('messageDuration', None))
	elif itemType == 'equals_word_stem':
		return TriggerItemEqualStems(dct['tokens'], (dct['reminder']), dct.get('lang', None), dct.get('replacementTokens', []), dct.get('cooldowns', []), dct.get('messageDuration', None))
	raise ValueError('Error: can not parse trigger item with type: ' + str(itemType))


def newjsondecode(data):
	if 'triggers' in data:
		return data['triggers']
	if all(k in data for k in ('type', 'tokens', 'reminder')):
		return toTriggerItem(data)
	if 'content' in data:
		return toTriggerItemReminder(data)
	if 'cooldown_type' in data:
		return toTriggerItemCooldown(data)
	raise ValueError('Error: can not parse data: ' + str(data))


class SimplePlugin(Plugin):

	def load(self, ctx):
		try:
			json_data = open('botconfig.json')
		except IOError as e:
			self.log.error('Error while opening config file: ' + str(e))
			self.log.error('Exiting...')
			sys.exit()
		else:
			with json_data:
				try:
# 					self.triggers = json.load(json_data, object_hook = newjsondecode, encoding="cp1252")
					self.triggers = json.load(json_data, object_hook=newjsondecode)
					self.log.info(self.triggers)
					for t in self.triggers:
						t.attachLogger(self.log)
				except ValueError as e:
					self.log.error('Can not process struture of botconfig.json: ' + str(e))
					sys.exit()

	@Plugin.listen('MessageCreate')
	def on_message_create(self, event):
		# never trigger on bot's own messages
		if (event.author.id == self.state.me.id):
			return
		for trigger in self.triggers:
			trigger.onMessageUpdate(event)
			craftedMessage, craftedEmbed, craftedAttachments = trigger.satisfies(event)
			if craftedMessage is not None:
				msg = event.reply(craftedMessage, attachments=craftedAttachments, embed=craftedEmbed)
				trigger.onReply(event, msg)
