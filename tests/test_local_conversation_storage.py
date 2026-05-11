"""LocalConversationStorage 单元测试。

测试覆盖：基本 CRUD、追加去重、生命周期、边界情况、并发安全。
"""

import asyncio
import os
import tempfile

import pytest

from openai.types.chat import ChatCompletionMessageParam
from src.nuwa.storages.base import Session
from src.nuwa.storages.local_conversation_storage import (
    LocalConversationStorage,
    _sanitize_filename,
    _SessionData,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_storage_dir():
    """创建临时存储目录并在测试后自动清理。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_session():
    """提供标准测试 Session。"""
    return Session(session_id="test-session", title="Test Title", description="Test Description")


@pytest.fixture
def sample_messages() -> list[ChatCompletionMessageParam]:
    """提供一组标准测试消息。"""
    return [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]


# ---------------------------------------------------------------------------
# 工具函数测试
# ---------------------------------------------------------------------------

def test_sanitize_filename():
    """验证路径不安全字符被正确替换。"""
    assert _sanitize_filename("simple") == "simple"
    assert _sanitize_filename("test/session:id") == "test_session_id"
    assert _sanitize_filename('foo\\bar*baz?') == "foo_bar_baz_"
    assert _sanitize_filename('a"b<c>d|e') == "a_b_c_d_e"


def test_session_data_model():
    """验证内部数据模型的创建和序列化。"""
    sd = _SessionData(session_id="sid", title="T", description="D")
    assert sd.session_id == "sid"
    assert sd.title == "T"
    assert sd.description == "D"
    assert sd.messages == []

    dumped = sd.model_dump()
    assert dumped["session_id"] == "sid"
    assert dumped["messages"] == []


# ---------------------------------------------------------------------------
# 初始化 / 生命周期测试
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_initialization(temp_storage_dir):
    """验证初始化后目录被创建，_store 为空。"""
    async with LocalConversationStorage(storage_dir=temp_storage_dir) as store:
        assert os.path.isdir(temp_storage_dir)
        assert store._store == {}


@pytest.mark.asyncio
async def test_initialize_loads_existing_file(temp_storage_dir, sample_session, sample_messages):
    """验证 initialize 后能从已有的 .msgpack 文件加载数据。"""
    # 第一个实例：保存并关闭
    async with LocalConversationStorage(storage_dir=temp_storage_dir) as store1:
        await store1.save_messages(sample_session, sample_messages)

    # 第二个实例：加载并验证
    async with LocalConversationStorage(storage_dir=temp_storage_dir) as store2:
        msgs = await store2.get_messages(sample_session)
        assert msgs == sample_messages


@pytest.mark.asyncio
async def test_close_writes_to_disk(temp_storage_dir, sample_session, sample_messages):
    """验证 close() 后文件正确写入磁盘。"""
    async with LocalConversationStorage(storage_dir=temp_storage_dir) as store:
        await store.save_messages(sample_session, sample_messages)

    # 验证文件已生成
    files = [f for f in os.listdir(temp_storage_dir) if f.endswith(".msgpack")]
    assert len(files) == 1
    assert files[0] == "test-session.msgpack"


# ---------------------------------------------------------------------------
# get_messages 测试
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_messages_empty_session(temp_storage_dir, sample_session):
    """验证不存在的 session 返回空列表。"""
    async with LocalConversationStorage(storage_dir=temp_storage_dir) as store:
        msgs = await store.get_messages(sample_session)
        assert msgs == []


@pytest.mark.asyncio
async def test_save_and_get_messages(temp_storage_dir, sample_session, sample_messages):
    """验证保存后能正确读取消息。"""
    async with LocalConversationStorage(storage_dir=temp_storage_dir) as store:
        await store.save_messages(sample_session, sample_messages)
        msgs = await store.get_messages(sample_session)
        assert msgs == sample_messages


@pytest.mark.asyncio
async def test_get_messages_ignores_user_input(temp_storage_dir, sample_session, sample_messages):
    """验证 user_input 参数不影响返回结果。"""
    async with LocalConversationStorage(storage_dir=temp_storage_dir) as store:
        await store.save_messages(sample_session, sample_messages)

        msgs1 = await store.get_messages(sample_session, user_input="")
        msgs2 = await store.get_messages(sample_session, user_input="some random text")
        msgs3 = await store.get_messages(sample_session, user_input="Hello")

        assert msgs1 == sample_messages
        assert msgs2 == sample_messages
        assert msgs3 == sample_messages


@pytest.mark.asyncio
async def test_get_messages_returns_copy(temp_storage_dir, sample_session, sample_messages):
    """验证返回的是副本，修改不影响内部数据。"""
    async with LocalConversationStorage(storage_dir=temp_storage_dir) as store:
        await store.save_messages(sample_session, sample_messages)

        msgs = await store.get_messages(sample_session)
        msgs.append({"role": "user", "content": "injected"})

        msgs2 = await store.get_messages(sample_session)
        assert msgs2 == sample_messages
        assert len(msgs2) == len(sample_messages)


@pytest.mark.asyncio
async def test_session_not_found_get_messages(temp_storage_dir):
    """验证不存在的 session 调用 get_messages 返回空列表。"""
    async with LocalConversationStorage(storage_dir=temp_storage_dir) as store:
        fake_session = Session(session_id="nonexistent", title="N/A")
        msgs = await store.get_messages(fake_session)
        assert msgs == []


# ---------------------------------------------------------------------------
# save_messages 测试
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_save_messages_append(temp_storage_dir, sample_session, sample_messages):
    """验证追加模式，两次保存后消息总数正确。"""
    async with LocalConversationStorage(storage_dir=temp_storage_dir) as store:
        await store.save_messages(sample_session, sample_messages)
        new_message: ChatCompletionMessageParam = {"role": "user", "content": "Another"}
        await store.save_messages(sample_session, [new_message])

        msgs = await store.get_messages(sample_session)
        assert len(msgs) == 3
        assert msgs[0] == sample_messages[0]
        assert msgs[1] == sample_messages[1]
        assert msgs[2] == new_message


@pytest.mark.asyncio
async def test_save_messages_dedup(temp_storage_dir, sample_session, sample_messages):
    """验证重复保存相同消息不会导致重复追加。"""
    async with LocalConversationStorage(storage_dir=temp_storage_dir) as store:
        await store.save_messages(sample_session, sample_messages)
        # 重复保存相同的消息
        await store.save_messages(sample_session, sample_messages)

        msgs = await store.get_messages(sample_session)
        assert len(msgs) == 2


@pytest.mark.asyncio
async def test_save_messages_partial_dedup(temp_storage_dir, sample_session, sample_messages):
    """验证部分去重：只去重重复的消息，新消息仍然追加。"""
    async with LocalConversationStorage(storage_dir=temp_storage_dir) as store:
        await store.save_messages(sample_session, sample_messages)

        new_msg: ChatCompletionMessageParam = {"role": "user", "content": "New"}
        mixed = [sample_messages[0], new_msg]  # 第一条约已存在，第二条是新
        await store.save_messages(sample_session, mixed)

        msgs = await store.get_messages(sample_session)
        assert len(msgs) == 3
        assert msgs[2] == new_msg


@pytest.mark.asyncio
async def test_save_messages_new_session(temp_storage_dir):
    """验证 session 不存在时自动创建并保存。"""
    async with LocalConversationStorage(storage_dir=temp_storage_dir) as store:
        session = Session(session_id="new-session", title="New", description="Desc")
        msg: ChatCompletionMessageParam = {"role": "user", "content": "First"}
        await store.save_messages(session, [msg])

        msgs = await store.get_messages(session)
        assert msgs == [msg]

        # 验证 session 元信息已保存
        assert store._store["new-session"].title == "New"
        assert store._store["new-session"].description == "Desc"


@pytest.mark.asyncio
async def test_save_messages_updates_metadata(temp_storage_dir, sample_session, sample_messages):
    """验证 save_messages 会同步更新 session 的 title 和 description。"""
    async with LocalConversationStorage(storage_dir=temp_storage_dir) as store:
        await store.save_messages(sample_session, sample_messages)

        updated_session = Session(
            session_id=sample_session.session_id,
            title="Updated Title",
            description="Updated Desc",
        )
        new_msg: ChatCompletionMessageParam = {"role": "user", "content": "More"}
        await store.save_messages(updated_session, [new_msg])

        stored = store._store[sample_session.session_id]
        assert stored.title == "Updated Title"
        assert stored.description == "Updated Desc"


@pytest.mark.asyncio
async def test_save_empty_messages(temp_storage_dir, sample_session):
    """验证保存空列表不崩溃，不影响已有数据。"""
    async with LocalConversationStorage(storage_dir=temp_storage_dir) as store:
        await store.save_messages(sample_session, [])
        msgs = await store.get_messages(sample_session)
        assert msgs == []


# ---------------------------------------------------------------------------
# clear_messages 测试
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_clear_messages(temp_storage_dir, sample_session, sample_messages):
    """验证清空 session 后消息为空。"""
    async with LocalConversationStorage(storage_dir=temp_storage_dir) as store:
        await store.save_messages(sample_session, sample_messages)
        await store.clear_messages(sample_session.session_id)

        msgs = await store.get_messages(sample_session)
        assert msgs == []


@pytest.mark.asyncio
async def test_clear_messages_file_removed(temp_storage_dir, sample_session, sample_messages):
    """验证 clear 后对应的 .msgpack 文件被删除。"""
    # 保存并关闭
    async with LocalConversationStorage(storage_dir=temp_storage_dir) as store:
        await store.save_messages(sample_session, sample_messages)

    # 重新加载，文件应存在
    async with LocalConversationStorage(storage_dir=temp_storage_dir) as store2:
        await store2.clear_messages(sample_session.session_id)

        files = [f for f in os.listdir(temp_storage_dir) if f.endswith(".msgpack")]
        assert len(files) == 0


@pytest.mark.asyncio
async def test_session_not_found_clear(temp_storage_dir):
    """验证清空不存在的 session 不报错。"""
    async with LocalConversationStorage(storage_dir=temp_storage_dir) as store:
        await store.clear_messages("nonexistent")
        # 不应抛出异常


# ---------------------------------------------------------------------------
# 综合 / 并发测试
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_lifecycle_full_roundtrip(temp_storage_dir, sample_session, sample_messages):
    """验证完整的生命周期：init → save → close → re-init → get → 数据一致。"""
    # 第一轮
    async with LocalConversationStorage(storage_dir=temp_storage_dir) as store1:
        await store1.save_messages(sample_session, sample_messages)

    # 第二轮
    async with LocalConversationStorage(storage_dir=temp_storage_dir) as store2:
        msgs = await store2.get_messages(sample_session)
        assert msgs == sample_messages

        # 追加
        new_msg: ChatCompletionMessageParam = {"role": "user", "content": "Round 2"}
        await store2.save_messages(sample_session, [new_msg])

    # 第三轮
    async with LocalConversationStorage(storage_dir=temp_storage_dir) as store3:
        msgs = await store3.get_messages(sample_session)
        assert len(msgs) == 3
        assert msgs[2] == new_msg


@pytest.mark.asyncio
async def test_concurrent_save_messages(temp_storage_dir, sample_session):
    """验证多协程同时 save 不会导致数据丢失。"""
    async with LocalConversationStorage(storage_dir=temp_storage_dir) as store:
        async def save_batch(prefix: str, count: int):
            for i in range(count):
                msg: ChatCompletionMessageParam = {
                    "role": "user",
                    "content": f"{prefix}-msg-{i}",
                }
                await store.save_messages(sample_session, [msg])

        # 两个协程同时写入
        await asyncio.gather(
            save_batch("A", 20),
            save_batch("B", 20),
        )

        msgs = await store.get_messages(sample_session)
        # 每条消息应该恰好出现一次
        assert len(msgs) == 40, f"Expected 40 messages, got {len(msgs)}"


@pytest.mark.asyncio
async def test_multiple_sessions_independent(temp_storage_dir):
    """验证多个 session 之间数据完全独立。"""
    async with LocalConversationStorage(storage_dir=temp_storage_dir) as store:
        s1 = Session(session_id="s1", title="Session 1")
        s2 = Session(session_id="s2", title="Session 2")
        msg1: ChatCompletionMessageParam = {"role": "user", "content": "Hello from s1"}
        msg2: ChatCompletionMessageParam = {"role": "user", "content": "Hello from s2"}

        await store.save_messages(s1, [msg1])
        await store.save_messages(s2, [msg2])

        assert await store.get_messages(s1) == [msg1]
        assert await store.get_messages(s2) == [msg2]

        # 清空 s1 不影响 s2
        await store.clear_messages("s1")
        assert await store.get_messages(s1) == []
        assert await store.get_messages(s2) == [msg2]


@pytest.mark.asyncio
async def test_sanitized_filename_on_disk(temp_storage_dir):
    """验证包含特殊字符的 session_id 生成的文件名被正确 sanitize。"""
    async with LocalConversationStorage(storage_dir=temp_storage_dir) as store:
        session = Session(session_id="a/b:c*?d", title="T")
        msg: ChatCompletionMessageParam = {"role": "user", "content": "test"}
        await store.save_messages(session, [msg])

    files = os.listdir(temp_storage_dir)
    assert "a_b_c__d.msgpack" in files
    assert "a/b:c*?d.msgpack" not in files


@pytest.mark.asyncio
async def test_async_context_manager(temp_storage_dir, sample_session, sample_messages):
    """验证支持 async with 上下文管理器。"""
    async with LocalConversationStorage(storage_dir=temp_storage_dir) as store:
        await store.save_messages(sample_session, sample_messages)
        msgs = await store.get_messages(sample_session)
        assert msgs == sample_messages

    # 上下文退出后文件应已写入
    files = os.listdir(temp_storage_dir)
    assert any(f.endswith(".msgpack") for f in files)