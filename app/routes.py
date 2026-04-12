from flask import Blueprint, request, jsonify
from app import db
from app.models import User, Household, Category, Transaction
from app.schemas import (user_schema, users_schema, household_schema, 
                        category_schema, categories_schema, transaction_schema)
from app.utils import calcular_transferencias
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

api = Blueprint('api', __name__)

# ==========================================
# 🔐 AUTENTICACIÓN Y REGISTRO
# ==========================================

@api.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password') or not data.get('email'):
        return jsonify({"error": "Faltan datos obligatorios"}), 400
    
    if User.query.filter_by(username=data['username']).first():
        return jsonify({"error": "El nombre de usuario ya existe"}), 400

    new_user = User(username=data['username'], email=data['email'])
    new_user.set_password(data['password']) # Encriptamos la clave
    
    db.session.add(new_user)
    db.session.commit()
    return user_schema.jsonify(new_user), 201

@api.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data.get('username')).first()
    
    if user and user.check_password(data.get('password')):
        # Si la clave es correcta, generamos el Token
        access_token = create_access_token(identity=str(user.id))
        return jsonify({
            "token": access_token,
            "user": user_schema.dump(user)
        }), 200
    
    return jsonify({"error": "Credenciales inválidas"}), 401

# ==========================================
# 🏠 GRUPOS (PROTEGIDOS)
# ==========================================

@api.route('/households', methods=['POST'])
@jwt_required() # Solo usuarios logueados
def create_household():
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    new_household = Household(name=data['name'], type=data.get('type', 'home'))
    
    # Agregamos automáticamente al creador como miembro
    creator = User.query.get(current_user_id)
    new_household.members.append(creator)
    
    # Agregamos otros miembros si vienen en el JSON
    user_ids = data.get('user_ids', [])
    if user_ids:
        others = User.query.filter(User.id.in_(user_ids)).all()
        new_household.members.extend(others)

    db.session.add(new_household)
    db.session.commit()
    return household_schema.jsonify(new_household), 201

# ==========================================
# 💸 TRANSACCIONES (PROTEGIDAS)
# ==========================================

@api.route('/transactions', methods=['POST'])
@jwt_required()
def create_transaction():
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    # El user_id lo tomamos del Token por seguridad, no del JSON
    new_transaction = Transaction(
        amount=data['amount'],
        type=data['type'],
        description=data.get('description'),
        household_id=data['household_id'],
        category_id=data['category_id'],
        user_id=current_user_id 
    )
    db.session.add(new_transaction)
    db.session.commit()
    return transaction_schema.jsonify(new_transaction), 201

# ==========================================
# 🧠 LIQUIDACIÓN (PROTEGIDA)
# ==========================================

@api.route('/households/<int:household_id>/settle', methods=['GET'])
@jwt_required()
def settle_debts(household_id):
    household = Household.query.get_or_404(household_id)
    
    # Validar que el usuario que pide el reporte pertenece al grupo
    current_user_id = int(get_jwt_identity())
    if current_user_id not in [m.id for m in household.members]:
        return jsonify({"error": "No tienes acceso a este grupo"}), 403

    expenses = Transaction.query.filter_by(household_id=household_id, type='expense').all()
    total_gastado = sum(float(t.amount) for t in expenses)
    cuota = total_gastado / len(household.members)

    pagos = {m.username: 0.0 for m in household.members}
    for t in expenses:
        pagos[t.user.username] += float(t.amount)

    balances = {user: monto - cuota for user, monto in pagos.items()}
    transferencias = calcular_transferencias(balances)

    return jsonify({
        "grupo": household.name,
        "resumen": {"total": round(total_gastado, 2), "por_persona": round(cuota, 2)},
        "transferencias": transferencias
    }), 200