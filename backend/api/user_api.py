"""
用户相关 API
"""
from flask import Blueprint, request, jsonify
from modules.db_manager import db, User
from modules.auth import token_required, admin_required
import logging

logger = logging.getLogger(__name__)

user_bp = Blueprint('users', __name__)


@user_bp.route('', methods=['GET'])
@admin_required
def get_users(current_user):
    """获取所有用户（仅管理员）"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    pagination = User.query.paginate(page=page, per_page=per_page)
    users = [user.to_dict() for user in pagination.items]
    
    return jsonify({
        'code': 0,
        'message': '获取用户列表成功',
        'data': {
            'users': users,
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page
        }
    }), 200


@user_bp.route('/<int:user_id>', methods=['GET'])
@token_required
def get_user(current_user, user_id):
    """获取用户详情"""
    # 普通用户只能查看自己的信息，管理员可以查看任何用户
    if current_user.role != 'admin' and current_user.id != user_id:
        return jsonify({'code': 403, 'message': '无权访问'}), 403
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'code': 404, 'message': '用户不存在'}), 404
    
    return jsonify({
        'code': 0,
        'message': '获取用户详情成功',
        'data': user.to_dict()
    }), 200


@user_bp.route('/<int:user_id>', methods=['PUT'])
@token_required
def update_user(current_user, user_id):
    """更新用户信息"""
    # 普通用户只能更新自己的信息
    if current_user.role != 'admin' and current_user.id != user_id:
        return jsonify({'code': 403, 'message': '无权访问'}), 403
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'code': 404, 'message': '用户不存在'}), 404
    
    data = request.get_json()
    
    # 允许更新的字段
    if 'email' in data:
        # 检查邮箱是否已被使用
        if User.query.filter_by(email=data['email']).filter(User.id != user_id).first():
            return jsonify({'code': 400, 'message': '邮箱已被使用'}), 400
        user.email = data['email']
    
    if 'password' in data:
        user.set_password(data['password'])
    
    # 只有管理员可以修改角色和状态
    if current_user.role == 'admin':
        if 'role' in data:
            user.role = data['role']
        if 'is_active' in data:
            user.is_active = data['is_active']
    
    db.session.commit()
    logger.info(f"用户 {user_id} 信息已更新")
    
    return jsonify({
        'code': 0,
        'message': '用户信息更新成功',
        'data': user.to_dict()
    }), 200


@user_bp.route('/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(current_user, user_id):
    """删除用户（仅管理员）"""
    if user_id == current_user.id:
        return jsonify({'code': 400, 'message': '不能删除自己'}), 400
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'code': 404, 'message': '用户不存在'}), 404
    
    db.session.delete(user)
    db.session.commit()
    logger.info(f"用户 {user_id} 已删除")
    
    return jsonify({
        'code': 0,
        'message': '用户删除成功'
    }), 200
