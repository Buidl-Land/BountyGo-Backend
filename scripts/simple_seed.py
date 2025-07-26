"""
简化的数据库种子脚本 - 直接SQL插入
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import get_db
from sqlalchemy import text


async def insert_test_data():
    """插入测试数据"""

    # 计算时间戳
    deadline1 = datetime.now() + timedelta(days=30)
    deadline2 = datetime.now() + timedelta(days=45)
    deadline3 = datetime.now() + timedelta(days=20)

    timestamp1 = int(deadline1.timestamp())
    timestamp2 = int(deadline2.timestamp())
    timestamp3 = int(deadline3.timestamp())

    # SQL插入语句
    sql_statements = [
        # 插入测试用户（如果不存在）
        """
        INSERT INTO users (email, nickname, avatar_url, is_active, created_at, updated_at)
        SELECT 'test@example.com', '测试用户', 'https://avatars.githubusercontent.com/u/1?v=4', true, NOW(), NOW()
        WHERE NOT EXISTS (SELECT 1 FROM users WHERE email = 'test@example.com');
        """,

        # 插入主办方
        """
        INSERT INTO organizers (name, is_verified, created_at, updated_at)
        SELECT '以太坊基金会', true, NOW(), NOW()
        WHERE NOT EXISTS (SELECT 1 FROM organizers WHERE name = '以太坊基金会');
        """,

        """
        INSERT INTO organizers (name, is_verified, created_at, updated_at)
        SELECT 'Polygon Labs', true, NOW(), NOW()
        WHERE NOT EXISTS (SELECT 1 FROM organizers WHERE name = 'Polygon Labs');
        """,

        """
        INSERT INTO organizers (name, is_verified, created_at, updated_at)
        SELECT 'Web3社区', false, NOW(), NOW()
        WHERE NOT EXISTS (SELECT 1 FROM organizers WHERE name = 'Web3社区');
        """,

        # 插入任务1 - 黑客松
        f"""
        INSERT INTO tasks (
            title, summary, description, category, deadline,
            sponsor_id, organizer_id, external_link, status, view_count, join_count,
            created_at, updated_at
        )
        SELECT
            'ETH Global 2024 黑客松大赛',
            '全球最大的以太坊开发者黑客松，48小时构建下一代DeFi应用',
            'ETH Global 2024 黑客松是全球最具影响力的以太坊开发者竞赛之一。本次比赛将汇聚来自世界各地的顶尖开发者，在48小时内构建创新的去中心化应用。

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
- 现场演示和答辩',
            '黑客松',
            {timestamp1},
            (SELECT id FROM users WHERE email = 'test@example.com'),
            (SELECT id FROM organizers WHERE name = '以太坊基金会'),
            'https://ethglobal.com/events/sf2024',
            'active',
            156,
            23,
            NOW(),
            NOW()
        WHERE NOT EXISTS (SELECT 1 FROM tasks WHERE title = 'ETH Global 2024 黑客松大赛');
        """,

        # 插入任务2 - 征文
        f"""
        INSERT INTO tasks (
            title, summary, description, category, deadline,
            sponsor_id, organizer_id, external_link, status, view_count, join_count,
            created_at, updated_at
        )
        SELECT
            'Polygon zkEVM 生态征文活动',
            '探索零知识证明技术在Web3中的应用，分享你的见解和经验',
            'Polygon zkEVM 生态征文活动邀请开发者、研究者和爱好者分享关于零知识证明技术的深度见解。

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
- 最受欢迎奖（1名）：5000 MATIC + 社区 AMA 机会',
            '征文',
            {timestamp2},
            (SELECT id FROM users WHERE email = 'test@example.com'),
            (SELECT id FROM organizers WHERE name = 'Polygon Labs'),
            'https://polygon.technology/blog/zkevm-writing-contest',
            'active',
            89,
            12,
            NOW(),
            NOW()
        WHERE NOT EXISTS (SELECT 1 FROM tasks WHERE title = 'Polygon zkEVM 生态征文活动');
        """,

        # 插入任务3 - Meme创作
        f"""
        INSERT INTO tasks (
            title, summary, description, category, deadline,
            sponsor_id, organizer_id, external_link, status, view_count, join_count,
            created_at, updated_at
        )
        SELECT
            'Web3 Meme 创作大赛 - 牛市来了！',
            '用创意和幽默诠释Web3文化，创作最有趣的加密货币Meme',
            'Web3 Meme 创作大赛邀请所有创意达人参与，用幽默和创意展现Web3世界的精彩瞬间！

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

奖励设置：
- 冠军（1名）：2000 USDC + 限量版NFT
- 亚军（2名）：每人 1000 USDC
- 季军（3名）：每人 500 USDC
- 人气奖（5名）：每人 200 USDC
- 参与奖：所有参赛者获得纪念版POAP',
            'Meme创作',
            {timestamp3},
            (SELECT id FROM users WHERE email = 'test@example.com'),
            (SELECT id FROM organizers WHERE name = 'Web3社区'),
            'https://web3community.org/meme-contest',
            'active',
            234,
            67,
            NOW(),
            NOW()
        WHERE NOT EXISTS (SELECT 1 FROM tasks WHERE title = 'Web3 Meme 创作大赛 - 牛市来了！');
        """
    ]

    # 执行SQL语句
    async for db in get_db():
        try:
            for sql in sql_statements:
                await db.execute(text(sql))

            await db.commit()
            print("✅ 测试数据插入成功！")

            # 查询插入的任务
            result = await db.execute(text("""
                SELECT t.title, t.category, o.name as organizer_name, t.view_count, t.join_count
                FROM tasks t
                LEFT JOIN organizers o ON t.organizer_id = o.id
                WHERE t.title IN (
                    'ETH Global 2024 黑客松大赛',
                    'Polygon zkEVM 生态征文活动',
                    'Web3 Meme 创作大赛 - 牛市来了！'
                )
                ORDER BY t.created_at DESC
            """))

            tasks = result.fetchall()
            print(f"\n📋 已插入 {len(tasks)} 个测试任务:")
            for task in tasks:
                print(f"- {task.title}")
                print(f"  分类: {task.category} | 主办方: {task.organizer_name}")
                print(f"  浏览: {task.view_count} | 参与: {task.join_count}")
                print()

        except Exception as e:
            await db.rollback()
            print(f"❌ 插入数据时出错: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            break


async def main():
    """主函数"""
    print("🚀 开始插入测试任务数据...")
    await insert_test_data()
    print("✨ 完成！现在可以在前端查看这些任务了。")


if __name__ == "__main__":
    asyncio.run(main())
