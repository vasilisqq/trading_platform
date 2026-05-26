class DomainError(Exception):
    pass


class UserAlreadyExistsError(DomainError):
    def __init__(self, field:str):
        self.field = field
        super().__init__(f"User with this {field} already exists")