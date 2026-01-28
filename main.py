from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, HTTPBasic, HTTPBasicCredentials
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from passlib.context import CryptContext
import jwt
from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel, EmailStr, ConfigDict
import enum
import os
from dotenv import load_dotenv
from math import radians, cos, sin, asin, sqrt
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter, Histogram

import logging, uuid, json, time, secrets

load_dotenv()


logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)

logger = logging.getLogger("api")


# Configuration
SECRET_KEY = os.environ.get("SECRET_KEY", None)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Database setup
SQLALCHEMY_DATABASE_URL = os.environ.get("SQLALCHEMY_DATABASE_URL", None)
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Enums
class UserRole(str, enum.Enum):
    ADMIN = "admin"
    VENDOR = "vendor"
    DELIVERY = "delivery"

class ProductStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class OrderStatus(str, enum.Enum):
    CART = "cart"
    PENDING = "pending"
    PAID = "paid"
    ASSIGNED = "assigned"
    IN_DELIVERY = "in_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

# ==================== MODELS ====================
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Vendor specific
    phone = Column(String)
    business_name = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    verification_documents = Column(String)  # JSON or file paths
    is_verified = Column(Boolean, default=False)
    
    # Relations
    products = relationship("Product", back_populates="vendor")
    deliveries = relationship("Order", back_populates="delivery_person")

class Category(Base):
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    products = relationship("Product", back_populates="category")

class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String)
    price = Column(Float, nullable=False)
    stock = Column(Integer, default=0)
    image_url = Column(String)
    status = Column(SQLEnum(ProductStatus), default=ProductStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    category_id = Column(Integer, ForeignKey("categories.id"))
    vendor_id = Column(Integer, ForeignKey("users.id"))
    
    category = relationship("Category", back_populates="products")
    vendor = relationship("User", back_populates="products")
    cart_items = relationship("CartItem", back_populates="product")
    order_items = relationship("OrderItem", back_populates="product")

class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String, unique=True, nullable=False)
    
    # Client info (anonymous)
    client_name = Column(String)
    client_email = Column(String)
    client_phone = Column(String)
    client_address = Column(String)
    client_latitude = Column(Float)
    client_longitude = Column(Float)
    
    total_amount = Column(Float, nullable=False)
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.PENDING)
    payment_reference = Column(String)  # Fedapay reference
    
    delivery_person_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    paid_at = Column(DateTime)
    delivered_at = Column(DateTime)
    
    delivery_person = relationship("User", back_populates="deliveries")
    order_items = relationship("OrderItem", back_populates="order")

class OrderItem(Base):
    __tablename__ = "order_items"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer, nullable=False)
    price_at_purchase = Column(Float, nullable=False)
    
    order = relationship("Order", back_populates="order_items")
    product = relationship("Product", back_populates="order_items")

class CartItem(Base):
    __tablename__ = "cart_items"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True, nullable=False)  # Pour clients anonymes
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    product = relationship("Product", back_populates="cart_items")

# Create tables
Base.metadata.create_all(bind=engine)

# ==================== SCHEMAS ====================
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str
    role: UserRole
    phone: Optional[str] = None
    business_name: Optional[str] = None
    verification_documents: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    role: UserRole
    is_active: bool
    is_verified: bool
    business_name: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None

class CategoryResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    stock: int
    category_id: int
    image_url: Optional[str] = None

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    stock: Optional[int] = None
    category_id: Optional[int] = None
    image_url: Optional[str] = None

class ProductResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    price: float
    stock: int
    status: ProductStatus
    category_id: int
    vendor_id: int
    
    model_config = ConfigDict(from_attributes=True)

class CartItemCreate(BaseModel):
    product_id: int
    quantity: int

class CartItemResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    product: ProductResponse
    
    model_config = ConfigDict(from_attributes=True)

class OrderCreate(BaseModel):
    session_id: str
    client_name: str
    client_email: EmailStr
    client_phone: str
    client_address: str
    client_latitude: float
    client_longitude: float

class OrderResponse(BaseModel):
    id: int
    order_number: str
    client_name: str
    total_amount: float
    status: OrderStatus
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# ==================== DEPENDENCIES ====================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username, role=role)
    except Exception:
        raise credentials_exception
    user = db.query(User).filter(User.username == token_data.username).first()
    if user is None:
        raise credentials_exception
    return user

