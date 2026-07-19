"""自定义异常类"""


class DBError(Exception):
    """数据库基础异常"""
    pass


class DBConnectionError(DBError):
    """数据库连接异常"""
    pass


class DBQueryError(DBError):
    """数据库查询异常"""
    pass


class DBMigrationError(DBError):
    """数据库迁移异常"""
    pass
