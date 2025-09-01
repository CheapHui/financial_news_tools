from rest_framework import serializers

class DocInputSerializer(serializers.Serializer):
    id = serializers.CharField()
    text = serializers.CharField(required=False, allow_blank=True)
    embedding = serializers.ListField(
        child=serializers.FloatField(), required=False
    )

class QueryInputSerializer(serializers.Serializer):
    id = serializers.CharField()
    text = serializers.CharField()
    relevant_ids = serializers.ListField(
        child=serializers.CharField(), required=False
    )
    relevance_map = serializers.DictField(
        child=serializers.FloatField(), required=False
    )

class EvalRequestSerializer(serializers.Serializer):
    docs = DocInputSerializer(many=True)
    queries = QueryInputSerializer(many=True)
    ks = serializers.ListField(
        child=serializers.IntegerField(min_value=1), required=False
    )