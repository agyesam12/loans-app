from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from packages.id_generator import UniqueIDField
from django.utils.timezone import now
from django.contrib.auth.hashers import make_password, check_password
import random
from django.core.exceptions import ValidationError


ID_TYPES = [
    ("Driver License", "Driver License"),
    ("Passport", "Passport"),
    ("Ghana Card", "Ghana Card"),
    ("Voter ID", "Voter ID"),
    ("NHIS ID", "NHIS ID"),
    ]

GENDER = [
    ("Male", "Male"), 
    ("Female", "Female"),
    ]


class CompanyBranch(models.Model):
    id = models.CharField(max_length=100, primary_key=True, unique=True, editable=False)
    branch_code = models.CharField(max_length=100, unique=True)
    branch_name = models.CharField(max_length=200, null=True, blank=False)
    location = models.CharField(max_length=200, null=True, blank=False)
    user = models.ForeignKey('User', on_delete=models.PROTECT)
    is_active = models.BooleanField(default=True)
    allow_sms = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    def __str__(self):
        return f"{self.branch_name}"

    class Meta:
        ordering = ['-created_at']
    
    def total_staffs(self):
        """Returns the total number of staff members assigned to this branch."""
        return User.objects.filter(company_branch=self, is_worker=True).count()

    def total_customers(self):
        """Returns the total number of customers assigned to this branch."""
        return User.objects.filter(company_branch=self, is_customer=True).count()
    
    def save(self, *args, **kwargs):
        
        is_new = self._state.adding
        
        if is_new:
            if not self.id:
                if self.branch_code:
                    self.id = self.branch_code + ''.join(str(random.randint(0, 9)) for _ in range(8))
                    
                else:
                    raise ValidationError("Branch Code not found, Report the issue to the Developer")
        super().save(*args, **kwargs)
        


class CustomUserManager(BaseUserManager):
    """
    Custom manager for the User model.
    """

    def create_user(self, phone_number, pin=None, email=None, password=None, **extra_fields):
        """
        Create a regular user.
        """
        if not phone_number:
            raise ValueError(_('The phone number must be set.'))

        if email:
            email = self.normalize_email(email)
        user = self.model(phone_number=phone_number, email=email, **extra_fields)

        # Hash and set pin (for phone-pin login)
        if pin:
            user.pin = make_password(pin)

        # Hash and set password (optional for phone-password login)
        if password:
            user.set_password(password)

        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, pin, email=None, password=None, **extra_fields):
        """
        Create a superuser.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self.create_user(phone_number, make_password(pin), email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model for phone_number and email-based authentication.
    """
    # Identity
    user_id = UniqueIDField(primary_key=True, unique=True, editable=False)
    email = models.EmailField(_('email address'), unique=True, null=True, blank=False)
    phone_number = models.CharField(_('phone number'), unique=True, max_length=15, validators=[RegexValidator(regex=r'^\+?\d{9,15}$', message=_('Phone number must be between 9 and 15 digits.'))])
    pin = models.CharField(_('pin'), max_length=128,null=True)
    
    # Profile
    username = models.CharField(max_length=150, unique=True)
    full_name = models.CharField(max_length=150, null=True, blank=False)
    country = models.CharField(max_length=100, null=True, blank=False)
    location = models.CharField(max_length=255, null=True, blank=False)
    occupation = models.CharField(max_length=255, null=True, blank=False)
    
    # KYC - Know Your Client/Customer
    date_of_birth = models.DateField(null=True, blank=False)
    gender = models.CharField(max_length=10, choices=GENDER, null=True, blank=False)
    photo = models.ImageField(upload_to='uploaded_files/kyc/photos/', default='media/profile.png', null=True, blank=True)
    id_type = models.CharField(max_length=200, choices=ID_TYPES, null=True, blank=False)
    id_number = models.CharField(max_length=50, unique=True, blank=False)
    id_front_view = models.ImageField(upload_to='uploaded_files/kyc/id_front/', null=True, blank=True)
    id_back_view = models.ImageField(upload_to='uploaded_files/kyc/id_back/', null=True, blank=True)
    date_joined = models.DateTimeField(default=now,null=True, blank=True)
    
    # Branch
    company_branch = models.ForeignKey(CompanyBranch, on_delete=models.SET_NULL, null=True, related_name='company_branches', blank=False)
    # Permissions
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    is_worker = models.BooleanField(default=False)
    is_customer = models.BooleanField(default=False)
    allow_sms = models.BooleanField(default=True)
    
    # Next of Kning
    nok_name = models.CharField(_('Next of Kins Name'), max_length=150, null=True, blank=False)
    nok_phone = models.CharField(_('Next of Kins Phone'), max_length=150, null=True, blank=False)
    nok_location = models.CharField(_('Next of Kin Location'), max_length=150, null=True, blank=False)
    
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['pin', 'email', 'username','id_number']

    def __str__(self):
        return f"{self.full_name} | {self.user_id}"

    def set_pin(self, raw_pin):
        """
        Hash and set the PIN.
        """
        self.pin = make_password(raw_pin)

    def check_pin(self, raw_pin):
        """
        Check the PIN against the hashed value.
        """
        return check_password(raw_pin, self.pin)
    
    def get_photo(self):
        if self.photo:
            return self.photo.url
        else:
            return ""
        
    def get_full_name(self):
        return f"{self.full_name}"

    def get_loan_history(self):
        return LoanHistory.objects.filter(user=self)
    
    def check_loan_eligibility(self):

    # Check the loan underwriting details first
        loan_underwriting = LoanUnderwriting.objects.filter(loan_application__user=self).first()
    
        if not loan_underwriting:
           return False, "No loan underwriting information found."

    # Check Credit Score (Example: Minimum credit score required is 600)
        if loan_underwriting.credit_score < 600:
           return False, "Credit score is too low."

    # Check Debt-to-Income Ratio (Example: Maximum allowable debt-to-income ratio is 0.40)
        if loan_underwriting.debt_to_income_ratio > 0.40:
           return False, "Debt-to-income ratio is too high."

    # Check Income (Example: Minimum required income is 1000)
       if loan_underwriting.income < 1000:
          return False, "Income is too low."

    # Check Previous Loan History (Example: No failed repayments allowed)
       failed_loans = LoanHistory.objects.filter(user=self, status='Denied')
       if failed_loans.exists():
          return False, "Previous loans have been denied."

    # If all checks pass, the user is eligible
       return True, "Eligible for a loan."


    
    
       class Meta:
         ordering=["-created_at"]





