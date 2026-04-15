from app import ma
from app.models import User, Household, Category, Transaction

class UserSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = User
        load_instance = True
        exclude = ('password_hash',)  # Nunca exponer el hash

class HouseholdSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Household
        load_instance = True
        # invite_code se incluye para mostrárselo al creador
    members = ma.Nested(UserSchema, many=True, only=('id', 'username'))

class CategorySchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Category
        load_instance = True
        include_fk = True
    subcategories = ma.Nested('CategorySchema', many=True, exclude=('parent_id',))

class TransactionSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Transaction
        load_instance = True
        include_fk = True
    # Quién realizó el movimiento
    user = ma.Nested(UserSchema, only=('id', 'username'), dump_only=True)

# Instancias
user_schema = UserSchema()
users_schema = UserSchema(many=True)
household_schema = HouseholdSchema()
households_schema = HouseholdSchema(many=True)
category_schema = CategorySchema()
categories_schema = CategorySchema(many=True)
transaction_schema = TransactionSchema()
transactions_schema = TransactionSchema(many=True)