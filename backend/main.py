from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="ElevenLabs Clone API", version="1.0.0")

# CORS configuration
# In main.py, update CORS to allow all origins during development:
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB configuration
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = "elevenlabs_clone"
COLLECTION_NAME = "audio_files"

# MongoDB client
client = AsyncIOMotorClient(MONGODB_URL)
database = client[DATABASE_NAME]
collection = database[COLLECTION_NAME]

# Pydantic models
class AudioFile(BaseModel):
    id: str
    language: str
    audio_url: str
    text_content: str

class AudioFileCreate(BaseModel):
    language: str
    audio_url: str
    text_content: str

# Sample data for initial setup
SAMPLE_AUDIO_DATA = [
    {
        "id": "english_audio",
        "language": "english",
        "audio_url": "https://www.soundjay.com/misc/sounds/bell-ringing-05.wav",
        "text_content": "In the ancient land of Eldoria, where skies shimmered and forests, whispered secrets to the wind, lived a dragon named Zephyros. [sarcastically] Not the \"burn it all down\" kind... [giggles] but he was gentle, wise, with eyes like old stars. [whispers] Even the birds fell silent when he passed."
    },
    {
        "id": "arabic_audio", 
        "language": "arabic",
        "audio_url": "https://www.soundjay.com/misc/sounds/bell-ringing-04.wav",
        "text_content": "في أرض إلدوريا القديمة، حيث تتألق السماء وتهمس الغابات بأسرارها للريح، عاش تنين يُدعى زيفيروس. ليس من النوع الذي يحرق كل شيء... بل كان لطيفاً وحكيماً، بعيون مثل النجوم القديمة. حتى الطيور كانت تصمت عندما يمر."
    }
]

@app.on_event("startup")
async def startup_event():
    # Comment out MongoDB connection for now
    print("API started successfully")
    
# Use in-memory storage for development:
audio_storage = SAMPLE_AUDIO_DATA.copy()

@app.get("/api/audio")
async def get_all_audio():
    return [AudioFile(**item) for item in audio_storage]

@app.get("/api/audio", response_model=List[AudioFile])
async def get_all_audio():
    """Get all audio files"""
    try:
        cursor = collection.find({})
        audio_files = []
        async for document in cursor:
            # Convert MongoDB ObjectId to string and use custom id field
            audio_file = AudioFile(
                id=document.get("id", str(document.get("_id"))),
                language=document["language"],
                audio_url=document["audio_url"],
                text_content=document["text_content"]
            )
            audio_files.append(audio_file)
        return audio_files
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching audio files: {str(e)}")

@app.get("/api/audio/{language}", response_model=AudioFile)
async def get_audio_by_language(language: str):
    """Get audio file by language"""
    try:
        document = await collection.find_one({"language": language})
        if not document:
            raise HTTPException(status_code=404, detail=f"Audio file not found for language: {language}")
        
        return AudioFile(
            id=document.get("id", str(document.get("_id"))),
            language=document["language"],
            audio_url=document["audio_url"],
            text_content=document["text_content"]
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching audio file: {str(e)}")

@app.post("/api/audio", response_model=AudioFile)
async def create_audio_file(audio_file: AudioFileCreate):
    """Create a new audio file entry"""
    try:
        # Check if audio file for this language already exists
        existing = await collection.find_one({"language": audio_file.language})
        if existing:
            raise HTTPException(status_code=400, detail=f"Audio file for language '{audio_file.language}' already exists")
        
        # Create new document
        document = {
            "id": f"{audio_file.language}_audio",
            "language": audio_file.language,
            "audio_url": audio_file.audio_url,
            "text_content": audio_file.text_content
        }
        
        result = await collection.insert_one(document)
        
        # Return the created document
        return AudioFile(
            id=document["id"],
            language=document["language"],
            audio_url=document["audio_url"],
            text_content=document["text_content"]
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating audio file: {str(e)}")

@app.put("/api/audio/{language}", response_model=AudioFile)
async def update_audio_file(language: str, audio_file: AudioFileCreate):
    """Update an existing audio file"""
    try:
        update_data = {
            "audio_url": audio_file.audio_url,
            "text_content": audio_file.text_content
        }
        
        result = await collection.update_one(
            {"language": language},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail=f"Audio file not found for language: {language}")
        
        # Return updated document
        updated_document = await collection.find_one({"language": language})
        return AudioFile(
            id=updated_document.get("id", str(updated_document.get("_id"))),
            language=updated_document["language"],
            audio_url=updated_document["audio_url"],
            text_content=updated_document["text_content"]
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating audio file: {str(e)}")

@app.delete("/api/audio/{language}")
async def delete_audio_file(language: str):
    """Delete an audio file by language"""
    try:
        result = await collection.delete_one({"language": language})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail=f"Audio file not found for language: {language}")
        
        return {"message": f"Audio file for language '{language}' deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting audio file: {str(e)}")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        await database.command("ping")
        return {
            "status": "healthy",
            "database": "connected",
            "message": "API is running successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unavailable: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    )