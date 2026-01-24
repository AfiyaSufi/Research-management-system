from rest_framework import viewsets, permissions, status, decorators, parsers
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from .models import Proposal, ProposalTimeline, Notice, Evaluator, CommitteeReview, RectorReview
from .serializers import (
    ProposalSerializer, ProposalListSerializer, ParticipantProposalSerializer, NoticeSerializer,
    EvaluatorSerializer, EvaluatorDetailSerializer,
    CommitteeReviewSerializer, CommitteeReviewDetailSerializer,
    RectorReviewSerializer, RectorReviewDetailSerializer
)
from .services import (
    send_evaluator_invite, send_committee_invite, send_rector_invite,
    send_rejection_email, send_acceptance_email, send_step_progress_email
)


class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'ADMIN'


class IsParticipantUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'PARTICIPANT'


class NoticeViewSet(viewsets.ModelViewSet):
    """ViewSet for managing research notices"""
    serializer_class = NoticeSerializer
    
    def get_queryset(self):
        user = self.request.user
        if user.is_anonymous:
            return Notice.objects.none()
        if user.role == 'ADMIN':
            return Notice.objects.all().order_by('-created_at')
        # Participants see only active notices
        return Notice.objects.filter(
            status='ACTIVE',
            deadline__gt=timezone.now()
        ).order_by('-created_at')

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class ProposalViewSet(viewsets.ModelViewSet):
    serializer_class = ProposalSerializer
    
    def get_queryset(self):
        user = self.request.user
        if user.is_anonymous:
            return Proposal.objects.none()
        
        queryset = Proposal.objects.all()
        
        if user.role != 'ADMIN':
            queryset = queryset.filter(participant=user)
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by step
        step_filter = self.request.query_params.get('step')
        if step_filter:
            queryset = queryset.filter(current_step=step_filter)
        
        # Filter by notice
        notice_filter = self.request.query_params.get('notice')
        if notice_filter:
            queryset = queryset.filter(notice_id=notice_filter)
        
        return queryset.order_by('-created_at')

    def get_serializer_class(self):
        user = self.request.user
        is_participant = hasattr(user, 'role') and user.role != 'ADMIN'
        
        if self.action == 'list':
            return ProposalListSerializer
        elif is_participant:
            # Use anonymous serializer for participants (hides evaluator names)
            return ParticipantProposalSerializer
        return ProposalSerializer

    def get_permissions(self):
        if self.action in ['create', 'upload_budget']:
            permission_classes = [IsParticipantUser]
        elif self.action in ['list', 'retrieve']:
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        proposal = serializer.save(participant=self.request.user)
        self.log_action(proposal, 'Submission', 'Proposal has been submitted')

    def log_action(self, proposal, step, action, details=None, actor=None, actor_name=None):
        ProposalTimeline.objects.create(
            proposal=proposal,
            step_name=step,
            action=action,
            actor=actor or self.request.user if hasattr(self, 'request') else None,
            actor_name=actor_name,
            details=details
        )

    @decorators.action(detail=False, methods=['get'])
    def library(self, request):
        """Get all accepted/rejected proposals for the library view"""
        if request.user.role != 'ADMIN':
            return Response({'error': 'Admin only'}, status=status.HTTP_403_FORBIDDEN)
        
        queryset = Proposal.objects.filter(status__in=['ACCEPTED', 'REJECTED'])
        
        # Apply filters
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        notice_filter = request.query_params.get('notice')
        if notice_filter:
            queryset = queryset.filter(notice_id=notice_filter)
        
        serializer = ProposalListSerializer(queryset.order_by('-updated_at'), many=True)
        return Response(serializer.data)

    @decorators.action(detail=True, methods=['post'])
    def format_check(self, request, pk=None):
        """Step 1: Format checking by admin"""
        proposal = self.get_object()
        if proposal.current_step != 1:
            return Response({'error': 'Invalid step'}, status=status.HTTP_400_BAD_REQUEST)
        
        accepted = request.data.get('accepted', False)
        reason = request.data.get('reason', '')
        
        if accepted:
            proposal.current_step = 2
            proposal.save()
            self.log_action(proposal, 'Format Check', 'Format checked')
            send_step_progress_email(proposal, 'Format Checking', True)
            return Response({'status': 'moved to step 2'})
        else:
            proposal.status = 'REJECTED'
            proposal.rejection_reason = reason or 'Format check failed'
            proposal.save()
            self.log_action(proposal, 'Format Check', 'Rejected', reason or 'Format check failed')
            send_rejection_email(proposal, 'Format Checking', reason or 'Format check failed')
            return Response({'status': 'rejected'})

    @decorators.action(detail=True, methods=['post'])
    def plagiarism_check(self, request, pk=None):
        """Step 2: Plagiarism checking by admin"""
        proposal = self.get_object()
        if proposal.current_step != 2:
            return Response({'error': 'Invalid step'}, status=status.HTTP_400_BAD_REQUEST)
        
        percentage = float(request.data.get('percentage', 0))
        proposal.plagiarism_percentage = percentage
        
        if percentage > 20:
            proposal.status = 'REJECTED'
            proposal.rejection_reason = f'Plagiarism score too high: {percentage}%'
            proposal.save()
            self.log_action(proposal, 'Plagiarism Check', f'Plagiarism checked: {percentage}%', 'Rejected - exceeded 20% threshold')
            send_rejection_email(proposal, 'Plagiarism Checking', f'Plagiarism score: {percentage}% (max allowed: 20%)')
            return Response({'status': 'rejected', 'percentage': percentage})
        else:
            proposal.current_step = 3
            proposal.save()
            self.log_action(proposal, 'Plagiarism Check', f'Plagiarism checked: {percentage}%')
            send_step_progress_email(proposal, 'Plagiarism Checking', True)
            return Response({'status': 'moved to step 3', 'percentage': percentage})

    @decorators.action(detail=True, methods=['post'])
    def invite_evaluator(self, request, pk=None):
        """Step 3: Invite external evaluators"""
        proposal = self.get_object()
        if proposal.current_step != 3:
            return Response({'error': 'Invalid step'}, status=status.HTTP_400_BAD_REQUEST)
        
        email = request.data.get('email')
        name = request.data.get('name')
        
        if not email or not name:
            return Response({'error': 'Email and name required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if evaluator already exists
        if Evaluator.objects.filter(proposal=proposal, email=email).exists():
            return Response({'error': 'Evaluator already invited'}, status=status.HTTP_400_BAD_REQUEST)
        
        evaluator = Evaluator.objects.create(
            proposal=proposal,
            email=email,
            name=name
        )
        
        # Send invitation email
        email_sent = send_evaluator_invite(evaluator)
        
        self.log_action(proposal, 'Evaluation', 'Evaluator Invited', f'Invited {name} ({email})')
        
        serializer = EvaluatorSerializer(evaluator)
        return Response({
            'evaluator': serializer.data,
            'email_sent': email_sent
        }, status=status.HTTP_201_CREATED)

    @decorators.action(detail=True, methods=['post'])
    def complete_evaluation(self, request, pk=None):
        """Step 3: Mark evaluation as complete and move to seminar"""
        proposal = self.get_object()
        if proposal.current_step != 3:
            return Response({'error': 'Invalid step'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if we have at least 2 completed evaluations
        completed_evals = proposal.evaluations.filter(status='COMPLETED').count()
        if completed_evals < 2:
            return Response({
                'error': f'Need at least 2 completed evaluations. Currently have {completed_evals}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check average marks
        avg = proposal.get_evaluator_average()
        if avg < 65:
            proposal.status = 'REJECTED'
            proposal.rejection_reason = f'Average evaluation score too low: {avg:.1f}'
            proposal.save()
            self.log_action(proposal, 'Evaluation', 'Rejected', f'Average marks {avg:.1f} < 65')
            send_rejection_email(proposal, 'Evaluation', f'Average evaluation score: {avg:.1f} (minimum required: 65)')
            return Response({'status': 'rejected', 'average': avg})
        
        proposal.current_step = 4
        proposal.save()
        self.log_action(proposal, 'Evaluation', 'Accepted', f'Average marks {avg:.1f} >= 65')
        send_step_progress_email(proposal, 'Evaluation', True)
        return Response({'status': 'moved to step 4', 'average': avg})

    @decorators.action(detail=True, methods=['post'])
    def seminar_decision(self, request, pk=None):
        """Step 4: Seminar presentation decision"""
        proposal = self.get_object()
        if proposal.current_step != 4:
            return Response({'error': 'Invalid step'}, status=status.HTTP_400_BAD_REQUEST)
        
        attended = request.data.get('attended', False)
        accepted = request.data.get('accepted', False)
        reason = request.data.get('reason', '')
        
        if not attended or not accepted:
            proposal.status = 'REJECTED'
            reason_text = 'Did not attend seminar' if not attended else (reason or 'Faculty rejected presentation')
            proposal.rejection_reason = reason_text
            proposal.save()
            self.log_action(proposal, 'Seminar', 'Faculty seminar rejected', reason_text)
            send_rejection_email(proposal, 'Seminar Presentation', reason_text)
            return Response({'status': 'rejected'})
        else:
            proposal.current_step = 5
            proposal.save()
            self.log_action(proposal, 'Seminar', 'Faculty seminar accepted')
            send_step_progress_email(proposal, 'Seminar Presentation', True)
            return Response({'status': 'moved to step 5'})

    @decorators.action(detail=True, methods=['post'], parser_classes=[parsers.MultiPartParser])
    def upload_budget(self, request, pk=None):
        """Step 5: Participant uploads budget and revised proposal"""
        proposal = self.get_object()
        if proposal.current_step != 5:
            return Response({'error': 'Invalid step'}, status=status.HTTP_400_BAD_REQUEST)
        
        if request.user != proposal.participant:
            return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)

        if 'budget_file' in request.FILES:
            proposal.budget_file = request.FILES['budget_file']
        if 'revised_file' in request.FILES:
            proposal.revised_file = request.FILES['revised_file']
        
        proposal.save()
        self.log_action(proposal, 'Research Committee', 'Files Uploaded', 
                       'Budget and Revised Proposal uploaded')
        return Response({'status': 'files uploaded'})

    @decorators.action(detail=True, methods=['post'])
    def invite_committee(self, request, pk=None):
        """Step 5: Invite research committee members"""
        proposal = self.get_object()
        if proposal.current_step != 5:
            return Response({'error': 'Invalid step'}, status=status.HTTP_400_BAD_REQUEST)
        
        email = request.data.get('email')
        name = request.data.get('name')
        
        if not email or not name:
            return Response({'error': 'Email and name required'}, status=status.HTTP_400_BAD_REQUEST)
        
        if CommitteeReview.objects.filter(proposal=proposal, email=email).exists():
            return Response({'error': 'Committee member already invited'}, status=status.HTTP_400_BAD_REQUEST)
        
        review = CommitteeReview.objects.create(
            proposal=proposal,
            email=email,
            name=name
        )
        
        email_sent = send_committee_invite(review)
        
        self.log_action(proposal, 'Research Committee', 'Member Invited', f'Invited {name} ({email})')
        
        serializer = CommitteeReviewSerializer(review)
        return Response({
            'review': serializer.data,
            'email_sent': email_sent
        }, status=status.HTTP_201_CREATED)

    @decorators.action(detail=True, methods=['post'])
    def complete_committee_review(self, request, pk=None):
        """Step 5: Complete committee review and move to rector"""
        proposal = self.get_object()
        if proposal.current_step != 5:
            return Response({'error': 'Invalid step'}, status=status.HTTP_400_BAD_REQUEST)
        
        completed_reviews = proposal.committee_reviews.filter(status='COMPLETED')
        if completed_reviews.count() == 0:
            return Response({'error': 'No completed committee reviews'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if any rejected
        rejected = completed_reviews.filter(decision='REJECTED').exists()
        if rejected:
            proposal.status = 'REJECTED'
            proposal.rejection_reason = 'Committee rejected proposal'
            proposal.save()
            self.log_action(proposal, 'Research Committee', 'Committee rejected')
            send_rejection_email(proposal, 'Research Committee', 'Committee rejected the proposal')
            return Response({'status': 'rejected'})
        
        # Get allocated budget - first check if admin provided one, then check committee reviews
        allocated_budget = request.data.get('allocated_budget')
        if not allocated_budget:
            # Check if any committee member provided a budget in their review
            approved_with_budget = completed_reviews.filter(
                decision='APPROVED', 
                allocated_budget__isnull=False
            ).first()
            if approved_with_budget:
                allocated_budget = approved_with_budget.allocated_budget
        
        if allocated_budget:
            try:
                proposal.allocated_budget = float(allocated_budget)
            except (ValueError, TypeError):
                return Response({'error': 'Invalid budget amount'}, status=status.HTTP_400_BAD_REQUEST)
        
        proposal.current_step = 6
        proposal.save()
        
        budget_detail = f'Allocated budget: ${proposal.allocated_budget:,.2f}' if proposal.allocated_budget else 'Committee approved'
        self.log_action(proposal, 'Research Committee', 'Committee approved', budget_detail)
        send_step_progress_email(proposal, 'Research Committee', True)
        return Response({'status': 'moved to step 6', 'allocated_budget': str(proposal.allocated_budget) if proposal.allocated_budget else None})

    @decorators.action(detail=True, methods=['post'])
    def invite_rector(self, request, pk=None):
        """Step 6: Invite rector for final approval"""
        proposal = self.get_object()
        if proposal.current_step != 6:
            return Response({'error': 'Invalid step'}, status=status.HTTP_400_BAD_REQUEST)
        
        email = request.data.get('email')
        name = request.data.get('name')
        
        if not email or not name:
            return Response({'error': 'Email and name required'}, status=status.HTTP_400_BAD_REQUEST)
        
        if hasattr(proposal, 'rector_review'):
            return Response({'error': 'Rector already invited'}, status=status.HTTP_400_BAD_REQUEST)
        
        review = RectorReview.objects.create(
            proposal=proposal,
            email=email,
            name=name
        )
        
        email_sent = send_rector_invite(review)
        
        self.log_action(proposal, 'Rector Approval', 'Rector Invited', f'Invited {name} ({email})')
        
        serializer = RectorReviewSerializer(review)
        return Response({
            'review': serializer.data,
            'email_sent': email_sent
        }, status=status.HTTP_201_CREATED)


# External Form Views (No authentication required - uses token)

class EvaluatorFormView(APIView):
    """External evaluator form - accessed via unique token"""
    permission_classes = [permissions.AllowAny]
    
    def get(self, request, token):
        """Get evaluation form data"""
        evaluator = get_object_or_404(Evaluator, token=token)
        
        if evaluator.is_expired:
            context = {
                'error': 'This link has expired',
                'evaluator': None
            }
            return render(request, 'evaluator_form.html', context)
        
        if evaluator.status == 'COMPLETED':
            context = {
                'error': 'Evaluation already submitted',
                'evaluator': None
            }
            return render(request, 'evaluator_form.html', context)
        
        # Prepare context data for the template
        serializer = EvaluatorDetailSerializer(evaluator, context={'request': request})
        context = {
            'evaluator': serializer.data,
            'error': None,
            'success': None
        }
        return render(request, 'evaluator_form.html', context)
    
    def post(self, request, token):
        """Submit evaluation"""
        evaluator = get_object_or_404(Evaluator, token=token)
        
        if evaluator.is_expired:
            context = {
                'error': 'This link has expired',
                'evaluator': None
            }
            return render(request, 'evaluator_form.html', context)
        
        if evaluator.status == 'COMPLETED':
            context = {
                'error': 'Evaluation already submitted',
                'evaluator': None
            }
            return render(request, 'evaluator_form.html', context)
        
        marks = request.POST.get('marks')
        comments = request.POST.get('comments', '')
        
        if marks is None or marks == '':
            serializer = EvaluatorDetailSerializer(evaluator, context={'request': request})
            context = {
                'error': 'Marks are required',
                'evaluator': serializer.data
            }
            return render(request, 'evaluator_form.html', context)
        
        try:
            marks = float(marks)
            if marks < 0 or marks > 100:
                serializer = EvaluatorDetailSerializer(evaluator, context={'request': request})
                context = {
                    'error': 'Marks must be between 0 and 100',
                    'evaluator': serializer.data
                }
                return render(request, 'evaluator_form.html', context)
        except ValueError:
            serializer = EvaluatorDetailSerializer(evaluator, context={'request': request})
            context = {
                'error': 'Invalid marks value',
                'evaluator': serializer.data
            }
            return render(request, 'evaluator_form.html', context)
        
        evaluator.marks = marks
        evaluator.comments = comments
        evaluator.status = 'COMPLETED'
        evaluator.completed_at = timezone.now()
        evaluator.save()
        
        # Log the action
        ProposalTimeline.objects.create(
            proposal=evaluator.proposal,
            step_name='Evaluation',
            action='Evaluation Submitted',
            actor_name=evaluator.name,
            details=f'Marks: {marks}/100'
        )
        
        context = {
            'success': 'Evaluation submitted successfully',
            'evaluator': None,
            'error': None
        }
        return render(request, 'evaluator_form.html', context)



class CommitteeFormView(APIView):
    """External committee review form - accessed via unique token"""
    permission_classes = [permissions.AllowAny]
    
    def get(self, request, token):
        """Get committee review form data"""
        review = get_object_or_404(CommitteeReview, token=token)
        
        if timezone.now() > review.expires_at and review.status == 'PENDING':
            context = {
                'error': 'This link has expired',
                'review': None
            }
            return render(request, 'committee_form.html', context)
        
        if review.status == 'COMPLETED':
            context = {
                'error': 'Review already submitted',
                'review': None
            }
            return render(request, 'committee_form.html', context)
        
        serializer = CommitteeReviewDetailSerializer(review, context={'request': request})
        context = {
            'review': serializer.data,
            'error': None,
            'success': None
        }
        return render(request, 'committee_form.html', context)
    
    def post(self, request, token):
        """Submit committee review"""
        review = get_object_or_404(CommitteeReview, token=token)
        
        if timezone.now() > review.expires_at and review.status == 'PENDING':
            context = {
                'error': 'This link has expired',
                'review': None
            }
            return render(request, 'committee_form.html', context)
        
        if review.status == 'COMPLETED':
            context = {
                'error': 'Review already submitted',
                'review': None
            }
            return render(request, 'committee_form.html', context)
        
        decision = request.POST.get('decision')
        comments = request.POST.get('comments', '')
        allocated_budget = request.POST.get('allocated_budget', '')
        
        if decision not in ['APPROVED', 'REJECTED', 'REVISION_REQUIRED']:
            serializer = CommitteeReviewDetailSerializer(review, context={'request': request})
            context = {
                'error': 'Invalid decision',
                'review': serializer.data
            }
            return render(request, 'committee_form.html', context)
        
        # Validate budget is provided when approving
        if decision == 'APPROVED' and not allocated_budget:
            serializer = CommitteeReviewDetailSerializer(review, context={'request': request})
            context = {
                'error': 'Please specify the allocated budget amount when approving',
                'review': serializer.data
            }
            return render(request, 'committee_form.html', context)
        
        review.decision = decision
        review.comments = comments
        review.status = 'COMPLETED'
        review.completed_at = timezone.now()
        
        # Save allocated budget if approving
        if decision == 'APPROVED' and allocated_budget:
            try:
                review.allocated_budget = float(allocated_budget)
                # Also save to the proposal
                review.proposal.allocated_budget = float(allocated_budget)
                review.proposal.save()
            except (ValueError, TypeError):
                pass
        
        review.save()
        
        # Build timeline details with budget if approved
        timeline_details = comments
        if decision == 'APPROVED' and allocated_budget:
            timeline_details = f'Allocated Budget: ${float(allocated_budget):,.2f}' + (f'\n{comments}' if comments else '')
        
        ProposalTimeline.objects.create(
            proposal=review.proposal,
            step_name='Research Committee',
            action=f'Committee Review: {decision}',
            actor_name=review.name,
            details=timeline_details
        )
        
        context = {
            'success': 'Review submitted successfully',
            'review': None,
            'error': None
        }
        return render(request, 'committee_form.html', context)



class RectorFormView(APIView):
    """External rector approval form - accessed via unique token"""
    permission_classes = [permissions.AllowAny]
    
    def get(self, request, token):
        """Get rector review form data"""
        review = get_object_or_404(RectorReview, token=token)
        
        if timezone.now() > review.expires_at and review.status == 'PENDING':
            context = {
                'error': 'This link has expired',
                'review': None
            }
            return render(request, 'rector_form.html', context)
        
        if review.status == 'COMPLETED':
            context = {
                'error': 'Decision already submitted',
                'review': None
            }
            return render(request, 'rector_form.html', context)
        
        serializer = RectorReviewDetailSerializer(review, context={'request': request})
        context = {
            'review': serializer.data,
            'error': None,
            'success': None
        }
        return render(request, 'rector_form.html', context)
    
    def post(self, request, token):
        """Submit rector decision"""
        review = get_object_or_404(RectorReview, token=token)
        
        if timezone.now() > review.expires_at and review.status == 'PENDING':
            context = {
                'error': 'This link has expired',
                'review': None
            }
            return render(request, 'rector_form.html', context)
        
        if review.status == 'COMPLETED':
            context = {
                'error': 'Decision already submitted',
                'review': None
            }
            return render(request, 'rector_form.html', context)
        
        decision = request.POST.get('decision')
        comments = request.POST.get('comments', '')
        
        if decision not in ['APPROVED', 'REJECTED']:
            serializer = RectorReviewDetailSerializer(review, context={'request': request})
            context = {
                'error': 'Invalid decision',
                'review': serializer.data
            }
            return render(request, 'rector_form.html', context)
        
        review.decision = decision
        review.comments = comments
        review.status = 'COMPLETED'
        review.completed_at = timezone.now()
        review.save()
        
        proposal = review.proposal
        
        if decision == 'APPROVED':
            proposal.status = 'ACCEPTED'
            proposal.save()
            ProposalTimeline.objects.create(
                proposal=proposal,
                step_name='Rector Approval',
                action='Rector approved',
                actor_name=review.name,
                details=comments
            )
            send_acceptance_email(proposal)
        else:
            proposal.status = 'REJECTED'
            proposal.rejection_reason = comments or 'Rejected by Rector'
            proposal.save()
            ProposalTimeline.objects.create(
                proposal=proposal,
                step_name='Rector Approval',
                action='Rector rejected',
                actor_name=review.name,
                details=comments
            )
            send_rejection_email(proposal, 'Rector Approval', comments or 'Rejected by Rector')
        
        context = {
            'success': 'Decision submitted successfully',
            'review': None,
            'error': None
        }
        return render(request, 'rector_form.html', context)


