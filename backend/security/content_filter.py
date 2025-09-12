"""
内容过滤和敏感词检测
"""

import re
import logging
from typing import List, Dict, Set, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import asyncio


class FilterAction(str, Enum):
    """过滤动作"""
    BLOCK = "block"          # 阻止
    REPLACE = "replace"      # 替换
    WARNING = "warning"      # 警告
    AUDIT = "audit"          # 审计


class FilterCategory(str, Enum):
    """过滤类别"""
    PROFANITY = "profanity"           # 亵渎
    VIOLENCE = "violence"             # 暴力
    HATE_SPEECH = "hate_speech"       # 仇恨言论
    SEXUAL_CONTENT = "sexual_content" # 性内容
    PERSONAL_INFO = "personal_info"   # 个人信息
    SPAM = "spam"                     # 垃圾信息
    CUSTOM = "custom"                 # 自定义


@dataclass
class FilterRule:
    """过滤规则"""
    pattern: str
    category: FilterCategory
    action: FilterAction
    severity: int  # 严重程度 1-10
    replacement: Optional[str] = None
    description: Optional[str] = None
    
    def __post_init__(self):
        # 编译正则表达式
        self.compiled_pattern = re.compile(self.pattern, re.IGNORECASE)


@dataclass
class FilterResult:
    """过滤结果"""
    original_text: str
    filtered_text: str
    is_blocked: bool
    violations: List[Dict[str, Any]]
    risk_score: int  # 风险评分 0-100


