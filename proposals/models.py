from django.db import models
from django.conf import settings
import uuid
from datetime import timedelta
from django.utils import timezone


class Notice(models.Model):
    """Admin creates notices for research topics"""
    STATUS_CHOICES = (
        ('ACTIVE', 'Active'),
        ('CLOSED', 'Closed'),
    )
    
    title = models.CharField(max_length=255)
    description = models.TextField()
    deadline = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notices')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
    
    @property
    def is_active(self):
        return self.status == 'ACTIVE' and self.deadline > timezone.now()


class Proposal(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('ACCEPTED', 'Accepted'),
        ('REJECTED', 'Rejected'),
    )
    
    STEP_CHOICES = (
        (1, 'Format Checking'),
        (2, 'Plagiarism Checking'),
        (3, 'Evaluation'),
        (4, 'Seminar'),
        (5, 'Research Committee'),
        (6, 'Rector Approval'),
    )

    notice = models.ForeignKey(Notice, on_delete=models.CASCADE, related_name='proposals', null=True, blank=True)
    participant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='proposals')
    title = models.CharField(max_length=255)
    description = models.TextField()
    
    # Files
    proposal_file = models.FileField(upload_to='proposals/')
    revised_file = models.FileField(upload_to='revised_proposals/', null=True, blank=True)
    budget_file = models.FileField(upload_to='budgets/', null=True, blank=True)
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    current_step = models.IntegerField(choices=STEP_CHOICES, default=1)
    rejection_reason = models.TextField(null=True, blank=True)
    
    # Step-specific data
    plagiarism_percentage = models.FloatField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
    
    def get_evaluator_average(self):
        """Calculate average marks from completed evaluations"""
        evaluations = self.evaluations.filter(status='COMPLETED')
        if evaluations.count() == 0:
            return None
        total = sum(e.marks for e in evaluations)
        return total / evaluations.count()


class Evaluator(models.Model):
    """External evaluator invited via email"""
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('EXPIRED', 'Expired'),
    )
    
    proposal = models.ForeignKey(Proposal, on_delete=models.CASCADE, related_name='evaluations')
    email = models.EmailField()
    name = models.CharField(max_length=255)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    # Evaluation data
    marks = models.FloatField(null=True, blank=True)
    comments = models.TextField(null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    invited_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} - {self.proposal.title}"
    
    @property
    def is_expired(self):
        return timezone.now() > self.expires_at and self.status == 'PENDING'


class CommitteeReview(models.Model):
    """Research Committee member review"""
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('EXPIRED', 'Expired'),
    )
    DECISION_CHOICES = (
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('REVISION_REQUIRED', 'Revision Required'),
    )
    
    proposal = models.ForeignKey(Proposal, on_delete=models.CASCADE, related_name='committee_reviews')
    email = models.EmailField()
    name = models.CharField(max_length=255)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    decision = models.CharField(max_length=20, choices=DECISION_CHOICES, null=True, blank=True)
    comments = models.TextField(null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    invited_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Committee: {self.name} - {self.proposal.title}"


class RectorReview(models.Model):
    """Rector/Vice-Chancellor final approval"""
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('EXPIRED', 'Expired'),
    )
    DECISION_CHOICES = (
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    )
    
    proposal = models.OneToOneField(Proposal, on_delete=models.CASCADE, related_name='rector_review')
    email = models.EmailField()
    name = models.CharField(max_length=255)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    decision = models.CharField(max_length=20, choices=DECISION_CHOICES, null=True, blank=True)
    comments = models.TextField(null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    invited_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Rector: {self.name} - {self.proposal.title}"


class ProposalTimeline(models.Model):
    proposal = models.ForeignKey(Proposal, on_delete=models.CASCADE, related_name='timeline')
    step_name = models.CharField(max_length=100)
    action = models.CharField(max_length=100)  # e.g., "Submitted", "Approved", "Rejected"
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    actor_name = models.CharField(max_length=255, null=True, blank=True)  # For external actors
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.proposal.title} - {self.action} at {self.timestamp}"

