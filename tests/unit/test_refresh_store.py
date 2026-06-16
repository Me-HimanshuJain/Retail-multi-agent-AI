import pytest
import time
from unittest.mock import patch, MagicMock
import src.api.refresh_store as refresh_store

def test_refresh_store_issue_consume_in_process():
    with patch("src.api.refresh_store._get_redis", return_value=None):
        token = refresh_store.issue("user1", "admin", 1)
        data = refresh_store.consume(token)
        assert data is not None
        assert data["username"] == "user1"
        assert data["role"] == "admin"
        assert refresh_store.consume(token) is None

def test_refresh_store_expired_in_process():
    with patch("src.api.refresh_store._get_redis", return_value=None):
        token = refresh_store.issue("user2", "viewer", -1)
        assert refresh_store.consume(token) is None

def test_refresh_store_revoke_in_process():
    with patch("src.api.refresh_store._get_redis", return_value=None):
        token = refresh_store.issue("user3", "operator", 10)
        refresh_store.revoke(token)
        assert refresh_store.consume(token) is None

def test_refresh_store_issue_redis():
    mock_redis = MagicMock()
    with patch("src.api.refresh_store._get_redis", return_value=mock_redis):
        token = refresh_store.issue("user1", "admin", 1)
        mock_redis.setex.assert_called_once()

def test_refresh_store_issue_redis_fallback():
    mock_redis = MagicMock()
    mock_redis.setex.side_effect = Exception("err")
    with patch("src.api.refresh_store._get_redis", return_value=mock_redis):
        token = refresh_store.issue("user1", "admin", 1)
        data = refresh_store.consume(token)
        # Should fallback to in_process
        assert data is not None

def test_refresh_store_consume_redis():
    mock_redis = MagicMock()
    mock_pipe = MagicMock()
    mock_redis.pipeline.return_value = mock_pipe
    mock_pipe.execute.return_value = ['{"username": "u1", "role": "admin"}']
    
    with patch("src.api.refresh_store._get_redis", return_value=mock_redis):
        data = refresh_store.consume("token1")
        assert data is not None
        assert data["username"] == "u1"
        
def test_refresh_store_consume_redis_not_found():
    mock_redis = MagicMock()
    mock_pipe = MagicMock()
    mock_redis.pipeline.return_value = mock_pipe
    mock_pipe.execute.return_value = [None]
    
    with patch("src.api.refresh_store._get_redis", return_value=mock_redis):
        data = refresh_store.consume("token_bad")
        assert data is None

def test_refresh_store_revoke_redis():
    mock_redis = MagicMock()
    with patch("src.api.refresh_store._get_redis", return_value=mock_redis):
        refresh_store.revoke("token1")
        mock_redis.delete.assert_called_once_with("refresh:token1")
