from app import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import random
import string

# 1. TABLA INTERMEDIA
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
    password_hash = db.Column(db.String(256), nullable=False)
    
    households = db.relationship('Household', secondary=household_members, back_populates='members')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

def generate_invite_code():
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=6))

# 3. EL GRUPO / HOUSEHOLD
class Household(db.Model):
    __tablename__ = 'households'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), default='home') 
    invite_code = db.Column(db.String(10), unique=True, nullable=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    members = db.relationship('User', secondary=household_members, back_populates='households')
    categories = db.relationship('Category', backref='household', lazy=True, cascade="all, delete-orphan")
    transactions = db.relationship('Transaction', backref='household', lazy=True, cascade="all, delete-orphan")

# 4. LAS CATEGORÍAS (Actualizado con campo 'type')
class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    # Agregamos el campo type para que coincida con la lógica de routes.py
    type = db.Column(db.String(20), nullable=False, default='expense') 
    
    household_id = db.Column(db.Integer, db.ForeignKey('households.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)

    subcategories = db.relationship(
        'Category',
        backref=db.backref('parent', remote_side=[id]),
        cascade="all, delete-orphan"
    )

# 5. LAS TRANSACCIONES
class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    type = db.Column(db.String(20), nullable=False) 
    date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    
    household_id = db.Column(db.Integer, db.ForeignKey('households.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    category = db.relationship('Category', backref=db.backref('transactions', lazy=True))
    user = db.relationship('User', backref=db.backref('transactions', lazy=True))