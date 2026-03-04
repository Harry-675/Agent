"""NewsItem data model."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class NewsItem:
    """新闻条目数据模型
    
    Attributes:
        id: 唯一标识符
        title: 新闻标题
        summary: 新闻摘要
        url: 新闻链接
        published_at: 发布时间
        source_id: 新闻源ID
        source_name: 新闻源名称
        categories: 主题分类列表（1-3个）
        duplicate_group_id: 去重组ID（可选）
        source_tags: 所有来源标签列表
        created_at: 创建时间
        updated_at: 更新时间
    """
    
    id: str
    title: str
    summary: str
    url: str
    published_at: datetime
    source_id: str
    source_name: str
    categories: List[str] = field(default_factory=list)
    duplicate_group_id: Optional[str] = None
    source_tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def validate_required_fields(self) -> bool:
        """验证必填字段
        
        Returns:
            bool: 必填字段是否有效
        """
        # 检查字符串字段非空
        if not all([
            self.id,
            self.title,
            self.summary,
            self.url,
            self.source_id,
            self.source_name
        ]):
            return False
        
        # 检查发布时间
        if not isinstance(self.published_at, datetime):
            return False
        
        return True
    
    def validate_categories(self) -> bool:
        """验证分类字段
        
        Returns:
            bool: 分类是否有效
        """
        # 分类必须是列表
        if not isinstance(self.categories, list):
            return False
        
        # 至少1个，最多3个分类
        if len(self.categories) < 1 or len(self.categories) > 3:
            return False
        
        # 所有分类必须是非空字符串
        for category in self.categories:
            if not isinstance(category, str) or not category.strip():
                return False
        
        # 预定义的有效分类
        valid_categories = {"金融", "科技", "体育", "娱乐", "政治", "健康"}
        
        # 所有分类必须在有效集合中
        for category in self.categories:
            if category not in valid_categories:
                return False
        
        return True
    
    def validate_source_tags(self) -> bool:
        """验证来源标签
        
        Returns:
            bool: 来源标签是否有效
        """
        # 来源标签必须是列表
        if not isinstance(self.source_tags, list):
            return False
        
        # 至少包含一个来源
        if len(self.source_tags) < 1:
            return False
        
        # 所有标签必须是非空字符串
        for tag in self.source_tags:
            if not isinstance(tag, str) or not tag.strip():
                return False
        
        return True
    
    def validate(self) -> bool:
        """验证整个数据模型的有效性
        
        Returns:
            bool: 数据模型是否有效
        """
        return (
            self.validate_required_fields() and
            self.validate_categories() and
            self.validate_source_tags()
        )
    
    def is_duplicate_of(self, other: 'NewsItem', threshold: float = 0.85) -> bool:
        """判断是否为重复新闻（基于相似度阈值）
        
        注意：此方法仅检查阈值逻辑，实际相似度计算由DeduplicationEngine完成
        
        Args:
            other: 另一条新闻
            threshold: 相似度阈值（默认0.85）
            
        Returns:
            bool: 是否为重复新闻
        """
        # 这个方法的实际实现需要调用大模型计算相似度
        # 这里只是一个占位符，实际逻辑在DeduplicationEngine中
        raise NotImplementedError(
            "实际相似度计算需要通过DeduplicationEngine完成"
        )
    
    def add_source_tag(self, source_name: str) -> None:
        """添加来源标签
        
        Args:
            source_name: 来源名称
        """
        if source_name and source_name not in self.source_tags:
            self.source_tags.append(source_name)
            self.updated_at = datetime.now()
    
    def merge_with(self, other: 'NewsItem') -> None:
        """合并另一条重复新闻的来源标签
        
        Args:
            other: 另一条重复新闻
        """
        # 合并来源标签
        for tag in other.source_tags:
            self.add_source_tag(tag)
        
        # 如果没有去重组ID，创建一个
        if not self.duplicate_group_id:
            self.duplicate_group_id = self.id
        
        self.updated_at = datetime.now()
