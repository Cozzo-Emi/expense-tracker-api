from flask import Blueprint, request, jsonify
from app import db
from app.models import User, Household, Category, Transaction, generate_invite_code
from app.schemas import (user_schema, household_schema, households_schema,
                        transaction_schema, transactions_schema)
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

    if User.query.filter_by(email=data['email']).first():
        return jsonify({"error": "El email ya está registrado"}), 400

    new_user = User(username=data['username'], email=data['email'])
    new_user.set_password(data['password'])
    db.session.add(new_user)
    db.session.commit()

    # Auto-login al registrarse
    access_token = create_access_token(identity=str(new_user.id))
    return jsonify({
        "token": access_token,
        "user": user_schema.dump(new_user)
    }), 201


@api.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data.get('username')).first()

    if user and user.check_password(data.get('password')):
        access_token = create_access_token(identity=str(user.id))
        return jsonify({
            "token": access_token,
            "user": user_schema.dump(user)
        }), 200

    return jsonify({"error": "Credenciales inválidas"}), 401


# ==========================================
# 🏠 GRUPOS / HOUSEHOLDS (PROTEGIDOS)
# ==========================================

@api.route('/households', methods=['GET'], endpoint='get_households')
@jwt_required()
def get_households():
    """Lista todos los grupos a los que pertenece el usuario"""
    current_user_id = int(get_jwt_identity())
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({"error": "Usuario no encontrado"}), 404
    return households_schema.jsonify(user.households), 200


@api.route('/households', methods=['POST'], endpoint='create_household')
@jwt_required()
def create_household():
    """Crea un nuevo grupo, genera su código y le asigna las categorías por defecto."""
    current_user_id = int(get_jwt_identity())
    data = request.get_json()

    if not data or not data.get('name'):
        return jsonify({"error": "El nombre del grupo es obligatorio"}), 400

    invite_code = generate_invite_code()
    while Household.query.filter_by(invite_code=invite_code).first():
        invite_code = generate_invite_code()

    new_household = Household(
        name=data['name'],
        type=data.get('type', 'home'),
        invite_code=invite_code,
        creator_id=current_user_id
    )

    creator = User.query.get(current_user_id)
    new_household.members.append(creator)

    db.session.add(new_household)
    db.session.commit() # Hacemos commit acá para que new_household tenga un ID real

    # --- INICIO DE MODIFICACIÓN: Auto-poblamos las categorías ---
    categorias_por_defecto = [
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
    
    for cat in categorias_por_defecto:
        nueva_cat = Category(name=cat["name"], type=cat["type"], household_id=new_household.id)
        db.session.add(nueva_cat)
        
    db.session.commit() # Guardamos todas las categorías en la base de datos
    # --- FIN DE MODIFICACIÓN ---

    return household_schema.jsonify(new_household), 201


@api.route('/households/join', methods=['POST'])
@jwt_required()
def join_household():
    """Permite unirse a un grupo privado usando su código de invitación."""
    current_user_id = int(get_jwt_identity())
    data = request.get_json()
    invite_code = data.get('invite_code', '').strip().upper()

    if not invite_code:
        return jsonify({"error": "Se requiere un código de invitación"}), 400

    household = Household.query.filter_by(invite_code=invite_code).first()
    if not household:
        return jsonify({"error": "Código inválido. Verificá que sea correcto."}), 404

    user = User.query.get(current_user_id)
    if user in household.members:
        return jsonify({"message": "Ya sos miembro de este grupo", "household": household_schema.dump(household)}), 200

    household.members.append(user)
    db.session.commit()
    return household_schema.jsonify(household), 200


@api.route('/households/<int:household_id>', methods=['DELETE'])
@jwt_required()
def delete_household(household_id):
    """Elimina un grupo. Solo el creador tiene permiso."""
    current_user_id = int(get_jwt_identity())
    household = Household.query.get_or_404(household_id)

    if household.creator_id != current_user_id:
        return jsonify({"error": "No tenés permiso para eliminar este grupo."}), 403

    db.session.delete(household)
    db.session.commit()
    return jsonify({"message": "Grupo eliminado correctamente"}), 200


@api.route('/households/<int:household_id>/categories', methods=['GET'])
@jwt_required()
def get_categories(household_id):
    """Devuelve las categorías disponibles para un grupo específico."""
    current_user_id = int(get_jwt_identity())
    household = Household.query.get_or_404(household_id)

    if current_user_id not in [m.id for m in household.members]:
        return jsonify({"error": "No tenés acceso a este grupo"}), 403

    categories = Category.query.filter_by(household_id=household_id).all()
    
    return jsonify([{
        "id": c.id, 
        "name": c.name,
        "type": c.type # O el campo correspondiente en tu modelo
    } for c in categories]), 200


# ==========================================
# 💸 TRANSACCIONES (PROTEGIDAS)
# ==========================================

@api.route('/transactions', methods=['GET'], endpoint='get_transactions')
@jwt_required()
def get_transactions():
    """Devuelve transacciones filtradas por household_id."""
    current_user_id = int(get_jwt_identity())
    user = User.query.get(current_user_id)

    if not user:
        return jsonify({"error": "Usuario no encontrado"}), 404

    household_id = request.args.get('household_id', type=int)

    if household_id:
        household = Household.query.get(household_id)
        if not household:
            return jsonify({"error": "Grupo no encontrado"}), 404
        if user not in household.members:
            return jsonify({"error": "No tenés acceso a este grupo"}), 403

        transactions = Transaction.query.filter_by(
            household_id=household_id
        ).order_by(Transaction.date.desc()).all()
    else:
        household_ids = [h.id for h in user.households]
        if not household_ids:
            return jsonify([]), 200
        transactions = Transaction.query.filter(
            Transaction.household_id.in_(household_ids)
        ).order_by(Transaction.date.desc()).all()

    return transactions_schema.jsonify(transactions), 200


@api.route('/transactions', methods=['POST'], endpoint='create_transaction')
@jwt_required()
def create_transaction():
    """Crea una nueva transacción verificando membresía."""
    current_user_id = int(get_jwt_identity())
    data = request.get_json()

    if not data or not data.get('amount') or not data.get('household_id'):
        return jsonify({"error": "Faltan datos obligatorios"}), 400

    household_id = data.get('household_id')
    user = User.query.get(current_user_id)
    household = Household.query.get(household_id)

    if not household:
        return jsonify({"error": "Grupo no encontrado"}), 404
    if user not in household.members:
        return jsonify({"error": "No tenés permiso para cargar en este grupo"}), 403

    new_transaction = Transaction(
        amount=data['amount'],
        type=data['type'],
        description=data.get('description'),
        household_id=household_id,
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
    """Calcula las deudas optimizadas del grupo."""
    household = Household.query.get_or_404(household_id)
    current_user_id = int(get_jwt_identity())

    if current_user_id not in [m.id for m in household.members]:
        return jsonify({"error": "No tenés acceso a este grupo"}), 403

    expenses = Transaction.query.filter_by(household_id=household_id, type='expense').all()
    if not expenses or not household.members:
        return jsonify({"grupo": household.name, "resumen": {"total": 0, "por_persona": 0}, "transferencias": []}), 200

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