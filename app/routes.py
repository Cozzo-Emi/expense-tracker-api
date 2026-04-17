from flask import Blueprint, request, jsonify
from app import db
from app.models import User, Household, Category, Transaction, generate_invite_code
from app.schemas import (user_schema, household_schema, households_schema,
                        transaction_schema, transactions_schema)
from app.utils import calcular_transferencias
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

api = Blueprint('api', __name__)

# --- AUTH ---
@api.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password') or not data.get('email'):
        return jsonify({"error": "Faltan datos obligatorios"}), 400
    if User.query.filter_by(username=data['username']).first():
        return jsonify({"error": "El nombre de usuario ya existe"}), 400
    new_user = User(username=data['username'], email=data['email'])
    new_user.set_password(data['password'])
    db.session.add(new_user)
    db.session.commit()
    access_token = create_access_token(identity=str(new_user.id))
    return jsonify({"token": access_token, "user": user_schema.dump(new_user)}), 201

@api.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data.get('username')).first()
    if user and user.check_password(data.get('password')):
        access_token = create_access_token(identity=str(user.id))
        return jsonify({"token": access_token, "user": user_schema.dump(user)}), 200
    return jsonify({"error": "Credenciales inválidas"}), 401

# --- HOUSEHOLDS ---
@api.route('/households', methods=['GET'], endpoint='get_households')
@jwt_required()
def get_households():
    current_user_id = int(get_jwt_identity())
    user = User.query.get(current_user_id)
    return households_schema.jsonify(user.households), 200

@api.route('/households', methods=['POST'], endpoint='create_household')
@jwt_required()
def create_household():
    current_user_id = int(get_jwt_identity())
    data = request.get_json()
    if not data or not data.get('name'):
        return jsonify({"error": "El nombre del grupo es obligatorio"}), 400

    invite_code = generate_invite_code()
    new_household = Household(
        name=data['name'],
        type=data.get('type', 'home'),
        invite_code=invite_code,
        creator_id=current_user_id
    )
    user = User.query.get(current_user_id)
    new_household.members.append(user)
    db.session.add(new_household)
    db.session.commit()

    # Creación automática de categorías
    def_categories = [
        {"name": "Supermercado", "type": "expense"},
        {"name": "Transporte", "type": "expense"},
        {"name": "Servicios", "type": "expense"},
        {"name": "Entretenimiento", "type": "expense"},
        {"name": "Alquiler / Expensas", "type": "expense"},
        {"name": "Sueldo", "type": "income"},
        {"name": "Transferencia", "type": "income"},
        {"name": "Ventas", "type": "income"},
        {"name": "Otros", "type": "both"}
    ]
    for cat in def_categories:
        new_cat = Category(name=cat["name"], type=cat["type"], household_id=new_household.id)
        db.session.add(new_cat)
    db.session.commit()
    return household_schema.jsonify(new_household), 201

@api.route('/households/join', methods=['POST'])
@jwt_required()
def join_household():
    current_user_id = int(get_jwt_identity())
    data = request.get_json()
    invite_code = data.get('invite_code', '').strip().upper()
    household = Household.query.filter_by(invite_code=invite_code).first()
    if not household:
        return jsonify({"error": "Código inválido"}), 404
    user = User.query.get(current_user_id)
    if user not in household.members:
        household.members.append(user)
        db.session.commit()
    return household_schema.jsonify(household), 200

@api.route('/households/<int:household_id>/categories', methods=['GET'])
@jwt_required()
def get_categories(household_id):
    categories = Category.query.filter_by(household_id=household_id).all()
    return jsonify([{"id": c.id, "name": c.name, "type": c.type} for c in categories]), 200

# --- TRANSACTIONS ---
@api.route('/transactions', methods=['GET'])
@jwt_required()
def get_transactions():
    household_id = request.args.get('household_id', type=int)
    transactions = Transaction.query.filter_by(household_id=household_id).order_by(Transaction.date.desc()).all()
    return transactions_schema.jsonify(transactions), 200

@api.route('/transactions', methods=['POST'])
@jwt_required()
def create_transaction():
    current_user_id = int(get_jwt_identity())
    data = request.get_json()
    new_tx = Transaction(
        amount=data['amount'],
        type=data['type'],
        description=data.get('description'),
        household_id=data['household_id'],
        category_id=data['category_id'],
        user_id=current_user_id
    )
    db.session.add(new_tx)
    db.session.commit()
    return transaction_schema.jsonify(new_tx), 201

# --- SETTLE ---
@api.route('/households/<int:household_id>/settle', methods=['GET'])
@jwt_required()
def settle_debts(household_id):
    household = Household.query.get_or_404(household_id)
    expenses = Transaction.query.filter_by(household_id=household_id, type='expense').all()
    if not expenses:
        return jsonify({"grupo": household.name, "transferencias": []}), 200
    total = sum(float(t.amount) for t in expenses)
    cuota = total / len(household.members)
    pagos = {m.username: 0.0 for m in household.members}
    for t in expenses:
        pagos[t.user.username] += float(t.amount)
    balances = {u: m - cuota for u, m in pagos.items()}
    return jsonify({"grupo": household.name, "transferencias": calcular_transferencias(balances)}), 200