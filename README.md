# Credit Approval System – Django + DRF

This project is a backend credit approval system built using Django, Django Rest Framework, PostgreSQL, and Docker.  
It evaluates customer loan eligibility based on credit score, approved limits, EMI affordability, and interest rate slabs.

The system:
- Calculates credit scores from historical loan data
- Applies interest correction based on credit score slabs
- Enforces EMI ≤ 50% of monthly salary
- Enforces approved credit limit
- Uses compound interest for EMI calculation
- Is fully containerized using Docker

---

## Tech Stack

- Python 3.11  
- Django 4+  
- Django Rest Framework  
- PostgreSQL  
- Docker & Docker Compose  

---

## Setup & Run (Using Docker)

Make sure Docker and Docker Compose are installed.

Clone the repository:

```bash
git clone https://github.com/Sephyroth1/CreditApprovalSystem/
cd CreditApprovalSystem
```

## Build and start containers:
```bash
docker compose up --build
```

The API will be available at:
```link
http://localhost:8000
```

## Running Tests
To run unit tests:
```bash
docker compose exec backend python manage.py test
```

# Loan Management API Documentation

## API Endpoints

### 1. Register Customer  
**POST** `/api/register/`

**Request Body:**
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "age": 28,
  "monthly_income": 50000,
  "phone_number": "9999999999"
}
```

### 2. Check Loan Eligibility
**POST** `/api/check-eligibility/`

**Request Body:**
```json
{
  "customer_id": 1,
  "loan_amount": 150000,
  "interest_rate": 8,
  "tenure": 18
}
```
Response Example:
```json
{
  "customer_id": 1,
  "approval": true,
  "interest_rate": 8,
  "corrected_interest_rate": 12,
  "tenure": 18,
  "monthly_installment": 8871.04,
}
```

### 3. Create Loan  
**POST** `/api/create-loan/`

Processes and stores an approved loan.

---

### 4. View Loan  
**GET** `/api/view-loan/<loan_id>/`

---

### 5. View All Loans of Customer  
**GET** `/api/view-loans/<customer_id>/`
