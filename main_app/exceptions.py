class CompositePrimaryKeyError(Exception):
    def __init__(self, msg: str = "Composite primary keys are not supported"):
        self.msg = msg

    def __str__(self) -> str:
        return self.msg


class ColumnDoesNotExistError(Exception):
    def __init__(self, column_name: str):
        self.msg = f"Column '{column_name}' does not exist."

    def __str__(self) -> str:
        return self.msg
