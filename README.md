🚀 HousePay - Backend API (Flask)

![Python](https://img.shields.io/badge/Python-3.12%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0%2B-black?style=for-the-badge&logo=flask&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15%2B-336791?style=for-the-badge&logo=postgresql&logoColor=white)

Esta es la API robusta que alimenta a **HousePay**, la aplicación para la gestión de gastos compartidos. Está diseñada para manejar múltiples hogares, transacciones en tiempo real y cálculos automáticos de deudas.

---

✨ Características Técnicas

- **Autenticación Segura:** Implementada con JWT (JSON Web Tokens) mediante `Flask-JWT-Extended`.
- **Arquitectura de Grupos:** Permite la creación de "Households" privados con códigos de invitación únicos (ej: `A3K9PZ`).
- **Sembrado Automático:** Cada vez que se crea un nuevo grupo, la API genera automáticamente 9 categorías financieras esenciales (Sueldo, Supermercado, etc.).
- **Lógica de Liquidación:** Algoritmo optimizado para calcular transferencias necesarias y dejar las "Cuentas Claras".
- **Base de Datos:** Estructura relacional con PostgreSQL y SQLAlchemy ORM.

---

🛠️ Tecnologías Utilizadas

* **Framework:** Flask
* **ORM:** SQLAlchemy
* **Seguridad:** Flask-JWT-Extended / Werkzeug
* **CORS:** Flask-CORS (para permitir peticiones desde la app Android)
* **Despliegue:** Configurada para **Render** con Gunicorn
