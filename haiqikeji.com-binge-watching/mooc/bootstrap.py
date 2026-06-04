import threading
from .user import User

class Bootstrap:
    def __init__(self, config):
        self.config = config
        self.users = []
        self.threads = []
        self.init_users()

    def init_users(self):
        for user_config in self.config['users']:
            user = User(
                base_url=user_config['base_url'],
                school_id=user_config['school_id'],
                username=user_config['username'],
                password=user_config['password']
            )
            self.users.append(user)

    def start(self):
        limit = self.config['global']['limit']
        for user in self.users[:limit]:
            thread = threading.Thread(target=user.run)
            thread.start()
            self.threads.append(thread)

    def stop(self):
        for user in self.users:
            user.stop()
        for thread in self.threads:
            thread.join() 