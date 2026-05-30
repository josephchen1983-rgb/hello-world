"""
WebSocket 事件处理模块
"""
from flask_socketio import emit, join_room, leave_room
from flask import request
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def socketio_events(socketio, mqtt_client):
    """注册 WebSocket 事件"""
    
    # 存储客户端间隔映射
    client_rooms = {}
    
    @socketio.on('connect')
    def handle_connect():
        """客户端连接事件"""
        client_id = request.sid
        logger.info(f"WebSocket 客户端定连接: {client_id}")
        emit('response', {
            'data': '定连接成功',
            'timestamp': datetime.now().isoformat()
        })
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """客户端断开事件"""
        client_id = request.sid
        logger.info(f"WebSocket 客户端断开: {client_id}")
        
        # 清理客户端间隔
        if client_id in client_rooms:
            for room in client_rooms[client_id]:
                leave_room(room)
            del client_rooms[client_id]
    
    @socketio.on('subscribe')
    def handle_subscribe(data):
        """订阅事件"""
        client_id = request.sid
        topic = data.get('topic')
        
        if not topic:
            emit('error', {'message': '不效的主题'})
            return
        
        # 使用主题作为房间名称
        room = f"topic:{topic}"
        join_room(room)
        
        if client_id not in client_rooms:
            client_rooms[client_id] = set()
        client_rooms[client_id].add(room)
        
        logger.info(f"客户端 {client_id} 订阅主题: {topic}")
        
        emit('subscribe_success', {
            'topic': topic,
            'message': f'成功订阅 {topic}',
            'timestamp': datetime.now().isoformat()
        })
    
    @socketio.on('unsubscribe')
    def handle_unsubscribe(data):
        """取消订阅事件"""
        client_id = request.sid
        topic = data.get('topic')
        
        if not topic:
            emit('error', {'message': '不效的主题'})
            return
        
        room = f"topic:{topic}"
        leave_room(room)
        
        if client_id in client_rooms:
            client_rooms[client_id].discard(room)
        
        logger.info(f"客户端 {client_id} 取消订阅: {topic}")
        
        emit('unsubscribe_success', {
            'topic': topic,
            'message': f'成功取消订阅 {topic}',
            'timestamp': datetime.now().isoformat()
        })
    
    @socketio.on('get_status')
    def handle_get_status():
        """获取 MQTT 客户端状态"""
        emit('status', {
            'connected': mqtt_client.connected,
            'subscribed_topics': list(mqtt_client.subscribed_topics),
            'timestamp': datetime.now().isoformat()
        })
    
    # 注册 MQTT 数据回调
    def mqtt_data_callback(topic, data):
        """处理 MQTT 消息"""
        room = f"topic:{topic}"
        socketio.emit('mqtt_message', {
            'topic': topic,
            'data': data,
            'timestamp': datetime.now().isoformat()
        }, room=room)
    
    mqtt_client.register_callback(mqtt_data_callback)
