from django.db import models
from django.conf import settings

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
    
    # Step-specific data
    plagiarism_percentage = models.FloatField(null=True, blank=True)
    evaluator_1_marks = models.FloatField(null=True, blank=True)
    evaluator_2_marks = models.FloatField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class ProposalTimeline(models.Model):
    proposal = models.ForeignKey(Proposal, on_delete=models.CASCADE, related_name='timeline')
    step_name = models.CharField(max_length=100)
    action = models.CharField(max_length=100) # e.g., "Submitted", "Approved", "Rejected"
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.proposal.title} - {self.action} at {self.timestamp}"

