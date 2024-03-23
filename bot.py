# залить на гитхаб
# загрузить на виртуалку
# запустить расписание

import imaplib
import email
from telegram import Bot
from bs4 import BeautifulSoup
import re
import asyncio

from config import bot_token, username, password, imap_url, chat_id

bot = Bot(token=bot_token)

def clean_string(input, search_string, direction):
    # Find the index of search string
    index = input.find(search_string)

    if index != -1:
        if direction == 'before':
            return input[index + len(search_string):]
        else:
            return input[:index - len(search_string)]
    else:
        return input

def get_images(html_content):
    soup = BeautifulSoup(html_content, "lxml")

    # Find all image tags
    images = soup.find_all('img')

    # Extract src attributes
    image_urls = [img['src'] for img in images if 'src' in img.attrs]
    filtered_urls = [url for url in image_urls if "assets/emails" not in url]
    filtered_urls = [url for url in filtered_urls if "mandrillapp.com" not in url]
    return filtered_urls


def check_email():
    # Connect to the email server
    mail = imaplib.IMAP4_SSL(imap_url)
    mail.login(username, password)
    mail.select("inbox")

    # Search for emails from the specific sender
    status, messages = mail.search(None, '(UNSEEN)', '(FROM "noreply@managebac.com")')
    if status != 'OK':
        print("No new emails found.")
        return

    email_ids = messages[0].split()
    emails = []

    for email_id in email_ids:
        # Fetch each email by its ID
        res, msg = mail.fetch(email_id, '(RFC822)')

        for response in msg:
            if isinstance(response, tuple):
                # parse a bytes email into a message object
                msg = email.message_from_bytes(response[1])
                html_data = msg.get_payload(decode=True).decode()

                images = get_images(html_data)
                soup = BeautifulSoup(html_data, "html.parser")
                plain_text = soup.get_text(separator='\n')
                final_text = clean_string(plain_text, 'Updated Task', 'before')
                final_text = clean_string(final_text, 'View full details', 'after')
                final_text = clean_string(final_text, 'in \nIB PYP', 'before')

                final_text = re.sub(r'\n+', '\n', final_text)
                final_text = final_text.strip()
                final_text = final_text.replace('.\nWhen:\n', '')

                # Проверка на общее письмо (не про Антона)
                if not ('Anton' in final_text):
                    emails.append({'text': final_text, 'img': images})

        # пометить как прочитанное
        email_num = email_id.decode('utf-8')
        mail.store(str(email_num), '+FLAGS', '\Seen')
    mail.logout()

    return emails


async def send_message_to_telegram(message, imgs):
    await bot.send_message(chat_id=chat_id, text=message)

    for img in imgs:
        await send_message_img_telegram(img)
        await asyncio.sleep(0.5)


async def send_message_img_telegram(img):
    await bot.send_message(chat_id=chat_id, text=f"[source]({img})", parse_mode='markdown')


async def process_emails():
    emails = check_email()

    if len(emails) > 0:
        for item in emails:
            text = item['text']
            imgs = item['img']
            await send_message_to_telegram(text, imgs)
            await asyncio.sleep(0.5)


async def periodically_check_emails(interval):
    while True:
        await process_emails()
        await asyncio.sleep(interval)

def main():
    asyncio.run(periodically_check_emails(300))


if __name__ == "__main__":
    main()
