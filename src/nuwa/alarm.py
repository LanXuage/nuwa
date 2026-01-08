import asyncio
import logging
from datetime import datetime
from typing import Literal, Callable, Optional, Dict, Any
from dataclasses import dataclass

from .tool import Tool, ToolEntity, ToolObjectParameter, ToolParameter
from .re_act import ReActAgent

logger = logging.getLogger(__name__)


@dataclass
class AlarmTask:
    """闹钟任务"""
    alarm_id: str
    time: datetime
    remindee: Literal["oneself", "user"]
    reminder: str
    agent: Optional[ReActAgent] = None
    callback: Optional[Callable[[str], Any]] = None
    task: Optional[asyncio.Task] = None


class AlarmManager:
    def __init__(self):
        self.tasks: Dict[str, AlarmTask] = {}
        self._next_id = 1
        self._lock = asyncio.Lock()

    def _generate_id(self) -> str:
        """生成唯一的闹钟ID"""
        alarm_id = f"alarm_{self._next_id}"
        self._next_id += 1
        return alarm_id

    async def set_alarm_for_oneself(
        self, 
        time: datetime, 
        reminder: str, 
        agent: ReActAgent,
        callback: Optional[Callable[[str], Any]] = None
    ) -> str:
        """
        为agent自己设置闹钟
        
        Args:
            time: 提醒时间
            reminder: 提醒信息
            agent: 相关的ReActAgent实例
            callback: 唤醒时的回调函数，接收提醒信息作为参数
            
        Returns:
            闹钟ID
        """
        async with self._lock:
            alarm_id = self._generate_id()
            task = AlarmTask(
                alarm_id=alarm_id,
                time=time,
                remindee="oneself",
                reminder=reminder,
                agent=agent,
                callback=callback
            )
            
            # 计算延迟时间
            now = datetime.now()
            if time <= now:
                logger.warning(f"闹钟时间 {time} 已过，立即触发")
                delay = 0
            else:
                delay = (time - now).total_seconds()
            
            # 创建异步任务
            task.task = asyncio.create_task(self._schedule_alarm(task, delay))
            self.tasks[alarm_id] = task
            
            logger.info(f"已设置闹钟 {alarm_id}: {time} - {reminder}")
            return alarm_id

    async def set_alarm_for_user(
        self, 
        time: datetime, 
        reminder: str,
        callback: Optional[Callable[[str], Any]] = None
    ) -> str:
        """
        为用户设置闹钟（预留接口）
        
        Args:
            time: 提醒时间
            reminder: 提醒信息
            callback: 唤醒时的回调函数
            
        Returns:
            闹钟ID
        """
        async with self._lock:
            alarm_id = self._generate_id()
            task = AlarmTask(
                alarm_id=alarm_id,
                time=time,
                remindee="user",
                reminder=reminder,
                agent=None,
                callback=callback
            )
            
            # 计算延迟时间
            now = datetime.now()
            if time <= now:
                logger.warning(f"用户闹钟时间 {time} 已过，立即触发")
                delay = 0
            else:
                delay = (time - now).total_seconds()
            
            # 创建异步任务
            task.task = asyncio.create_task(self._schedule_alarm(task, delay))
            self.tasks[alarm_id] = task
            
            logger.info(f"已设置用户闹钟 {alarm_id}: {time} - {reminder}")
            return alarm_id

    async def _schedule_alarm(self, alarm_task: AlarmTask, delay: float):
        """调度闹钟任务"""
        try:
            if delay > 0:
                await asyncio.sleep(delay)
            
            # 触发闹钟
            await self._trigger_alarm(alarm_task)
            
        except asyncio.CancelledError:
            logger.info(f"闹钟 {alarm_task.alarm_id} 已被取消")
        except Exception as e:
            logger.error(f"闹钟 {alarm_task.alarm_id} 触发失败: {e}")
        finally:
            # 从任务列表中移除
            async with self._lock:
                self.tasks.pop(alarm_task.alarm_id, None)

    async def _trigger_alarm(self, alarm_task: AlarmTask):
        """触发闹钟"""
        logger.info(f"闹钟触发: {alarm_task.alarm_id} - {alarm_task.reminder}")
        
        if alarm_task.remindee == "oneself":
            await self._wake_up_agent(alarm_task)
        else:  # "user"
            await self._notify_user(alarm_task)

    async def _wake_up_agent(self, alarm_task: AlarmTask):
        """唤醒agent自身"""
        reminder_msg = f"⏰ 闹钟提醒: {alarm_task.reminder}"
        
        if alarm_task.callback:
            try:
                await alarm_task.callback(reminder_msg)
            except Exception as e:
                logger.error(f"闹钟回调执行失败: {e}")
        
        # 如果没有回调，至少记录日志
        logger.info(f"Agent闹钟唤醒: {reminder_msg}")

    async def _notify_user(self, alarm_task: AlarmTask):
        """通知用户（预留接口）"""
        reminder_msg = f"⏰ 用户闹钟提醒: {alarm_task.reminder}"
        
        if alarm_task.callback:
            try:
                await alarm_task.callback(reminder_msg)
            except Exception as e:
                logger.error(f"用户闹钟回调执行失败: {e}")
        
        # 记录日志，实际应用中应该通过其他方式通知用户
        logger.info(f"用户闹钟触发（预留接口）: {reminder_msg}")

    async def cancel_alarm(self, alarm_id: str) -> bool:
        """取消闹钟"""
        async with self._lock:
            task = self.tasks.get(alarm_id)
            if task and task.task:
                task.task.cancel()
                self.tasks.pop(alarm_id, None)
                logger.info(f"已取消闹钟 {alarm_id}")
                return True
            return False

    def list_alarms(self) -> list:
        """列出所有活跃的闹钟"""
        return [
            {
                "alarm_id": task.alarm_id,
                "time": task.time.isoformat(),
                "remindee": task.remindee,
                "reminder": task.reminder,
                "status": "active"
            }
            for task in self.tasks.values()
        ]


