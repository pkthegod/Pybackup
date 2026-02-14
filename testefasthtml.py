# main.py
from fasthtml.common import *
from models import Item, create_database, SessionLocal
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse

# Inicializa a aplicação FastHTML
app, rt = fast_app()

# Conecta com o banco de dados
create_database()

# Função para obter a sessão do DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Rota para página de login
@rt('/login')
def login_page():
    return Titled("Login", 
                  Form("Login Form", 
                       Input(name="username", placeholder="Username"), 
                       Input(name="password", type="password", placeholder="Password"), 
                       Button("Login", type="submit")))

# Rota para autenticar o usuário
@rt('/login', methods=["post"])
def login(req, db: Session = next(get_db())):
    username = req.form['username']
    password = req.form['password']
    # Simples verificação de login
    if username == 'admin' and password == 'admin':
        return RedirectResponse('/dashboard')
    return "Usuário ou senha incorretos"

# Dashboard CRUD com campo de busca
@rt('/dashboard')
def dashboard(search: str = "", db: Session = next(get_db())):
    query = db.query(Item)
    if search:
        query = query.filter(Item.name.contains(search))
    items = query.all()
    
    # Renderiza a interface CRUD
    return Titled("Dashboard", 
                  Form("Search", Input(name="search", value=search), Button("Buscar")),
                  Ul(*[Li(f"{item.name} - {item.description} (ID: {item.id})", 
                          Button("Delete", hx_delete=f"/item/{item.id}")) for item in items]),
                  Form("New Item", 
                       Input(name="name", placeholder="Item Name"), 
                       Input(name="description", placeholder="Item Description"), 
                       Button("Add Item", type="submit")))

# Rota para adicionar um item
@rt('/item', methods=["post"])
def add_item(req, db: Session = next(get_db())):
    name = req.form['name']
    description = req.form['description']
    new_item = Item(name=name, description=description)
    db.add(new_item)
    db.commit()
    return RedirectResponse('/dashboard')

# Rota para deletar um item
@rt('/item/{item_id}')
def delete_item(item_id: int, db: Session = next(get_db())):
    item = db.query(Item).filter(Item.id == item_id).first()
    if item:
        db.delete(item)
        db.commit()
    return RedirectResponse('/dashboard')

serve()
