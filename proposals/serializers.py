from rest_framework import serializers
from .models import Proposal, ProposalTimeline, Notice, Evaluator, CommitteeReview, RectorReview
from users.serializers import UserSerializer


class NoticeSerializer(serializers.ModelSerializer):
    created_by_name = serializers.ReadOnlyField(source='created_by.username')
    proposal_count = serializers.SerializerMethodField()
    is_active = serializers.ReadOnlyField()

    class Meta:
        model = Notice
        fields = '__all__'
        read_only_fields = ('created_by', 'created_at', 'updated_at')

    def get_proposal_count(self, obj):
        return obj.proposals.count()


class ProposalTimelineSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = ProposalTimeline
        fields = '__all__'

    def get_actor_name(self, obj):
        if obj.actor:
            return obj.actor.username
        return obj.actor_name or 'System'


class EvaluatorSerializer(serializers.ModelSerializer):
    is_expired = serializers.ReadOnlyField()

    class Meta:
        model = Evaluator
        fields = ['id', 'proposal', 'email', 'name', 'marks', 'comments', 
                  'status', 'invited_at', 'completed_at', 'expires_at', 'is_expired']
        read_only_fields = ('token', 'invited_at', 'completed_at', 'status')


class EvaluatorAnonymousSerializer(serializers.ModelSerializer):
    """Serializer for participant view - hides evaluator identity"""
    class Meta:
        model = Evaluator
        fields = ['id', 'marks', 'comments', 'status', 'completed_at']


class EvaluatorDetailSerializer(serializers.ModelSerializer):
    """Serializer for external evaluator form (includes proposal details)"""
    proposal_title = serializers.ReadOnlyField(source='proposal.title')
    proposal_description = serializers.ReadOnlyField(source='proposal.description')
    proposal_file_url = serializers.SerializerMethodField()
    participant_name = serializers.SerializerMethodField()

    class Meta:
        model = Evaluator
        fields = ['id', 'name', 'email', 'proposal_title', 'proposal_description',
                  'proposal_file_url', 'participant_name', 'marks', 'comments',
                  'status', 'expires_at']

    def get_proposal_file_url(self, obj):
        if obj.proposal.proposal_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.proposal.proposal_file.url)
            return obj.proposal.proposal_file.url
        return None

    def get_participant_name(self, obj):
        participant = obj.proposal.participant
        return participant.get_full_name() or participant.username


class CommitteeReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommitteeReview
        fields = ['id', 'proposal', 'email', 'name', 'decision', 'comments',
                  'status', 'invited_at', 'completed_at', 'expires_at']
        read_only_fields = ('token', 'invited_at', 'completed_at', 'status')


class CommitteeReviewDetailSerializer(serializers.ModelSerializer):
    """Serializer for external committee form (includes proposal and budget details)"""
    proposal_title = serializers.ReadOnlyField(source='proposal.title')
    proposal_description = serializers.ReadOnlyField(source='proposal.description')
    proposal_file_url = serializers.SerializerMethodField()
    budget_file_url = serializers.SerializerMethodField()
    revised_file_url = serializers.SerializerMethodField()
    participant_name = serializers.SerializerMethodField()
    evaluator_average = serializers.SerializerMethodField()

    class Meta:
        model = CommitteeReview
        fields = ['id', 'name', 'email', 'proposal_title', 'proposal_description',
                  'proposal_file_url', 'budget_file_url', 'revised_file_url',
                  'participant_name', 'evaluator_average', 'decision', 'comments',
                  'status', 'expires_at']

    def get_proposal_file_url(self, obj):
        if obj.proposal.proposal_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.proposal.proposal_file.url)
            return obj.proposal.proposal_file.url
        return None

    def get_budget_file_url(self, obj):
        if obj.proposal.budget_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.proposal.budget_file.url)
            return obj.proposal.budget_file.url
        return None

    def get_revised_file_url(self, obj):
        if obj.proposal.revised_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.proposal.revised_file.url)
            return obj.proposal.revised_file.url
        return None

    def get_participant_name(self, obj):
        participant = obj.proposal.participant
        return participant.get_full_name() or participant.username

    def get_evaluator_average(self, obj):
        return obj.proposal.get_evaluator_average()


class RectorReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = RectorReview
        fields = ['id', 'proposal', 'email', 'name', 'decision', 'comments',
                  'status', 'invited_at', 'completed_at', 'expires_at']
        read_only_fields = ('token', 'invited_at', 'completed_at', 'status')