class SensitiveWordFilter:
    """敏感词过滤器"""
    
    def __init__(self):
        self.logger = logging.getLogger("security.content_filter")
        
        # 敏感词库
        self.sensitive_words: Dict[FilterCategory, Set[str]] = {
            FilterCategory.PROFANITY: set(),
            FilterCategory.VIOLENCE: set(),
            FilterCategory.HATE_SPEECH: set(),
            FilterCategory.SEXUAL_CONTENT: set(),
            FilterCategory.PERSONAL_INFO: set(),
            FilterCategory.SPAM: set(),
            FilterCategory.CUSTOM: set()
        }
        
        # 过滤规则
        self.filter_rules: List[FilterRule] = []
        
        # 白名单
        self.whitelist: Set[str] = set()
        
        # 初始化默认规则
        self._initialize_default_rules()
    
    def _initialize_default_rules(self):
        """初始化默认过滤规则"""
        # 个人信息模式
        self.filter_rules.extend([
            FilterRule(
                pattern=r'\b\d{11}\b',  # 手机号
                category=FilterCategory.PERSONAL_INFO,
                action=FilterAction.REPLACE,
                severity=7,
                replacement="[手机号]",
                description="手机号码"
            ),
            FilterRule(
                pattern=r'\b\d{15,18}\b',  # 身份证号
                category=FilterCategory.PERSONAL_INFO,
                action=FilterAction.REPLACE,
                severity=9,
                replacement="[身份证号]",
                description="身份证号码"
            ),
            FilterRule(
                pattern=r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # 邮箱
                category=FilterCategory.PERSONAL_INFO,
                action=FilterAction.REPLACE,
                severity=5,
                replacement="[邮箱地址]",
                description="邮箱地址"
            ),
            FilterRule(
                pattern=r'\b(?:\d{1,3}\.){3}\d{1,3}\b',  # IP地址
                category=FilterCategory.PERSONAL_INFO,
                action=FilterAction.REPLACE,
                severity=6,
                replacement="[IP地址]",
                description="IP地址"
            )
        ])
        
        # 垃圾信息模式
        self.filter_rules.extend([
            FilterRule(
                pattern=r'(?i)(免费|赚钱|兼职|代理|加微信|QQ群)',
                category=FilterCategory.SPAM,
                action=FilterAction.WARNING,
                severity=5,
                description="疑似垃圾信息"
            ),
            FilterRule(
                pattern=r'(?i)(点击链接|立即下载|马上注册)',
                category=FilterCategory.SPAM,
                action=FilterAction.WARNING,
                severity=6,
                description="疑似垃圾链接"
            )
        ])
        
        # 初始化敏感词库
        self._load_sensitive_words()
    
    def _load_sensitive_words(self):
        """加载敏感词库"""
        # 这里应该从文件或数据库加载敏感词
        # 暂时添加一些示例词汇
        
        profanity_words = ["垃圾", "废物", "白痴", "蠢货"]
        self.sensitive_words[FilterCategory.PROFANITY].update(profanity_words)
        
        violence_words = ["杀死", "暴力", "血腥", "恐怖"]
        self.sensitive_words[FilterCategory.VIOLENCE].update(violence_words)
        
        hate_speech_words = ["歧视", "仇恨", "种族主义"]
        self.sensitive_words[FilterCategory.HATE_SPEECH].update(hate_speech_words)
    
    async def filter_text(self, text: str) -> FilterResult:
        """过滤文本"""
        try:
            if not text or not text.strip():
                return FilterResult(
                    original_text=text,
                    filtered_text=text,
                    is_blocked=False,
                    violations=[],
                    risk_score=0
                )
            
            # 检查白名单
            if text.lower() in self.whitelist:
                return FilterResult(
                    original_text=text,
                    filtered_text=text,
                    is_blocked=False,
                    violations=[],
                    risk_score=0
                )
            
            filtered_text = text
            violations = []
            total_risk_score = 0
            is_blocked = False
            
            # 应用规则过滤
            for rule in self.filter_rules:
                matches = rule.compiled_pattern.finditer(text)
                for match in matches:
                    violation = {
                        "rule": rule.description or rule.pattern,
                        "category": rule.category.value,
                        "severity": rule.severity,
                        "action": rule.action.value,
                        "matched_text": match.group(),
                        "start": match.start(),
                        "end": match.end()
                    }
                    violations.append(violation)
                    
                    # 累计风险分数
                    total_risk_score += rule.severity
                    
                    # 执行过滤动作
                    if rule.action == FilterAction.BLOCK:
                        is_blocked = True
                    elif rule.action == FilterAction.REPLACE and rule.replacement:
                        filtered_text = rule.compiled_pattern.sub(
                            rule.replacement, filtered_text
                        )
            
            # 敏感词检测
            word_violations = await self._check_sensitive_words(text)
            violations.extend(word_violations)
            
            # 计算总风险分数
            for violation in word_violations:
                total_risk_score += violation["severity"]
                if violation["action"] == FilterAction.BLOCK.value:
                    is_blocked = True
                elif violation["action"] == FilterAction.REPLACE.value:
                    # 替换敏感词
                    word = violation["matched_text"]
                    replacement = "*" * len(word)
                    filtered_text = filtered_text.replace(word, replacement)
            
            # 规范化风险分数
            risk_score = min(100, total_risk_score * 2)
            
            # 高风险自动阻止
            if risk_score >= 80:
                is_blocked = True
            
            return FilterResult(
                original_text=text,
                filtered_text=filtered_text,
                is_blocked=is_blocked,
                violations=violations,
                risk_score=risk_score
            )
            
        except Exception as e:
            self.logger.error(f"Text filtering error: {e}")
            # 出错时不过滤，但记录日志
            return FilterResult(
                original_text=text,
                filtered_text=text,
                is_blocked=False,
                violations=[],
                risk_score=0
            )
    
    async def _check_sensitive_words(self, text: str) -> List[Dict[str, Any]]:
        """检查敏感词"""
        violations = []
        text_lower = text.lower()
        
        for category, words in self.sensitive_words.items():
            for word in words:
                if word.lower() in text_lower:
                    # 查找所有匹配位置
                    start_pos = 0
                    while True:
                        pos = text_lower.find(word.lower(), start_pos)
                        if pos == -1:
                            break
                        
                        violation = {
                            "rule": f"敏感词: {word}",
                            "category": category.value,
                            "severity": self._get_word_severity(category),
                            "action": self._get_word_action(category).value,
                            "matched_text": text[pos:pos+len(word)],
                            "start": pos,
                            "end": pos + len(word)
                        }
                        violations.append(violation)
                        
                        start_pos = pos + 1
        
        return violations
    
    def _get_word_severity(self, category: FilterCategory) -> int:
        """获取词汇严重程度"""
        severity_map = {
            FilterCategory.PROFANITY: 4,
            FilterCategory.VIOLENCE: 8,
            FilterCategory.HATE_SPEECH: 9,
            FilterCategory.SEXUAL_CONTENT: 7,
            FilterCategory.PERSONAL_INFO: 6,
            FilterCategory.SPAM: 3,
            FilterCategory.CUSTOM: 5
        }
        return severity_map.get(category, 5)
    
    def _get_word_action(self, category: FilterCategory) -> FilterAction:
        """获取词汇过滤动作"""
        action_map = {
            FilterCategory.PROFANITY: FilterAction.REPLACE,
            FilterCategory.VIOLENCE: FilterAction.BLOCK,
            FilterCategory.HATE_SPEECH: FilterAction.BLOCK,
            FilterCategory.SEXUAL_CONTENT: FilterAction.REPLACE,
            FilterCategory.PERSONAL_INFO: FilterAction.REPLACE,
            FilterCategory.SPAM: FilterAction.WARNING,
            FilterCategory.CUSTOM: FilterAction.WARNING
        }
        return action_map.get(category, FilterAction.WARNING)
    
    def add_sensitive_word(self, word: str, category: FilterCategory):
        """添加敏感词"""
        self.sensitive_words[category].add(word.lower())
        self.logger.info(f"Added sensitive word: {word} to category: {category.value}")
    
    def remove_sensitive_word(self, word: str, category: FilterCategory):
        """移除敏感词"""
        self.sensitive_words[category].discard(word.lower())
        self.logger.info(f"Removed sensitive word: {word} from category: {category.value}")
    
    def add_filter_rule(self, rule: FilterRule):
        """添加过滤规则"""
        self.filter_rules.append(rule)
        self.logger.info(f"Added filter rule: {rule.description}")
    
    def remove_filter_rule(self, pattern: str):
        """移除过滤规则"""
        self.filter_rules = [
            rule for rule in self.filter_rules 
            if rule.pattern != pattern
        ]
        self.logger.info(f"Removed filter rule: {pattern}")
    
    def add_whitelist(self, text: str):
        """添加白名单"""
        self.whitelist.add(text.lower())
        self.logger.info(f"Added to whitelist: {text}")
    
    def remove_whitelist(self, text: str):
        """移除白名单"""
        self.whitelist.discard(text.lower())
        self.logger.info(f"Removed from whitelist: {text}")
    
    async def batch_filter(self, texts: List[str]) -> List[FilterResult]:
        """批量过滤文本"""
        tasks = [self.filter_text(text) for text in texts]
        return await asyncio.gather(*tasks)
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_rules": len(self.filter_rules),
            "total_sensitive_words": sum(len(words) for words in self.sensitive_words.values()),
            "whitelist_size": len(self.whitelist),
            "categories": {
                category.value: len(words) 
                for category, words in self.sensitive_words.items()
            }
        }


