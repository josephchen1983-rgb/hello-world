"""
MQTT 客户端模块
"""
import paho.mqtt.client as mqtt
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class MQTTClient:
    """管理 MQTT 标准客户端"""
    
    def __init__(self, app=None):
        """初始化 MQTT 客户端"""
        self.app = app
        self.client = mqtt.Client()
        self.connected = False
        self.subscribed_topics = set()
        self.data_callbacks = []
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """初始化应用"""
        self.app = app
        
        # 配置 MQTT 客户端回调
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.client.on_publish = self._on_publish
        self.client.on_subscribe = self._on_subscribe
        
        # 连接到 MQTT Broker
        self.connect()
    
    def connect(self):
        """连接到 MQTT Broker"""
        try:
            self.client.connect(
                self.app.config['MQTT_BROKER_HOST'],
                self.app.config['MQTT_BROKER_PORT'],
                keepalive=self.app.config['MQTT_KEEPALIVE']
            )
            self.client.loop_start()
            logger.info("MQTT 客户端已启动")
        except Exception as e:
            logger.error(f"MQTT 连接失败: {e}")
    
    def disconnect(self):
        """断开 MQTT Broker"""
        self.client.loop_stop()
        self.client.disconnect()
    
    def subscribe(self, topic):
        """订阅 MQTT 主题"""
        self.client.subscribe(topic, qos=self.app.config['MQTT_QOS'])
        self.subscribed_topics.add(topic)
        logger.info(f"已订阅: {topic}")
    
    def publish(self, topic, payload, qos=1):
        """发布 MQTT 消息"""
        try:
            self.client.publish(topic, payload, qos=qos)
            logger.info(f"已发布: {topic}")
        except Exception as e:
            logger.error(f"发布失败: {e}")
    
    def register_callback(self, callback):
        """注册数据回调函数"""
        self.data_callbacks.append(callback)
    
    def _on_connect(self, client, userdata, flags, rc):
        """连接回调"""
        if rc == 0:
            logger.info("MQTT 客户端已连接")
            self.connected = True
            
            # 订阅配置的主题
            for topic in self.app.config['MQTT_TOPICS']:
                self.subscribe(topic)
        else:
            logger.error(f"MQTT 连接失败: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """断开回调"""
        self.connected = False
        if rc != 0:
            logger.warning(f"意外断开: {rc}")
    
    def _on_message(self, client, userdata, msg):
        """接收消息回调"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
            logger.debug(f"接收消息 - 主题: {topic}, 载荷: {payload}")
            
            # 解析 JSON 数据
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                logger.warning(f"无效的 JSON 数据: {payload}")
                return
            
            # 执行标注的回调
            for callback in self.data_callbacks:
                try:
                    callback(topic, data)
                except Exception as e:
                    logger.error(f"回调函数字护失败: {e}")
        except Exception as e:
            logger.error(f"处理消息失败: {e}")
    
    def _on_publish(self, client, userdata, mid):
        """发布回调"""
        logger.debug(f"消息已发布: {mid}")
    
    def _on_subscribe(self, client, userdata, mid, granted_qos):
        """订阅回调"""
        logger.debug(f"订阅完成: {mid}")
