import pandas as pd
from django.core.management.base import BaseCommand

from credit_aprprove.models import Customer, Loan


class Command(BaseCommand):
    help = "Load initial customer and loan data"

    def handle(self, *args, **kwargs):
        customers = pd.read_excel("customer_data.xlsx")
        customers.columns = (
            customers.columns.str.strip().str.lower().str.replace(" ", "_")
        )
        for _, row in customers.iterrows():
            Customer.objects.get_or_create(
                customer_id=row["customer_id"],
                defaults={
                    "first_name": row["first_name"],
                    "last_name": row["last_name"],
                    "phone_number": str(row["phone_number"]),
                    "monthly_salary": row["monthly_salary"],
                    "approved_limit": row["approved_limit"],
                    "current_debt": 0,
                },
            )

        loans = pd.read_excel("loan_data.xlsx")
        loans.columns = loans.columns.str.strip().str.lower().str.replace(" ", "_")
        for _, row in loans.iterrows():
            customer = Customer.objects.get(customer_id=row["customer_id"])

            Loan.objects.get_or_create(
                loan_id=row["loan_id"],
                defaults={
                    "customer": customer,
                    "loan_amount": row["loan_amount"],
                    "tenure": row["tenure"],
                    "interest_rate": row["interest_rate"],
                    "monthly_repayment": row["monthly_payment"],
                    "emis_paid_on_time": row["emis_paid_on_time"],
                    "start_date": row["date_of_approval"],
                    "end_date": row["end_date"],
                },
            )

        self.stdout.write(self.style.SUCCESS("Data loaded successfully"))