class ContentFilter:
    """内容过滤器（高级版本）"""
    
    def __init__(self):
        self.logger = logging.getLogger("security.content_filter")
        self.sensitive_word_filter = SensitiveWordFilter()
        
        # 内容分析器
        self.content_analyzers = {}
        
    async def analyze_content(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """全面分析内容"""
        try:
            # 基础过滤
            filter_result = await self.sensitive_word_filter.filter_text(text)
            
            # 内容特征分析
            features = await self._analyze_content_features(text)
            
            # 上下文分析
            context_analysis = await self._analyze_context(text, context or {})
            
            return {
                "filter_result": filter_result,
                "content_features": features,
                "context_analysis": context_analysis,
                "final_risk_score": self._calculate_final_risk_score(
                    filter_result, features, context_analysis
                )
            }
            
        except Exception as e:
            self.logger.error(f"Content analysis error: {e}")
            return {
                "filter_result": FilterResult(
                    original_text=text,
                    filtered_text=text,
                    is_blocked=False,
                    violations=[],
                    risk_score=0
                ),
                "content_features": {},
                "context_analysis": {},
                "final_risk_score": 0
            }
    
    async def _analyze_content_features(self, text: str) -> Dict[str, Any]:
        """分析内容特征"""
        features = {
            "length": len(text),
            "word_count": len(text.split()),
            "has_urls": bool(re.search(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text)),
            "has_email": bool(re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)),
            "has_phone": bool(re.search(r'\b\d{11}\b', text)),
            "uppercase_ratio": sum(1 for c in text if c.isupper()) / len(text) if text else 0,
            "special_char_ratio": sum(1 for c in text if not c.isalnum() and not c.isspace()) / len(text) if text else 0,
            "repeated_chars": len(re.findall(r'(.)\1{2,}', text)),  # 连续重复字符
        }
        
        return features
    
    async def _analyze_context(self, text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """分析上下文"""
        analysis = {
            "user_history_risk": context.get("user_risk_score", 0),
            "conversation_context": context.get("conversation_type", "unknown"),
            "time_based_risk": self._calculate_time_risk(context.get("timestamp")),
            "frequency_risk": context.get("message_frequency", 0)
        }
        
        return analysis
    
    def _calculate_time_risk(self, timestamp: Optional[float]) -> int:
        """计算时间相关风险"""
        if not timestamp:
            return 0
        
        # 夜间时段风险较高
        import datetime
        dt = datetime.datetime.fromtimestamp(timestamp)
        hour = dt.hour
        
        if 23 <= hour or hour <= 5:  # 深夜时段
            return 5
        elif 6 <= hour <= 8 or 22 <= hour <= 23:  # 早晚时段
            return 2
        else:
            return 0
    
    def _calculate_final_risk_score(
        self,
        filter_result: FilterResult,
        features: Dict[str, Any],
        context_analysis: Dict[str, Any]
    ) -> int:
        """计算最终风险分数"""
        base_score = filter_result.risk_score
        
        # 内容特征风险
        feature_risk = 0
        if features.get("uppercase_ratio", 0) > 0.5:
            feature_risk += 10  # 大量大写字母
        if features.get("special_char_ratio", 0) > 0.3:
            feature_risk += 15  # 大量特殊字符
        if features.get("repeated_chars", 0) > 3:
            feature_risk += 10  # 大量重复字符
        
        # 上下文风险
        context_risk = sum(context_analysis.values())
        
        # 计算最终分数
        final_score = base_score + feature_risk + context_risk
        
        return min(100, final_score)


# 全局过滤器实例
content_filter = ContentFilter()
sensitive_word_filter = SensitiveWordFilter()


def get_content_filter() -> ContentFilter:
    """获取内容过滤器实例"""
    return content_filter


def get_sensitive_word_filter() -> SensitiveWordFilter:
    """获取敏感词过滤器实例"""
    return sensitive_word_filter