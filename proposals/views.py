from rest_framework import viewsets, permissions, status, decorators, parsers
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Proposal, ProposalTimeline
from .serializers import ProposalSerializer

class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'ADMIN'

class IsParticipantUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'PARTICIPANT'

class ProposalViewSet(viewsets.ModelViewSet):
    serializer_class = ProposalSerializer
    
    def get_queryset(self):
        user = self.request.user
        if user.is_anonymous:
            return Proposal.objects.none()
        if user.role == 'ADMIN':
            return Proposal.objects.all()
        return Proposal.objects.filter(participant=user)

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
        self.log_action(proposal, 'Submission', 'Proposal Submitted', f"Initial submission by {self.request.user.username}")

    def log_action(self, proposal, step, action, details=None):
        ProposalTimeline.objects.create(
            proposal=proposal,
            step_name=step,
            action=action,
            actor=self.request.user,
            details=details
        )

    @decorators.action(detail=True, methods=['post'])
    def format_check(self, request, pk=None):
        proposal = self.get_object()
        if proposal.current_step != 1:
            return Response({'error': 'Invalid step'}, status=status.HTTP_400_BAD_REQUEST)
        
        accepted = request.data.get('accepted', False)
        if accepted:
            proposal.current_step = 2
            proposal.save()
            self.log_action(proposal, 'Format Check', 'Accepted', 'Format check passed')
            return Response({'status': 'moved to step 2'})
        else:
            proposal.status = 'REJECTED'
            proposal.save()
            self.log_action(proposal, 'Format Check', 'Rejected', 'Format check failed')
            return Response({'status': 'rejected'})

    @decorators.action(detail=True, methods=['post'])
    def plagiarism_check(self, request, pk=None):
        proposal = self.get_object()
        if proposal.current_step != 2:
            return Response({'error': 'Invalid step'}, status=status.HTTP_400_BAD_REQUEST)
        
        percentage = float(request.data.get('percentage', 0))
        proposal.plagiarism_percentage = percentage
        
        if percentage > 20:
            proposal.status = 'REJECTED'
            proposal.save()
            self.log_action(proposal, 'Plagiarism Check', 'Rejected', f'Plagiarism {percentage}% > 20%')
            return Response({'status': 'rejected'})
        else:
            proposal.current_step = 3
            proposal.save()
            self.log_action(proposal, 'Plagiarism Check', 'Accepted', f'Plagiarism {percentage}% <= 20%')
            return Response({'status': 'moved to step 3'})

    @decorators.action(detail=True, methods=['post'])
    def evaluate(self, request, pk=None):
        proposal = self.get_object()
        if proposal.current_step != 3:
            return Response({'error': 'Invalid step'}, status=status.HTTP_400_BAD_REQUEST)
        
        m1 = float(request.data.get('mark1', 0))
        m2 = float(request.data.get('mark2', 0))
        proposal.evaluator_1_marks = m1
        proposal.evaluator_2_marks = m2
        
        total = m1 + m2
        if total < 65:
            proposal.status = 'REJECTED'
            proposal.save()
            self.log_action(proposal, 'Evaluation', 'Rejected', f'Total marks {total} < 65')
            return Response({'status': 'rejected'})
        else:
            proposal.current_step = 4
            proposal.save()
            self.log_action(proposal, 'Evaluation', 'Accepted', f'Total marks {total} >= 65')
            return Response({'status': 'moved to step 4'})

    @decorators.action(detail=True, methods=['post'])
    def seminar_decision(self, request, pk=None):
        proposal = self.get_object()
        if proposal.current_step != 4:
            return Response({'error': 'Invalid step'}, status=status.HTTP_400_BAD_REQUEST)
        
        attended = request.data.get('attended', False)
        accepted = request.data.get('accepted', False)
        
        if not attended or not accepted:
            proposal.status = 'REJECTED'
            proposal.save()
            reason = 'Not attended' if not attended else 'Faculty rejected'
            self.log_action(proposal, 'Seminar', 'Rejected', reason)
            return Response({'status': 'rejected'})
        else:
            proposal.current_step = 5
            proposal.save()
            self.log_action(proposal, 'Seminar', 'Accepted', 'Seminar successful')
            return Response({'status': 'moved to step 5'})

    @decorators.action(detail=True, methods=['post'], parser_classes=[parsers.MultiPartParser])
    def upload_budget(self, request, pk=None):
        proposal = self.get_object()
        if proposal.current_step != 5:
            return Response({'error': 'Invalid step'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Only participant can upload
        if request.user != proposal.participant:
             return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)

        if 'budget_file' in request.FILES:
            proposal.budget_file = request.FILES['budget_file']
        if 'revised_file' in request.FILES:
            proposal.revised_file = request.FILES['revised_file']
        
        proposal.save()
        self.log_action(proposal, 'Research Committee', 'Files Uploaded', 'Budget and Revised Proposal uploaded')
        return Response({'status': 'files uploaded'})

    @decorators.action(detail=True, methods=['post'])
    def committee_decision(self, request, pk=None):
        proposal = self.get_object()
        if proposal.current_step != 5:
            return Response({'error': 'Invalid step'}, status=status.HTTP_400_BAD_REQUEST)
        
        accepted = request.data.get('accepted', False)
        if accepted:
            proposal.current_step = 6
            proposal.save()
            self.log_action(proposal, 'Research Committee', 'Accepted', 'Committee approved budget')
            return Response({'status': 'moved to step 6'})
        else:
            proposal.status = 'REJECTED'
            proposal.save()
            self.log_action(proposal, 'Research Committee', 'Rejected', 'Committee rejected')
            return Response({'status': 'rejected'})

    @decorators.action(detail=True, methods=['post'])
    def rector_decision(self, request, pk=None):
        proposal = self.get_object()
        if proposal.current_step != 6:
            return Response({'error': 'Invalid step'}, status=status.HTTP_400_BAD_REQUEST)
        
        accepted = request.data.get('accepted', False)
        if accepted:
            proposal.status = 'ACCEPTED'
            proposal.save()
            self.log_action(proposal, 'Rector Approval', 'Accepted', 'Final Approval. Report Generated.')
            return Response({'status': 'accepted'})
        else:
            proposal.status = 'REJECTED'
            proposal.save()
            self.log_action(proposal, 'Rector Approval', 'Rejected', 'Rector rejected')
            return Response({'status': 'rejected'})

