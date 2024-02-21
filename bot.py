# bot.py
import telegram as tg
from telegram.ext import Updater
import logging
import json
import urllib.parse
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler, Filters
from telegram import MessageEntity
from aliexpress_api import AliexpressApi, models
import re
import requests
import os

PORT = int(os.environ.get('PORT', 5000))

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)
#Read env variables
TOKEN = os.environ['TOKEN']
baseURL = os.environ['baseURL'] 
affiliate_tag = os.environ['affiliate_tag']
HEROKU_URL = os.environ['HEROKU_URL']
ALITOKEN = os.environ['ALITOKEN']
SECRET = os.environ['SECRET']
TRACKING_ID = os.environ['TRACKING_ID']
aliexpress = AliexpressApi(ALITOKEN, SECRET, models.Language.EN, models.Currency.EUR, TRACKING_ID)

# baseURL should have https and www before amazon, but we also want to detect URL without it
# Ensure that we can detect all but the baseURL has the correct https URL
if baseURL.startswith("https://www."):
    searchURL = baseURL[12:]
elif baseURL.startswith("http://www."):
    searchURL = baseURL[11:]
    baseURL = "https://www."+searchURL
else:
    searchURL = baseURL
    baseURL = "https://www."+baseURL

# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
def start(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Hola! Este bot responde a los enlaces de amazon y aliexpress añadiendo un codigo de afiliado!")

# Create the new URL with the refer tag
def newReferURL(pcode):
    return baseURL+pcode+"?tag="+affiliate_tag

#Expand shorted URL (amzn.to links) to normal Amazon URL
def unshortURL(url):
    resp = requests.get("https://"+url)
    return resp.url

#Filter the msg text to extract the URL if found. Then send the corresponding reply
# with the new affiliate URL
def filterText(update, context):
    pCode=""
    msg = update.message.text
    sender = "<a href=\"tg://user?id="+str(update.message.from_user.id)+"\">"+update.message.from_user.first_name+"</a>"
    start = msg.find("amzn.to")
    if start!=-1:
        msg = unshortURL(msg[start:].split()[0])
    start = msg.find("amzn.eu")
    if start!=-1:
        msg = unshortURL(msg[start:].split()[0])
    start = msg.find(searchURL)
    if start != -1:
        #Regular expression to extract the product code. Adjust if different URL schemes are found.
        m = re.search(r'(?:dp\/[\w]*)|(?:gp\/product\/[\w]*)|(?:gp\/aw\/d\/[\w]*)',msg[start:].split(" ")[0])
        if m != None:
            pCode = m.group(0)
#        reflong = newReferURL(pCode)
#        bitly = json.loads(requests.get("http://api.bit.ly/shorten?version=2.0.1&longUrl="+urllib.parse.quote(reflong, safe='')+"&login=ghir0&apiKey=R_c7d78316d223d5a1d7827d58d80e76be&format=json").text)
#        refshort = bitly["results"][reflong]['shortUrl']
#        link = "<a href=\""+reflong+"\">"+str(refshort)+"</a>"
        link = "<a href=\""+newReferURL(pCode)+"\">"+baseURL+pCode+"</a>"
        context.bot.send_message(chat_id=update.message.chat_id,reply_to_message_id=update.message.message_id, text="🔥 Aporte de  <b>"+sender+"</b> \n\n➡️ "+link,parse_mode='HTML')
        context.bot.delete_message(chat_id=update.message.chat_id,message_id=update.message.message_id)
    start = msg.find("aliexpress")
    if start!=-1:
        e = re.search(r'(?:\/e\/[\w]*)',msg[start:].split(" ")[0])
        a = re.search(r'(?:com\/_[\w]*)',msg[start:].split(" ")[0])
        i = re.search(r'(?:com\/item\/[\w]*)',msg[start:].split(" ")[0])
        if e != None:
            pCode = e.group(0)
            msg = "https://s.click.aliexpress.com"+pCode
        else:
            if a != None:
                pCode = a.group(0)
                msg = "https://a.aliexpress."+pCode
            else:
                pCode = i.group(0)
                msg = "https://es.aliexpress."+pCode+".html"
        alilink = aliexpress.get_affiliate_links(msg)
        alitest = str(alilink)
        start = alitest.find("promotion_link")
        if start!=-1:
            context.bot.send_message(chat_id=update.message.chat_id,reply_to_message_id=update.message.message_id, text="🔥 Aporte de  <b>"+sender+"</b> \n\n➡️ "+alilink[0].promotion_link,parse_mode='HTML')
            context.bot.delete_message(chat_id=update.message.chat_id,message_id=update.message.message_id)


def main():
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    updater = Updater(TOKEN, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(    
                   Filters.text & (Filters.entity(MessageEntity.URL) |
                                    Filters.entity(MessageEntity.TEXT_LINK)),filterText))
    # Start the Bot
    updater.start_webhook(listen="0.0.0.0",
                          port=int(PORT),
                          url_path=TOKEN)
    updater.bot.setWebhook(HEROKU_URL + TOKEN)

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()

if __name__ == '__main__':
    main()
