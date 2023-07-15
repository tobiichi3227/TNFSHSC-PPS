"""
    @author: tobiichi3227
    @day: 2023/7/7
"""


class Error(object):
    pass


class _Success(Error):
    def __str__(self):
        return 'S'


Success = _Success()


class _ExistError(Error):

    def __str__(self):
        return 'Eexist'


ExistError = _ExistError()


class _NotExistError(Error):
    def __str__(self):
        return 'Enoext'


NotExistError = _NotExistError()


class _MemberNotFoundError(Error):
    def __repr__(self):
        return 'Emembernoext'


MemberNotFoundError = _MemberNotFoundError()


class _WrongPasswordError(Error):
    def __str__(self):
        return 'Ewrongpw'


WrongPasswordError = _WrongPasswordError()


class _MemberLockedError(Error):
    def __str__(self):
        return 'Elocked'


MemberLockedError = _MemberNotFoundError()


class _WrongParamError(Error):
    def __str__(self):
        return 'Eparam'


WrongParamError = _WrongParamError()


class _CanNotAccessError(Error):
    def __str__(self):
        return 'Eacces'


CanNotAccessError = _CanNotAccessError()


class _UnknownError(Error):
    def __str__(self):
        return 'Eunk'


UnknownError = _UnknownError
