"""
Email services for the Research Management System
Handles sending emails for evaluator invitations, committee reviews, and rector approvals
"""
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def get_site_url():
    """Get the site URL from settings"""
    return getattr(settings, 'SITE_URL', 'http://localhost:8000')


def send_evaluator_invite(evaluator):
    """
    Send invitation email to an external evaluator
    """
    site_url = get_site_url()
    evaluation_link = f"{site_url}/external/evaluate/{evaluator.token}/"
    
    subject = f"Research Proposal Evaluation Request: {evaluator.proposal.title}"
    
    html_message = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #6366f1;">Research Proposal Evaluation Request</h2>
            
            <p>Dear {evaluator.name},</p>
            
            <p>You have been invited to evaluate a research proposal submitted to our Research Management System.</p>
            
            <div style="background-color: #f3f4f6; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <h3 style="margin-top: 0; color: #4f46e5;">Proposal Details</h3>
                <p><strong>Title:</strong> {evaluator.proposal.title}</p>
                <p><strong>Submitted by:</strong> {evaluator.proposal.participant.get_full_name() or evaluator.proposal.participant.username}</p>
                <p><strong>Description:</strong> {evaluator.proposal.description[:200]}...</p>
            </div>
            
            <p>Please click the button below to access the evaluation form:</p>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{evaluation_link}" 
                   style="background-color: #6366f1; color: white; padding: 12px 30px; 
                          text-decoration: none; border-radius: 6px; display: inline-block;">
                    Evaluate Proposal
                </a>
            </div>
            
            <p style="color: #666; font-size: 14px;">
                <strong>Note:</strong> This link will expire on {evaluator.expires_at.strftime('%B %d, %Y at %I:%M %p')}.
            </p>
            
            <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">
            
            <p style="color: #666; font-size: 12px;">
                This is an automated message from the Research Management System. 
                Please do not reply to this email.
            </p>
        </div>
    </body>
    </html>
    """
    
    plain_message = strip_tags(html_message)
    
    try:
        result = send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[evaluator.email],
            html_message=html_message,
            fail_silently=False,
        )
        print(f"[EMAIL] Successfully sent evaluator invite to {evaluator.email} for proposal '{evaluator.proposal.title}'. Result: {result}")
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send evaluator invite to {evaluator.email}: {e}")
        return False


def send_committee_invite(committee_review):
    """
    Send invitation email to a research committee member
    """
    site_url = get_site_url()
    review_link = f"{site_url}/external/committee/{committee_review.token}/"
    
    subject = f"Research Committee Review Required: {committee_review.proposal.title}"
    
    html_message = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #6366f1;">Research Committee Review Request</h2>
            
            <p>Dear {committee_review.name},</p>
            
            <p>A research proposal requires your review as a member of the Research Committee.</p>
            
            <div style="background-color: #f3f4f6; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <h3 style="margin-top: 0; color: #4f46e5;">Proposal Details</h3>
                <p><strong>Title:</strong> {committee_review.proposal.title}</p>
                <p><strong>Submitted by:</strong> {committee_review.proposal.participant.get_full_name() or committee_review.proposal.participant.username}</p>
                <p><strong>Current Step:</strong> Research Committee Review</p>
            </div>
            
            <p>The proposal has passed the following stages:</p>
            <ul>
                <li>✅ Format Checking</li>
                <li>✅ Plagiarism Checking (Score: {committee_review.proposal.plagiarism_percentage or 'N/A'}%)</li>
                <li>✅ External Evaluation</li>
                <li>✅ Seminar Presentation</li>
            </ul>
            
            <p>Please click the button below to review the proposal and budget:</p>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{review_link}" 
                   style="background-color: #6366f1; color: white; padding: 12px 30px; 
                          text-decoration: none; border-radius: 6px; display: inline-block;">
                    Review Proposal
                </a>
            </div>
            
            <p style="color: #666; font-size: 14px;">
                <strong>Note:</strong> This link will expire on {committee_review.expires_at.strftime('%B %d, %Y at %I:%M %p')}.
            </p>
            
            <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">
            
            <p style="color: #666; font-size: 12px;">
                This is an automated message from the Research Management System.
            </p>
        </div>
    </body>
    </html>
    """
    
    plain_message = strip_tags(html_message)
    
    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[committee_review.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Failed to send committee invite: {e}")
        return False


def send_rector_invite(rector_review):
    """
    Send invitation email to the Rector/Vice-Chancellor for final approval
    """
    site_url = get_site_url()
    review_link = f"{site_url}/external/rector/{rector_review.token}/"
    
    subject = f"Final Approval Required: {rector_review.proposal.title}"
    
    html_message = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #6366f1;">Research Proposal - Final Approval Required</h2>
            
            <p>Dear {rector_review.name},</p>
            
            <p>A research proposal requires your final approval.</p>
            
            <div style="background-color: #f3f4f6; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <h3 style="margin-top: 0; color: #4f46e5;">Proposal Details</h3>
                <p><strong>Title:</strong> {rector_review.proposal.title}</p>
                <p><strong>Submitted by:</strong> {rector_review.proposal.participant.get_full_name() or rector_review.proposal.participant.username}</p>
            </div>
            
            <p>This proposal has successfully completed all review stages:</p>
            <ul>
                <li>✅ Format Checking - Passed</li>
                <li>✅ Plagiarism Checking - {rector_review.proposal.plagiarism_percentage or 'N/A'}%</li>
                <li>✅ External Evaluation - Passed</li>
                <li>✅ Seminar Presentation - Completed</li>
                <li>✅ Research Committee - Approved</li>
            </ul>
            
            <p>Please click the button below to review and provide your final decision:</p>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{review_link}" 
                   style="background-color: #6366f1; color: white; padding: 12px 30px; 
                          text-decoration: none; border-radius: 6px; display: inline-block;">
                    Review & Approve
                </a>
            </div>
            
            <p style="color: #666; font-size: 14px;">
                <strong>Note:</strong> This link will expire on {rector_review.expires_at.strftime('%B %d, %Y at %I:%M %p')}.
            </p>
            
            <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">
            
            <p style="color: #666; font-size: 12px;">
                This is an automated message from the Research Management System.
            </p>
        </div>
    </body>
    </html>
    """
    
    plain_message = strip_tags(html_message)
    
    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[rector_review.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Failed to send rector invite: {e}")
        return False


def send_rejection_email(proposal, step_name, reason):
    """
    Send rejection notification to the participant
    """
    subject = f"Proposal Update: {proposal.title}"
    
    html_message = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #ef4444;">Proposal Status Update</h2>
            
            <p>Dear {proposal.participant.get_full_name() or proposal.participant.username},</p>
            
            <p>We regret to inform you that your research proposal has not been approved at the <strong>{step_name}</strong> stage.</p>
            
            <div style="background-color: #fef2f2; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #ef4444;">
                <h3 style="margin-top: 0; color: #dc2626;">Proposal Details</h3>
                <p><strong>Title:</strong> {proposal.title}</p>
                <p><strong>Stage:</strong> {step_name}</p>
                <p><strong>Reason:</strong> {reason}</p>
            </div>
            
            <p>If you have any questions, please contact the research administration office.</p>
            
            <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">
            
            <p style="color: #666; font-size: 12px;">
                This is an automated message from the Research Management System.
            </p>
        </div>
    </body>
    </html>
    """
    
    plain_message = strip_tags(html_message)
    
    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[proposal.participant.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Failed to send rejection email: {e}")
        return False


def send_acceptance_email(proposal):
    """
    Send final acceptance notification to the participant
    """
    subject = f"Congratulations! Your Proposal Has Been Approved: {proposal.title}"
    
    html_message = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #10b981;">🎉 Congratulations!</h2>
            
            <p>Dear {proposal.participant.get_full_name() or proposal.participant.username},</p>
            
            <p>We are pleased to inform you that your research proposal has been <strong>approved</strong> at all stages and has received final approval from the Rector.</p>
            
            <div style="background-color: #ecfdf5; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #10b981;">
                <h3 style="margin-top: 0; color: #059669;">Approved Proposal</h3>
                <p><strong>Title:</strong> {proposal.title}</p>
                <p><strong>Status:</strong> ✅ Fully Approved</p>
            </div>
            
            <p>Your proposal has successfully passed through:</p>
            <ul>
                <li>✅ Format Checking</li>
                <li>✅ Plagiarism Checking</li>
                <li>✅ External Evaluation</li>
                <li>✅ Seminar Presentation</li>
                <li>✅ Research Committee Review</li>
                <li>✅ Rector Approval</li>
            </ul>
            
            <p>Please contact the research administration office for next steps regarding your research project.</p>
            
            <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">
            
            <p style="color: #666; font-size: 12px;">
                This is an automated message from the Research Management System.
            </p>
        </div>
    </body>
    </html>
    """
    
    plain_message = strip_tags(html_message)
    
    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[proposal.participant.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Failed to send acceptance email: {e}")
        return False


def send_step_progress_email(proposal, step_name, passed=True):
    """
    Send progress notification to the participant when a step is completed
    """
    status_text = "passed" if passed else "requires attention"
    status_color = "#10b981" if passed else "#f59e0b"
    
    subject = f"Proposal Progress: {step_name} - {proposal.title}"
    
    html_message = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: {status_color};">Proposal Progress Update</h2>
            
            <p>Dear {proposal.participant.get_full_name() or proposal.participant.username},</p>
            
            <p>Your research proposal has {status_text} the <strong>{step_name}</strong> stage.</p>
            
            <div style="background-color: #f3f4f6; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <p><strong>Proposal:</strong> {proposal.title}</p>
                <p><strong>Current Step:</strong> {dict(proposal.STEP_CHOICES).get(proposal.current_step, 'Unknown')}</p>
            </div>
            
            <p>You can log in to the system to track the full progress of your proposal.</p>
            
            <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">
            
            <p style="color: #666; font-size: 12px;">
                This is an automated message from the Research Management System.
            </p>
        </div>
    </body>
    </html>
    """
    
    plain_message = strip_tags(html_message)
    
    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[proposal.participant.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Failed to send progress email: {e}")
        return False
