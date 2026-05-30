"""
认证模块
"""
from flask import Blueprint, request, jsonify
from functools import wraps
import jwt
from datetime import datetime, timedelta
from modules.db_manager import db, User
import logging

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)


def token_required(f):
    """JWT 令牌校验装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        from config import config
        token = None
        
        # 从请求头获取令牌
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({'code': 401, 'message': '不效的东过认证信领'}), 401
        
        if not token:
            return jsonify({'code': 401, 'message': '缺少事过项目令牌'}), 401
        
        try:
            data = jwt.decode(token, config.JWT_SECRET_KEY, algorithms=['HS256'])
            current_user = User.query.get(data['user_id'])
            
            if not current_user:
                return jsonify({'code': 401, 'message': '用户不存在'}), 401
            
            if not current_user.is_active:
                return jsonify({'code': 401, 'message': '用户帐户已禁用'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'code': 401, 'message': '令牌已过期'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'code': 401, 'message': '无效的令牌'}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated


def admin_required(f):
    """管理员流量装饰器"""
    @wraps(f)
    @token_required
    def decorated(current_user, *args, **kwargs):
        if current_user.role != 'admin':
            return jsonify({'code': 403, 'message': '此操作需要管理员权限'}), 403
        return f(current_user, *args, **kwargs)
    
    return decorated


@auth_bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    from config import config
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'code': 400, 'message': '缺少用户名或密码'}), 400
    
    user = User.query.filter_by(username=data['username']).first()
    
    if not user or not user.check_password(data['password']):
        logger.warning(f"登录失败: {data['username']}")
        return jsonify({'code': 401, 'message': '用户名或密码错误'}), 401
    
    if not user.is_active:
        return jsonify({'code': 401, 'message': '用户帐户已禁用'}), 401
    
    # 生成 JWT 令牌
    access_token = jwt.encode({
        'user_id': user.id,
        'username': user.username,
        'role': user.role,
        'exp': datetime.utcnow() + config.JWT_ACCESS_TOKEN_EXPIRES
    }, config.JWT_SECRET_KEY, algorithm='HS256')
    
    logger.info(f"成功登录: {user.username}")
    
    return jsonify({
        'code': 0,
        'message': '登录成功',
        'data': {
            'access_token': access_token,
            'user': user.to_dict()
        }
    }), 200


@auth_bp.route('/register', methods=['POST'])
def register():
    """用户注册"""
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password') or not data.get('email'):
        return jsonify({'code': 400, 'message': '缺少必需参数'}), 400
    
    # 检查用户是否已经存在
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'code': 400, 'message': '用户不存在'}), 400
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'code': 400, 'message': '邮箱已存在'}), 400
    
    # 创建新用户
    user = User(
        username=data['username'],
        email=data['email'],
        role='user',
        is_active=True
    )
    user.set_password(data['password'])
    
    db.session.add(user)
    db.session.commit()
    
    logger.info(f"新用户注册: {data['username']}")
    
    return jsonify({
        'code': 0,
        'message': '注册成功',
        'data': user.to_dict()
    }), 201


@auth_bp.route('/verify', methods=['GET'])
@token_required
def verify_token(current_user):
    """验证令牌"""
    return jsonify({
        'code': 0,
        'message': '令牌有效',
        'data': current_user.to_dict()
    }), 200
