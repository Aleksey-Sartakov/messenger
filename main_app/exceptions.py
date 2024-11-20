class CompositePrimaryKeyError(Exception):
    def __init__(self, msg: str | None = None):
        if msg:
            self.msg = msg
        else:
            self.msg = "Composite primary keys are not supported"

    def __str__(self) -> str:
        return self.msg


class ColumnDoesNotExistError(Exception):
    def __init__(self, column_name: str):
        self.msg = f"Column '{column_name}' does not exist."

    def __str__(self) -> str:
        return self.msg
