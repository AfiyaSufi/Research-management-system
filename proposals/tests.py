from django.test import TestCase, override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model
from datetime import timedelta
import uuid
import tempfile
import os

from .models import (
    Notice, Proposal, Evaluator, CommitteeReview, 
    RectorReview, ProposalTimeline
)

User = get_user_model()

# Use a temp directory for test media files
TEMP_MEDIA_ROOT = tempfile.mkdtemp()

User = get_user_model()


class NoticeModelTests(TestCase):
    """Tests for Notice model"""

    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass',
            role='ADMIN'
        )

    def test_create_notice(self):
        """Test creating a notice"""
        notice = Notice.objects.create(
            title='Research Call 2026',
            description='Call for research proposals',
            deadline=timezone.now() + timedelta(days=30),
            created_by=self.admin
        )
        self.assertEqual(notice.title, 'Research Call 2026')
        self.assertEqual(notice.status, 'ACTIVE')
        self.assertEqual(notice.created_by, self.admin)

    def test_notice_string_representation(self):
        """Test notice __str__ method"""
        notice = Notice.objects.create(
            title='Test Notice',
            description='Test description',
            deadline=timezone.now() + timedelta(days=30),
            created_by=self.admin
        )
        self.assertEqual(str(notice), 'Test Notice')

    def test_notice_is_active_property(self):
        """Test is_active property with active notice"""
        notice = Notice.objects.create(
            title='Active Notice',
            description='Active description',
            deadline=timezone.now() + timedelta(days=30),
            status='ACTIVE',
            created_by=self.admin
        )
        self.assertTrue(notice.is_active)

    def test_notice_is_not_active_when_closed(self):
        """Test is_active property with closed notice"""
        notice = Notice.objects.create(
            title='Closed Notice',
            description='Closed description',
            deadline=timezone.now() + timedelta(days=30),
            status='CLOSED',
            created_by=self.admin
        )
        self.assertFalse(notice.is_active)

    def test_notice_is_not_active_when_expired(self):
        """Test is_active property with expired deadline"""
        notice = Notice.objects.create(
            title='Expired Notice',
            description='Expired description',
            deadline=timezone.now() - timedelta(days=1),
            status='ACTIVE',
            created_by=self.admin
        )
        self.assertFalse(notice.is_active)


class ProposalModelTests(TestCase):
    """Tests for Proposal model"""

    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass',
            role='ADMIN'
        )
        self.participant = User.objects.create_user(
            username='participant',
            email='participant@example.com',
            password='participantpass',
            role='PARTICIPANT'
        )
        self.notice = Notice.objects.create(
            title='Research Call',
            description='Call for proposals',
            deadline=timezone.now() + timedelta(days=30),
            created_by=self.admin
        )
        self.test_file = SimpleUploadedFile(
            "proposal.pdf",
            b"file_content",
            content_type="application/pdf"
        )

    def test_create_proposal(self):
        """Test creating a proposal"""
        proposal = Proposal.objects.create(
            notice=self.notice,
            participant=self.participant,
            title='My Research Proposal',
            description='Research description',
            proposal_file=self.test_file
        )
        self.assertEqual(proposal.title, 'My Research Proposal')
        self.assertEqual(proposal.status, 'PENDING')
        self.assertEqual(proposal.current_step, 1)
        self.assertEqual(proposal.participant, self.participant)

    def test_proposal_string_representation(self):
        """Test proposal __str__ method"""
        proposal = Proposal.objects.create(
            participant=self.participant,
            title='Test Proposal',
            description='Test description',
            proposal_file=self.test_file
        )
        self.assertEqual(str(proposal), 'Test Proposal')

    def test_proposal_default_status(self):
        """Test default status is PENDING"""
        proposal = Proposal.objects.create(
            participant=self.participant,
            title='Test Proposal',
            description='Test description',
            proposal_file=self.test_file
        )
        self.assertEqual(proposal.status, 'PENDING')

    def test_proposal_default_step(self):
        """Test default step is 1 (Format Checking)"""
        proposal = Proposal.objects.create(
            participant=self.participant,
            title='Test Proposal',
            description='Test description',
            proposal_file=self.test_file
        )
        self.assertEqual(proposal.current_step, 1)

    def test_get_evaluator_average_no_evaluations(self):
        """Test average with no evaluations returns None"""
        proposal = Proposal.objects.create(
            participant=self.participant,
            title='Test Proposal',
            description='Test description',
            proposal_file=self.test_file
        )
        self.assertIsNone(proposal.get_evaluator_average())

    def test_get_evaluator_average_with_evaluations(self):
        """Test average calculation with evaluations"""
        proposal = Proposal.objects.create(
            participant=self.participant,
            title='Test Proposal',
            description='Test description',
            proposal_file=self.test_file
        )
        Evaluator.objects.create(
            proposal=proposal,
            email='eval1@example.com',
            name='Evaluator 1',
            marks=80,
            status='COMPLETED',
            expires_at=timezone.now() + timedelta(days=7)
        )
        Evaluator.objects.create(
            proposal=proposal,
            email='eval2@example.com',
            name='Evaluator 2',
            marks=70,
            status='COMPLETED',
            expires_at=timezone.now() + timedelta(days=7)
        )
        self.assertEqual(proposal.get_evaluator_average(), 75.0)

    def test_get_evaluator_average_ignores_pending(self):
        """Test average ignores pending evaluations"""
        proposal = Proposal.objects.create(
            participant=self.participant,
            title='Test Proposal',
            description='Test description',
            proposal_file=self.test_file
        )
        Evaluator.objects.create(
            proposal=proposal,
            email='eval1@example.com',
            name='Evaluator 1',
            marks=80,
            status='COMPLETED',
            expires_at=timezone.now() + timedelta(days=7)
        )
        Evaluator.objects.create(
            proposal=proposal,
            email='eval2@example.com',
            name='Evaluator 2',
            marks=50,
            status='PENDING',
            expires_at=timezone.now() + timedelta(days=7)
        )
        self.assertEqual(proposal.get_evaluator_average(), 80.0)


