from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse
from .serializers import EvalRequestSerializer
from .services import evaluate_embeddings
# from app.ai.llm_client import embed_texts  # 用你實際的 embeddings
embed_texts = None  # 如果你已有實作，改成實際函數

class EmbeddingEvalView(APIView):
    """
    POST /api/evals/embedding
    payload:
    {
      "docs": [{"id":"d1","text":"..."}, {"id":"d2","embedding":[...]}],
      "queries": [
        {"id":"q1","text":"...","relevant_ids":["d1","d3"]},
        {"id":"q2","text":"...","relevance_map":{"d2":2,"d5":1}}
      ],
      "ks": [1,3,5,10]
    }
    """
    def post(self, request):
        serializer = EvalRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        result = evaluate_embeddings(
            docs=data["docs"],
            queries=data["queries"],
            ks=data.get("ks", (1,3,5,10)),
            embed_texts=embed_texts
        )
        return Response(result, status=status.HTTP_200_OK)

class EmbeddingQualityView(APIView):
    """
    GET /api/evals/quality
    返回當前系統的 embedding 質量指標概覽
    """
    def get(self, request):
        # 這裡可以從數據庫獲取最近的評估結果
        # 暫時返回示例數據
        sample_data = {
            "last_evaluation": "2025-01-27T10:30:00Z",
            "overall_quality": {
                "grade": "Good",
                "color": "blue",
                "score": 0.72
            },
            "metrics": {
                "recall_at_1": 0.65,
                "recall_at_3": 0.78,
                "recall_at_5": 0.85,
                "recall_at_10": 0.92,
                "ndcg_at_1": 0.65,
                "ndcg_at_3": 0.71,
                "ndcg_at_5": 0.75,
                "ndcg_at_10": 0.78
            },
            "stats": {
                "total_docs": 1250,
                "total_queries": 150,
                "avg_first_relevant_rank": 2.3,
                "evaluation_count": 5
            }
        }
        return JsonResponse(sample_data)

class QuickEvalView(APIView):
    """
    POST /api/evals/quick
    快速評估接口 - 用於實時顯示評估結果
    payload: {
        "query_text": "string",
        "doc_texts": ["string1", "string2", ...],
        "relevant_doc_indices": [0, 2]  // 哪些文檔是相關的
    }
    """
    def post(self, request):
        query_text = request.data.get('query_text', '')
        doc_texts = request.data.get('doc_texts', [])
        relevant_indices = request.data.get('relevant_doc_indices', [])
        
        if not query_text or not doc_texts:
            return Response({
                'error': 'query_text and doc_texts are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 構造評估數據格式
        docs = [
            {"id": f"doc_{i}", "text": text} 
            for i, text in enumerate(doc_texts)
        ]
        
        relevant_ids = [f"doc_{i}" for i in relevant_indices]
        queries = [{
            "id": "query_1",
            "text": query_text,
            "relevant_ids": relevant_ids
        }]
        
        try:
            result = evaluate_embeddings(
                docs=docs,
                queries=queries,
                ks=[1, 3, 5, 10],
                embed_texts=embed_texts
            )
            
            # 簡化結果以便前端顯示
            simplified_result = {
                "quality_metrics": result.get('quality_metrics', {}),
                "summary": result.get('summary', {}),
                "query_result": result.get('per_query', [{}])[0] if result.get('per_query') else {},
                "timestamp": result.get('quality_metrics', {}).get('evaluation_timestamp')
            }
            
            return Response(simplified_result, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)