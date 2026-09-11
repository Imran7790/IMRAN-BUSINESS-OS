# IMRAN BUSINESS OS Architecture

## Core principle

One platform supports many legitimate business industries.

Business configuration determines which specialized modules are enabled.

## Global configuration

Each business has:
- Country
- Currency
- Language
- Timezone
- Units
- Tax configuration

## Core modules

Businesses
Users/Roles
Customers
Suppliers
Products/Services
Inventory
Sales
Purchases
Expenses
Quotations
Invoices
Payments
Reports

## Industry modules

Retail
Grocery
Supermarket
Automotive
Real Estate
Restaurants
Bars
Hotels
Construction
Agriculture
Logistics
Professional Services
and additional industries.

## Security

Every business-owned record must be isolated by business_id.
Authentication and authorization will be enforced at the API layer.
Production deployments must use HTTPS and a strong secret configuration.

## Scalability

The API is versioned under /api/v1.
The Android and web clients will consume the same API.
PostgreSQL is the intended production database.
