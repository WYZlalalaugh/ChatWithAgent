-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS chatbot_platform 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

-- 使用数据库
USE chatbot_platform;

-- 创建用户表
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    platform_user_id VARCHAR(255) NOT NULL,
    platform_type VARCHAR(50) NOT NULL,
    username VARCHAR(255),
    avatar_url TEXT,
    profile_data JSON,
    last_active DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_platform_user (platform_type, platform_user_id),
    INDEX idx_platform_type (platform_type),
    INDEX idx_last_active (last_active)
);

-- 创建机器人表
CREATE TABLE IF NOT EXISTS bots (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    platform_type VARCHAR(50) NOT NULL,
    platform_config JSON,
    llm_config JSON,
    agent_config JSON,
    knowledge_base_ids JSON,
    plugin_configs JSON,
    status ENUM('active', 'inactive', 'error') DEFAULT 'inactive',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_platform_type (platform_type),
    INDEX idx_status (status)
);

-- 创建对话表
CREATE TABLE IF NOT EXISTS conversations (
    id VARCHAR(36) PRIMARY KEY,
    bot_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    chat_type ENUM('private', 'group', 'channel') DEFAULT 'private',
    platform_chat_id VARCHAR(255),
    context_data JSON,
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_message_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bot_id) REFERENCES bots(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_bot_user (bot_id, user_id),
    INDEX idx_last_message (last_message_at)
);

-- 创建消息表
CREATE TABLE IF NOT EXISTS chat_messages (
    id VARCHAR(36) PRIMARY KEY,
    conversation_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36),
    message_type ENUM('text', 'image', 'audio', 'video', 'file', 'system') DEFAULT 'text',
    content LONGTEXT,
    metadata JSON,
    is_from_bot BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_conversation (conversation_id),
    INDEX idx_created_at (created_at)
);

-- 创建知识库表
CREATE TABLE IF NOT EXISTS knowledge_bases (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    embedding_model VARCHAR(255) DEFAULT 'text-embedding-ada-002',
    vector_store_type VARCHAR(50) DEFAULT 'chroma',
    vector_store_config JSON,
    config JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_name (name)
);

-- 创建文档表
CREATE TABLE IF NOT EXISTS documents (
    id VARCHAR(36) PRIMARY KEY,
    knowledge_base_id VARCHAR(36) NOT NULL,
    title VARCHAR(500) NOT NULL,
    file_path VARCHAR(1000),
    content_type VARCHAR(100),
    source_type ENUM('upload', 'url', 'api', 'chat') DEFAULT 'upload',
    content LONGTEXT,
    metadata JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (knowledge_base_id) REFERENCES knowledge_bases(id) ON DELETE CASCADE,
    INDEX idx_knowledge_base (knowledge_base_id),
    INDEX idx_source_type (source_type)
);

-- 创建文档分块表
CREATE TABLE IF NOT EXISTS document_chunks (
    id VARCHAR(36) PRIMARY KEY,
    document_id VARCHAR(36) NOT NULL,
    content LONGTEXT NOT NULL,
    embedding JSON,
    metadata JSON,
    chunk_index INT NOT NULL,
    chunk_type VARCHAR(50) DEFAULT 'text',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
    INDEX idx_document (document_id),
    INDEX idx_chunk_index (chunk_index)
);

-- 创建聊天记录表（用于导入已有聊天记录）
CREATE TABLE IF NOT EXISTS chat_records (
    id VARCHAR(36) PRIMARY KEY,
    conversation_id VARCHAR(36),
    knowledge_base_id VARCHAR(36) NOT NULL,
    chat_content LONGTEXT NOT NULL,
    chat_metadata JSON,
    chat_time DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE SET NULL,
    FOREIGN KEY (knowledge_base_id) REFERENCES knowledge_bases(id) ON DELETE CASCADE,
    INDEX idx_knowledge_base (knowledge_base_id),
    INDEX idx_chat_time (chat_time)
);