alarm_manager = AlarmManager()

async def get_alarm_tool(agent: ReActAgent) -> Tool:

    async def set_alarm(time: str, remindee: Literal["oneself", "user"], reminder: str):
        """
        设置闹钟提醒
        
        Args:
            time: ISO格式的时间字符串，如：2026-01-01T20:25:56.847307
            remindee: 被提醒的人，oneself（自己）或user（用户）
            reminder: 提醒信息
            
        Returns:
            设置结果信息
        """
        try:
            # 解析ISO时间字符串
            alarm_time = datetime.fromisoformat(time)
        except ValueError:
            return {"success": False, "message": f"无效的时间格式: {time}"}
        
        try:
            if remindee == "oneself":
                alarm_id = await alarm_manager.set_alarm_for_oneself(
                    time=alarm_time,
                    reminder=reminder,
                    agent=agent
                )
                return {
                    "success": True,
                    "message": f"已为自己设置闹钟: {reminder}",
                    "alarm_id": alarm_id,
                    "scheduled_time": alarm_time.isoformat()
                }
            else:  # "user"
                alarm_id = await alarm_manager.set_alarm_for_user(
                    time=alarm_time,
                    reminder=reminder
                )
                return {
                    "success": True,
                    "message": f"已为用户设置闹钟: {reminder}",
                    "alarm_id": alarm_id,
                    "scheduled_time": alarm_time.isoformat()
                }
        except Exception as e:
            logger.error(f"设置闹钟失败: {e}")
            return {"success": False, "message": f"设置闹钟失败: {str(e)}"}

    return Tool(
        func=set_alarm,
        entity=ToolEntity(
            name="set_alarm",
            description="设置闹钟提醒",
            parameters=ToolObjectParameter(
                type="object",
                properties={
                    "time": ToolParameter(
                        type="string",
                        description="闹钟或提醒的时间，标准ISO时间格式字符串，如：2026-01-01T20:25:56.847307",
                    ),
                    "remindee": ToolParameter(
                        type="string",
                        description="被提醒的人，可选oneself（自己）或user（用户）",
                        enum=["oneself", "user"],
                    ),
                    "reminder": ToolParameter(type="string", description="备忘信息"),
                },
            ),
        ),
    )
