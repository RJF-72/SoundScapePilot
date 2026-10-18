"""PR wire stub module."""


class PRWire:
    def __init__(self):
        self.outlets = []

    def dispatch(self, release):
        return {"status": "logged", "reason": "SMTP credentials not configured"}