-- 创建多模态内容表
CREATE TABLE IF NOT EXISTS multimodal_contents (
    id VARCHAR(36) PRIMARY KEY,
    knowledge_base_id VARCHAR(36) NOT NULL,
    content_type ENUM('image', 'audio', 'video') NOT NULL,
    file_path VARCHAR(1000) NOT NULL,
    original_filename VARCHAR(500),
    extracted_text LONGTEXT,
    content_metadata JSON,
    embedding JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (knowledge_base_id) REFERENCES knowledge_bases(id) ON DELETE CASCADE,
    INDEX idx_knowledge_base (knowledge_base_id),
    INDEX idx_content_type (content_type)
);

-- 创建插件表
CREATE TABLE IF NOT EXISTS plugins (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    version VARCHAR(50) NOT NULL,
    description TEXT,
    author VARCHAR(255),
    manifest JSON,
    status ENUM('active', 'inactive', 'error') DEFAULT 'inactive',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_name (name),
    INDEX idx_status (status)
);

-- 创建机器人插件关联表
CREATE TABLE IF NOT EXISTS bot_plugins (
    id VARCHAR(36) PRIMARY KEY,
    bot_id VARCHAR(36) NOT NULL,
    plugin_id VARCHAR(36) NOT NULL,
    config JSON,
    is_enabled BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bot_id) REFERENCES bots(id) ON DELETE CASCADE,
    FOREIGN KEY (plugin_id) REFERENCES plugins(id) ON DELETE CASCADE,
    UNIQUE KEY unique_bot_plugin (bot_id, plugin_id)
);

-- 创建模型配置表
CREATE TABLE IF NOT EXISTS models (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    provider VARCHAR(100) NOT NULL,
    model_type ENUM('chat', 'embedding', 'image', 'audio') DEFAULT 'chat',
    api_config JSON,
    parameters JSON,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_provider (provider),
    INDEX idx_model_type (model_type),
    INDEX idx_is_active (is_active)
);

-- 创建模型使用日志表
CREATE TABLE IF NOT EXISTS model_usage_logs (
    id VARCHAR(36) PRIMARY KEY,
    model_id VARCHAR(36) NOT NULL,
    bot_id VARCHAR(36),
    conversation_id VARCHAR(36),
    request_tokens INT DEFAULT 0,
    response_tokens INT DEFAULT 0,
    total_tokens INT DEFAULT 0,
    cost DECIMAL(10, 6) DEFAULT 0,
    response_time INT,
    status ENUM('success', 'error', 'timeout') DEFAULT 'success',
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (model_id) REFERENCES models(id) ON DELETE CASCADE,
    FOREIGN KEY (bot_id) REFERENCES bots(id) ON DELETE SET NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE SET NULL,
    INDEX idx_model (model_id),
    INDEX idx_created_at (created_at)
);

-- 创建用户权限表
CREATE TABLE IF NOT EXISTS user_permissions (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id VARCHAR(36),
    permission_level ENUM('read', 'write', 'admin') DEFAULT 'read',
    granted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    granted_by VARCHAR(36),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_resource (user_id, resource_type)
);

-- 插入默认数据
-- 默认管理员用户
INSERT IGNORE INTO users (id, platform_user_id, platform_type, username) 
VALUES ('admin-user-id', 'admin', 'system', 'Administrator');

-- 默认聊天模型
INSERT IGNORE INTO models (id, name, provider, model_type, api_config, parameters, is_active) 
VALUES 
('gpt-3.5-turbo-id', 'GPT-3.5 Turbo', 'openai', 'chat', '{"model": "gpt-3.5-turbo"}', '{"temperature": 0.7, "max_tokens": 2048}', TRUE),
('text-embedding-ada-002-id', 'Text Embedding Ada 002', 'openai', 'embedding', '{"model": "text-embedding-ada-002"}', '{}', TRUE);