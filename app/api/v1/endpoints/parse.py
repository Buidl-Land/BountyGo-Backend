"""
内容解析API端点 - 为前端提供URL和文本解析功能
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field, HttpUrl

from app.core.database import get_db
from app.models.task import Organizer
from app.agent.url_parsing_agent import URLParsingAgent
from app.agent.models import TaskInfo

router = APIRouter()
logger = logging.getLogger(__name__)


class ParseRequest(BaseModel):
    """解析请求模型"""
    url: Optional[HttpUrl] = Field(None, description="要解析的网页URL")
    content: Optional[str] = Field(None, description="要解析的文本内容")


class OrganizerResponse(BaseModel):
    """主办方响应模型"""
    id: int
    name: str
    is_verified: bool


class ParseResponse(BaseModel):
    """解析响应模型"""
    title: str
    summary: Optional[str] = None
    description: Optional[str] = None
    deadline: Optional[int] = Field(None, description="截止日期时间戳")
    category: Optional[str] = None
    reward_details: Optional[str] = None
    reward_type: Optional[str] = None
    organizer_name: Optional[str] = None
    organizer: Optional[OrganizerResponse] = None
    source_url: Optional[str] = None


@router.post("/", response_model=ParseResponse, summary="解析URL或文本内容")
async def parse_content(
    request: ParseRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    解析URL或文本内容，提取任务信息

    - **url**: 要解析的网页URL（与content二选一）
    - **content**: 要解析的文本内容（与url二选一）

    返回解析后的任务信息，如果数据库中有对应的主办方信息则一并返回
    """
    if not request.url and not request.content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="必须提供url或content参数"
        )

    if request.url and request.content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="url和content参数不能同时提供"
        )

    try:
        # 初始化解析代理
        agent = URLParsingAgent()

        # 解析内容
        if request.url:
            # URL解析
            task_info = await agent.extract_task_info(str(request.url))
            source_url = str(request.url)
        else:
            # 文本解析
            task_info = await agent.extract_from_content(request.content)
            source_url = None

        # 查找主办方信息
        organizer_response = None
        if task_info.organizer_name:
            # 查找已存在的主办方
            result = await db.execute(
                select(Organizer).where(Organizer.name == task_info.organizer_name)
            )
            organizer = result.scalar_one_or_none()

            if organizer:
                organizer_response = OrganizerResponse(
                    id=organizer.id,
                    name=organizer.name,
                    is_verified=organizer.is_verified
                )
            else:
                # 如果数据库中没有，使用AI推理创建新的主办方
                new_organizer = Organizer(name=task_info.organizer_name)
                db.add(new_organizer)
                await db.commit()
                await db.refresh(new_organizer)

                organizer_response = OrganizerResponse(
                    id=new_organizer.id,
                    name=new_organizer.name,
                    is_verified=new_organizer.is_verified
                )

                logger.info(f"Created new organizer from AI inference: {task_info.organizer_name}")

        # 构建响应
        response = ParseResponse(
            title=task_info.title,
            summary=task_info.summary,
            description=task_info.description,
            deadline=task_info.deadline,
            category=task_info.category,
            reward_details=task_info.reward_details,
            reward_type=task_info.reward_type,
            organizer_name=task_info.organizer_name,
            organizer=organizer_response,
            source_url=source_url
        )

        return response

    except Exception as e:
        logger.error(f"Error parsing content: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"解析失败: {str(e)}"
        )


@router.get("/categories", summary="获取支持的任务分类")
async def get_categories():
    """
    获取系统支持的任务分类列表
    """
    categories = [
        {
            "value": "黑客松",
            "label": "黑客松",
            "description": "编程竞赛、开发比赛、技术挑战、Hackathon"
        },
        {
            "value": "征文",
            "label": "征文",
            "description": "文章写作、内容创作、博客征集、写作比赛"
        },
        {
            "value": "Meme创作",
            "label": "Meme创作",
            "description": "表情包制作、创意图片、幽默内容、设计比赛"
        },
        {
            "value": "Web3交互",
            "label": "Web3交互",
            "description": "区块链操作、DeFi体验、NFT相关、链上交互"
        },
        {
            "value": "推特抽奖",
            "label": "推特抽奖",
            "description": "社交媒体活动、转发抽奖、关注有奖、Twitter活动"
        },
        {
            "value": "开发实战",
            "label": "开发实战",
            "description": "代码实现、技术学习、项目开发、编程练习"
        }
    ]

    return {
        "categories": categories,
        "total": len(categories)
    }


@router.post("/validate", summary="验证解析结果")
async def validate_parse_result(
    task_info: TaskInfo,
    db: AsyncSession = Depends(get_db)
):
    """
    验证前端修改后的解析结果

    用于前端在用户修改解析结果后，提交前进行验证
    """
    try:
        # 验证必需字段
        if not task_info.title or not task_info.title.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="任务标题不能为空"
            )

        # 验证分类
        if task_info.category:
            valid_categories = ["黑客松", "征文", "Meme创作", "Web3交互", "推特抽奖", "开发实战"]
            if task_info.category not in valid_categories:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"无效的任务分类: {task_info.category}"
                )

        # 验证主办方
        organizer_response = None
        if task_info.organizer_name:
            # 查找或创建主办方
            result = await db.execute(
                select(Organizer).where(Organizer.name == task_info.organizer_name)
            )
            organizer = result.scalar_one_or_none()

            if not organizer:
                # 创建新主办方
                organizer = Organizer(name=task_info.organizer_name)
                db.add(organizer)
                await db.commit()
                await db.refresh(organizer)

            organizer_response = OrganizerResponse(
                id=organizer.id,
                name=organizer.name,
                is_verified=organizer.is_verified
            )

        return {
            "valid": True,
            "message": "验证通过",
            "organizer": organizer_response
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating parse result: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"验证失败: {str(e)}"
        )
