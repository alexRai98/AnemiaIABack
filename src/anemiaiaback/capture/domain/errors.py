class DomainError(Exception):
    """Base error for expected domain/application failures."""


class InvalidImageError(DomainError):
    pass


class UploadTooLargeError(DomainError):
    pass


class CaptureValidationError(DomainError):
    pass


class EyeNotFoundError(DomainError):
    pass


class IrisNotFoundError(DomainError):
    pass


class InvalidConjunctivaCropError(DomainError):
    pass


class ConjunctivaContourNotFoundError(DomainError):
    pass


class InfrastructureError(Exception):
    """Base error for failures outside the application core."""


class ConfigurationError(InfrastructureError):
    pass


class StorageError(InfrastructureError):
    pass


class PersistenceError(InfrastructureError):
    pass