class EvaluatorModelTests(TestCase):
    """Tests for Evaluator model"""

    def setUp(self):
        self.participant = User.objects.create_user(
            username='participant',
            password='participantpass',
            role='PARTICIPANT'
        )
        self.test_file = SimpleUploadedFile(
            "proposal.pdf", b"content", content_type="application/pdf"
        )
        self.proposal = Proposal.objects.create(
            participant=self.participant,
            title='Test Proposal',
            description='Test description',
            proposal_file=self.test_file
        )

    def test_create_evaluator(self):
        """Test creating an evaluator"""
        evaluator = Evaluator.objects.create(
            proposal=self.proposal,
            email='evaluator@example.com',
            name='Dr. Smith'
        )
        self.assertEqual(evaluator.name, 'Dr. Smith')
        self.assertEqual(evaluator.status, 'PENDING')
        self.assertIsNotNone(evaluator.token)
        self.assertIsNotNone(evaluator.expires_at)

    def test_evaluator_auto_expires_at(self):
        """Test expires_at is auto-set to 7 days from now"""
        before = timezone.now()
        evaluator = Evaluator.objects.create(
            proposal=self.proposal,
            email='evaluator@example.com',
            name='Dr. Smith'
        )
        after = timezone.now()
        expected_min = before + timedelta(days=7)
        expected_max = after + timedelta(days=7)
        self.assertGreaterEqual(evaluator.expires_at, expected_min)
        self.assertLessEqual(evaluator.expires_at, expected_max)

    def test_evaluator_is_expired_when_past_deadline(self):
        """Test is_expired when past deadline and still pending"""
        evaluator = Evaluator.objects.create(
            proposal=self.proposal,
            email='evaluator@example.com',
            name='Dr. Smith',
            expires_at=timezone.now() - timedelta(days=1)
        )
        self.assertTrue(evaluator.is_expired)

    def test_evaluator_not_expired_when_completed(self):
        """Test is_expired is False when completed even if past deadline"""
        evaluator = Evaluator.objects.create(
            proposal=self.proposal,
            email='evaluator@example.com',
            name='Dr. Smith',
            status='COMPLETED',
            expires_at=timezone.now() - timedelta(days=1)
        )
        self.assertFalse(evaluator.is_expired)

    def test_evaluator_unique_token(self):
        """Test each evaluator gets unique token"""
        eval1 = Evaluator.objects.create(
            proposal=self.proposal,
            email='eval1@example.com',
            name='Evaluator 1'
        )
        eval2 = Evaluator.objects.create(
            proposal=self.proposal,
            email='eval2@example.com',
            name='Evaluator 2'
        )
        self.assertNotEqual(eval1.token, eval2.token)


