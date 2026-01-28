from datetime import date, datetime

from dateutil.relativedelta import relativedelta
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Customer, Loan
from .serializers import RegisterCustomerSerializer


@api_view(["POST"])
def register_customer(request):
    serializer = RegisterCustomerSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if Customer.objects.filter(
        phone_number=serializer.validated_data["phone_number"]
    ).exists():
        return Response({"error": "Customer already exists"}, status=400)

    data = serializer.validated_data
    approved_limit = round((36 * data["monthly_income"]) / 100000) * 100000

    customer = Customer.objects.create(
        first_name=data["first_name"],
        last_name=data["last_name"],
        phone_number=data["phone_number"],
        monthly_salary=data["monthly_income"],
        approved_limit=approved_limit,
        current_debt=0,
    )

    return Response(
        {
            "customer_id": customer.id,
            "name": f"{customer.first_name} {customer.last_name}",
            "age": data["age"],
            "monthly_salary": data["monthly_income"],
            "approved_limit": approved_limit,
            "phone_number": customer.phone_number,
        },
        status=status.HTTP_201_CREATED,
    )


def evaluate_loan(customer_id, interest_rate, loan_amount, tenure):
    customer = Customer.objects.filter(id=customer_id).first()
    if not customer:
        return {
            "approval": False,
            "monthly_installment": None,
            "score": 0,
            "message": "Customer not found",
        }

    loans = Loan.objects.filter(customer=customer)
    active_loans = [l for l in loans if l.end_date > date.today()]
    r = interest_rate / 1200
    P = loan_amount
    n = tenure
    new_emi = P / n if r == 0 else (P * r * (1 + r) ** n) / ((1 + r) ** n - 1)
    total_current_loans = sum(l.loan_amount for l in loans)
    total_current_emi = sum(l.monthly_repayment for l in loans)

    if total_current_emi + new_emi > customer.monthly_salary * 0.5:
        return {
            "approval": False,
            "message": "EMI exceeds 50% of salary",
        }

    if total_current_loans + loan_amount > customer.approved_limit:
        return {
            "approval": False,
            "message": "Approved limit exceeded",
        }

    score = 0

    if loans.exists():
        total_expected = sum(l.tenure for l in loans)
        total_paid = sum(l.emis_paid_on_time for l in loans)
        ratio = total_paid / total_expected if total_expected else 0
        score += ratio * 20
    else:
        score += 5

    count = loans.count()
    if count == 0:
        score += 5
    elif count <= 2:
        score += 10
    elif count <= 5:
        score += 7
    else:
        score += 3

    this_year = loans.filter(start_date__year=datetime.now().year).count()
    if this_year == 0:
        score += 10
    elif this_year <= 3:
        score += 5
    else:
        score += 2

    ratio = (
        total_current_loans / customer.approved_limit if customer.approved_limit else 1
    )
    if ratio < 0.3:
        score += 10
    elif ratio < 0.6:
        score += 5
    elif ratio < 0.9:
        score += 1
    else:
        score += 0

    score = round(min(score, 100), 2)

    corrected_interest = interest_rate
    approval = True

    if score > 50:
        pass
    elif 30 < score <= 50:
        if interest_rate < 12:
            corrected_interest = 12
    elif 10 < score <= 30:
        if interest_rate < 16:
            corrected_interest = 16
    else:
        approval = False

    EMI = None
    if approval:
        r = corrected_interest / 1200
        P = loan_amount
        n = tenure
        EMI = P / n if r == 0 else (P * r * (1 + r) ** n) / ((1 + r) ** n - 1)

    return {
        "approval": approval,
        "corrected_interest_rate": corrected_interest,
        "monthly_installment": round(EMI, 2) if EMI else None,
        "score": score,
        "message": "Loan approved" if approval else "Loan rejected due to credit score",
    }


