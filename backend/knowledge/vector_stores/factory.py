"""
向量数据库工厂和配置管理
"""

import logging
from typing import Dict, Any, Optional
from enum import Enum

from .manager import VectorStoreManager, VectorStoreType
from app.config import settings


class VectorStoreFactory:
    """向量数据库工厂类"""
    
    @staticmethod
    def create_manager(config: Optional[Dict[str, Any]] = None) -> VectorStoreManager:
        """创建向量数据库管理器"""
        default_config = {
            'dimension': settings.EMBEDDING_DIMENSION,
            'collection_name': 'default'
        }
        
        if config:
            default_config.update(config)
            
        return VectorStoreManager(default_config)
    
    @staticmethod
    def get_default_configs() -> Dict[VectorStoreType, Dict[str, Any]]:
        """获取默认配置"""
        return {
            VectorStoreType.CHROMA: {
                'type': 'chroma',
                'host': 'localhost',
                'port': 8000,
                'persist_directory': './data/chroma',
                'dimension': settings.EMBEDDING_DIMENSION,
                'collection_name': 'default'
            },
            VectorStoreType.FAISS: {
                'type': 'faiss',
                'index_type': 'IVFFlat',
                'nlist': 100,
                'persist_directory': './data/faiss',
                'metric_type': 'IP',
                'dimension': settings.EMBEDDING_DIMENSION,
                'collection_name': 'default'
            },
            VectorStoreType.QDRANT: {
                'type': 'qdrant',
                'host': 'localhost',
                'port': 6333,
                'api_key': None,
                'url': None,
                'distance_metric': 'Cosine',
                'dimension': settings.EMBEDDING_DIMENSION,
                'collection_name': 'default'
            },
            VectorStoreType.PINECONE: {
                'type': 'pinecone',
                'api_key': None,
                'environment': 'us-west1-gcp',
                'metric': 'cosine',
                'cloud': 'gcp',
                'region': 'us-west1',
                'dimension': settings.EMBEDDING_DIMENSION,
                'collection_name': 'default'
            }
        }
    
    @staticmethod
    def validate_config(store_type: VectorStoreType, config: Dict[str, Any]) -> bool:
        """验证配置"""
        try:
            required_fields = {
                VectorStoreType.CHROMA: ['dimension'],
                VectorStoreType.FAISS: ['dimension', 'persist_directory'],
                VectorStoreType.QDRANT: ['dimension'],
                VectorStoreType.PINECONE: ['api_key', 'dimension']
            }
            
            required = required_fields.get(store_type, [])
            for field in required:
                if field not in config or config[field] is None:
                    logging.error(f"Missing required field '{field}' for {store_type.value}")
                    return False
            
            # 验证维度
            dimension = config.get('dimension', 0)
            if not isinstance(dimension, int) or dimension <= 0:
                logging.error(f"Invalid dimension: {dimension}")
                return False
                
            return True
            
        except Exception as e:
            logging.error(f"Config validation failed: {str(e)}")
            return False


class VectorStoreConfigManager:
    """向量数据库配置管理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.configs: Dict[str, Dict[str, Any]] = {}
        
    def load_config(self, config_path: str) -> bool:
        """从文件加载配置"""
        try:
            import json
            with open(config_path, 'r', encoding='utf-8') as f:
                self.configs = json.load(f)
            return True
        except Exception as e:
            self.logger.error(f"Failed to load config from {config_path}: {str(e)}")
            return False
    
    def save_config(self, config_path: str) -> bool:
        """保存配置到文件"""
        try:
            import json
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.configs, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            self.logger.error(f"Failed to save config to {config_path}: {str(e)}")
            return False
    
    def add_config(self, name: str, store_type: VectorStoreType, config: Dict[str, Any]) -> bool:
        """添加配置"""
        try:
            if not VectorStoreFactory.validate_config(store_type, config):
                return False
                
            config['type'] = store_type.value
            self.configs[name] = config
            return True
        except Exception as e:
            self.logger.error(f"Failed to add config {name}: {str(e)}")
            return False
    
    def get_config(self, name: str) -> Optional[Dict[str, Any]]:
        """获取配置"""
        return self.configs.get(name)
    
    def remove_config(self, name: str) -> bool:
        """移除配置"""
        if name in self.configs:
            del self.configs[name]
            return True
        return False
    
    def list_configs(self) -> Dict[str, str]:
        """列出所有配置"""
        return {name: config.get('type', 'unknown') for name, config in self.configs.items()}
    
    def get_default_config(self, store_type: VectorStoreType) -> Dict[str, Any]:
        """获取默认配置"""
        defaults = VectorStoreFactory.get_default_configs()
        return defaults.get(store_type, {})


# 全局向量数据库管理器实例
vector_store_manager = None

def get_vector_store_manager() -> VectorStoreManager:
    """获取全局向量数据库管理器"""
    global vector_store_manager
    if vector_store_manager is None:
        vector_store_manager = VectorStoreFactory.create_manager()
    return vector_store_manager


async def initialize_default_vector_store():
    """初始化默认向量数据库"""
    try:
        manager = get_vector_store_manager()
        
        # 根据配置选择默认的向量数据库
        default_store_type = getattr(settings, 'DEFAULT_VECTOR_STORE', 'chroma').lower()
        
        store_type_map = {
            'chroma': VectorStoreType.CHROMA,
            'faiss': VectorStoreType.FAISS,
            'qdrant': VectorStoreType.QDRANT,
            'pinecone': VectorStoreType.PINECONE
        }
        
        store_type = store_type_map.get(default_store_type, VectorStoreType.CHROMA)
        
        # 获取默认配置
        config = VectorStoreFactory.get_default_configs()[store_type]
        
        # 从环境变量或设置中覆盖配置
        if store_type == VectorStoreType.PINECONE:
            pinecone_api_key = getattr(settings, 'PINECONE_API_KEY', None)
            if pinecone_api_key:
                config['api_key'] = pinecone_api_key
        elif store_type == VectorStoreType.QDRANT:
            qdrant_url = getattr(settings, 'QDRANT_URL', None)
            qdrant_api_key = getattr(settings, 'QDRANT_API_KEY', None)
            if qdrant_url:
                config['url'] = qdrant_url
            if qdrant_api_key:
                config['api_key'] = qdrant_api_key
        
        # 创建默认存储
        success = await manager.create_store('default', store_type, config)
        
        if success:
            logging.info(f"Initialized default vector store: {store_type.value}")
        else:
            logging.error(f"Failed to initialize default vector store: {store_type.value}")
            
        return success
        
    except Exception as e:
        logging.error(f"Failed to initialize default vector store: {str(e)}")
        return False