def get_admin_user(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return current_user

def get_vendor_user(current_user: User = Depends(get_current_user)):
    if current_user.role not in [UserRole.VENDOR, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Vendor privileges required")
    return current_user

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two GPS coordinates using Haversine formula (in km)"""
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    km = 6371 * c
    return km

# ==================== APP ====================
app = FastAPI(
    title="E-commerce API",
    description="API REST pour plateforme e-commerce avec vendeurs, livreurs et admins",
    version="1.0.0"
)



@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    start_time = time.time()
    request_id = str(uuid.uuid4())

    response = await call_next(request)

    process_time = round(time.time() - start_time, 4)

    log_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "status_code": response.status_code,
        "duration_ms": int(process_time * 1000),
        "client_ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
    }

    logger.info(json.dumps(log_data))

    response.headers["X-Request-ID"] = request_id
    return response



PROM_USERNAME = os.environ.get("PROM_USERNAME", None)
PROM_PASSWORD = os.environ.get("PROM_PASSWORD", None)

async def basic_auth(credentials: HTTPBasicCredentials = Depends(HTTPBasic())):
    if PROM_USERNAME is None or PROM_PASSWORD is None:
        raise HTTPException(status_code=500, detail="Metrics auth not configured")
    
    correct_username = secrets.compare_digest(credentials.username, PROM_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, PROM_PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return True


instrumentator = Instrumentator(
    should_group_status_codes=False,
    should_ignore_untemplated=True,
    should_respect_env_var=False,
    should_instrument_requests_inprogress=True,
    excluded_handlers=["/metrics"],
    inprogress_name="inprogress",
    inprogress_labels=True
)

instrumentator.instrument(app)

instrumentator.expose(
    app,
    endpoint="/metrics",
    dependencies=[Depends(basic_auth)]
)



ORDERS_CREATED = Counter(
    "orders_created_total",
    "Total number of orders created"
)

ORDERS_PAID = Counter(
    "orders_paid_total",
    "Total number of paid orders"
)

ORDER_TOTAL_AMOUNT = Histogram(
    "order_total_amount",
    "Order total amount distribution",
    buckets=(10, 25, 50, 100, 200, 500, 1000)
)

LOGIN_FAILURES = Counter(
    "login_failures_total",
    "Total failed login attempts"
)

# ==================== AUTH ENDPOINTS ====================
@app.post("/token", response_model=Token, tags=["Authentication"])
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Connexion pour Admin, Vendeur ou Livreur"""
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        LOGIN_FAILURES.inc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/register/vendor", response_model=UserResponse, tags=["Authentication"])
async def register_vendor(user: UserCreate, db: Session = Depends(get_db)):
    """Inscription d'un vendeur (avec vérification à faire par admin)"""
    if user.role != UserRole.VENDOR:
        raise HTTPException(status_code=400, detail="This endpoint is for vendor registration only")
    
    # Check if user exists
    db_user = db.query(User).filter(
        (User.email == user.email) | (User.username == user.username)
    ).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email or username already registered")
    
    # Create vendor
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password,
        role=user.role,
        phone=user.phone,
        business_name=user.business_name,
        verification_documents=user.verification_documents,
        is_verified=False  # Admin must verify
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# ==================== ADMIN ENDPOINTS ====================
@app.post("/admin/categories", response_model=CategoryResponse, tags=["Admin - Categories"])
async def create_category(
    category: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Créer une catégorie (Admin uniquement)"""
    db_category = Category(**category.dict())
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

@app.delete("/admin/categories/{category_id}", tags=["Admin - Categories"])
async def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Supprimer une catégorie (Admin uniquement)"""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    db.delete(category)
    db.commit()
    return {"message": "Category deleted successfully"}

@app.put("/admin/products/{product_id}/validate", response_model=ProductResponse, tags=["Admin - Products"])
async def validate_product(
    product_id: int,
    approve: bool,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Valider ou rejeter un produit vendeur (Admin uniquement)"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product.status = ProductStatus.APPROVED if approve else ProductStatus.REJECTED
    db.commit()
    db.refresh(product)
    return product

@app.delete("/admin/vendors/{vendor_id}", tags=["Admin - Vendors"])
async def delete_vendor(
    vendor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Supprimer un vendeur (Admin uniquement)"""
    vendor = db.query(User).filter(
        User.id == vendor_id,
        User.role == UserRole.VENDOR
    ).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    db.delete(vendor)
    db.commit()
    return {"message": "Vendor deleted successfully"}

@app.get("/admin/vendors/pending", response_model=List[UserResponse], tags=["Admin - Vendors"])
async def get_pending_vendors(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Liste des vendeurs en attente de vérification"""
    vendors = db.query(User).filter(
        User.role == UserRole.VENDOR,
        User.is_verified == False
    ).all()
    return vendors

@app.put("/admin/vendors/{vendor_id}/verify", tags=["Admin - Vendors"])
async def verify_vendor(
    vendor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Vérifier un vendeur"""
    vendor = db.query(User).filter(
        User.id == vendor_id,
        User.role == UserRole.VENDOR
    ).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    vendor.is_verified = True
    db.commit()
    return {"message": "Vendor verified successfully"}

# ==================== VENDOR ENDPOINTS ====================
@app.post("/vendor/products", response_model=ProductResponse, tags=["Vendor - Products"])
async def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_vendor_user)
):
    """Créer un produit (statut: en attente de validation admin)"""
    if current_user.role == UserRole.VENDOR and not current_user.is_verified:
        raise HTTPException(status_code=403, detail="Vendor not verified yet")
    
    db_product = Product(
        **product.dict(),
        vendor_id=current_user.id,
        status=ProductStatus.PENDING if current_user.role == UserRole.VENDOR else ProductStatus.APPROVED
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@app.put("/vendor/products/{product_id}", response_model=ProductResponse, tags=["Vendor - Products"])
async def update_product(
    product_id: int,
    product: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_vendor_user)
):
    """Modifier un produit"""
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if current_user.role == UserRole.VENDOR and db_product.vendor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this product")
    
    for key, value in product.dict(exclude_unset=True).items():
        setattr(db_product, key, value)
    
    db.commit()
    db.refresh(db_product)
    return db_product

@app.delete("/vendor/products/{product_id}", tags=["Vendor - Products"])
async def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_vendor_user)
):
    """Supprimer un produit"""
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if current_user.role == UserRole.VENDOR and db_product.vendor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this product")
    
    db.delete(db_product)
    db.commit()
    return {"message": "Product deleted successfully"}

@app.put("/vendor/location", tags=["Vendor - Profile"])
async def update_vendor_location(
    latitude: float,
    longitude: float,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_vendor_user)
):
    """Définir la localisation du vendeur"""
    current_user.latitude = latitude
    current_user.longitude = longitude
    db.commit()
    return {"message": "Location updated successfully"}

@app.get("/vendor/sales", tags=["Vendor - Sales"])
async def get_vendor_sales(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_vendor_user)
):
    """Historique des ventes du vendeur"""
    sales = db.query(OrderItem).join(Product).filter(
        Product.vendor_id == current_user.id
    ).all()
    return sales

# ==================== PUBLIC ENDPOINTS ====================
@app.get("/categories", response_model=List[CategoryResponse], tags=["Public - Categories"])
async def get_categories(db: Session = Depends(get_db)):
    """Liste de toutes les catégories"""
    categories = db.query(Category).all()
    return categories

@app.get("/products", response_model=List[ProductResponse], tags=["Public - Products"])
async def get_products(
    category_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Liste des produits approuvés (avec filtre optionnel par catégorie)"""
    query = db.query(Product).filter(Product.status == ProductStatus.APPROVED)
    if category_id:
        query = query.filter(Product.category_id == category_id)
    products = query.all()
    return products

@app.get("/products/{product_id}", response_model=ProductResponse, tags=["Public - Products"])
async def get_product(product_id: int, db: Session = Depends(get_db)):
    """Détails d'un produit"""
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.status == ProductStatus.APPROVED
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

# ==================== CART ENDPOINTS ====================
@app.post("/cart", response_model=CartItemResponse, tags=["Public - Cart"])
async def add_to_cart(
    session_id: str,
    item: CartItemCreate,
    db: Session = Depends(get_db)
):
    """Ajouter un produit au panier"""
    product = db.query(Product).filter(Product.id == item.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check if item already in cart
    cart_item = db.query(CartItem).filter(
        CartItem.session_id == session_id,
        CartItem.product_id == item.product_id
    ).first()
    
    if cart_item:
        cart_item.quantity += item.quantity
    else:
        cart_item = CartItem(
            session_id=session_id,
            product_id=item.product_id,
            quantity=item.quantity
        )
        db.add(cart_item)
    
    db.commit()
    db.refresh(cart_item)
    return cart_item

@app.get("/cart/{session_id}", response_model=List[CartItemResponse], tags=["Public - Cart"])
async def get_cart(session_id: str, db: Session = Depends(get_db)):
    """Voir le panier"""
    cart_items = db.query(CartItem).filter(CartItem.session_id == session_id).all()
    return cart_items

@app.delete("/cart/{session_id}/{item_id}", tags=["Public - Cart"])
async def remove_from_cart(session_id: str, item_id: int, db: Session = Depends(get_db)):
    """Supprimer un article du panier"""
    cart_item = db.query(CartItem).filter(
        CartItem.id == item_id,
        CartItem.session_id == session_id
    ).first()
    if not cart_item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    db.delete(cart_item)
    db.commit()
    return {"message": "Item removed from cart"}

# ==================== ORDER ENDPOINTS ====================
@app.post("/orders", response_model=OrderResponse, tags=["Public - Orders"])
async def create_order(order_data: OrderCreate, db: Session = Depends(get_db)):
    """Créer une commande à partir du panier"""
    # Get cart items
    cart_items = db.query(CartItem).filter(
        CartItem.session_id == order_data.session_id
    ).all()
    
    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")
    
    # Calculate total
    total = sum(item.product.price * item.quantity for item in cart_items)
    
    # Create order
    order_number = f"ORD-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    order = Order(
        order_number=order_number,
        client_name=order_data.client_name,
        client_email=order_data.client_email,
        client_phone=order_data.client_phone,
        client_address=order_data.client_address,
        client_latitude=order_data.client_latitude,
        client_longitude=order_data.client_longitude,
        total_amount=total,
        status=OrderStatus.PENDING
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    
    # Create order items
    for cart_item in cart_items:
        order_item = OrderItem(
            order_id=order.id,
            product_id=cart_item.product_id,
            quantity=cart_item.quantity,
            price_at_purchase=cart_item.product.price
        )
        db.add(order_item)
    
    # Clear cart
    db.query(CartItem).filter(CartItem.session_id == order_data.session_id).delete()
    
    db.commit()

    ORDERS_CREATED.inc()
    ORDER_TOTAL_AMOUNT.observe(total)

    logger.info(json.dumps({
        "event": "order_created",
        "order_id": order.id,
        "order_number": order.order_number,
        "total": total
    }))

    return order

@app.post("/orders/{order_id}/payment", tags=["Public - Orders"])
async def process_payment(
    order_id: int,
    payment_reference: str,
    db: Session = Depends(get_db)
):
    """Traiter le paiement Fedapay et assigner un livreur"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # TODO: Intégrer vraiment Fedapay ici
    order.payment_reference = payment_reference
    order.status = OrderStatus.PAID
    order.paid_at = datetime.utcnow()
    ORDERS_PAID.inc()
    
    # Find closest delivery person
    order_items = db.query(OrderItem).filter(OrderItem.order_id == order_id).all()
    vendor_ids = set(item.product.vendor_id for item in order_items)
    
    # Get average vendor location (simplified - prendre le premier vendeur)
    first_vendor = db.query(User).filter(User.id == list(vendor_ids)[0]).first()
    
    if first_vendor and first_vendor.latitude and first_vendor.longitude:
        # Find closest delivery person
        delivery_persons = db.query(User).filter(
            User.role == UserRole.DELIVERY,
            User.is_active == True
        ).all()
        
        closest_delivery = None
        min_distance = float('inf')
        
        for delivery in delivery_persons:
            if delivery.latitude and delivery.longitude:
                distance = calculate_distance(
                    first_vendor.latitude,
                    first_vendor.longitude,
                    order.client_latitude,
                    order.client_longitude
                )
                if distance < min_distance:
                    min_distance = distance
                    closest_delivery = delivery
        
        if closest_delivery:
            order.delivery_person_id = closest_delivery.id
            order.status = OrderStatus.ASSIGNED
    
    db.commit()

    logger.info(json.dumps({
        "event": "order_paid",
        "order_id": order.id,
        "payment_reference": payment_reference
    }))

    return {"message": "Payment processed and delivery assigned", "order_id": order.id}

@app.get("/orders/global-sales", tags=["Public - Statistics"])
async def get_global_sales(db: Session = Depends(get_db)):
    """Historique global des ventes"""
    sales = db.query(OrderItem).all()
    return sales

# ==================== DELIVERY ENDPOINTS ====================
@app.get("/delivery/orders", tags=["Delivery - Orders"])
async def get_assigned_deliveries(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Liste des livraisons assignées au livreur"""
    if current_user.role != UserRole.DELIVERY:
        raise HTTPException(status_code=403, detail="Delivery person only")
    
    orders = db.query(Order).filter(
        Order.delivery_person_id == current_user.id,
        Order.status.in_([OrderStatus.ASSIGNED, OrderStatus.IN_DELIVERY])
    ).all()
    return orders

@app.put("/delivery/orders/{order_id}/status", tags=["Delivery - Orders"])
async def update_delivery_status(
    order_id: int,
    new_status: OrderStatus,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mettre à jour le statut de livraison"""
    if current_user.role != UserRole.DELIVERY:
        raise HTTPException(status_code=403, detail="Delivery person only")
    
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.delivery_person_id == current_user.id
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    order.status = new_status
    if new_status == OrderStatus.DELIVERED:
        order.delivered_at = datetime.utcnow()
    
    db.commit()
    return {"message": "Status updated successfully"}

# ==================== HEALTH CHECK ====================
@app.get("/", tags=["Health"])
async def root():
    return {"message": "E-commerce API is running", "version": "1.0.0"}
