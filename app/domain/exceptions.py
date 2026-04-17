class ResumeAppError(Exception):
    """Base exception for all application errors."""
    pass

class UnsupportedFileTypeError(ResumeAppError):
    pass

class FileSizeExceededError(ResumeAppError):
    pass

class FileSignatureMismatchError(ResumeAppError):
    pass

class DocumentClassificationError(ResumeAppError):
    pass

class DocumentParsingError(ResumeAppError):
    pass
