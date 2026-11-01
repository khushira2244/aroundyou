class DomainError(Exception):
    def __init__(self, code, message, status=409):
        self.code, self.message, self.status = code, message, status
        super().__init__(code)

def missing():
    raise DomainError("not_found", "Record not found or inaccessible", 404)
