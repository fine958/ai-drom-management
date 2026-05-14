# attendance/consumers.py
import time
import json
import asyncio
import websockets
import logging
import traceback   # [新增] 导入 traceback 用于打印详细异常堆栈
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)

APP_KEY = 'sk-xuanji-2026714479-THdMeGpXZ25oWm5QdEFQVw=='


class ASRConsumer(AsyncWebsocketConsumer):
    """处理WebSocket连接，作为中转站连接vivo ASR API"""

    async def connect(self):
        """当有新的WebSocket连接请求时调用"""
        await self.accept()
        # [新增] 打印连接成功日志
        print("[DEBUG] 前端 WebSocket 连接已接受")
        logger.info("前端WebSocket连接成功")
        self.vivo_websocket = None
        self.asr_task = None

    async def disconnect(self, close_code):
        """当WebSocket连接断开时调用"""
        print(f"[DEBUG] 前端 WebSocket 连接断开，代码: {close_code}")   # [新增]
        logger.info(f"前端WebSocket连接断开，代码: {close_code}")
        if self.vivo_websocket:
            await self.vivo_websocket.close()
        if self.asr_task:
            self.asr_task.cancel()

    async def receive(self, text_data=None, bytes_data=None):
        """当从前端接收到消息时调用"""
        # [新增] 打印收到的消息类型
        if text_data:
            print(f"[DEBUG] 收到前端文本消息: {text_data[:200]}")   # 打印前200字符
        elif bytes_data:
            print(f"[DEBUG] 收到前端二进制消息，长度: {len(bytes_data)} 字节")
        else:
            print("[DEBUG] 收到空消息")

        # 处理文本消息（如启动指令、结束标识）
        if text_data:
            await self.handle_text_message(text_data)
        # 处理二进制消息（音频数据）
        elif bytes_data:
            await self.handle_binary_message(bytes_data)

    async def handle_text_message(self, message_str):
        """处理从前端发来的文本控制消息"""
        try:
            message = json.loads(message_str)
            msg_type = message.get('type')
            print(f"[DEBUG] 解析文本消息类型: {msg_type}")   # [新增]

            # 1. 前端发送的启动指令
            if msg_type == 'start':
                if self.vivo_websocket is None:
                    print("[DEBUG] 收到 start 指令，准备连接 vivo ASR...")   # [新增]
                    await self.connect_to_vivo_asr(message)
                else:
                    logger.warning("vivo连接已存在，忽略重复的start指令")

            # 2. 前端发送的结束标识
            elif msg_type == 'end':
                print("[DEBUG] 收到 end 指令")   # [新增]
                if self.vivo_websocket:
                    await self.vivo_websocket.send(" --end-- ")
                    logger.info("已向vivo发送结束标识")

            # 3. 前端主动要求关闭连接
            elif msg_type == 'close':
                print("[DEBUG] 收到 close 指令")   # [新增]
                if self.vivo_websocket:
                    await self.vivo_websocket.send(" --close-- ")
                    await self.vivo_websocket.close()
                    self.vivo_websocket = None
                    logger.info("已关闭vivo连接")

        except json.JSONDecodeError:
            print(f"[ERROR] 接收到非JSON格式的文本消息: {message_str}")   # [新增]
            logger.error(f"接收到非JSON格式的文本消息: {message_str}")

    async def handle_binary_message(self, audio_chunk):
        """处理从前端发来的二进制音频数据，并转发给vivo"""
        if self.vivo_websocket:
            try:
                await self.vivo_websocket.send(audio_chunk)
                # [新增] 打印转发成功（避免日志过多，可选）
                # print(f"[DEBUG] 转发音频帧，大小: {len(audio_chunk)} 字节")
            except Exception as e:
                print(f"[ERROR] 转发音频数据到vivo时出错: {e}")   # [新增]
                logger.error(f"转发音频数据到vivo时出错: {e}")
        else:
            print("[WARNING] vivo连接不存在，无法转发音频数据")   # [新增]

    async def connect_to_vivo_asr(self, start_message):
        """主动连接到vivo的WebSocket ASR服务"""
        vivo_ws_url = "ws://api-ai.vivo.com.cn/asr/v2"

        import uuid
        params = {
            "user_id": start_message.get('user_id', str(uuid.uuid4()).replace('-', '')[:32]),
            "package": start_message.get('package', "com.your.app"),
            "client_version": start_message.get('client_version', "1.0.0"),
            "sdk_version": start_message.get('sdk_version', "1.0.0"),
            "system_time": str(int(time.time() * 1000)),
            "net_type": start_message.get('net_type', "1"),
            "engineid": start_message.get('engineid', "shortasrinput"),
            "requestId": str(uuid.uuid4()),
            "android_version": "unknown",  # 新增
            "system_version": "unknown",  # 新增
            "model": "unknown",  # 可选，建议加上
        }

        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        full_url = f"{vivo_ws_url}?{query_string}"

        extra_headers = [("Authorization", f"Bearer {APP_KEY}")]   # 注意格式

        print(f"[DEBUG] 准备连接 vivo ASR，URL: {full_url}")   # [新增]
        print(f"[DEBUG] 请求头: {extra_headers}")   # [新增]

        try:
            # 建立到vivo的连接
            self.vivo_websocket = await websockets.connect(full_url, extra_headers=extra_headers)
            print("[DEBUG] 成功连接到 vivo ASR 服务")   # [新增]
            logger.info("成功连接到vivo ASR服务")

            # 启动一个后台任务来持续接收vivo的识别结果
            self.asr_task = asyncio.create_task(self.receive_from_vivo_asr())

            # 发送启动识别的文本帧
            asr_start_message = {
                "type": "started",
                "request_id": params['requestId'],
                "asr_info": {
                    "end_vad_time": 300,
                    "audio_type": "pcm",
                    "chinese2digital": 0,
                    "punctuation": 1
                }
            }
            await self.vivo_websocket.send(json.dumps(asr_start_message))
            print("[DEBUG] 已向 vivo 发送启动识别指令")   # [新增]
            logger.info("已向vivo发送启动识别指令")

        except Exception as e:
            print(f"[ERROR] 连接vivo ASR服务失败: {e}")   # [新增]
            traceback.print_exc()   # [新增] 打印完整错误堆栈
            logger.error(f"连接vivo ASR服务失败: {e}")
            self.vivo_websocket = None
            # 通知前端连接失败
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'无法连接到语音识别服务: {str(e)}'
            }))

    async def receive_from_vivo_asr(self):
        """持续接收来自vivo的识别结果，并转发给前端"""
        try:
            async for message in self.vivo_websocket:
                print(f"[DEBUG] 收到 vivo 完整消息: {message}")
                # 然后转发给前端
                await self.send(text_data=message)
        except websockets.exceptions.ConnectionClosed:
            print("[DEBUG] 与 vivo ASR 服务的连接已关闭")   # [新增]
            logger.info("与vivo ASR服务的连接已关闭")
        except Exception as e:
            print(f"[ERROR] 接收vivo识别结果时出错: {e}")   # [新增]
            traceback.print_exc()
            logger.error(f"接收vivo识别结果时出错: {e}")
        finally:
            self.vivo_websocket = None