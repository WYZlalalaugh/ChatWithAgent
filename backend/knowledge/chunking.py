"""
内容分块器
"""

import re
import math
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from loguru import logger


@dataclass
class TextChunk:
    """文本块"""
    content: str
    start_index: int
    end_index: int
    metadata: Dict[str, Any]
    
    def __len__(self) -> int:
        return len(self.content)


class TextSplitter(ABC):
    """文本分割器基类"""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: Optional[List[str]] = None
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", "。", "！", "？", ". ", "! ", "? "]
    
    @abstractmethod
    def split_text(self, text: str) -> List[TextChunk]:
        """分割文本"""
        pass
    
    def _merge_splits(self, splits: List[str], separator: str) -> List[TextChunk]:
        """合并分割后的文本块"""
        chunks = []
        current_chunk = ""
        current_start = 0
        
        for i, split in enumerate(splits):
            if not split.strip():
                continue
                
            # 计算加上这个分割后的长度
            test_chunk = current_chunk + (separator if current_chunk else "") + split
            
            if len(test_chunk) <= self.chunk_size:
                # 可以添加到当前块
                current_chunk = test_chunk
            else:
                # 当前块已满，保存并开始新块
                if current_chunk:
                    chunk = TextChunk(
                        content=current_chunk,
                        start_index=current_start,
                        end_index=current_start + len(current_chunk),
                        metadata={
                            "chunk_index": len(chunks),
                            "separator": separator
                        }
                    )
                    chunks.append(chunk)
                
                # 开始新块，考虑重叠
                if self.chunk_overlap > 0 and current_chunk:
                    overlap_text = current_chunk[-self.chunk_overlap:]
                    current_chunk = overlap_text + separator + split
                    current_start = max(0, current_start + len(current_chunk) - len(overlap_text) - len(separator))
                else:
                    current_chunk = split
                    current_start = current_start + len(current_chunk) if chunks else 0
        
        # 添加最后一个块
        if current_chunk:
            chunk = TextChunk(
                content=current_chunk,
                start_index=current_start,
                end_index=current_start + len(current_chunk),
                metadata={
                    "chunk_index": len(chunks),
                    "separator": separator
                }
            )
            chunks.append(chunk)
        
        return chunks


class RecursiveCharacterTextSplitter(TextSplitter):
    """递归字符文本分割器"""
    
    def split_text(self, text: str) -> List[TextChunk]:
        """递归分割文本"""
        return self._split_text_recursive(text, self.separators)
    
    def _split_text_recursive(self, text: str, separators: List[str]) -> List[TextChunk]:
        """递归分割文本"""
        if not text.strip():
            return []
        
        if len(text) <= self.chunk_size:
            return [TextChunk(
                content=text,
                start_index=0,
                end_index=len(text),
                metadata={"chunk_index": 0}
            )]
        
        # 尝试使用分隔符分割
        for separator in separators:
            if separator in text:
                splits = text.split(separator)
                if len(splits) > 1:
                    # 递归处理每个分割
                    all_chunks = []
                    current_pos = 0
                    
                    for split in splits:
                        if split.strip():
                            # 递归分割大的片段
                            remaining_separators = separators[separators.index(separator) + 1:]
                            sub_chunks = self._split_text_recursive(split, remaining_separators)
                            
                            # 调整位置索引
                            for chunk in sub_chunks:
                                chunk.start_index += current_pos
                                chunk.end_index += current_pos
                                chunk.metadata["chunk_index"] = len(all_chunks)
                                all_chunks.append(chunk)
                        
                        current_pos += len(split) + len(separator)
                    
                    return all_chunks
        
        # 如果没有合适的分隔符，强制分割
        return self._force_split(text)
    
    def _force_split(self, text: str) -> List[TextChunk]:
        """强制分割文本"""
        chunks = []
        start = 0
        
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            
            # 尝试在单词边界分割
            if end < len(text):
                # 向前查找空格或标点
                for i in range(end, max(start, end - 100), -1):
                    if text[i] in [' ', '\n', '\t', '，', '。', '！', '？', ',', '.', '!', '?']:
                        end = i + 1
                        break
            
            chunk_content = text[start:end].strip()
            if chunk_content:
                chunk = TextChunk(
                    content=chunk_content,
                    start_index=start,
                    end_index=end,
                    metadata={
                        "chunk_index": len(chunks),
                        "force_split": True
                    }
                )
                chunks.append(chunk)
            
            # 计算下一个开始位置（考虑重叠）
            start = max(start + 1, end - self.chunk_overlap)
        
        return chunks


