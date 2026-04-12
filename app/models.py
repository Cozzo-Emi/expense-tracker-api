from app import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# 1. TABLA INTERMEDIA: Conecta a los usuarios con los múltiples grupos (Casa, Viaje, etc.)
household_members = db.Table('household_members',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('household_id', db.Integer, db.ForeignKey('households.id'), primary_key=True)
)

# 2. EL USUARIO
class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(256), nullable=False) # Nueva columna encriptada
    
    households = db.relationship('Household', secondary=household_members, back_populates='members')
    
    # Métodos de seguridad
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"


# 3. EL GRUPO / VIAJE / CASA (La Billetera Compartida)
class Household(db.Model):
    __tablename__ = 'households'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False) # Ej: "Economía Casa" o "Viaje a Bariloche"
    type = db.Column(db.String(50), default='home')  # Ej: 'home', 'trip', 'event'
    
    members = db.relationship('User', secondary=household_members, back_populates='households')
    categories = db.relationship('Category', backref='household', lazy=True, cascade="all, delete-orphan")
    transactions = db.relationship('Transaction', backref='household', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Household {self.name}>"


# 4. LAS CATEGORÍAS (Específicas de cada grupo)
class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    
    household_id = db.Column(db.Integer, db.ForeignKey('households.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)

    subcategories = db.relationship(
        'Category',
        backref=db.backref('parent', remote_side=[id]),
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Category {self.name}>"


# 5. LAS TRANSACCIONES (Con tipo de movimiento y quién lo pagó)
class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    type = db.Column(db.String(20), nullable=False) # 'income' (Ingreso) o 'expense' (Gasto)
    date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    
    household_id = db.Column(db.Integer, db.ForeignKey('households.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False) # ¿Quién lo pagó?

    category = db.relationship('Category', backref=db.backref('transactions', lazy=True))
    user = db.relationship('User', backref=db.backref('transactions', lazy=True))

    def __repr__(self):
        return f"<Transaction {self.type} {self.amount} by User:{self.user_id}>"