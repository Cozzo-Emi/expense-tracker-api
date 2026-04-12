from app import ma
from app.models import User, Household, Category, Transaction

# Esquema para Usuarios
class UserSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = User
        load_instance = True # Permite deserializar a objetos SQLAlchemy

# Esquema para Grupos (Billeteras / Viajes)
class HouseholdSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Household
        load_instance = True
    
    # Anidamos los usuarios para que al pedir un Grupo, nos devuelva quiénes están adentro
    members = ma.Nested(UserSchema, many=True, only=('id', 'username'))

# Instancias listas para usar en las rutas
user_schema = UserSchema()
users_schema = UserSchema(many=True)
household_schema = HouseholdSchema()
households_schema = HouseholdSchema(many=True)

# Esquema para Categorías
class CategorySchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Category
        load_instance = True
        include_fk = True # Muestra IDs de relaciones (household_id, parent_id)
    
    # Para ver las subcategorías anidadas cuando pidamos una categoría padre
    subcategories = ma.Nested('CategorySchema', many=True, exclude=('parent_id',))

# Esquema para Transacciones
class TransactionSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Transaction
        load_instance = True
        include_fk = True

# Instancias para exportar
category_schema = CategorySchema()
categories_schema = CategorySchema(many=True)
transaction_schema = TransactionSchema()
transactions_schema = TransactionSchema(many=True)