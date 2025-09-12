-- ChatAgent数据库初始化脚本

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS chatagent CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 使用数据库
USE chatagent;

-- 创建用户表
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    username VARCHAR(50) UNIQUE NOT NULL,
    nickname VARCHAR(100),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'user', 'developer') DEFAULT 'user',
    avatar_url VARCHAR(500),
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_username (username),
    INDEX idx_email (email),
    INDEX idx_role (role),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建机器人表
CREATE TABLE IF NOT EXISTS bots (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    avatar_url VARCHAR(500),
    user_id VARCHAR(36) NOT NULL,
    platform_type VARCHAR(50) NOT NULL,
    platform_config JSON,
    llm_config JSON,
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_platform_type (platform_type),
    INDEX idx_is_active (is_active),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建对话表
CREATE TABLE IF NOT EXISTS conversations (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    title VARCHAR(200) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    bot_id VARCHAR(36) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    platform_chat_id VARCHAR(255),
    status ENUM('active', 'paused', 'ended') DEFAULT 'active',
    context JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_message_at TIMESTAMP NULL,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (bot_id) REFERENCES bots(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_bot_id (bot_id),
    INDEX idx_platform (platform),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at),
    INDEX idx_last_message_at (last_message_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建消息表
CREATE TABLE IF NOT EXISTS messages (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    conversation_id VARCHAR(36) NOT NULL,
    content TEXT NOT NULL,
    message_type ENUM('text', 'image', 'audio', 'video', 'file', 'system') DEFAULT 'text',
    sender_type ENUM('user', 'bot', 'system') NOT NULL,
    sender_id VARCHAR(36),
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    INDEX idx_conversation_id (conversation_id),
    INDEX idx_sender_type (sender_type),
    INDEX idx_message_type (message_type),
    INDEX idx_created_at (created_at),
    INDEX idx_sender_id (sender_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建知识库表
CREATE TABLE IF NOT EXISTS knowledge_bases (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    user_id VARCHAR(36) NOT NULL,
    vector_store_type VARCHAR(50) DEFAULT 'chroma',
    vector_store_config JSON,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_is_active (is_active),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建文档表
CREATE TABLE IF NOT EXISTS documents (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    knowledge_base_id VARCHAR(36) NOT NULL,
    title VARCHAR(200) NOT NULL,
    content TEXT,
    file_path VARCHAR(500),
    file_type VARCHAR(50),
    file_size BIGINT,
    metadata JSON,
    processed_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (knowledge_base_id) REFERENCES knowledge_bases(id) ON DELETE CASCADE,
    INDEX idx_knowledge_base_id (knowledge_base_id),
    INDEX idx_file_type (file_type),
    INDEX idx_created_at (created_at),
    INDEX idx_processed_at (processed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建插件表
CREATE TABLE IF NOT EXISTS plugins (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    name VARCHAR(100) NOT NULL,
    version VARCHAR(20) NOT NULL,
    description TEXT,
    author VARCHAR(100),
    repository_url VARCHAR(500),
    config_schema JSON,
    is_active BOOLEAN DEFAULT FALSE,
    is_builtin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY unique_name_version (name, version),
    INDEX idx_name (name),
    INDEX idx_is_active (is_active),
    INDEX idx_is_builtin (is_builtin),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建用户插件配置表
CREATE TABLE IF NOT EXISTS user_plugin_configs (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    user_id VARCHAR(36) NOT NULL,
    plugin_id VARCHAR(36) NOT NULL,
    config JSON,
    is_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (plugin_id) REFERENCES plugins(id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_plugin (user_id, plugin_id),
    INDEX idx_user_id (user_id),
    INDEX idx_plugin_id (plugin_id),
    INDEX idx_is_enabled (is_enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建API密钥表
CREATE TABLE IF NOT EXISTS api_keys (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    user_id VARCHAR(36) NOT NULL,
    name VARCHAR(100) NOT NULL,
    key_hash VARCHAR(255) NOT NULL,
    permissions JSON,
    last_used_at TIMESTAMP NULL,
    expires_at TIMESTAMP NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_key_hash (key_hash),
    INDEX idx_is_active (is_active),
    INDEX idx_expires_at (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建系统配置表
CREATE TABLE IF NOT EXISTS system_configs (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    config_key VARCHAR(100) UNIQUE NOT NULL,
    config_value JSON,
    description TEXT,
    is_encrypted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_config_key (config_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 插入默认管理员用户
INSERT IGNORE INTO users (id, username, nickname, email, password_hash, role, is_active)
VALUES (
    'admin-user-id-000000000000000000',
    'admin',
    '系统管理员',
    'admin@chatagent.com',
    -- 密码: admin123 (使用bcrypt哈希)
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewvhJpTRGLRh3Mja',
    'admin',
    TRUE
);

-- 插入默认系统配置
INSERT IGNORE INTO system_configs (config_key, config_value, description) VALUES
('app.name', '"ChatAgent"', '应用名称'),
('app.version', '"1.0.0"', '应用版本'),
('app.description', '"开源大语言模型原生即时通信机器人开发平台"', '应用描述'),
('security.max_login_attempts', '5', '最大登录尝试次数'),
('security.lockout_duration', '300', '账户锁定时长（秒）'),
('rate_limit.default_requests_per_minute', '100', '默认每分钟请求限制'),
('rate_limit.default_burst_size', '20', '默认突发请求大小'),
('file.max_upload_size', '104857600', '最大上传文件大小（字节）'),
('file.allowed_extensions', '["jpg", "jpeg", "png", "gif", "pdf", "doc", "docx", "txt", "mp3", "mp4", "wav"]', '允许的文件扩展名');

-- 创建数据库索引优化
-- 为经常查询的字段创建复合索引
CREATE INDEX idx_conversations_user_bot ON conversations(user_id, bot_id);
CREATE INDEX idx_messages_conversation_created ON messages(conversation_id, created_at);
CREATE INDEX idx_documents_kb_processed ON documents(knowledge_base_id, processed_at);

-- 创建全文索引（用于搜索）
ALTER TABLE messages ADD FULLTEXT(content);
ALTER TABLE documents ADD FULLTEXT(title, content);

-- 设置数据库参数优化
SET GLOBAL innodb_buffer_pool_size = 268435456; -- 256MB
SET GLOBAL max_connections = 200;
SET GLOBAL query_cache_size = 67108864; -- 64MB
SET GLOBAL tmp_table_size = 33554432; -- 32MB
SET GLOBAL max_heap_table_size = 33554432; -- 32MB

-- 显示创建结果
SELECT 'Database initialization completed successfully!' as message;
SELECT TABLE_NAME, TABLE_ROWS, DATA_LENGTH, INDEX_LENGTH 
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = 'chatagent'
ORDER BY TABLE_NAME;