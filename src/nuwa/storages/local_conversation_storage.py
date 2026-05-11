"""本地文件对话存储，将对话信息存储到本地 msgpack 文件。

本模块提供 LocalConversationStorage 类，实现 ConversationStorage 抽象接口。
每个 Session 存储为一个独立的 .msgpack 文件，支持消息的持久化、检索和清除功能。
遵循整体架构设计，提供零外部依赖的消息存储后端。
"""

import os
import re
import json
import asyncio
import logging
import msgpack

from typing import List, Dict
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel, Field

from .base import ConversationStorage, Session

logger = logging.getLogger(__name__)

# 文件名中不安全字符的正则模式
_UNSAFE_PATH_CHARS_RE = re.compile(r'[/\\:*?"<>|]')


def _sanitize_filename(session_id: str) -> str:
    """将 session_id 中的路径不安全字符替换为下划线。

    Args:
        session_id: 原始会话标识符。

    Returns:
        安全的文件名片段。
    """
    return _UNSAFE_PATH_CHARS_RE.sub("_", session_id)


class _SessionData(BaseModel):
    """单个会话的内部数据模型。

    Attributes:
        session_id: 会话标识符。
        title: 会话标题。
        description: 会话描述，默认为空字符串。
        messages: 消息列表，默认为空列表。
    """

    session_id: str
    title: str
    description: str = ""
    messages: List[ChatCompletionMessageParam] = Field(default_factory=list)


class LocalConversationStorage(ConversationStorage):
    """基于本地文件的对话存储后端。

    实现 ConversationStorage 抽象接口，将每个 Session 的消息存储为独立的
    .msgpack 文件。采用批量读写模式：initialize() 时从目录加载全部 session，
    close() 时将所有 session 写回磁盘。

    Attributes:
        _storage_dir: 存储目录路径。
        _store: 内存中的 session 数据字典，key 为 session_id。
        _lock: 协程锁，保证并发安全。
    """

    def __init__(self, storage_dir: str = "./data/conversations/"):
        """初始化本地对话存储。

        Args:
            storage_dir: 对话文件存储目录路径，默认为 "./data/conversations/"。
        """
        super().__init__()
        self._storage_dir = storage_dir
        self._store: Dict[str, _SessionData] = {}
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # 生命周期方法
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """从存储目录加载所有 .msgpack 文件到内存。

        自动创建不存在的目录。扫描目录下所有 .msgpack 文件，
        msgpack 解码后填充 _store。解码失败的文件仅记录警告，不中断加载。
        """
        await super().initialize()
        os.makedirs(self._storage_dir, exist_ok=True)

        for entry in os.scandir(self._storage_dir):
            if not entry.is_file() or not entry.name.endswith(".msgpack"):
                continue
            try:
                with open(entry.path, "rb") as f:
                    data = msgpack.unpack(f, raw=False)
                session_data = _SessionData(**data)
                self._store[session_data.session_id] = session_data
                logger.debug("Loaded session %s from %s", session_data.session_id, entry.path)
            except Exception as e:
                logger.warning("Failed to load session file %s: %s", entry.path, e)

    async def close(self) -> None:
        """将所有内存中的 session 写回磁盘并清空内存。

        使用协程锁保护，遍历 _store 中所有 session，
        msgpack 编码后写入对应的 .msgpack 文件，然后清空 _store。
        """
        async with self._lock:
            for session_id, session_data in self._store.items():
                filepath = self._get_filepath(session_id)
                try:
                    with open(filepath, "wb") as f:
                        msgpack.pack(session_data.model_dump(warnings=False), f)
                    logger.debug("Wrote session %s to %s", session_id, filepath)
                except Exception as e:
                    logger.error("Failed to write session %s to %s: %s", session_id, filepath, e)
                    raise
            self._store.clear()

    # ------------------------------------------------------------------
    # ConversationStorage 接口实现
    # ------------------------------------------------------------------

    async def get_messages(
        self, session: Session, user_input: str = ""
    ) -> List[ChatCompletionMessageParam]:
        """获取指定 session 的全部消息。

        忽略 user_input 参数（本地文件存储不需要语义检索），
        直接返回该 session 的消息列表副本。

        Args:
            session: 会话对象，通过 session_id 定位。
            user_input: 用户输入（忽略，保留以符合接口签名）。

        Returns:
            消息列表副本；如果 session 不存在则返回空列表。
        """
        async with self._lock:
            session_data = self._store.get(session.session_id)
            if session_data is None:
                return []
            # 返回副本，防止外部修改影响内部状态
            return list(session_data.messages)

    async def save_messages(
        self, session: Session, messages: List[ChatCompletionMessageParam],
    ):
        """追加消息到指定 session（带去重检查）。

        如果 session 不存在则新建。对每条新消息生成 JSON 指纹，
        与已有消息指纹集合对比，仅追加未出现过的消息。
        session 的 title 和 description 会同步更新。

        Args:
            session: 会话对象。
            messages: 要追加的消息列表。
        """
        if not messages:
            return

        async with self._lock:
            if session.session_id not in self._store:
                self._store[session.session_id] = _SessionData(
                    session_id=session.session_id,
                    title=session.title,
                    description=session.description,
                )

            session_data = self._store[session.session_id]
            # 同步更新 session 元信息
            session_data.title = session.title
            session_data.description = session.description

            # 去重：基于 JSON 指纹
            existing_fps = {
                json.dumps(msg, sort_keys=True, ensure_ascii=False)
                for msg in session_data.messages
            }

            for msg in messages:
                fp = json.dumps(msg, sort_keys=True, ensure_ascii=False)
                if fp not in existing_fps:
                    session_data.messages.append(msg)
                    existing_fps.add(fp)

    async def clear_messages(self, session_id: str):
        """清除指定 session 的全部消息记录。

        从内存中删除 session 并移除对应的 .msgpack 文件。
        如果 session 或文件不存在，不报错（幂等操作）。

        Args:
            session_id: 要清除的会话标识符。
        """
        async with self._lock:
            if session_id in self._store:
                del self._store[session_id]

            filepath = self._get_filepath(session_id)
            try:
                os.remove(filepath)
                logger.debug("Removed session file %s", filepath)
            except FileNotFoundError:
                pass

    # ------------------------------------------------------------------
    # 内部工具方法
    # ------------------------------------------------------------------

    def _get_filepath(self, session_id: str) -> str:
        """获取 session 对应的完整文件路径。

        Args:
            session_id: 会话标识符。

        Returns:
            拼接后的文件路径，格式为 {storage_dir}/{sanitized_session_id}.msgpack。
        """
        return os.path.join(
            self._storage_dir,
            _sanitize_filename(session_id) + ".msgpack",
        )