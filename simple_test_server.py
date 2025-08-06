#!/usr/bin/env python3
"""
간단한 테스트 서버 - 패키지 의존성 없이 기본 테스트
"""

import json
import socket
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import time

class TestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        
        # CORS 헤더 추가
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        # 엔드포인트별 응답
        if parsed_path.path == '/health':
            response = {
                "status": "healthy",
                "timestamp": time.time(),
                "message": "테스트 서버가 정상 작동 중입니다"
            }
        elif parsed_path.path.startswith('/api/v1/'):
            response = {
                "status": "success",
                "endpoint": parsed_path.path,
                "message": "API 엔드포인트가 정상 작동합니다",
                "data": {
                    "search_results": [
                        {
                            "title": "테스트 검색 결과 1",
                            "url": "https://example.com/1",
                            "snippet": "이것은 테스트 검색 결과입니다."
                        }
                    ]
                }
            }
        else:
            response = {
                "error": "Not Found",
                "path": parsed_path.path
            }
        
        self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
    
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        # CORS 헤더 추가
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        try:
            request_data = json.loads(post_data.decode('utf-8'))
            response = {
                "status": "success",
                "received": request_data,
                "message": "POST 요청이 성공적으로 처리되었습니다",
                "timestamp": time.time()
            }
        except Exception as e:
            response = {
                "status": "error",
                "message": f"요청 처리 중 오류: {str(e)}"
            }
        
        self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
    
    def do_OPTIONS(self):
        # CORS 프리플라이트 요청 처리
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
    
    def log_message(self, format, *args):
        # 로그 출력
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {format % args}")

def check_port_available(port):
    """포트 사용 가능 여부 확인"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('', port))
            return True
        except OSError:
            return False

def start_test_server(port=8000):
    """테스트 서버 시작"""
    if not check_port_available(port):
        print(f"포트 {port}가 이미 사용 중입니다. 다른 포트를 시도합니다...")
        port = 8001
        if not check_port_available(port):
            print(f"포트 {port}도 사용 중입니다. 서버를 시작할 수 없습니다.")
            return None
    
    server = HTTPServer(('localhost', port), TestHandler)
    print(f"🚀 테스트 서버가 http://localhost:{port} 에서 시작되었습니다")
    print("다음 엔드포인트를 테스트할 수 있습니다:")
    print(f"  - GET  http://localhost:{port}/health")
    print(f"  - GET  http://localhost:{port}/api/v1/search")
    print(f"  - POST http://localhost:{port}/api/v1/chat")
    print("\nCtrl+C로 서버를 종료할 수 있습니다.")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n서버를 종료합니다...")
        server.shutdown()
        return server
    
    return server

if __name__ == "__main__":
    start_test_server()