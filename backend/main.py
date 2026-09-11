from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.models import core

from app.routers import businesses
from app.routers import customers
from app.routers import products
from app.routers import suppliers
from app.routers import auth
from app.routers import audit_logs
from app.routers import sales
from app.routers import purchases
from app.routers import inventory
from app.routers import invoices
from app.routers import payments
from app.routers import quotations
from app.routers import notifications
from app.routers import appointments
from app.routers import employees
from app.routers import services, service_jobs

Base.metadata.create_all(bind=engine)

app = FastAPI(title="IMRAN BUSINESS OS API", version="1.0.0", description="International multi-industry business operating platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8080",
        "http://localhost:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(businesses.router)
app.include_router(customers.router)
app.include_router(products.router)
app.include_router(suppliers.router)
app.include_router(auth.router)
app.include_router(audit_logs.router)
app.include_router(sales.router)
app.include_router(purchases.router)
app.include_router(inventory.router)
app.include_router(invoices.router)
app.include_router(payments.router)
app.include_router(quotations.router)
app.include_router(notifications.router)
app.include_router(appointments.router)
app.include_router(employees.router)
app.include_router(services.router)
app.include_router(service_jobs.router)

@app.get("/")
def root():
    return {"name": "IMRAN BUSINESS OS", "status": "online", "version": "1.0.0"}

@app.get("/health")
def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.get("/api/v1")
def api_v1():
    return {"name": "IMRAN BUSINESS OS API", "version": "1.0.0", "status": "online"}
