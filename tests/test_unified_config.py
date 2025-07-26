"""
Tests for unified configuration manager.
"""
import os
import pytest
from unittest.mock import patch

from app.agent.unified_config import (
    UnifiedConfigManager, AgentRole, AgentConfig, ModelProvider,
    get_config_manager, get_agent_config
)


class TestUnifiedConfigManager:
    """Test unified configuration manager"""
    
    @patch.dict('os.environ', {
        'PPIO_API_KEY': 'sk_test_key',
        'URL_PARSER_MODEL': 'test-model',
        'WORKFORCE_SIZE': '3'
    })
    def test_config_loading_from_env(self):
        """Test configuration loading from environment variables"""
        config_manager = UnifiedConfigManager()
        config_manager.initialize()
        
        # 检查Agent配置
        url_agent_config = config_manager.get_agent_config(AgentRole.URL_PARSER)
        assert url_agent_config is not None
        assert url_agent_config.api_key == 'sk_test_key'
        assert url_agent_config.model_name == 'test-model'
        
        # 检查工作流配置
        workflow_config = config_manager.get_workflow_config()
        assert workflow_config.workforce_size == 3
    
    @patch.dict('os.environ', {
        'PPIO_API_KEY': 'sk_test_key'
    })
    def test_default_agent_configs(self):
        """Test default agent configurations"""
        config_manager = UnifiedConfigManager()
        config_manager.initialize()
        
        # 检查是否创建了默认的Agent配置
        url_config = config_manager.get_agent_config(AgentRole.URL_PARSER)
        image_config = config_manager.get_agent_config(AgentRole.IMAGE_ANALYZER)
        
        assert url_config is not None
        assert image_config is not None
        
        # 检查模型能力
        assert url_config.supports_function_calling
        assert image_config.supports_vision
    
    @patch.dict('os.environ', {
        'PPIO_API_KEY': 'sk_test_key'
    })
    def test_config_validation(self):
        """Test configuration validation"""
        config_manager = UnifiedConfigManager()
        config_manager.initialize()
        
        # 配置应该通过验证
        assert config_manager.is_initialized()
        
        # 测试无效配置 - 这应该在创建时就失败
        with pytest.raises(ValueError, match="PPIO API密钥格式无效"):
            AgentConfig(
                role=AgentRole.URL_PARSER,
                provider=ModelProvider.PPIO,
                model_name="test-model",
                api_key="invalid_key",  # 无效的API密钥格式
                temperature=0.1
            )
    
    def test_global_config_manager(self):
        """Test global configuration manager instance"""
        with patch.dict('os.environ', {'PPIO_API_KEY': 'sk_test_key'}):
            # 第一次调用应该创建实例
            manager1 = get_config_manager()
            assert manager1 is not None
            assert manager1.is_initialized()
            
            # 第二次调用应该返回同一个实例
            manager2 = get_config_manager()
            assert manager1 is manager2
    
    def test_convenience_functions(self):
        """Test convenience functions"""
        with patch.dict('os.environ', {
            'PPIO_API_KEY': 'sk_test_key',
            'URL_PARSER_MODEL': 'custom-model'
        }):
            # 重置全局配置管理器以应用新的环境变量
            from app.agent.unified_config import reset_config_manager
            reset_config_manager()
            
            # 测试便捷函数
            url_config = get_agent_config(AgentRole.URL_PARSER)
            assert url_config is not None
            assert url_config.model_name == 'custom-model'
    
    @patch.dict('os.environ', {
        'PPIO_API_KEY': 'sk_test_key'
    })
    def test_config_summary(self):
        """Test configuration summary"""
        config_manager = get_config_manager()
        summary = config_manager.get_config_summary()
        
        assert 'system' in summary
        assert 'workflow' in summary
        assert 'agents' in summary
        assert summary['initialized'] is True
        
        # 检查Agent摘要
        agents_summary = summary['agents']
        assert AgentRole.URL_PARSER.value in agents_summary
        assert 'model' in agents_summary[AgentRole.URL_PARSER.value]
        assert 'provider' in agents_summary[AgentRole.URL_PARSER.value]


class TestAgentConfig:
    """Test agent configuration"""
    
    def test_valid_agent_config(self):
        """Test valid agent configuration"""
        config = AgentConfig(
            role=AgentRole.URL_PARSER,
            provider=ModelProvider.PPIO,
            model_name="qwen/qwen3-coder-480b-a35b-instruct",
            api_key="sk_valid_key_12345",
            temperature=0.1
        )
        
        assert config.role == AgentRole.URL_PARSER
        assert config.provider == ModelProvider.PPIO
        assert config.supports_function_calling
        assert config.supports_structured_output
    
    def test_invalid_api_key(self):
        """Test invalid API key validation"""
        with pytest.raises(ValueError, match="API密钥格式无效"):
            AgentConfig(
                role=AgentRole.URL_PARSER,
                provider=ModelProvider.PPIO,
                model_name="test-model",
                api_key="invalid_key",
                temperature=0.1
            )
    
    def test_invalid_temperature(self):
        """Test invalid temperature validation"""
        with pytest.raises(ValueError, match="温度参数必须在0-2之间"):
            AgentConfig(
                role=AgentRole.URL_PARSER,
                provider=ModelProvider.PPIO,
                model_name="test-model",
                api_key="sk_valid_key",
                temperature=3.0
            )
    
    def test_model_capabilities_detection(self):
        """Test model capabilities detection"""
        # 测试视觉模型
        vision_config = AgentConfig(
            role=AgentRole.IMAGE_ANALYZER,
            provider=ModelProvider.PPIO,
            model_name="baidu/ernie-4.5-vl-28b-a3b",
            api_key="sk_valid_key",
            temperature=0.1
        )
        
        assert vision_config.supports_vision
        
        # 测试非视觉模型
        text_config = AgentConfig(
            role=AgentRole.URL_PARSER,
            provider=ModelProvider.PPIO,
            model_name="moonshotai/kimi-k2-instruct",
            api_key="sk_valid_key",
            temperature=0.1
        )
        
        assert not text_config.supports_vision
        assert text_config.supports_function_calling