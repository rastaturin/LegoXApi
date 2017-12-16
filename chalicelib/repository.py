import datetime
import time
import secrets

from chalicelib.dynamodb import DynamoDb
from chalicelib.exceptions import NotFoundException


class AbstractRepository:
    PREFIX = "LEGOX"

    def __init__(self):
        table_name = self.PREFIX + '_' + self.get_table_name()
        self.db = DynamoDb(table_name)

    def get_table_name(self):
        raise NotImplementedError

    def insert(self, item, uniq_attr=None):

        if 'createdAt' not in item:
            item['createdAt'] = str(datetime.datetime.now())
        item['updatedAt'] = str(datetime.datetime.now())
        return self.db.insert_item(item, uniq_attr)

    def get(self, query):
        return self.db.get_item(query)

    def remove(self, query):
        self.db.del_item(query)

    def query(self, key, value, index=None, limit=0, key_sort=None, value_sort=None):
        result = self.db.query(key, value, index, limit, key_sort, value_sort)
        if result['Count'] == 0:
            return []
        return result['Items']

    def scan(self):
        result = self.db.scan()
        if result['Count'] == 0:
            return []
        return result['Items']

    def get_table(self):
        return self.db.table


class ThemesRepository(AbstractRepository):
    def get_table_name(self):
        return 'themes'


class MysetsRepository(AbstractRepository):
    def get_table_name(self):
        return 'mysets'


class SetsRepository(AbstractRepository):
    def get_table_name(self):
        return 'sets'

    def search_year(self, year, limit):
        return self.query('year', year, 'year-theme-index', limit)

    def search_theme(self, theme, limit):
        return self.query('theme', theme, 'theme-index', limit)

    def search(self, year, theme, limit):
        return self.query('year', year, 'year-theme-index', limit, 'theme', theme)


class UserRepository(AbstractRepository):
    def get_table_name(self):
        return 'users'

    def reg_user(self, email, password):
        return self.insert({'email': email, 'password': password, 'nickname': 'User', 'logo': 'face_2.png'})

    def update_profile(self, email, params):
        return self.db.update_item(
            {'email': email},
            params
        )


class AuthcodesRepository(AbstractRepository):
    def get_table_name(self):
        return 'authcodes'

    def add_code(self, email):
        code = secrets.token_hex(16)
        expires = time.time() + datetime.timedelta(days=7).total_seconds()
        self.insert({'code': code, 'expires': int(expires), 'email': email})
        return code

    def get_email(self, code):
        result = self.query('code', code)
        if len(result) == 0:
            raise NotFoundException('Code not found')
        return result[0].get('email')

