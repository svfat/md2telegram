#!/usr/bin/env python3
import re
import logging
import sys
from typing import List, Dict

from telegram import Update
from telegram.ext import (Application,
                          ApplicationBuilder,
                          CommandHandler,
                          ContextTypes,
                          CallbackQueryHandler)
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

from config import (TELEGRAM_BOT_TOKEN,
                    PAGES_DIR,
                    MENUS_DIR,
                    PORT,
                    HEROKU_APP_NAME)

logger = logging.getLogger(__name__)
stdout_handler = logging.StreamHandler(sys.stdout)
handlers = [stdout_handler]

logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',
    handlers=handlers
)


class PageRenderer:
    metadata_label = '[_metadata_:'

    def __init__(self, page_name: str):
        self.raw_page = self._load_file(PAGES_DIR / page_name)
        self.metadata = self.extract_metadata(self.raw_page)
        self.inline_keyboard_markup = self.create_inline_keyboard_markup(
            self.metadata.get('inline_buttons'))
        self.page = self.clean_page(self.raw_page)

    def extract_metadata(self, raw_page) -> Dict[str, str]:
        metadata = [
            line for line in raw_page if line.startswith(self.metadata_label)
        ]
        pattern = r"^\[_metadata_:(.*)\]\:\-.*[\",\'](.*)[\",\']$"
        result = {k: v for k, v in
                  [re.search(pattern, line).groups() for line in metadata]}
        return result

    def create_inline_keyboard_markup(self, filename) -> InlineKeyboardMarkup:
        if filename:
            lines = self._load_file(MENUS_DIR / filename)
            pattern = r"^\[(.*)\]\((.*)\)$"
            kb_data = [
                re.search(pattern, line).groups() for line in lines
            ]
            inline_keyboard = [
                [
                    InlineKeyboardButton(text=text, callback_data=callback_data)
                ] for text, callback_data in kb_data
            ]

            return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

    def clean_page(self, raw_page: List[str]) -> str:
        return ''.join(
            line for line in raw_page if not line.startswith(self.metadata_label)
        )

    def _load_file(self, path):
        with open(path, 'r') as f:
            return f.readlines()

    def _get_template_vars(self, update: Update,
                           context: ContextTypes.DEFAULT_TYPE) -> dict:
        return {
            'first_name': update.effective_user.first_name,
        }

    async def send_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                         image: str):
        kwargs = {
            "chat_id": update.effective_chat.id,
            "parse_mode": "Markdown",
            "photo": image,
            "caption": self.page.format(**self._get_template_vars(update, context))
        }
        if self.inline_keyboard_markup:
            kwargs["reply_markup"] = self.inline_keyboard_markup
        await context.bot.send_photo(
            **kwargs
        )

    async def send_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        kwargs = {
            "chat_id": update.effective_chat.id,
            "parse_mode": "Markdown",
            "text": self.page.format(**self._get_template_vars(update, context))
        }
        if self.inline_keyboard_markup:
            kwargs["reply_markup"] = self.inline_keyboard_markup
        await context.bot.send_message(
            **kwargs
        )

    async def show(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        image = self.metadata.get('image')
        if image:
            await self.send_image(update, context, image)
        else:
            await self.send_text(update, context)


class QueryProcessor:
    @staticmethod
    def parse_command(data):
        spl = data.split(':')
        return {'command': spl[0], 'args': spl[1]}

    @staticmethod
    async def show_page(page_name: str, update: Update,
                        context: ContextTypes.DEFAULT_TYPE):
        page_renderer = PageRenderer(page_name)
        await page_renderer.show(update, context)

    @property
    def handlers(self):
        return {
            '/page': self.show_page,
        }

    async def callback_query_processing(self: "QueryProcessor", update: Update,
                                        context: ContextTypes.DEFAULT_TYPE) -> None:
        """Parses the CallbackQuery and updates the message text."""
        query = update.callback_query
        await query.answer()
        parsed_command = self.parse_command(query.data)
        handler = self.handlers[parsed_command['command']]
        await handler(parsed_command['args'], update=update, context=context)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await PageRenderer("start.md").show(update, context)


def init_app(app: Application):
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(QueryProcessor().callback_query_processing))
    return app


if __name__ == '__main__':

    app: Application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    init_app(app)
    if HEROKU_APP_NAME:
        logger.info(f"Detected Heroku environment, starting bot on port {PORT}")
        webhook_url = f"https://{HEROKU_APP_NAME}.herokuapp.com/{TELEGRAM_BOT_TOKEN}"
        app.run_webhook(listen="0.0.0.0",
                              port=PORT,
                              url_path=TELEGRAM_BOT_TOKEN,
                              webhook_url=webhook_url)
        app.bot.set_webhook(webhook_url)
    else:
        logger.info("Detected local environment, starting polling")
        app.run_polling()
