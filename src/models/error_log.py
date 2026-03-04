"""ErrorLog data model."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional


@dataclass
class ErrorLog:
    """错误日志数据模型
    
    Attributes:
        timestamp: 错误发生时间
        error_type: 错误类型（network, parse, api, database, system）
        component: 组件名称（crawler, dedup, classifier, agent）
        operation: 操作名称
        error_message: 错误消息
        stack_trace: 堆栈跟踪
        context: 额外的上下文信息
    """
    
    timestamp: datetime
    error_type: str
    component: str
    operation: str
    error_message: str
    stack_trace: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    
    # 有效的错误类型
    VALID_ERROR_TYPES = {'network', 'parse', 'api', 'database', 'system'}
    
    # 有效的组件名称
    VALID_COMPONENTS = {'crawler', 'dedup', 'classifier', 'agent', 'api', 'database', 'cache'}
    
    def validate_error_type(self) -> bool:
        """验证错误类型
        
        Returns:
            bool: 错误类型是否有效
        """
        return self.error_type in self.VALID_ERROR_TYPES
    
    def validate_component(self) -> bool:
        """验证组件名称
        
        Returns:
            bool: 组件名称是否有效
        """
        return self.component in self.VALID_COMPONENTS
    
    def validate_required_fields(self) -> bool:
        """验证必填字段
        
        Returns:
            bool: 必填字段是否有效
        """
        # 检查时间戳
        if not isinstance(self.timestamp, datetime):
            return False
        
        # 检查字符串字段非空
        if not all([
            self.error_type,
            self.component,
            self.operation,
            self.error_message
        ]):
            return False
        
        return True
    
    def validate(self) -> bool:
        """验证整个数据模型的有效性
        
        Returns:
            bool: 数据模型是否有效
        """
        return (
            self.validate_required_fields() and
            self.validate_error_type() and
            self.validate_component()
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式
        
        Returns:
            Dict[str, Any]: 字典表示
        """
        return {
            'timestamp': self.timestamp.isoformat(),
            'error_type': self.error_type,
            'component': self.component,
            'operation': self.operation,
            'error_message': self.error_message,
            'stack_trace': self.stack_trace,
            'context': self.context
        }
    
    @classmethod
    def from_exception(
        cls,
        error_type: str,
        component: str,
        operation: str,
        exception: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> 'ErrorLog':
        """从异常创建错误日志
        
        Args:
            error_type: 错误类型
            component: 组件名称
            operation: 操作名称
            exception: 异常对象
            context: 额外的上下文信息
            
        Returns:
            ErrorLog: 错误日志实例
        """
        import traceback
        
        return cls(
            timestamp=datetime.now(),
            error_type=error_type,
            component=component,
            operation=operation,
            error_message=str(exception),
            stack_trace=traceback.format_exc(),
            context=context or {}
        )
