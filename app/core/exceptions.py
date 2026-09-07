class AppError(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class UnauthorizedError(AppError):
    def __init__(self, message: str = "未认证或登录已过期"):
        super().__init__(401, message)


class ForbiddenError(AppError):
    def __init__(self, message: str = "无权限访问"):
        super().__init__(403, message)


class NotFoundError(AppError):
    def __init__(self, message: str = "资源不存在"):
        super().__init__(404, message)


class BadRequestError(AppError):
    def __init__(self, message: str = "请求参数错误"):
        super().__init__(400, message)


class ConflictError(AppError):
    def __init__(self, message: str = "资源冲突"):
        super().__init__(409, message)