class RectorReviewDetailSerializer(serializers.ModelSerializer):
    """Serializer for external rector form"""
    proposal_title = serializers.ReadOnlyField(source='proposal.title')
    proposal_description = serializers.ReadOnlyField(source='proposal.description')
    proposal_file_url = serializers.SerializerMethodField()
    budget_file_url = serializers.SerializerMethodField()
    revised_file_url = serializers.SerializerMethodField()
    participant_name = serializers.SerializerMethodField()
    evaluator_average = serializers.SerializerMethodField()
    committee_decisions = serializers.SerializerMethodField()

    class Meta:
        model = RectorReview
        fields = ['id', 'name', 'email', 'proposal_title', 'proposal_description',
                  'proposal_file_url', 'budget_file_url', 'revised_file_url',
                  'participant_name', 'evaluator_average', 'committee_decisions',
                  'decision', 'comments', 'status', 'expires_at']

    def get_proposal_file_url(self, obj):
        if obj.proposal.proposal_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.proposal.proposal_file.url)
            return obj.proposal.proposal_file.url
        return None

    def get_budget_file_url(self, obj):
        if obj.proposal.budget_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.proposal.budget_file.url)
            return obj.proposal.budget_file.url
        return None

    def get_revised_file_url(self, obj):
        if obj.proposal.revised_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.proposal.revised_file.url)
            return obj.proposal.revised_file.url
        return None

    def get_participant_name(self, obj):
        participant = obj.proposal.participant
        return participant.get_full_name() or participant.username

    def get_evaluator_average(self, obj):
        return obj.proposal.get_evaluator_average()

    def get_committee_decisions(self, obj):
        reviews = obj.proposal.committee_reviews.filter(status='COMPLETED')
        return [{'name': r.name, 'decision': r.decision} for r in reviews]


class ProposalSerializer(serializers.ModelSerializer):
    participant_name = serializers.ReadOnlyField(source='participant.username')
    notice_title = serializers.ReadOnlyField(source='notice.title')
    timeline = ProposalTimelineSerializer(many=True, read_only=True)
    evaluations = EvaluatorSerializer(many=True, read_only=True)
    committee_reviews = CommitteeReviewSerializer(many=True, read_only=True)
    evaluator_average = serializers.SerializerMethodField()
    step_display = serializers.SerializerMethodField()

    class Meta:
        model = Proposal
        fields = '__all__'
        read_only_fields = ('participant', 'status', 'current_step', 'created_at', 'updated_at',
                            'plagiarism_percentage', 'rejection_reason')

    def get_evaluator_average(self, obj):
        return obj.get_evaluator_average()

    def get_step_display(self, obj):
        return dict(obj.STEP_CHOICES).get(obj.current_step, 'Unknown')

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['participant'] = request.user
        return super().create(validated_data)


class ProposalListSerializer(serializers.ModelSerializer):
    """Lighter serializer for listing proposals - includes evaluations for admin dashboard"""
    participant_name = serializers.ReadOnlyField(source='participant.username')
    notice_title = serializers.ReadOnlyField(source='notice.title')
    step_display = serializers.SerializerMethodField()
    evaluations = EvaluatorSerializer(many=True, read_only=True)
    committee_reviews = CommitteeReviewSerializer(many=True, read_only=True)
    evaluator_average = serializers.SerializerMethodField()

    class Meta:
        model = Proposal
        fields = ['id', 'title', 'participant_name', 'notice_title', 'status', 
                  'current_step', 'step_display', 'created_at', 'updated_at',
                  'evaluations', 'committee_reviews', 'evaluator_average',
                  'proposal_file', 'budget_file', 'revised_file', 'plagiarism_percentage']

    def get_step_display(self, obj):
        return dict(obj.STEP_CHOICES).get(obj.current_step, 'Unknown')

    def get_evaluator_average(self, obj):
        return obj.get_evaluator_average()


class ParticipantProposalSerializer(serializers.ModelSerializer):
    """Serializer for participant view - hides evaluator identities"""
    notice_title = serializers.ReadOnlyField(source='notice.title')
    timeline = ProposalTimelineSerializer(many=True, read_only=True)
    evaluations = EvaluatorAnonymousSerializer(many=True, read_only=True)
    evaluator_average = serializers.SerializerMethodField()
    step_display = serializers.SerializerMethodField()

    class Meta:
        model = Proposal
        fields = ['id', 'title', 'description', 'notice', 'notice_title', 'status',
                  'current_step', 'step_display', 'proposal_file', 'timeline',
                  'evaluations', 'evaluator_average', 'created_at', 'updated_at']
        read_only_fields = ('status', 'current_step', 'created_at', 'updated_at')

    def get_evaluator_average(self, obj):
        return obj.get_evaluator_average()

    def get_step_display(self, obj):
        return dict(obj.STEP_CHOICES).get(obj.current_step, 'Unknown')

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['participant'] = request.user
        return super().create(validated_data)