class LoanType(models.Model):
    name = models.CharField(max_length=100)  # E.g., Personal, Car, Home
    description = models.TextField(null=True, blank=True)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)  # Annual Interest Rate
    min_amount = models.DecimalField(max_digits=10, decimal_places=2)
    max_amount = models.DecimalField(max_digits=10, decimal_places=2)
    term_months = models.PositiveIntegerField()  # Loan term in months

    def __str__(self):
        return self.name


class LoanApplication(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    loan_type = models.ForeignKey(LoanType, on_delete=models.CASCADE)
    amount_requested = models.DecimalField(max_digits=10, decimal_places=2)
    amount_approved = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    collateral = models.ForeignKey('Collateral', on_delete=models.SET_NULL, null=True, blank=True)  # For secured loans
    status = models.CharField(max_length=20, choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Denied', 'Denied')], default='Pending')
    application_date = models.DateTimeField(auto_now_add=True)
    repayment_schedule = models.JSONField(null=True, blank=True)  # Schedule of monthly repayments
    approval_date = models.DateTimeField(null=True, blank=True)  # When loan was approved
    loan_underwriting = models.ForeignKey('LoanUnderwriting', on_delete=models.SET_NULL, null=True, blank=True)
    
    def approve_loan(self, approved_amount):
        self.status = 'Approved'
        self.amount_approved = approved_amount
        self.approval_date = now()
        self.save()

    def deny_loan(self):
        self.status = 'Denied'
        self.save()



class LoanUnderwriting(models.Model):
    loan_application = models.OneToOneField(LoanApplication, on_delete=models.CASCADE)
    credit_score = models.IntegerField(null=True, blank=True)  # Credit score from credit provider
    debt_to_income_ratio = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)  # Debt to income ratio
    income = models.DecimalField(max_digits=15, decimal_places=2)  # User's income
    previous_loans = models.IntegerField(default=0)  # Number of loans previously taken
    underwriter_notes = models.TextField(null=True, blank=True)  # Notes from loan underwriter

    def evaluate(self):
        # Implement logic for evaluation of loan applications
        if self.credit_score < 600:
            self.loan_application.deny_loan()
        else:
            self.loan_application.approve_loan(approved_amount=self.loan_application.amount_requested)




class Collateral(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    loan_application = models.ForeignKey(LoanApplication, on_delete=models.CASCADE)
    collateral_type = models.CharField(max_length=100)
    collateral_value = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=[('Pending', 'Pending'), ('Verified', 'Verified'), ('Released', 'Released')], default='Pending')

    def __str__(self):
        return f"{self.collateral_type} for loan {self.loan_application.id}"



class RepaymentMethod(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name



class LoanRepayment(models.Model):
    loan_application = models.ForeignKey(LoanApplication, on_delete=models.CASCADE)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    repayment_method = models.ForeignKey(RepaymentMethod, on_delete=models.CASCADE)
    remaining_balance = models.DecimalField(max_digits=10, decimal_places=2)

    def make_repayment(self, amount, method):
        self.amount_paid = amount
        self.repayment_method = method
        self.remaining_balance -= amount
        self.save()

    def overdue_penalty(self):
        # Implement logic to apply penalty if payment is overdue
        pass

class LoanInterestRate(models.Model):
    loan_type = models.ForeignKey(LoanType, on_delete=models.CASCADE)
    rate = models.DecimalField(max_digits=5, decimal_places=2)  # Interest rate
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()

    def __str__(self):
        return f"Interest Rate for {self.loan_type.name} - {self.rate}%"



class LoanHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    loan_application = models.ForeignKey(LoanApplication, on_delete=models.CASCADE)
    action_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[('Applied', 'Applied'), ('Approved', 'Approved'), ('Denied', 'Denied'), ('Repaid', 'Repaid')])
    note = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Loan History for {self.user.full_name} - {self.status}"
