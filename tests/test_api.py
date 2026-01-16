import pytest
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import app


def test_index_route():
    client = app.test_client()
    response = client.get('/')
    assert response.status_code == 200

def test_upload_file():
    client = app.test_client()

    # 检查上传路由是否存在
    response = client.post('/upload')
    assert response.status_code == 400  # 应返回错误，因为没有文件

def test_api_endpoints():
    client = app.test_client()

    # 测试 transcript 端点
    response = client.get('/api/transcript')
    assert response.status_code == 200

    # 测试 status 端点
    response = client.get('/api/status')
    assert response.status_code == 200

    # 测试 clear 端点
    response = client.post('/api/clear')
    assert response.status_code == 200