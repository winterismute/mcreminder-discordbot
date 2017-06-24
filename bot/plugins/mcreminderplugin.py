from disco.bot import Bot, Plugin
from triggeritem import TriggerItem, TriggerItemReminder
import re
import json
import sys

def toTriggerItemReminder(dct):
	return TriggerItemReminder(dct['content'], dct.get('embed', None), dct.get('attachments', []))

def toTriggerItem(dct):
	return TriggerItem(dct['type'], dct['tokens'], (dct['reminder']), dct.get('replacementTokens',[]), dct.get('cooldownTime', 0))

def newjsondecode(data):
	if 'triggers' in data:
		return data['triggers']
	if all(k in data for k in ('type', 'tokens', 'reminder')):
		return toTriggerItem(data)
	if 'content' in data:
		return toTriggerItemReminder(data)
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
					#self.triggers = json.load(json_data, object_hook = newjsondecode, encoding="cp1252")
					self.triggers = json.load(json_data, object_hook = newjsondecode)
					self.log.info(self.triggers)
				except ValueError as e:
					self.log.error('Can not process struture of botconfig.json: ' + str(e))
					sys.exit()

	@Plugin.listen('MessageCreate')
	def on_message_create(self, event):
		# never trigger on bot's own messages
		if (event.author.id == self.state.me.id):
			return
		for trigger in self.triggers:
			craftedMessage, craftedEmbed, craftedAttachments = trigger.satisfiesTrigger(event)
			if not craftedMessage is None:
				event.reply(craftedMessage, attachments=craftedAttachments, embed=craftedEmbed)