"""
加密服务
"""

import os
import hashlib
import secrets
import logging
from typing import Optional, Union, Dict, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from app.config import settings


class EncryptionService:
    """加密服务"""
    
    def __init__(self, master_key: Optional[str] = None):
        self.logger = logging.getLogger("security.encryption")
        
        # 主密钥
        self.master_key = master_key or getattr(settings, 'MASTER_KEY', None)
        if not self.master_key:
            self.master_key = self._generate_master_key()
            self.logger.warning("No master key provided, generated new one")
        
        # 初始化Fernet加密器
        self.fernet = self._create_fernet_cipher(self.master_key)
        
        # 加密算法配置
        self.hash_algorithm = hashes.SHA256()
        self.key_iterations = 100000
    
    def _generate_master_key(self) -> str:
        """生成主密钥"""
        return base64.urlsafe_b64encode(os.urandom(32)).decode()
    
    def _create_fernet_cipher(self, master_key: str) -> Fernet:
        """创建Fernet加密器"""
        try:
            # 如果master_key不是32字节的base64编码，需要派生
            try:
                key_bytes = base64.urlsafe_b64decode(master_key.encode())
                if len(key_bytes) != 32:
                    raise ValueError("Invalid key length")
            except:
                # 从master_key派生32字节密钥
                key_bytes = self._derive_key(master_key.encode(), b"master_salt")
            
            fernet_key = base64.urlsafe_b64encode(key_bytes)
            return Fernet(fernet_key)
            
        except Exception as e:
            self.logger.error(f"Failed to create Fernet cipher: {e}")
            raise
    
    def _derive_key(self, password: bytes, salt: bytes) -> bytes:
        """派生密钥"""
        kdf = PBKDF2HMAC(
            algorithm=self.hash_algorithm,
            length=32,
            salt=salt,
            iterations=self.key_iterations,
        )
        return kdf.derive(password)
    
    def encrypt(self, data: Union[str, bytes]) -> str:
        """加密数据"""
        try:
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            encrypted_data = self.fernet.encrypt(data)
            return base64.urlsafe_b64encode(encrypted_data).decode()
            
        except Exception as e:
            self.logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt(self, encrypted_data: str) -> str:
        """解密数据"""
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = self.fernet.decrypt(encrypted_bytes)
            return decrypted_data.decode('utf-8')
            
        except Exception as e:
            self.logger.error(f"Decryption failed: {e}")
            raise
    
    def encrypt_with_password(self, data: Union[str, bytes], password: str) -> Dict[str, str]:
        """使用密码加密数据"""
        try:
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            # 生成随机盐
            salt = os.urandom(16)
            
            # 派生密钥
            key = self._derive_key(password.encode(), salt)
            
            # 创建Fernet实例
            fernet_key = base64.urlsafe_b64encode(key)
            fernet = Fernet(fernet_key)
            
            # 加密数据
            encrypted_data = fernet.encrypt(data)
            
            return {
                "encrypted_data": base64.urlsafe_b64encode(encrypted_data).decode(),
                "salt": base64.urlsafe_b64encode(salt).decode()
            }
            
        except Exception as e:
            self.logger.error(f"Password encryption failed: {e}")
            raise
    
    def decrypt_with_password(
        self,
        encrypted_data: str,
        salt: str,
        password: str
    ) -> str:
        """使用密码解密数据"""
        try:
            # 解码数据
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            salt_bytes = base64.urlsafe_b64decode(salt.encode())
            
            # 派生密钥
            key = self._derive_key(password.encode(), salt_bytes)
            
            # 创建Fernet实例
            fernet_key = base64.urlsafe_b64encode(key)
            fernet = Fernet(fernet_key)
            
            # 解密数据
            decrypted_data = fernet.decrypt(encrypted_bytes)
            return decrypted_data.decode('utf-8')
            
        except Exception as e:
            self.logger.error(f"Password decryption failed: {e}")
            raise
    
    def hash_password(self, password: str) -> Dict[str, str]:
        """哈希密码"""
        try:
            # 生成随机盐
            salt = secrets.token_hex(16)
            
            # 使用PBKDF2哈希密码
            password_hash = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt.encode('utf-8'),
                self.key_iterations
            )
            
            return {
                "hash": password_hash.hex(),
                "salt": salt
            }
            
        except Exception as e:
            self.logger.error(f"Password hashing failed: {e}")
            raise
    
    def verify_password(self, password: str, stored_hash: str, salt: str) -> bool:
        """验证密码"""
        try:
            # 使用相同的盐和算法哈希输入密码
            password_hash = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt.encode('utf-8'),
                self.key_iterations
            )
            
            # 比较哈希值
            return secrets.compare_digest(password_hash.hex(), stored_hash)
            
        except Exception as e:
            self.logger.error(f"Password verification failed: {e}")
            return False
    
    def generate_secure_token(self, length: int = 32) -> str:
        """生成安全令牌"""
        return secrets.token_urlsafe(length)
    
    def generate_api_key(self) -> str:
        """生成API密钥"""
        return f"sk-{secrets.token_urlsafe(32)}"
    
    def hash_data(self, data: Union[str, bytes], algorithm: str = "sha256") -> str:
        """哈希数据"""
        try:
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            if algorithm == "sha256":
                hash_obj = hashlib.sha256(data)
            elif algorithm == "sha512":
                hash_obj = hashlib.sha512(data)
            elif algorithm == "md5":
                hash_obj = hashlib.md5(data)
            else:
                raise ValueError(f"Unsupported hash algorithm: {algorithm}")
            
            return hash_obj.hexdigest()
            
        except Exception as e:
            self.logger.error(f"Data hashing failed: {e}")
            raise
    
    def encrypt_sensitive_fields(self, data: Dict[str, Any], fields: list) -> Dict[str, Any]:
        """加密敏感字段"""
        try:
            encrypted_data = data.copy()
            
            for field in fields:
                if field in encrypted_data and encrypted_data[field]:
                    encrypted_data[field] = self.encrypt(str(encrypted_data[field]))
            
            return encrypted_data
            
        except Exception as e:
            self.logger.error(f"Field encryption failed: {e}")
            raise
    
    def decrypt_sensitive_fields(self, data: Dict[str, Any], fields: list) -> Dict[str, Any]:
        """解密敏感字段"""
        try:
            decrypted_data = data.copy()
            
            for field in fields:
                if field in decrypted_data and decrypted_data[field]:
                    try:
                        decrypted_data[field] = self.decrypt(decrypted_data[field])
                    except:
                        # 如果解密失败，保持原值
                        self.logger.warning(f"Failed to decrypt field: {field}")
            
            return decrypted_data
            
        except Exception as e:
            self.logger.error(f"Field decryption failed: {e}")
            raise
    
    def create_checksum(self, data: Union[str, bytes]) -> str:
        """创建校验和"""
        return self.hash_data(data, "sha256")
    
    def verify_checksum(self, data: Union[str, bytes], checksum: str) -> bool:
        """验证校验和"""
        try:
            calculated_checksum = self.create_checksum(data)
            return secrets.compare_digest(calculated_checksum, checksum)
        except:
            return False
    
    def get_encryption_info(self) -> Dict[str, Any]:
        """获取加密信息"""
        return {
            "hash_algorithm": self.hash_algorithm.name,
            "key_iterations": self.key_iterations,
            "fernet_available": self.fernet is not None,
            "master_key_set": bool(self.master_key)
        }


# 全局加密服务实例
encryption_service = None


def get_encryption_service() -> EncryptionService:
    """获取加密服务实例"""
    global encryption_service
    if encryption_service is None:
        encryption_service = EncryptionService()
    return encryption_service


# 便捷函数
def encrypt_data(data: Union[str, bytes]) -> str:
    """加密数据（便捷函数）"""
    return get_encryption_service().encrypt(data)


def decrypt_data(encrypted_data: str) -> str:
    """解密数据（便捷函数）"""
    return get_encryption_service().decrypt(encrypted_data)


def hash_password(password: str) -> Dict[str, str]:
    """哈希密码（便捷函数）"""
    return get_encryption_service().hash_password(password)


def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    """验证密码（便捷函数）"""
    return get_encryption_service().verify_password(password, stored_hash, salt)


def generate_secure_token(length: int = 32) -> str:
    """生成安全令牌（便捷函数）"""
    return get_encryption_service().generate_secure_token(length)