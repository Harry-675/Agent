"""NewsSource data model."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict
from urllib.parse import urlparse
import re


@dataclass
class NewsSource:
    """新闻源配置数据模型
    
    Attributes:
        id: 唯一标识符
        name: 新闻源名称
        url: 新闻源URL
        enabled: 是否启用
        crawl_rules: 爬取规则（CSS选择器或XPath）
        timeout: 超时时间（秒）
        created_at: 创建时间
        updated_at: 更新时间
    """
    
    id: str
    name: str
    url: str
    enabled: bool
    crawl_rules: Dict[str, str]
    timeout: int = 30
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def validate_url(self) -> bool:
        """验证URL有效性
        
        Returns:
            bool: URL是否有效
        """
        if not self.url or not isinstance(self.url, str):
            return False
        
        # 检查URL格式
        try:
            result = urlparse(self.url)
            # 必须有scheme和netloc
            if not all([result.scheme, result.netloc]):
                return False
            # scheme必须是http或https
            if result.scheme not in ['http', 'https']:
                return False
            # netloc必须包含有效的域名
            if not self._is_valid_domain(result.netloc):
                return False
            return True
        except Exception:
            return False
    
    def _is_valid_domain(self, domain: str) -> bool:
        """验证域名有效性
        
        Args:
            domain: 域名字符串
            
        Returns:
            bool: 域名是否有效
        """
        # 移除端口号
        domain = domain.split(':')[0]
        
        # 域名正则表达式
        domain_pattern = re.compile(
            r'^(?:[a-zA-Z0-9]'  # 第一个字符
            r'(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)'  # 子域名
            r'+[a-zA-Z]{2,}$'  # 顶级域名
        )
        
        return bool(domain_pattern.match(domain))
    
    def validate_crawl_rules(self) -> bool:
        """验证爬取规则有效性
        
        Returns:
            bool: 爬取规则是否有效
        """
        if not isinstance(self.crawl_rules, dict):
            return False
        
        # 至少需要包含title规则
        if 'title' not in self.crawl_rules:
            return False
        
        # 所有规则值必须是非空字符串
        for key, value in self.crawl_rules.items():
            if not isinstance(value, str) or not value.strip():
                return False
        
        return True
    
    def validate(self) -> bool:
        """验证整个数据模型的有效性
        
        Returns:
            bool: 数据模型是否有效
        """
        # 验证必填字段
        if not self.id or not self.name:
            return False
        
        # 验证URL
        if not self.validate_url():
            return False
        
        # 验证爬取规则
        if not self.validate_crawl_rules():
            return False
        
        # 验证timeout
        if not isinstance(self.timeout, int) or self.timeout <= 0:
            return False
        
        return True
