#!/usr/bin/env python3
"""
WebSocket 클라이언트 테스트
"""

import asyncio
import websockets
import json
import time

async def test_websocket():
    uri = "ws://127.0.0.1:8001/api/v1/ws/chat/test_conversation?user_id=test_user"
    
    try:
        print(f"연결 시도: {uri}")
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket 연결 성공!")
            
            # 연결 확인 메시지 수신
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                print(f"연결 응답: {response}")
            except asyncio.TimeoutError:
                print("연결 응답 타임아웃")
            
            # 테스트 메시지 전송
            test_message = {
                "type": "chat",
                "content": "안녕하세요! WebSocket 테스트입니다.",
                "model": "gemini",
                "agent_type": "web_search",
                "metadata": {
                    "timestamp": time.time(),
                    "user_id": "test_user"
                }
            }
            
            print(f"메시지 전송: {test_message}")
            await websocket.send(json.dumps(test_message))
            
            # 응답 수신
            print("응답 대기 중...")
            timeout_count = 0
            max_timeout = 3
            
            while timeout_count < max_timeout:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10)
                    response_data = json.loads(response)
                    print(f"수신: {response_data}")
                    
                    if response_data.get("type") == "assistant_end":
                        print("✅ 응답 완료!")
                        break
                        
                except asyncio.TimeoutError:
                    timeout_count += 1
                    print(f"응답 대기 타임아웃 ({timeout_count}/{max_timeout})")
                except json.JSONDecodeError as e:
                    print(f"JSON 파싱 오류: {e}")
                    print(f"원본 응답: {response}")
            
            # Ping 테스트
            print("\nPing 테스트...")
            ping_message = {"type": "ping"}
            await websocket.send(json.dumps(ping_message))
            
            try:
                pong_response = await asyncio.wait_for(websocket.recv(), timeout=5)
                print(f"Pong 응답: {pong_response}")
            except asyncio.TimeoutError:
                print("Pong 응답 타임아웃")
            
    except Exception as e:
        print(f"❌ WebSocket 연결 오류: {e}")
        return False
    
    return True

async def main():
    print("🚀 WebSocket 클라이언트 테스트 시작")
    print("=" * 50)
    
    success = await test_websocket()
    
    print("=" * 50)
    if success:
        print("✅ WebSocket 테스트 완료!")
    else:
        print("❌ WebSocket 테스트 실패!")

if __name__ == "__main__":
    asyncio.run(main())