import logging
import os
import datetime

from fastapi import FastAPI
from dotenv import load_dotenv
import inngest
import inngest.fast_api

from data_loader import load_and_chunk_pdf, embed_texts
from vector_db import QdrantStorage
from custom_types import RAGChunkAndSrc, RAGUpsertResult, RAGSearchResult, RAGQueryResult


load_dotenv()

inngest_client = inngest.Inngest(
    app_id="rag_app",
    logger=logging.getLogger("uvicorn"),
    is_production=False,
    serializer=inngest.PydanticSerializer(),
)


@inngest_client.create_function(
    fn_id="RAG: Ingest PDF",
    trigger=inngest.TriggerEvent(event="rag/ingest_pdf"),
)
async def rag_ingest_pdf(ctx: inngest.Context):
    # Fonction interne 1 : charger + découper le PDF
    def _load(ctx: inngest.Context) -> RAGChunkAndSrc:
        pdf_path = ctx.event.data["pdf_path"]
        source_id = ctx.event.data.get("source_id", pdf_path)
        chunks = load_and_chunk_pdf(pdf_path)
        return RAGChunkAndSrc(chunk=chunks, source_id=source_id)


    # Fonction interne 2 : embedder + upsert dans Qdrant
    def _upsert(ctx: inngest.Context, data: RAGChunkAndSrc) -> RAGUpsertResult:
        chunks = data.chunk
        source_id = data.source_id
        vecs = embed_texts(chunks)
        ids = [f"{source_id}:{i}" for i in range(len(chunks))]
        payloads = [{"source_id": source_id, "text": chunks[i]} for i in range(len(chunks))]
        QdrantStorage().upsert(ids, vecs, payloads)
        return RAGUpsertResult(ingested=len(chunks))

    # Step 1 : charger et chunker le PDF
    chunks_and_src = await ctx.step.run(
        "load-and-chunk",
        lambda: _load(ctx),
        output_type=RAGChunkAndSrc,
    )


    # Step 2 : embedder les chunks + stocker dans Qdrant
    ingested = await ctx.step.run(
        "embed-and-upsert",
        lambda: _upsert(ctx, chunks_and_src),
        output_type=RAGUpsertResult,
    )

    return ingested.model_dump()


app = FastAPI()
inngest.fast_api.serve(app, inngest_client, [rag_ingest_pdf])