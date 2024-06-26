import configparser
import logging


class Config:
    config_obj = None
    logger_level = 'INFO'

    def load_config(self) -> configparser.ConfigParser:
        config = configparser.ConfigParser()
        config.read('config.ini')
        self.config_obj = config
        return config

    def write_to_config(self, value: str):
        config = self.load_config()
        config['Telegram']['message_id'] = str(value)
        with open('config.ini', 'w') as configfile:
            config.write(configfile)

    def read_from_config(self) -> tuple[bool, int]:
        config = self.load_config()
        message_id = config['Telegram'].getint('message_id')
        if message_id == 0:
            return False, 0
        return True, message_id

    def get_start_values(self) -> tuple[str, str, str]:
        config = self.load_config()
        bot_token = config['Telegram']['bot_token']
        chat_id = config['Telegram']['chat_id']
        api_url = config['Web']['url_api']
        self.parse_logger_sec()
        return bot_token, chat_id, api_url

    def parse_logger_sec(self):
        config = self.config_obj
        is_logger_sec = config.has_section('Logger')
        if is_logger_sec:
            is_logger_opt = config.has_option('Logger', 'level')
            if is_logger_opt:
                self.logger_level = config.get('Logger', 'level')


config_data = Config()
