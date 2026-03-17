import os
try:
    from pinecone import Pinecone, ServerlessSpec
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False
    print("Pinecone client not found. Semantic search will be disabled.")

from dotenv import load_dotenv

load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "recruit-ai")

pc = None
index = None

def get_pinecone_index():
    global pc, index
    if index:
        return index
    
    if not PINECONE_AVAILABLE or not PINECONE_API_KEY:
        return None
        
    try:
        if not pc:
            pc = Pinecone(api_key=PINECONE_API_KEY)
        
        # Create index if it doesn't exist
        # Note: This is still a blocking call if called for the first time
        # but now it only happens when a feature is actually used.
        if PINECONE_INDEX_NAME not in pc.list_indexes().names():
            pc.create_index(
                name=PINECONE_INDEX_NAME,
                dimension=768, # Dimension for gemini-embedding-2-preview
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1"
                )
            )
        
        index = pc.Index(PINECONE_INDEX_NAME)
        return index
    except Exception as e:
        print(f"Pinecone Initialization Error: {e}")
        return None

def upsert_candidate_vector(candidate_id: int, embedding: list, metadata: dict):
    idx = get_pinecone_index()
    if not idx:
        return False
    try:
        idx.upsert(
            vectors=[
                {
                    "id": str(candidate_id),
                    "values": embedding,
                    "metadata": metadata
                }
            ]
        )
        return True
    except Exception as e:
        print(f"Pinecone Upsert Error: {e}")
        return False

def query_candidates(embedding: list, top_k: int = 10):
    idx = get_pinecone_index()
    if not idx:
        return []
    try:
        results = idx.query(
            vector=embedding,
            top_k=top_k,
            include_metadata=True
        )
        return results.matches
    except Exception as e:
        print(f"Pinecone Query Error: {e}")
        return []