class CommitteeReviewModelTests(TestCase):
    """Tests for CommitteeReview model"""

    def setUp(self):
        self.participant = User.objects.create_user(
            username='participant',
            password='participantpass',
            role='PARTICIPANT'
        )
        self.test_file = SimpleUploadedFile(
            "proposal.pdf", b"content", content_type="application/pdf"
        )
        self.proposal = Proposal.objects.create(
            participant=self.participant,
            title='Test Proposal',
            description='Test description',
            proposal_file=self.test_file
        )

    def test_create_committee_review(self):
        """Test creating a committee review"""
        review = CommitteeReview.objects.create(
            proposal=self.proposal,
            email='committee@example.com',
            name='Prof. Johnson'
        )
        self.assertEqual(review.name, 'Prof. Johnson')
        self.assertEqual(review.status, 'PENDING')
        self.assertIsNone(review.decision)


class RectorReviewModelTests(TestCase):
    """Tests for RectorReview model"""

    def setUp(self):
        self.participant = User.objects.create_user(
            username='participant',
            password='participantpass',
            role='PARTICIPANT'
        )
        self.test_file = SimpleUploadedFile(
            "proposal.pdf", b"content", content_type="application/pdf"
        )
        self.proposal = Proposal.objects.create(
            participant=self.participant,
            title='Test Proposal',
            description='Test description',
            proposal_file=self.test_file
        )

    def test_create_rector_review(self):
        """Test creating a rector review"""
        review = RectorReview.objects.create(
            proposal=self.proposal,
            email='rector@university.edu',
            name='Rector Name'
        )
        self.assertEqual(review.name, 'Rector Name')
        self.assertEqual(review.status, 'PENDING')

    def test_rector_review_one_to_one(self):
        """Test only one rector review per proposal"""
        RectorReview.objects.create(
            proposal=self.proposal,
            email='rector@university.edu',
            name='Rector Name'
        )
        # Attempting to create another should fail
        with self.assertRaises(Exception):
            RectorReview.objects.create(
                proposal=self.proposal,
                email='another@university.edu',
                name='Another Rector'
            )


