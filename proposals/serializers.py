from rest_framework import serializers
from .models import Proposal, ProposalTimeline
from users.serializers import UserSerializer

class ProposalTimelineSerializer(serializers.ModelSerializer):
    actor_name = serializers.ReadOnlyField(source='actor.username')

    class Meta:
        model = ProposalTimeline
        fields = '__all__'

class ProposalSerializer(serializers.ModelSerializer):
    participant_name = serializers.ReadOnlyField(source='participant.username')
    timeline = ProposalTimelineSerializer(many=True, read_only=True)

    class Meta:
        model = Proposal
        fields = '__all__'
        read_only_fields = ('participant', 'status', 'current_step', 'created_at', 'updated_at', 
                            'plagiarism_percentage', 'evaluator_1_marks', 'evaluator_2_marks')

    def create(self, validated_data):
        # Assign current user as participant
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['participant'] = request.user
        return super().create(validated_data)
