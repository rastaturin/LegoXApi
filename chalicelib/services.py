from chalicelib.exceptions import NotFoundException, AuthFailed, TokenExpired


class UserService:
    def __init__(self, auth_repo, user_repo):
        self.auth_repo = auth_repo
        self.user_repo = user_repo

    def login(self, email):
        try:
            user = self.user_repo.get_user(email)
        except NotFoundException as e:
            raise AuthFailed(str(e))

        return self.auth_repo.add_code(email)

    def auth_user(self, code):
        try:
            email = self.auth_repo.get_email(code)
        except NotFoundException:
            raise TokenExpired('Token expired')
        return self.user_repo.get_user(email)


