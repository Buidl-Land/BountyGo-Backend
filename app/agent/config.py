"""
Configuration for PPIO model and URL agent settings.
"""
import asyncio
import aiohttp
from typing import Optional
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings


class PPIOModelConfig(BaseModel):
    """PPIO模型配置类"""
    api_key: str = Field(..., description="PPIO API密钥")
    base_url: str = Field(default="https://api.ppinfra.com/v3/openai", description="PPIO API基础URL")
    model_name: str = Field(default="moonshotai/kimi-k2-instruct", description="模型名称")
    max_tokens: int = Field(default=4000, description="最大token数")
    temperature: float = Field(default=0.1, description="温度参数")
    timeout: int = Field(default=60, description="请求超时时间(秒)")
    max_retries: int = Field(default=3, description="最大重试次数")

    @validator('api_key')
    def validate_api_key(cls, v):
        """验证API密钥格式"""
        if not v or not isinstance(v, str):
            raise ValueError("API密钥不能为空")
        if not v.startswith('sk_'):
            raise ValueError("API密钥格式无效，应以'sk_'开头")
        if len(v) < 10:
            raise ValueError("API密钥长度过短")
        return v

    @validator('temperature')
    def validate_temperature(cls, v):
        """验证温度参数范围"""
        if not 0 <= v <= 2:
            raise ValueError("温度参数必须在0-2之间")
        return v

    @validator('max_tokens')
    def validate_max_tokens(cls, v):
        """验证最大token数"""
        if v <= 0 or v > 32000:
            raise ValueError("最大token数必须在1-32000之间")
        return v

    async def validate_api_connection(self) -> bool:
        """验证API连接和密钥有效性"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # 发送简单的模型列表请求来验证API密钥
            test_payload = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": "test"}],
                "max_tokens": 1
            }
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=test_payload
                ) as response:
                    if response.status == 200:
                        return True
                    elif response.status == 401:
                        raise ValueError("API密钥无效或已过期")
                    elif response.status == 403:
                        raise ValueError("API密钥权限不足")
                    else:
                        error_text = await response.text()
                        raise ValueError(f"API连接失败: {response.status} - {error_text}")
                        
        except asyncio.TimeoutError:
            raise ValueError(f"API连接超时 ({self.timeout}秒)")
        except aiohttp.ClientError as e:
            raise ValueError(f"网络连接错误: {str(e)}")
        except Exception as e:
            raise ValueError(f"API验证失败: {str(e)}")

    def get_supported_models(self) -> list[str]:
        """获取支持的模型列表（按优先级排序）"""
        return [
            "qwen/qwen3-coder-480b-a35b-instruct",  # 支持function-calling和structured-outputs
            "moonshotai/kimi-k2-instruct",          # 支持function-calling和structured-outputs
            "deepseek/deepseek-r1-0528",            # 支持structured-outputs和function-calling
            "qwen/qwen3-235b-a22b-instruct-2507"    # 支持function-calling和structured-outputs
        ]

    def supports_structured_output(self) -> bool:
        """检查当前模型是否支持结构化输出"""
        structured_models = [
            "qwen/qwen3-coder-480b-a35b-instruct",
            "moonshotai/kimi-k2-instruct", 
            "deepseek/deepseek-r1-0528",
            "qwen/qwen3-235b-a22b-instruct-2507"
        ]
        return self.model_name in structured_models

    def supports_function_calling(self) -> bool:
        """检查当前模型是否支持function calling"""
        function_calling_models = [
            "qwen/qwen3-coder-480b-a35b-instruct",
            "moonshotai/kimi-k2-instruct",
            "deepseek/deepseek-r1-0528", 
            "qwen/qwen3-235b-a22b-instruct-2507"
        ]
        return self.model_name in function_calling_models


class URLAgentSettings(BaseSettings):
    """URL代理设置"""
    # PPIO模型配置
    ppio_api_key: Optional[str] = Field(default=None, env="PPIO_API_KEY", description="PPIO API密钥")
    ppio_base_url: str = Field(default="https://api.ppinfra.com/v3/openai", env="PPIO_BASE_URL")
    ppio_model_name: str = Field(default="moonshotai/kimi-k2-instruct", env="PPIO_MODEL_NAME")
    ppio_max_tokens: int = Field(default=4000, env="PPIO_MAX_TOKENS")
    ppio_temperature: float = Field(default=0.1, env="PPIO_TEMPERATURE")
    
    # 内容提取配置
    content_extraction_timeout: int = Field(default=30, env="CONTENT_EXTRACTION_TIMEOUT")
    max_content_length: int = Field(default=50000, env="MAX_CONTENT_LENGTH")
    
    # 代理配置
    use_proxy: bool = Field(default=False, env="USE_PROXY")
    proxy_url: Optional[str] = Field(default=None, env="PROXY_URL")
    
    # 缓存配置
    enable_content_cache: bool = Field(default=True, env="ENABLE_CONTENT_CACHE")
    content_cache_ttl: int = Field(default=3600, env="CONTENT_CACHE_TTL")  # 1小时
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # 忽略额外的环境变量

    def get_ppio_config(self) -> PPIOModelConfig:
        """获取PPIO模型配置"""
        if not self.ppio_api_key:
            raise ValueError("PPIO_API_KEY is required for URL agent functionality")
        
        return PPIOModelConfig(
            api_key=self.ppio_api_key,
            base_url=self.ppio_base_url,
            model_name=self.ppio_model_name,
            max_tokens=self.ppio_max_tokens,
            temperature=self.ppio_temperature
        )


# 全局设置实例
url_agent_settings = URLAgentSettings()