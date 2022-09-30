class ArgumentError(Exception):
    def __init__(self, message, **kwargs):
        self.message = message
        super().__init__(self.message)


class ChecksumVerificationError(Exception):
    def __init__(self, message, **kwargs):
        self.message = message
        super().__init__(self.message)


class ConfigError(Exception):
    def __init__(self, message, **kwargs):
        self.message = message
        super().__init__(self.message)


class DataFormatError(Exception):
    def __init__(self, message, **kwargs):
        self.message = message
        super().__init__(self.message)
