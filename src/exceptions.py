class DomainError(Exception):
    pass


class UserAlreadyExistsError(DomainError):
    def __init__(self, field:str):
        self.field = field
        super().__init__(f"User with this {field} already exists")


class DataBaseError(DomainError):
    def __init__(self, table_name:str):
        self.table_name = table_name
        super().__init__(f"Error with creating new {table_name}")


class TokenCreatingError(DomainError):
    def __init__(self, type:str):
        self.token_type=type
        super().__init__(f"Error with creating {type} token")