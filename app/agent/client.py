"""
PPIO model client implementation.
"""
import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional, Union

import httpx
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .config import PPIOModelConfig
from .exceptions import ModelAPIError, ConfigurationError

logger = logging.getLogger(__name__)


class PPIOModelClient:
    """PPIO模型客户端封装"""
    
    def __init__(self, config: PPIOModelConfig):
        self.config = config
        self._validate_config()
        
        # 初始化OpenAI客户端，使用PPIO的兼容API
        self.client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout,
            max_retries=config.max_retries
        )
        
        # 统计信息
        self.request_count = 0
        self.total_tokens = 0
        self.error_count = 0
    
    def _validate_config(self) -> None:
        """验证配置"""
        if not self.config.api_key:
            raise ConfigurationError("PPIO API key is required")
        
        if not self.config.api_key.startswith("sk_"):
            raise ConfigurationError("Invalid PPIO API key format")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError))
    )
    async def test_connection(self) -> bool:
        """测试模型连接"""
        try:
            start_time = time.time()
            response = await self.client.chat.completions.create(
                model=self.config.model_name,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            
            # 记录统计信息
            self.request_count += 1
            if hasattr(response, 'usage') and response.usage:
                self.total_tokens += response.usage.total_tokens
            
            logger.info(f"Connection test successful in {time.time() - start_time:.2f}s")
            return bool(response.choices)
            
        except Exception as e:
            self.error_count += 1
            logger.error(f"PPIO model connection test failed: {e}")
            return False
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError))
    )
    async def extract_structured_info(
        self, 
        content: str, 
        system_prompt: str,
        response_format: Optional[Dict[str, Any]] = None,
        functions: Optional[List[Dict[str, Any]]] = None,
        function_call: Optional[Union[str, Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """提取结构化信息，支持结构化输出和function calling"""
        try:
            start_time = time.time()
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content}
            ]
            
            # 构建请求参数
            request_params = {
                "model": self.config.model_name,
                "messages": messages,
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
            }
            
            # 优先使用结构化输出
            if response_format and self.config.supports_structured_output():
                request_params["response_format"] = response_format
                logger.debug("Using structured output format")
            
            # 如果支持function calling且提供了functions
            elif functions and self.config.supports_function_calling():
                request_params["functions"] = functions
                if function_call:
                    request_params["function_call"] = function_call
                logger.debug("Using function calling")
            
            response = await self.client.chat.completions.create(**request_params)
            
            # 记录统计信息
            self.request_count += 1
            if hasattr(response, 'usage') and response.usage:
                self.total_tokens += response.usage.total_tokens
            
            if not response.choices:
                raise ModelAPIError("No response from model")
            
            choice = response.choices[0]
            
            # 处理function call响应
            if hasattr(choice.message, 'function_call') and choice.message.function_call:
                try:
                    function_args = json.loads(choice.message.function_call.arguments)
                    return {
                        "function_call": {
                            "name": choice.message.function_call.name,
                            "arguments": function_args
                        }
                    }
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse function call arguments: {e}")
                    return {"raw_function_call": choice.message.function_call.arguments}
            
            # 处理普通文本响应
            content_text = choice.message.content
            if not content_text:
                raise ModelAPIError("Empty response from model")
            
            # 尝试解析JSON响应
            try:
                result = json.loads(content_text)
                logger.info(f"Structured extraction completed in {time.time() - start_time:.2f}s")
                return result
            except json.JSONDecodeError:
                # 如果不是JSON，返回原始内容
                logger.warning("Response is not valid JSON, returning raw content")
                return {"raw_content": content_text}
                
        except Exception as e:
            self.error_count += 1
            logger.error(f"PPIO model API call failed: {e}")
            raise ModelAPIError(f"Failed to extract structured info: {str(e)}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError))
    )
    async def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        **kwargs
    ) -> str:
        """通用聊天完成接口"""
        try:
            start_time = time.time()
            
            request_params = {
                "model": self.config.model_name,
                "messages": messages,
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
                **kwargs
            }
            
            response = await self.client.chat.completions.create(**request_params)
            
            # 记录统计信息
            self.request_count += 1
            if hasattr(response, 'usage') and response.usage:
                self.total_tokens += response.usage.total_tokens
            
            if not response.choices:
                raise ModelAPIError("No response from model")
            
            content = response.choices[0].message.content
            if not content:
                raise ModelAPIError("Empty response from model")
            
            logger.info(f"Chat completion finished in {time.time() - start_time:.2f}s")
            return content
            
        except Exception as e:
            self.error_count += 1
            logger.error(f"PPIO chat completion failed: {e}")
            raise ModelAPIError(f"Chat completion failed: {str(e)}")
    
    async def function_call(
        self,
        messages: List[Dict[str, str]],
        functions: List[Dict[str, Any]],
        function_call: Optional[Union[str, Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Function calling接口"""
        if not self.config.supports_function_calling():
            raise ModelAPIError(f"Model {self.config.model_name} does not support function calling")
        
        try:
            start_time = time.time()
            
            request_params = {
                "model": self.config.model_name,
                "messages": messages,
                "functions": functions,
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
            }
            
            if function_call:
                request_params["function_call"] = function_call
            
            response = await self.client.chat.completions.create(**request_params)
            
            # 记录统计信息
            self.request_count += 1
            if hasattr(response, 'usage') and response.usage:
                self.total_tokens += response.usage.total_tokens
            
            if not response.choices:
                raise ModelAPIError("No response from model")
            
            choice = response.choices[0]
            
            if hasattr(choice.message, 'function_call') and choice.message.function_call:
                try:
                    function_args = json.loads(choice.message.function_call.arguments)
                    result = {
                        "type": "function_call",
                        "function_call": {
                            "name": choice.message.function_call.name,
                            "arguments": function_args
                        }
                    }
                    logger.info(f"Function call completed in {time.time() - start_time:.2f}s")
                    return result
                except json.JSONDecodeError as e:
                    raise ModelAPIError(f"Failed to parse function call arguments: {e}")
            else:
                # 返回普通文本响应
                return {
                    "type": "text",
                    "content": choice.message.content
                }
                
        except Exception as e:
            self.error_count += 1
            logger.error(f"Function call failed: {e}")
            raise ModelAPIError(f"Function call failed: {str(e)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取客户端统计信息"""
        return {
            "request_count": self.request_count,
            "total_tokens": self.total_tokens,
            "error_count": self.error_count,
            "error_rate": self.error_count / max(self.request_count, 1),
            "model_name": self.config.model_name,
            "supports_structured_output": self.config.supports_structured_output(),
            "supports_function_calling": self.config.supports_function_calling()
        }
    
    def reset_stats(self) -> None:
        """重置统计信息"""
        self.request_count = 0
        self.total_tokens = 0
        self.error_count = 0
    
    async def close(self):
        """关闭客户端连接"""
        if hasattr(self.client, 'close'):
            await self.client.close()
        logger.info(f"Client closed. Final stats: {self.get_stats()}")