from flask import Blueprint, request, jsonify
from app import db
from app.models import User, Household, Category, Transaction
from app.schemas import (user_schema, household_schema, households_schema,
                        transaction_schema, transactions_schema)
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

# Importamos las funciones lógicas
from app.services import (create_household_service, get_settlement_service, 
                          get_monthly_report_service)

api = Blueprint('api', __name__)

# --- AUTH ---
@api.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    new_user = User(username=data['username'], email=data['email'])
    new_user.set_password(data['password'])
    db.session.add(new_user)
    db.session.commit()
    token = create_access_token(identity=str(new_user.id))
    return jsonify({"token": token, "user": user_schema.dump(new_user)}), 201

@api.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data.get('username')).first()
    if user and user.check_password(data.get('password')):
        token = create_access_token(identity=str(user.id))
        return jsonify({"token": token, "user": user_schema.dump(user)}), 200
    return jsonify({"error": "Credenciales inválidas"}), 401

# --- HOUSEHOLDS ---
@api.route('/households', methods=['GET'])
@jwt_required()
def get_households():
    user = User.query.get(int(get_jwt_identity()))
    return households_schema.jsonify(user.households), 200

@api.route('/households', methods=['POST'])
@jwt_required()
def create_household():
    data = request.get_json()
    user_id = int(get_jwt_identity())
    new_h = create_household_service(data, user_id)
    return household_schema.jsonify(new_h), 201

@api.route('/households/join', methods=['POST'])
@jwt_required()
def join_household():
    data = request.get_json()
    invite_code = data.get('invite_code', '').strip().upper()
    household = Household.query.filter_by(invite_code=invite_code).first()
    if not household:
        return jsonify({"error": "Código inválido"}), 404
    user = User.query.get(int(get_jwt_identity()))
    if user not in household.members:
        household.members.append(user)
        db.session.commit()
    return household_schema.jsonify(household), 200

@api.route('/households/<int:household_id>', methods=['DELETE'])
@jwt_required()
def delete_household(household_id):
    from app.services import delete_household_service
    user_id = int(get_jwt_identity())
    delete_household_service(household_id, user_id)
    return jsonify({"message": "Grupo eliminado"}), 200

@api.route('/households/<int:household_id>/categories', methods=['GET'])
@jwt_required()
def get_categories(household_id):
    categories = Category.query.filter_by(household_id=household_id).all()
    return jsonify([{"id": c.id, "name": c.name, "type": c.type} for c in categories]), 200

# --- TRANSACTIONS ---
@api.route('/transactions', methods=['GET'])
@jwt_required()
def get_transactions():
    h_id = request.args.get('household_id', type=int)
    transactions = Transaction.query.filter_by(household_id=h_id).order_by(Transaction.date.desc()).all()
    return transactions_schema.jsonify(transactions), 200

@api.route('/transactions', methods=['POST'])
@jwt_required()
def create_transaction():
    data = request.get_json()
    new_tx = Transaction(
        amount=data['amount'], type=data['type'], description=data.get('description'),
        household_id=data['household_id'], category_id=data['category_id'],
        user_id=int(get_jwt_identity())
    )
    db.session.add(new_tx)
    db.session.commit()
    return transaction_schema.jsonify(new_tx), 201

# --- REPORTES Y LIQUIDACIÓN (AQUÍ ESTÁ LO QUE BUSCABAS) ---

@api.route('/households/<int:household_id>/settle', methods=['GET'])
@jwt_required()
def settle_debts(household_id):
    """Llama al servicio de liquidación para ver quién debe a quién."""
    resultado = get_settlement_service(household_id)
    return jsonify(resultado), 200

@api.route('/households/<int:household_id>/monthly-report', methods=['GET'])
@jwt_required()
def get_monthly_report(household_id):
    """Nuevo endpoint para el balance mensual detallado."""
    reporte = get_monthly_report_service(household_id)
    return jsonify(reporte), 200