@api_view(["POST"])
def check_eligibility(request):
    customer_id = request.data.get("customer_id")
    interest_rate = request.data.get("interest_rate")
    loan_amount = request.data.get("loan_amount")
    tenure = request.data.get("tenure")

    if not customer_id or not interest_rate or not loan_amount or not tenure:
        return Response(
            {
                "error": "customer_id, interest_rate, loan_amount and tenure are required"
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        interest_rate = float(interest_rate)
        loan_amount = float(loan_amount)
        tenure = int(tenure)
    except ValueError:
        return Response(
            {
                "error": "interest_rate and loan_amount must be numbers, tenure must be integer"
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    result = evaluate_loan(customer_id, interest_rate, loan_amount, tenure)
    if not result["approval"]:
        return Response({"approval": result["approval"], "message": result["message"]})

    if "corrected_interest_rate" not in result:
        return Response(
            {
                "customer_id": customer_id,
                "approval": result.get("approval", False),
                "message": result.get("message", "Loan rejected"),
                "interest_rate": interest_rate,
                "corrected_interest_rate": None,
                "tenure": tenure,
                "monthly_installment": None,
            },
            status=status.HTTP_200_OK,
        )

    return Response(
        {
            "customer_id": customer_id,
            "approval": result["approval"],
            "interest_rate": interest_rate,
            "corrected_interest_rate": result["corrected_interest_rate"],
            "tenure": tenure,
            "monthly_installment": result["monthly_installment"],
            "message": result.get("message"),
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
def create_loan(request):
    customer_id = request.data.get("customer_id")
    interest_rate = float(request.data.get("interest_rate"))
    loan_amount = float(request.data.get("loan_amount"))
    tenure = int(request.data.get("tenure"))

    result = evaluate_loan(customer_id, interest_rate, loan_amount, tenure)

    if not result["approval"]:
        return Response(
            {
                "loan_id": None,
                "customer_id": customer_id,
                "loan_approved": False,
                "message": result["message"],
                "monthly_installment": None,
            }
        )

    customer = Customer.objects.get(id=customer_id)
    start_date = date.today()
    end_date = start_date + relativedelta(months=tenure)

    loan = Loan.objects.create(
        customer=customer,
        loan_amount=loan_amount,
        interest_rate=result["corrected_interest_rate"],
        tenure=tenure,
        monthly_repayment=result["monthly_installment"],
        start_date=start_date,
        end_date=end_date,
        emis_paid_on_time=0,
    )

    return Response(
        {
            "loan_id": loan.id,
            "customer_id": customer_id,
            "loan_approved": True,
            "message": "Loan approved successfully",
            "monthly_installment": result["monthly_installment"],
        }
    )


@api_view(["GET"])
def view_loan(request, loan_id):
    loan = Loan.objects.filter(id=loan_id).first()

    if not loan:
        return Response({"error": "Loan not found"}, status=404)

    c = loan.customer

    return Response(
        {
            "loan_id": loan.id,
            "customer": {
                "id": c.id,
                "first_name": c.first_name,
                "last_name": c.last_name,
                "phone_number": c.phone_number,
                "age": c.age,
            },
            "loan_amount": loan.loan_amount,
            "interest_rate": loan.interest_rate,
            "monthly_installment": round(loan.monthly_repayment, 2),
            "tenure": loan.tenure,
        }
    )


@api_view(["GET"])
def view_loans(request, customer_id):
    customer = Customer.objects.filter(id=customer_id).first()

    if not customer:
        return Response({"error": "Customer not found"}, status=404)

    loans = Loan.objects.filter(customer=customer)

    data = []
    for loan in loans:
        data.append(
            {
                "loan_id": loan.id,
                "loan_amount": loan.loan_amount,
                "interest_rate": loan.interest_rate,
                "monthly_installment": round(loan.monthly_repayment, 2),
                "repayments_left": max(0, loan.tenure - loan.emis_paid_on_time),
            }
        )

    return Response(data)
