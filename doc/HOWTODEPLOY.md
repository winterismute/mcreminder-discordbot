# How to Deploy the bot
* Prepare everything for the bot, including tokens etc, following this guide: https://github.com/reactiflux/discord-irc/wiki/Creating-a-discord-bot-&-getting-a-token
* Install dependencies, copy on your server the content of the "bot" folder and all the subdirectories
* In the config.yaml file, set your own token for the bot. Also set up a correct botconfig.json
* Run
python -m disco.cli --config config.yaml
* Enjoy!