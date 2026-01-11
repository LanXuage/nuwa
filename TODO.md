# 添加清空历史聊天记录功能

## 步骤
1. [ ] 修改 `src/nuwa/base.py`：在 MessagesManager 类中添加抽象方法 `clear_messages(session_id: str)`
2. [ ] 修改 `src/nuwa/qdrant.py`：在 QdrantMessagesManager 类中实现 `clear_messages` 方法
3. [ ] 可选：在 `src/nuwa/chat.py` 的 ChatLLM 类中添加公共方法 `clear_chat_history()`
4. [ ] 验证更改，确保没有语法错误

## 依赖文件
- src/nuwa/base.py
- src/nuwa/qdrant.py
- src/nuwa/chat.py (可选)

## 完成状态
- [x] 修改 `src/nuwa/base.py`：在 MessagesManager 类中添加抽象方法 `clear_messages(session_id: str)`
- [x] 修改 `src/nuwa/qdrant.py`：在 QdrantMessagesManager 类中实现 `clear_messages` 方法
- [x] 可选：在 `src/nuwa/chat.py` 的 ChatLLM 类中添加公共方法 `clear_chat_history()`
- [x] 验证更改，确保没有语法错误
