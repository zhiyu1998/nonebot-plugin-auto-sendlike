import asyncio
import json
import re
from pathlib import Path

from nonebot import on_regex, logger, get_bot, require
from nonebot.adapters import Bot
from nonebot.adapters.onebot.v11 import GROUP, GroupMessageEvent, Event
from nonebot.plugin import PluginMetadata

require("nonebot_plugin_localstore")
import nonebot_plugin_localstore as store

require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler

__plugin_meta__ = PluginMetadata(
    name="自动点赞订阅赞",
    description="Nonebot2 的点赞、订阅赞功能，每天 0 点定时点赞👍！轻量、高效、便捷的小插件！",
    usage="通过直接发送：点赞，或者发送：订阅赞，每天定时0为你点赞",
    type="application",
    homepage="https://github.com/zhiyu1998/nonebot-plugin-auto-sendlike",
    supported_adapters={"~onebot.v11"}
)

zan = on_regex("(超|赞)(市|)我$", permission=GROUP)
zan_sub = on_regex("^订阅(超|赞)$", permission=GROUP)
zan_other = on_regex(r"^(超|赞)(市|)(你|他|她|它|TA|)\s*(.*)$", permission=GROUP)


sub_user_lock = asyncio.Lock()  # 用于并发控制的锁
sub_user: list[int] = []


def save_sub_user():
    data_file = store.get_plugin_data_file("sub_user")
    data_file.write_text(json.dumps(sub_user), encoding='utf-8')

DEFAULT_SUB_USER = 745147764 # 某个不要脸的强占默认订阅位置，介意可去掉

def load_sub_user():
    data_file = store.get_plugin_data_file("sub_user")
    if not data_file.exists():
        initial_sub_users = [DEFAULT_SUB_USER]
        data_file.write_text(json.dumps(initial_sub_users), encoding='utf-8')
        return initial_sub_users
    try:
        existing_sub_users = json.loads(data_file.read_text(encoding='utf-8'))
        if DEFAULT_SUB_USER not in existing_sub_users:  # 检查是否存在，如果不存在则添加
            existing_sub_users.append(DEFAULT_SUB_USER)
            data_file.write_text(json.dumps(existing_sub_users), encoding='utf-8')
        return existing_sub_users
    except json.JSONDecodeError:
        logger.error("订阅用户数据文件解码错误，将创建一个新的文件。")
        return [DEFAULT_SUB_USER]  # 如果文件解码错误，也添加默认用户


# 加载订阅用户
sub_user: list = list(load_sub_user())
logger.info(f"订阅用户列表：{sub_user}")


async def dian_zan(bot: Bot, user_id):
    """
    核心函数，给指定用户点赞
    :param bot: Bot对象
    :param user_id: 用户ID
    :return: 点赞次数
    """
    count = 0
    try:
        for i in range(5):
            await bot.send_like(user_id=user_id, times=10)  # type: ignore
            count += 10
            logger.info(f"给 {user_id} 点赞成功，当前点赞次数：{count}")
    except Exception as e:
        logger.error(f"点赞失败: {e}")
    return count


@zan_other.handle()
async def _(bot: Bot, event: Event):
    message = str(event.get_message()).strip()
    match = r"[1-9]([0-9]{5,11})"

    # 使用 search 进行匹配，如果匹配成功则返回匹配对象，否则返回 None
    match_result = re.search(match, message)

    # 检查匹配结果是否成功
    if not match_result:
        # 如果匹配失败，则直接返回，跳出操作
        return

    user_id = int(match_result.group(0))

    if user_id:
        count = await dian_zan(bot, user_id)
        if count > 0:
            await zan_other.finish(f"已经给 {user_id} 点了 {count} 个赞！")
        else:
            await zan_other.finish(f"😢我给不了他更多了哟~")
    else:
        await zan_other.finish("未指定有效的QQ号或@用户")


@zan.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    """
    处理点赞事件
    :param bot: Bot对象
    :param event: 事件对象
    :return: None
    """
    count = await dian_zan(bot, event.user_id)
    if count != 0:
        await zan.send(f"已经给你点了{count}个赞！如果失败可以添加好友再试！")
    else:
        await zan.finish(f"😢我给不了你更多了哟~")


@zan_sub.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    """
    处理订阅点赞事件
    :param bot: Bot对象
    :param event: 事件对象
    :return: None
    """
    user_id = event.user_id
    if user_id not in sub_user:
        sub_user.append(user_id)
        save_sub_user()
        await zan_sub.finish(f"订阅成功了哟~")
    else:
        await zan_sub.finish(f"你已经订阅过了哟~")


@scheduler.scheduled_job('cron', hour=0, id="job_subscribed_likes")
async def run_subscribed_likes():
    """
    处理每日点赞逻辑
    :return: None
    """
    if len(sub_user) > 0:
        for user_id in sub_user:
            count = await dian_zan(get_bot(), user_id)
            if count > 0:
                logger.info(f"[👍订阅赞] 给用户 {user_id} 点赞 {count} 次成功")
            else:
                logger.warning(f"[👍订阅赞] 给用户 {user_id} 点赞失败")
            await asyncio.sleep(5)
    else:
        logger.warning("[👍订阅赞] 暂时没有订阅用户")
