"""
Alembic 环境配置
"""

import asyncio
import os
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from app.config import settings
from app.models.base import Base

# Alembic Config 对象，提供对 .ini 文件值的访问
config = context.config

# 解释 config 文件中的日志配置
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 添加你的模型的 MetaData 对象用于 'autogenerate' 支持
target_metadata = Base.metadata

# 其他从 config 中需要的值，由 env.py 定义，
# 可以在 alembic 命令行中的 `-x` 参数中使用。


def get_url():
    """获取数据库连接 URL"""
    return settings.DATABASE_URL


def run_migrations_offline() -> None:
    """在'离线'模式下运行迁移。

    这将配置上下文只使用 URL
    而不是 Engine，尽管 Engine 也是可以接受的。
    通过跳过 Engine 创建，我们甚至不需要 DBAPI 来可用。

    调用 context.execute() 来输出生成的 SQL 脚本。
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """运行迁移的主要函数"""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """异步运行迁移"""
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()
    
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """在'在线'模式下运行迁移。

    在这种情况下，我们需要创建一个 Engine
    并将连接与上下文关联。
    """
    # 处理异步数据库引擎
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()