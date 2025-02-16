import pytest
import os
from whisk.config import WhiskConfig, ClientConfigError, ServerConfig, FastAPIConfig, NatsConfig, ClientConfig
import tempfile
import yaml

def test_config_requires_client_id():
    """Test that config raises error when WHISK_CLIENT_ID is not set"""
    # Ensure WHISK_CLIENT_ID is not set
    if "WHISK_CLIENT_ID" in os.environ:
        del os.environ["WHISK_CLIENT_ID"]
    
    with pytest.raises(ClientConfigError) as exc_info:
        WhiskConfig.from_env()
    
    assert "WHISK_CLIENT_ID environment variable must be set" in str(exc_info.value)

def test_config_loads_with_client_id():
    """Test that config loads successfully when WHISK_CLIENT_ID is set"""
    os.environ["WHISK_CLIENT_ID"] = "test_client"
    
    config = WhiskConfig.from_env()
    assert config.client.id == "test_client"

def test_config_with_custom_values():
    """Test that config loads custom values from environment"""
    os.environ.update({
        "WHISK_CLIENT_ID": "test_client",
        "WHISK_NATS_URL": "nats://custom:4222",
        "WHISK_NATS_USER": "custom_user",
        "WHISK_NATS_PASSWORD": "custom_pass",
        "WHISK_CHROMA_PATH": "custom_path"
    })
    
    config = WhiskConfig.from_env()
    assert config.client.id == "test_client"
    assert config.nats.url == "nats://custom:4222"
    assert config.nats.user == "custom_user"
    assert config.nats.password == "custom_pass"
    assert config.chroma.path == "custom_path"

def test_config_fastapi_only():
    config = WhiskConfig(
        server=ServerConfig(
            type="fastapi",
            fastapi=FastAPIConfig(
                host="0.0.0.0",
                port=8000,
                prefix="/v1"
            )
        ),
        nats=NatsConfig(
            url="nats://localhost:4222",
            user="test",
            password="test"
        ),
        client=ClientConfig(
            id="test_client"
        )
    )
    assert config.server.type == "fastapi"
    assert config.server.fastapi.host == "0.0.0.0"
    assert config.server.fastapi.port == 8000

def test_config_nats_only():
    config = WhiskConfig(
        server={
            "type": "nats",
            "nats": {
                "url": "nats://localhost:4222",
                "user": "test",
                "password": "test",
                "client_id": "test_client"
            }
        },
        nats={
            "url": "nats://localhost:4222",
            "user": "test",
            "password": "test"
        },
        client={
            "id": "test_client"
        }
    )
    assert config.server.type == "nats"
    assert config.server.nats.url == "nats://localhost:4222"

def test_config_both_services():
    config = WhiskConfig(
        server={
            "type": "both",
            "fastapi": {
                "host": "0.0.0.0",
                "port": 8000,
                "prefix": "/v1"
            },
            "nats": {
                "url": "nats://localhost:4222",
                "user": "test",
                "password": "test",
                "client_id": "test_client"
            }
        },
        nats={
            "url": "nats://localhost:4222",
            "user": "test",
            "password": "test"
        },
        client={
            "id": "test_client"
        }
    )
    assert config.server.type == "both"
    assert config.server.fastapi.port == 8000
    assert config.server.nats.url == "nats://localhost:4222"

def test_config_from_yaml():
    config_data = {
        "server": {
            "type": "both",
            "fastapi": {
                "host": "0.0.0.0",
                "port": 8000,
                "prefix": "/v1"
            },
            "nats": {
                "url": "nats://localhost:4222",
                "user": "test",
                "password": "test",
                "client_id": "test_client"
            }
        },
        "nats": {
            "url": "nats://localhost:4222",
            "user": "test",
            "password": "test"
        },
        "client": {
            "id": "test_client"
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml') as tmp:
        yaml.dump(config_data, tmp)
        tmp.flush()
        
        config = WhiskConfig.from_file(tmp.name)
        assert config.server.type == "both"
        assert config.server.fastapi.port == 8000
        assert config.server.nats.url == "nats://localhost:4222"

def test_invalid_server_type():
    with pytest.raises(ValueError):
        WhiskConfig(
            server={
                "type": "invalid",
                "fastapi": {
                    "host": "0.0.0.0",
                    "port": 8000
                }
            }
        ) 