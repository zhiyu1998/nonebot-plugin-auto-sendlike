import asyncio
import json
from pathlib import Path

from nonebot import on_regex, logger, get_bot, require
from nonebot.adapters import Bot
from nonebot.adapters.onebot.v11 import GROUP, GroupMessageEvent
from nonebot.plugin import PluginMetadata

require("nonebot_plugin_localstore")

import nonebot_plugin_localstore as store

# 导入调度器
require("nonebot_plugin_apscheduler")

from nonebot_plugin_apscheduler import scheduler

__plugin_meta__ = PluginMetadata(
    name="自动点赞订阅赞",
    description="Nonebot2 的点赞、订阅赞功能，每天 12 点定时点赞👍！轻量、高效、便捷的小插件！",
    usage="通过直接发送：点赞，或者发送：订阅赞，每天定时12为你点赞",
    type="application",
    homepage="https://github.com/zhiyu1998/nonebot-plugin-auto-sendlike",
    supported_adapters={ "~onebot.v11" }
)

zan = on_regex("^(超|赞)(市|)我$", permission=GROUP)
zan_sub = on_regex("^订阅(超|赞)$", permission=GROUP)


def save_sub_user():
    """
    使用pickle将对象保存到文件
    :return: None
    """
    data_file = store.get_plugin_data_file("sub_user")
    data_file.write_text(json.dumps(sub_user))


def load_sub_user():
    """
    从文件中加载对象
    :return: 订阅用户列表
    """
    data_file = store.get_plugin_data_file("sub_user")
    # 判断是否存在
    if not data_file.exists():
        data_file.write_text(json.dumps([]))
    return json.loads(data_file.read_text())


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
            logger.info(f"点赞成功，当前点赞次数：{count}")
    except Exception as e:
        logger.error(f"点赞失败: {e}")
    return count


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
        await zan.finish(f"我给不了你更多了哟~")


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
