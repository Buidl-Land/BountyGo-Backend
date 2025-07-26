"""
数据库种子脚本 - 插入测试任务数据
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.models.task import Task, Organizer
from app.models.user import User


async def create_test_user():
    """创建测试用户"""
    async with AsyncSessionLocal() as session:
        # 检查是否已存在测试用户
        from sqlalchemy import select
        result = await session.execute(
            select(User).where(User.email == "test@example.com")
        )
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                email="test@example.com",
                nickname="测试用户",
                avatar_url="https://avatars.githubusercontent.com/u/1?v=4",
                is_active=True
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            print(f"Created test user: {user.email}")
        else:
            print(f"Test user already exists: {user.email}")

        return user


async def create_test_organizers():
    """创建测试主办方"""
    organizers_data = [
        {"name": "以太坊基金会", "is_verified": True},
        {"name": "Polygon Labs", "is_verified": True},
        {"name": "Web3社区", "is_verified": False}
    ]

    async with AsyncSessionLocal() as session:
        organizers = []

        for org_data in organizers_data:
            from sqlalchemy import select
            result = await session.execute(
                select(Organizer).where(Organizer.name == org_data["name"])
            )
            organizer = result.scalar_one_or_none()

            if not organizer:
                organizer = Organizer(**org_data)
                session.add(organizer)
                await session.commit()
                await session.refresh(organizer)
                print(f"Created organizer: {organizer.name}")
            else:
                print(f"Organizer already exists: {organizer.name}")

            organizers.append(organizer)

        return organizers


async def create_test_tasks():
    """创建测试任务"""
    # 获取测试用户和主办方
    user = await create_test_user()
    organizers = await create_test_organizers()

    # 任务数据
    tasks_data = [
        {
            "title": "ETH Global 2024 黑客松大赛",
            "summary": "全球最大的以太坊开发者黑客松，48小时构建下一代DeFi应用",
            "description": """
ETH Global 2024 黑客松是全球最具影响力的以太坊开发者竞赛之一。本次比赛将汇聚来自世界各地的顶尖开发者，在48小时内构建创新的去中心化应用。

比赛主题：
- DeFi 2.0 创新协议
- NFT 实用性应用
- Layer 2 扩容解决方案
- 跨链互操作性
- 去中心化身份认证

奖励设置：
- 一等奖：50,000 USDC + 孵化器机会
- 二等奖：20,000 USDC
- 三等奖：10,000 USDC
- 最佳创意奖：5,000 USDC

参赛要求：
- 团队规模：1-4人
- 必须使用以太坊或其Layer 2网络
- 代码开源，提交到GitHub
- 现场演示和答辩

报名截止：2024年3月15日
比赛时间：2024年3月20-22日
地点：旧金山会展中心
            """,
            "category": "黑客松",
            "deadline": int((datetime.now() + timedelta(days=30)).timestamp()),
            "external_link": "https://ethglobal.com/events/sf2024",
            "organizer": organizers[0]  # 以太坊基金会
        },
        {
            "title": "Polygon zkEVM 生态征文活动",
            "summary": "探索零知识证明技术在Web3中的应用，分享你的见解和经验",
            "description": """
Polygon zkEVM 生态征文活动邀请开发者、研究者和爱好者分享关于零知识证明技术的深度见解。

征文主题：
1. zkEVM 技术原理解析
2. 零知识证明在隐私保护中的应用
3. zkEVM vs Optimistic Rollup 对比分析
4. 构建在 Polygon zkEVM 上的 DApp 开发经验
5. 零知识证明的未来发展趋势

文章要求：
- 字数：2000-5000字
- 原创内容，未在其他平台发布
- 技术深度和实用性并重
- 配图和代码示例加分

奖励机制：
- 优秀奖（10名）：每人 1000 MATIC
- 最佳技术奖（3名）：每人 3000 MATIC + Polygon 官方推荐
- 最受欢迎奖（1名）：5000 MATIC + 社区 AMA 机会

提交方式：
- 发布到个人博客或技术平台
- 在推特上分享并@PolygonLabs
- 填写提交表单

评选标准：
- 技术准确性（40%）
- 内容深度（30%）
- 实用价值（20%）
- 表达清晰度（10%）
            """,
            "category": "征文",
            "deadline": int((datetime.now() + timedelta(days=45)).timestamp()),
            "external_link": "https://polygon.technology/blog/zkevm-writing-contest",
            "organizer": organizers[1]  # Polygon Labs
        },
        {
            "title": "Web3 Meme 创作大赛 - 牛市来了！",
            "summary": "用创意和幽默诠释Web3文化，创作最有趣的加密货币Meme",
            "description": """
Web3 Meme 创作大赛邀请所有创意达人参与，用幽默和创意展现Web3世界的精彩瞬间！

创作主题：
- 牛市熊市的心路历程
- DeFi 挖矿的日常
- NFT 收藏家的执着
- 加密货币价格的魔幻现实
- Web3 社区的有趣文化

作品要求：
- 原创Meme图片或短视频
- 内容积极正面，体现Web3文化
- 可以是静态图片、GIF或15秒内短视频
- 分辨率不低于1080p

参赛方式：
1. 创作你的Meme作品
2. 发布到Twitter并添加话题 #Web3MemeContest
3. @Web3Community 并邀请3个朋友点赞
4. 填写参赛表单提交作品链接

奖励设置：
- 冠军（1名）：2000 USDC + 限量版NFT
- 亚军（2名）：每人 1000 USDC
- 季军（3名）：每人 500 USDC
- 人气奖（5名）：每人 200 USDC
- 参与奖：所有参赛者获得纪念版POAP

评选维度：
- 创意性（40%）
- 幽默感（30%）
- Web3相关性（20%）
- 社区互动（10%）

特别说明：
- 作品必须原创，不得抄袭
- 获奖作品将在官方社交媒体展示
- 优秀作品有机会成为社区表情包
            """,
            "category": "Meme创作",
            "deadline": int((datetime.now() + timedelta(days=20)).timestamp()),
            "external_link": "https://web3community.org/meme-contest",
            "organizer": organizers[2]  # Web3社区
        }
    ]

    async with AsyncSessionLocal() as session:
        created_tasks = []

        for task_data in tasks_data:
            # 检查任务是否已存在
            from sqlalchemy import select
            result = await session.execute(
                select(Task).where(Task.title == task_data["title"])
            )
            existing_task = result.scalar_one_or_none()

            if existing_task:
                print(f"Task already exists: {task_data['title']}")
                continue

            # 创建新任务
            organizer = task_data.pop("organizer")
            task = Task(
                sponsor_id=user.id,
                organizer_id=organizer.id,
                status="active",
                view_count=0,
                join_count=0,
                **task_data
            )

            session.add(task)
            await session.commit()
            await session.refresh(task)

            created_tasks.append(task)
            print(f"Created task: {task.title}")

        return created_tasks


async def main():
    """主函数"""
    print("开始创建测试数据...")

    try:
        tasks = await create_test_tasks()
        print(f"\n成功创建 {len(tasks)} 个测试任务:")
        for task in tasks:
            print(f"- {task.title} (分类: {task.category})")

        print("\n测试数据创建完成！")

    except Exception as e:
        print(f"创建测试数据时出错: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