class NoticeAPITests(APITestCase):
    """Tests for Notice API endpoints"""

    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass',
            role='ADMIN'
        )
        self.participant = User.objects.create_user(
            username='participant',
            email='participant@example.com',
            password='participantpass',
            role='PARTICIPANT'
        )
        self.admin_token = Token.objects.create(user=self.admin)
        self.participant_token = Token.objects.create(user=self.participant)
        self.notices_url = '/api/notices/'

    def test_admin_can_create_notice(self):
        """Test admin can create a notice"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        data = {
            'title': 'New Research Call',
            'description': 'Description of the call',
            'deadline': (timezone.now() + timedelta(days=30)).isoformat()
        }
        response = self.client.post(self.notices_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Notice.objects.count(), 1)
        notice = Notice.objects.first()
        self.assertEqual(notice.created_by, self.admin)

    def test_participant_cannot_create_notice(self):
        """Test participant cannot create a notice"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.participant_token.key}')
        data = {
            'title': 'New Research Call',
            'description': 'Description',
            'deadline': (timezone.now() + timedelta(days=30)).isoformat()
        }
        response = self.client.post(self.notices_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_participant_sees_only_active_notices(self):
        """Test participant only sees active notices with future deadline"""
        # Create active notice
        Notice.objects.create(
            title='Active Notice',
            description='Active',
            deadline=timezone.now() + timedelta(days=30),
            status='ACTIVE',
            created_by=self.admin
        )
        # Create closed notice
        Notice.objects.create(
            title='Closed Notice',
            description='Closed',
            deadline=timezone.now() + timedelta(days=30),
            status='CLOSED',
            created_by=self.admin
        )
        # Create expired notice
        Notice.objects.create(
            title='Expired Notice',
            description='Expired',
            deadline=timezone.now() - timedelta(days=1),
            status='ACTIVE',
            created_by=self.admin
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.participant_token.key}')
        response = self.client.get(self.notices_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Active Notice')

    def test_admin_sees_all_notices(self):
        """Test admin sees all notices regardless of status"""
        Notice.objects.create(
            title='Active Notice',
            description='Active',
            deadline=timezone.now() + timedelta(days=30),
            status='ACTIVE',
            created_by=self.admin
        )
        Notice.objects.create(
            title='Closed Notice',
            description='Closed',
            deadline=timezone.now() + timedelta(days=30),
            status='CLOSED',
            created_by=self.admin
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.get(self.notices_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class ProposalAPITests(APITestCase):
    """Tests for Proposal API endpoints"""

    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass',
            role='ADMIN'
        )
        self.participant = User.objects.create_user(
            username='participant',
            email='participant@example.com',
            password='participantpass',
            role='PARTICIPANT'
        )
        self.participant2 = User.objects.create_user(
            username='participant2',
            email='participant2@example.com',
            password='participantpass2',
            role='PARTICIPANT'
        )
        self.admin_token = Token.objects.create(user=self.admin)
        self.participant_token = Token.objects.create(user=self.participant)
        self.participant2_token = Token.objects.create(user=self.participant2)
        
        self.notice = Notice.objects.create(
            title='Research Call',
            description='Description',
            deadline=timezone.now() + timedelta(days=30),
            created_by=self.admin
        )
        self.proposals_url = '/api/proposals/'

    def test_participant_can_create_proposal(self):
        """Test participant can create a proposal"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.participant_token.key}')
        test_file = SimpleUploadedFile(
            "proposal.pdf", b"content", content_type="application/pdf"
        )
        data = {
            'title': 'My Research',
            'description': 'Research description',
            'proposal_file': test_file,
            'notice': self.notice.id
        }
        response = self.client.post(self.proposals_url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        proposal = Proposal.objects.first()
        self.assertEqual(proposal.participant, self.participant)
        self.assertEqual(proposal.current_step, 1)

    def test_admin_cannot_create_proposal(self):
        """Test admin cannot create a proposal"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        test_file = SimpleUploadedFile(
            "proposal.pdf", b"content", content_type="application/pdf"
        )
        data = {
            'title': 'Admin Research',
            'description': 'Description',
            'proposal_file': test_file
        }
        response = self.client.post(self.proposals_url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_participant_sees_only_own_proposals(self):
        """Test participant only sees their own proposals"""
        test_file1 = SimpleUploadedFile(
            "proposal1.pdf", b"content1", content_type="application/pdf"
        )
        test_file2 = SimpleUploadedFile(
            "proposal2.pdf", b"content2", content_type="application/pdf"
        )
        # Create proposal for participant1
        Proposal.objects.create(
            participant=self.participant,
            title='Participant 1 Proposal',
            description='Desc',
            proposal_file=test_file1
        )
        # Create proposal for participant2
        Proposal.objects.create(
            participant=self.participant2,
            title='Participant 2 Proposal',
            description='Desc',
            proposal_file=test_file2
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.participant_token.key}')
        response = self.client.get(self.proposals_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Participant 1 Proposal')

    def test_admin_sees_all_proposals(self):
        """Test admin sees all proposals"""
        test_file1 = SimpleUploadedFile(
            "proposal1.pdf", b"content1", content_type="application/pdf"
        )
        test_file2 = SimpleUploadedFile(
            "proposal2.pdf", b"content2", content_type="application/pdf"
        )
        Proposal.objects.create(
            participant=self.participant,
            title='Participant 1 Proposal',
            description='Desc',
            proposal_file=test_file1
        )
        Proposal.objects.create(
            participant=self.participant2,
            title='Participant 2 Proposal',
            description='Desc',
            proposal_file=test_file2
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.get(self.proposals_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class ProposalWorkflowTests(APITestCase):
    """Tests for the 6-step proposal workflow"""

    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass',
            role='ADMIN'
        )
        self.participant = User.objects.create_user(
            username='participant',
            email='participant@example.com',
            password='participantpass',
            role='PARTICIPANT'
        )
        self.admin_token = Token.objects.create(user=self.admin)
        self.participant_token = Token.objects.create(user=self.participant)
        
        self.test_file = SimpleUploadedFile(
            "proposal.pdf", b"content", content_type="application/pdf"
        )
        self.proposal = Proposal.objects.create(
            participant=self.participant,
            title='Test Proposal',
            description='Test description',
            proposal_file=self.test_file
        )
        self.proposals_url = '/api/proposals/'

    # Step 1: Format Checking Tests
    def test_format_check_accept(self):
        """Test Step 1: Format check acceptance moves to step 2"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.post(
            f'{self.proposals_url}{self.proposal.id}/format_check/',
            {'accepted': True},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.proposal.refresh_from_db()
        self.assertEqual(self.proposal.current_step, 2)
        self.assertEqual(self.proposal.status, 'PENDING')

    def test_format_check_reject(self):
        """Test Step 1: Format check rejection"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.post(
            f'{self.proposals_url}{self.proposal.id}/format_check/',
            {'accepted': False, 'reason': 'Invalid format'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.proposal.refresh_from_db()
        self.assertEqual(self.proposal.status, 'REJECTED')
        self.assertEqual(self.proposal.rejection_reason, 'Invalid format')

    def test_format_check_wrong_step(self):
        """Test format check fails if not on step 1"""
        self.proposal.current_step = 2
        self.proposal.save()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.post(
            f'{self.proposals_url}{self.proposal.id}/format_check/',
            {'accepted': True},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # Step 2: Plagiarism Checking Tests
    def test_plagiarism_check_pass(self):
        """Test Step 2: Plagiarism <= 20% moves to step 3"""
        self.proposal.current_step = 2
        self.proposal.save()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.post(
            f'{self.proposals_url}{self.proposal.id}/plagiarism_check/',
            {'percentage': 15},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.proposal.refresh_from_db()
        self.assertEqual(self.proposal.current_step, 3)
        self.assertEqual(self.proposal.plagiarism_percentage, 15)

    def test_plagiarism_check_fail(self):
        """Test Step 2: Plagiarism > 20% rejects proposal"""
        self.proposal.current_step = 2
        self.proposal.save()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.post(
            f'{self.proposals_url}{self.proposal.id}/plagiarism_check/',
            {'percentage': 25},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.proposal.refresh_from_db()
        self.assertEqual(self.proposal.status, 'REJECTED')
        self.assertIn('25', self.proposal.rejection_reason)

    def test_plagiarism_boundary_20_percent(self):
        """Test plagiarism exactly at 20% passes"""
        self.proposal.current_step = 2
        self.proposal.save()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.post(
            f'{self.proposals_url}{self.proposal.id}/plagiarism_check/',
            {'percentage': 20},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.proposal.refresh_from_db()
        self.assertEqual(self.proposal.current_step, 3)

    # Step 3: Evaluation Tests
    def test_invite_evaluator(self):
        """Test Step 3: Invite evaluator"""
        self.proposal.current_step = 3
        self.proposal.save()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.post(
            f'{self.proposals_url}{self.proposal.id}/invite_evaluator/',
            {'email': 'evaluator@example.com', 'name': 'Dr. Smith'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Evaluator.objects.count(), 1)

    def test_invite_duplicate_evaluator(self):
        """Test cannot invite same evaluator twice"""
        self.proposal.current_step = 3
        self.proposal.save()
        Evaluator.objects.create(
            proposal=self.proposal,
            email='evaluator@example.com',
            name='Dr. Smith'
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.post(
            f'{self.proposals_url}{self.proposal.id}/invite_evaluator/',
            {'email': 'evaluator@example.com', 'name': 'Dr. Smith'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_complete_evaluation_needs_two_evaluators(self):
        """Test evaluation completion requires at least 2 evaluators"""
        self.proposal.current_step = 3
        self.proposal.save()
        Evaluator.objects.create(
            proposal=self.proposal,
            email='eval1@example.com',
            name='Evaluator 1',
            marks=80,
            status='COMPLETED',
            expires_at=timezone.now() + timedelta(days=7)
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.post(
            f'{self.proposals_url}{self.proposal.id}/complete_evaluation/',
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_complete_evaluation_with_two_evaluators_pass(self):
        """Test evaluation passes with avg >= 65"""
        self.proposal.current_step = 3
        self.proposal.save()
        Evaluator.objects.create(
            proposal=self.proposal,
            email='eval1@example.com',
            name='Evaluator 1',
            marks=70,
            status='COMPLETED',
            expires_at=timezone.now() + timedelta(days=7)
        )
        Evaluator.objects.create(
            proposal=self.proposal,
            email='eval2@example.com',
            name='Evaluator 2',
            marks=70,
            status='COMPLETED',
            expires_at=timezone.now() + timedelta(days=7)
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.post(
            f'{self.proposals_url}{self.proposal.id}/complete_evaluation/',
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.proposal.refresh_from_db()
        self.assertEqual(self.proposal.current_step, 4)

    def test_complete_evaluation_fail_low_marks(self):
        """Test evaluation fails with avg < 65"""
        self.proposal.current_step = 3
        self.proposal.save()
        Evaluator.objects.create(
            proposal=self.proposal,
            email='eval1@example.com',
            name='Evaluator 1',
            marks=50,
            status='COMPLETED',
            expires_at=timezone.now() + timedelta(days=7)
        )
        Evaluator.objects.create(
            proposal=self.proposal,
            email='eval2@example.com',
            name='Evaluator 2',
            marks=60,
            status='COMPLETED',
            expires_at=timezone.now() + timedelta(days=7)
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.post(
            f'{self.proposals_url}{self.proposal.id}/complete_evaluation/',
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.proposal.refresh_from_db()
        self.assertEqual(self.proposal.status, 'REJECTED')

    # Step 4: Seminar Tests
    def test_seminar_accept(self):
        """Test Step 4: Seminar acceptance moves to step 5"""
        self.proposal.current_step = 4
        self.proposal.save()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.post(
            f'{self.proposals_url}{self.proposal.id}/seminar_decision/',
            {'attended': True, 'accepted': True},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.proposal.refresh_from_db()
        self.assertEqual(self.proposal.current_step, 5)

    def test_seminar_not_attended(self):
        """Test Step 4: Not attending seminar rejects"""
        self.proposal.current_step = 4
        self.proposal.save()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.post(
            f'{self.proposals_url}{self.proposal.id}/seminar_decision/',
            {'attended': False, 'accepted': False},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.proposal.refresh_from_db()
        self.assertEqual(self.proposal.status, 'REJECTED')

    # Step 5: Committee Review Tests
    def test_invite_committee(self):
        """Test Step 5: Invite committee member"""
        self.proposal.current_step = 5
        self.proposal.save()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.post(
            f'{self.proposals_url}{self.proposal.id}/invite_committee/',
            {'email': 'committee@example.com', 'name': 'Prof. Johnson'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CommitteeReview.objects.count(), 1)

    def test_complete_committee_approved(self):
        """Test Step 5: Committee approval moves to step 6"""
        self.proposal.current_step = 5
        self.proposal.save()
        CommitteeReview.objects.create(
            proposal=self.proposal,
            email='committee@example.com',
            name='Prof. Johnson',
            decision='APPROVED',
            status='COMPLETED',
            expires_at=timezone.now() + timedelta(days=7)
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.post(
            f'{self.proposals_url}{self.proposal.id}/complete_committee_review/',
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.proposal.refresh_from_db()
        self.assertEqual(self.proposal.current_step, 6)

    def test_complete_committee_rejected(self):
        """Test Step 5: Committee rejection fails proposal"""
        self.proposal.current_step = 5
        self.proposal.save()
        CommitteeReview.objects.create(
            proposal=self.proposal,
            email='committee@example.com',
            name='Prof. Johnson',
            decision='REJECTED',
            status='COMPLETED',
            expires_at=timezone.now() + timedelta(days=7)
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.post(
            f'{self.proposals_url}{self.proposal.id}/complete_committee_review/',
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.proposal.refresh_from_db()
        self.assertEqual(self.proposal.status, 'REJECTED')

    # Step 6: Rector Review Tests
    def test_invite_rector(self):
        """Test Step 6: Invite rector"""
        self.proposal.current_step = 6
        self.proposal.save()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.post(
            f'{self.proposals_url}{self.proposal.id}/invite_rector/',
            {'email': 'rector@university.edu', 'name': 'Rector Name'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(RectorReview.objects.count(), 1)

    def test_invite_rector_duplicate(self):
        """Test cannot invite rector twice"""
        self.proposal.current_step = 6
        self.proposal.save()
        RectorReview.objects.create(
            proposal=self.proposal,
            email='rector@university.edu',
            name='Rector Name'
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.post(
            f'{self.proposals_url}{self.proposal.id}/invite_rector/',
            {'email': 'another@university.edu', 'name': 'Another Rector'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class ExternalFormTests(APITestCase):
    """Tests for external evaluation/committee/rector forms"""

    def setUp(self):
        self.participant = User.objects.create_user(
            username='participant',
            email='participant@example.com',
            password='participantpass',
            role='PARTICIPANT'
        )
        self.test_file = SimpleUploadedFile(
            "proposal.pdf", b"content", content_type="application/pdf"
        )
        self.proposal = Proposal.objects.create(
            participant=self.participant,
            title='Test Proposal',
            description='Test description',
            proposal_file=self.test_file,
            current_step=3
        )
        self.evaluator = Evaluator.objects.create(
            proposal=self.proposal,
            email='evaluator@example.com',
            name='Dr. Smith'
        )

    def test_evaluator_form_get(self):
        """Test getting evaluator form with valid token"""
        response = self.client.get(f'/external/evaluate/{self.evaluator.token}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_evaluator_form_expired(self):
        """Test evaluator form with expired token"""
        self.evaluator.expires_at = timezone.now() - timedelta(days=1)
        self.evaluator.save()
        response = self.client.get(f'/external/evaluate/{self.evaluator.token}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, 'expired')

    def test_evaluator_form_submit(self):
        """Test submitting evaluation"""
        response = self.client.post(
            f'/external/evaluate/{self.evaluator.token}/',
            {'marks': 85, 'comments': 'Good work'}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.evaluator.refresh_from_db()
        self.assertEqual(self.evaluator.marks, 85)
        self.assertEqual(self.evaluator.status, 'COMPLETED')

    def test_evaluator_form_invalid_marks(self):
        """Test submitting evaluation with invalid marks"""
        response = self.client.post(
            f'/external/evaluate/{self.evaluator.token}/',
            {'marks': 150, 'comments': 'Invalid'}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, 'between 0 and 100')

    def test_evaluator_form_already_completed(self):
        """Test accessing completed evaluation form"""
        self.evaluator.status = 'COMPLETED'
        self.evaluator.marks = 80
        self.evaluator.save()
        response = self.client.get(f'/external/evaluate/{self.evaluator.token}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, 'already submitted')


class ProposalTimelineTests(TestCase):
    """Tests for ProposalTimeline tracking"""

    def setUp(self):
        self.participant = User.objects.create_user(
            username='participant',
            password='participantpass',
            role='PARTICIPANT'
        )
        self.test_file = SimpleUploadedFile(
            "proposal.pdf", b"content", content_type="application/pdf"
        )
        self.proposal = Proposal.objects.create(
            participant=self.participant,
            title='Test Proposal',
            description='Test description',
            proposal_file=self.test_file
        )

    def test_timeline_creation(self):
        """Test creating timeline entry"""
        timeline = ProposalTimeline.objects.create(
            proposal=self.proposal,
            step_name='Submission',
            action='Proposal Submitted',
            actor=self.participant,
            details='Initial submission'
        )
        self.assertEqual(timeline.proposal, self.proposal)
        self.assertEqual(timeline.step_name, 'Submission')

    def test_timeline_with_external_actor(self):
        """Test timeline with external actor name"""
        timeline = ProposalTimeline.objects.create(
            proposal=self.proposal,
            step_name='Evaluation',
            action='Evaluation Submitted',
            actor_name='Dr. External Evaluator',
            details='Marks: 85/100'
        )
        self.assertIsNone(timeline.actor)
        self.assertEqual(timeline.actor_name, 'Dr. External Evaluator')


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PermissionTests(APITestCase):
    """Tests for permission enforcement"""

    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin',
            password='adminpass',
            role='ADMIN'
        )
        self.participant = User.objects.create_user(
            username='participant',
            password='participantpass',
            role='PARTICIPANT'
        )
        self.admin_token = Token.objects.create(user=self.admin)
        self.participant_token = Token.objects.create(user=self.participant)
        
        self.test_file = SimpleUploadedFile(
            "proposal.pdf", b"content", content_type="application/pdf"
        )
        self.proposal = Proposal.objects.create(
            participant=self.participant,
            title='Test Proposal',
            description='Test description',
            proposal_file=self.test_file
        )
        self.proposals_url = '/api/proposals/'

    def test_participant_cannot_format_check(self):
        """Test participant cannot perform format check"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.participant_token.key}')
        response = self.client.post(
            f'{self.proposals_url}{self.proposal.id}/format_check/',
            {'accepted': True},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_access_proposals(self):
        """Test unauthenticated user cannot access proposals"""
        response = self.client.get(self.proposals_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_participant_cannot_delete_proposal(self):
        """Test participant cannot delete proposal"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.participant_token.key}')
        response = self.client.delete(f'{self.proposals_url}{self.proposal.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
