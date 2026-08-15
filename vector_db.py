from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct

class QdrantStorage: 
    def __init__(self, url="http://localhost:6333", collection="docs", dim=3072):
        self.client = QdrantClient(url=url, timeout=30)
        self.collection = collection
        if not self.client.collection_exists(self.collection):
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )
    def upsert(self, id: str, vector: list[float], payload: dict):
        points = [
            PointStruct(id=id, vector=vector, payload=payload[i]) 
            for i in range(len(id))
            ]
        self.client.upsert(self.collection, points=points)

    def search(self, query_vector, top_K: int = 5):
        result = self.client.query_points(
            collection_name=self.collection,
            query=query_vector,
            with_payload=True,
            limit=top_K,
        ).points
    
        contexts = []
        sources = set()
    
        for r in result:
            payload = getattr(r, "payload", None) or {}
            text = payload.get("text", "")
            source = payload.get("source", "")
            if text:
                contexts.append(text)
                sources.add(source)
    
        return {"contexts": contexts, "sources": list(sources)}
        