class SentenceTextSplitter(TextSplitter):
    """句子文本分割器"""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 100):
        super().__init__(chunk_size, chunk_overlap)
        # 中英文句子结束标点
        self.sentence_endings = [
            '。', '！', '？', '；',  # 中文
            '.', '!', '?', ';',      # 英文
            '\n\n'                   # 段落
        ]
    
    def split_text(self, text: str) -> List[TextChunk]:
        """按句子分割文本"""
        sentences = self._split_into_sentences(text)
        return self._merge_sentences_into_chunks(sentences)
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """分割成句子"""
        sentences = []
        current_sentence = ""
        
        for char in text:
            current_sentence += char
            
            if char in self.sentence_endings:
                sentence = current_sentence.strip()
                if sentence:
                    sentences.append(sentence)
                current_sentence = ""
        
        # 添加最后一个句子
        if current_sentence.strip():
            sentences.append(current_sentence.strip())
        
        return sentences
    
    def _merge_sentences_into_chunks(self, sentences: List[str]) -> List[TextChunk]:
        """合并句子成块"""
        chunks = []
        current_chunk = ""
        current_start = 0
        sentence_start = 0
        
        for i, sentence in enumerate(sentences):
            test_chunk = current_chunk + (" " if current_chunk else "") + sentence
            
            if len(test_chunk) <= self.chunk_size:
                current_chunk = test_chunk
            else:
                # 保存当前块
                if current_chunk:
                    chunk = TextChunk(
                        content=current_chunk,
                        start_index=current_start,
                        end_index=current_start + len(current_chunk),
                        metadata={
                            "chunk_index": len(chunks),
                            "sentence_count": i - sentence_start
                        }
                    )
                    chunks.append(chunk)
                
                # 开始新块
                current_chunk = sentence
                current_start = current_start + len(current_chunk) if chunks else 0
                sentence_start = i
        
        # 添加最后一个块
        if current_chunk:
            chunk = TextChunk(
                content=current_chunk,
                start_index=current_start,
                end_index=current_start + len(current_chunk),
                metadata={
                    "chunk_index": len(chunks),
                    "sentence_count": len(sentences) - sentence_start
                }
            )
            chunks.append(chunk)
        
        return chunks


class SemanticTextSplitter(TextSplitter):
    """语义文本分割器"""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 100,
        similarity_threshold: float = 0.7
    ):
        super().__init__(chunk_size, chunk_overlap)
        self.similarity_threshold = similarity_threshold
    
    def split_text(self, text: str) -> List[TextChunk]:
        """基于语义相似度分割文本"""
        # 首先按段落分割
        paragraphs = self._split_into_paragraphs(text)
        
        if len(paragraphs) <= 1:
            # 如果只有一个段落，退回到字符分割
            splitter = RecursiveCharacterTextSplitter(self.chunk_size, self.chunk_overlap)
            return splitter.split_text(text)
        
        # 计算段落相似度并分组
        paragraph_groups = self._group_similar_paragraphs(paragraphs)
        
        # 将分组合并成块
        return self._merge_groups_into_chunks(paragraph_groups, text)
    
    def _split_into_paragraphs(self, text: str) -> List[str]:
        """分割成段落"""
        paragraphs = re.split(r'\n\s*\n', text)
        return [p.strip() for p in paragraphs if p.strip()]
    
    def _group_similar_paragraphs(self, paragraphs: List[str]) -> List[List[str]]:
        """根据相似度分组段落"""
        if len(paragraphs) <= 1:
            return [paragraphs]
        
        groups = []
        current_group = [paragraphs[0]]
        
        for i in range(1, len(paragraphs)):
            # 计算与当前组的相似度（简化版本）
            similarity = self._calculate_similarity(
                " ".join(current_group),
                paragraphs[i]
            )
            
            if similarity >= self.similarity_threshold:
                current_group.append(paragraphs[i])
            else:
                groups.append(current_group)
                current_group = [paragraphs[i]]
        
        groups.append(current_group)
        return groups
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度（简化版本）"""
        # 简单的词汇重叠相似度
        words1 = set(re.findall(r'\w+', text1.lower()))
        words2 = set(re.findall(r'\w+', text2.lower()))
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _merge_groups_into_chunks(self, groups: List[List[str]], original_text: str) -> List[TextChunk]:
        """将分组合并成块"""
        chunks = []
        current_pos = 0
        
        for group_idx, group in enumerate(groups):
            group_text = "\n\n".join(group)
            
            if len(group_text) <= self.chunk_size:
                # 整个组作为一个块
                chunk = TextChunk(
                    content=group_text,
                    start_index=current_pos,
                    end_index=current_pos + len(group_text),
                    metadata={
                        "chunk_index": len(chunks),
                        "group_index": group_idx,
                        "paragraph_count": len(group)
                    }
                )
                chunks.append(chunk)
            else:
                # 组太大，需要进一步分割
                splitter = RecursiveCharacterTextSplitter(self.chunk_size, self.chunk_overlap)
                sub_chunks = splitter.split_text(group_text)
                
                for sub_chunk in sub_chunks:
                    sub_chunk.start_index += current_pos
                    sub_chunk.end_index += current_pos
                    sub_chunk.metadata.update({
                        "chunk_index": len(chunks),
                        "group_index": group_idx,
                        "is_sub_chunk": True
                    })
                    chunks.append(sub_chunk)
            
            current_pos += len(group_text) + 2  # +2 for \n\n
        
        return chunks


class ChunkingService:
    """分块服务"""
    
    def __init__(self):
        self.splitters = {
            "recursive": RecursiveCharacterTextSplitter,
            "sentence": SentenceTextSplitter,
            "semantic": SemanticTextSplitter
        }
    
    def chunk_text(
        self,
        text: str,
        strategy: str = "recursive",
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        **kwargs
    ) -> List[TextChunk]:
        """分块文本"""
        if strategy not in self.splitters:
            logger.warning(f"未知分块策略: {strategy}，使用默认策略")
            strategy = "recursive"
        
        splitter_class = self.splitters[strategy]
        splitter = splitter_class(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            **kwargs
        )
        
        chunks = splitter.split_text(text)
        logger.info(f"文本分块完成: {len(chunks)} 个块，策略: {strategy}")
        
        return chunks
    
    def register_splitter(self, name: str, splitter_class: type):
        """注册分割器"""
        self.splitters[name] = splitter_class
        logger.info(f"分割器已注册: {name}")
    
    def list_strategies(self) -> List[str]:
        """列出可用策略"""
        return list(self.splitters.keys())


# 全局分块服务实例
chunking_service = ChunkingService()