import configparser


class Config:

    config_obj = None

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
        return bot_token, chat_id, api_url
