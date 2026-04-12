from app import create_app, db
from app.models import User, Household, Category, Transaction 

app = create_app()

with app.app_context():
    db.drop_all()   
    db.create_all() 
    print("✅ ¡Tablas actualizadas y sincronizadas a la versión Multi-Usuario!")