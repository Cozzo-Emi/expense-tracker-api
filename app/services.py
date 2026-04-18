from app import db
from app.models import Household, Category, Transaction, User, generate_invite_code
from sqlalchemy import func
from datetime import datetime
from app.utils import calcular_transferencias

def create_household_service(data, current_user_id):
    """Crea el grupo y siembra las categorías automáticamente."""
    invite_code = generate_invite_code()
    while Household.query.filter_by(invite_code=invite_code).first():
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

    # Categorías base para que la app no arranque vacía
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
    return new_household

def get_monthly_report_service(household_id):
    """Procesa el flujo de caja del mes actual con descripciones y categorías."""
    ahora = datetime.utcnow()
    transactions = Transaction.query.filter(
        Transaction.household_id == household_id,
        func.extract('month', Transaction.date) == ahora.month,
        func.extract('year', Transaction.date) == ahora.year
    ).order_by(Transaction.date.desc()).all()

    reporte = {
        "resumen": {"ingresos": 0, "gastos": 0, "neto": 0},
        "por_usuario": {},
        "movimientos": []
    }

    for t in transactions:
        monto = float(t.amount)
        user = t.user.username
        
        if user not in reporte["por_usuario"]:
            reporte["por_usuario"][user] = {"ingresos": 0, "gastos": 0}

        if t.type == 'income':
            reporte["resumen"]["ingresos"] += monto
            reporte["por_usuario"][user]["ingresos"] += monto
        else:
            reporte["resumen"]["gastos"] += monto
            reporte["por_usuario"][user]["gastos"] += monto

        reporte["movimientos"].append({
            "usuario": user,
            "tipo": t.type,
            "monto": monto,
            "categoria": t.category.name,
            "descripcion": t.description or "Sin descripción",
            "fecha": t.date.strftime("%d/%m/%Y")
        })

    reporte["resumen"]["neto"] = reporte["resumen"]["ingresos"] - reporte["resumen"]["gastos"]
    return reporte

def get_settlement_service(household_id):
    """Calcula las deudas cruzadas para saldar cuentas."""
    household = Household.query.get_or_404(household_id)
    expenses = Transaction.query.filter_by(household_id=household_id, type='expense').all()
    
    if not expenses:
        return {"grupo": household.name, "transferencias": []}

    total = sum(float(t.amount) for t in expenses)
    cuota = total / len(household.members)
    
    pagos = {m.username: 0.0 for m in household.members}
    for t in expenses:
        pagos[t.user.username] += float(t.amount)
    
    balances = {u: m - cuota for u, m in pagos.items()}
    return {
        "grupo": household.name, 
        "resumen": {"total": round(total, 2), "cuota": round(cuota, 2)},
        "transferencias": calcular_transferencias(balances)
    }

def delete_household_service(household_id, current_user_id):
    """Elimina un grupo si el usuario actual es el creador."""
    household = Household.query.get_or_404(household_id)
    if household.creator_id != current_user_id:
        from flask import abort
        abort(403, description="Solo el creador puede eliminar el grupo")
    
    db.session.delete(household)
    db.session.commit()
    return True