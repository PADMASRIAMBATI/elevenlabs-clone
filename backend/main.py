from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv
import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = FastAPI(title="ElevenLabs Clone API", version="1.0.0")

# CORS configuration for production
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# MongoDB configuration
MONGODB_URL = os.getenv("MONGODB_URL")
DATABASE_NAME = os.getenv("DATABASE_NAME", "elevenlabs_clone")
COLLECTION_NAME = "audio_files"

# Global variables for database connection
client = None
database = None
collection = None
db_connected = False

async def connect_to_mongo():
    """Initialize MongoDB connection with production-ready configuration"""
    global client, database, collection, db_connected
    
    if not MONGODB_URL:
        logger.error("MONGODB_URL environment variable is not set")
        return False
    
    logger.info("Attempting to connect to MongoDB Atlas...")
    
    try:
        # Production-ready connection options
        connection_options = {
            'maxPoolSize': 50,
            'minPoolSize': 5,
            'maxIdleTimeMS': 30000,
            'connectTimeoutMS': 20000,
            'socketTimeoutMS': 20000,
            'serverSelectionTimeoutMS': 20000,
            'retryWrites': True,
            'w': 'majority',
            'readPreference': 'primary'
        }
        
        client = AsyncIOMotorClient(MONGODB_URL, **connection_options)
        
        # Test the connection
        await asyncio.wait_for(client.admin.command('ping'), timeout=30.0)
        logger.info("✅ Successfully connected to MongoDB Atlas!")
        
        database = client[DATABASE_NAME]
        collection = database[COLLECTION_NAME]
        db_connected = True
        
        # Create indexes for better performance
        await collection.create_index("language", unique=True)
        logger.info("Database indexes created/verified")
        
        return True
        
    except asyncio.TimeoutError:
        logger.error("❌ MongoDB connection timed out")
        db_connected = False
        return False
    except Exception as e:
        logger.error(f"❌ Failed to connect to MongoDB: {e}")
        db_connected = False
        return False

async def close_mongo_connection():
    """Close MongoDB connection"""
    global client, db_connected
    if client:
        client.close()
        logger.info("Disconnected from MongoDB")
        db_connected = False

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

# In-memory fallback storage
fallback_audio_data = {}

@app.on_event("startup")
async def startup_event():
    """Initialize database connection and sample data"""
    global collection, fallback_audio_data
    
    logger.info("🚀 Starting ElevenLabs Clone API...")
    
    # Initialize fallback data first
    for item in SAMPLE_AUDIO_DATA:
        fallback_audio_data[item['language']] = item
    
    # Try to connect to MongoDB
    connected = await connect_to_mongo()
    
    if connected:
        try:
            # Check if collection exists and has data
            count = await collection.count_documents({})
            if count == 0:
                # Insert sample data
                await collection.insert_many(SAMPLE_AUDIO_DATA)
                logger.info(f"✅ Sample audio data inserted into database")
            else:
                logger.info(f"✅ Database contains {count} audio files")
        except Exception as e:
            logger.error(f"❌ Error during startup data initialization: {e}")
            logger.info("🔄 Continuing with fallback mode...")
    else:
        logger.warning("⚠️  Running in fallback mode - using in-memory storage")

@app.on_event("shutdown")
async def shutdown_event():
    """Close database connections"""
    await close_mongo_connection()

@app.get("/")
async def root():
    return {
        "message": "ElevenLabs Clone API", 
        "version": "1.0.0",
        "database_connected": db_connected,
        "status": "healthy"
    }

@app.get("/api/audio", response_model=List[AudioFile])
async def get_all_audio():
    """Get all audio files"""
    
    if db_connected and collection:
        try:
            cursor = collection.find({}).sort("language", 1)
            audio_files = []
            async for document in cursor:
                audio_file = AudioFile(
                    id=document.get("id", str(document.get("_id"))),
                    language=document["language"],
                    audio_url=document["audio_url"],
                    text_content=document["text_content"]
                )
                audio_files.append(audio_file)
            return audio_files
        except Exception as e:
            logger.error(f"Database error, falling back to memory: {e}")
            # Fall through to fallback mode
    
    # Fallback to in-memory data
    audio_files = []
    for item in fallback_audio_data.values():
        audio_file = AudioFile(
            id=item["id"],
            language=item["language"],
            audio_url=item["audio_url"],
            text_content=item["text_content"]
        )
        audio_files.append(audio_file)
    
    return sorted(audio_files, key=lambda x: x.language)

@app.get("/api/audio/{language}", response_model=AudioFile)
async def get_audio_by_language(language: str):
    """Get audio file by language"""
    
    if db_connected and collection:
        try:
            document = await collection.find_one({"language": language})
            if document:
                return AudioFile(
                    id=document.get("id", str(document.get("_id"))),
                    language=document["language"],
                    audio_url=document["audio_url"],
                    text_content=document["text_content"]
                )
        except Exception as e:
            logger.error(f"Database error, checking fallback: {e}")
            # Fall through to fallback mode
    
    # Fallback to in-memory data
    if language in fallback_audio_data:
        item = fallback_audio_data[language]
        return AudioFile(
            id=item["id"],
            language=item["language"],
            audio_url=item["audio_url"],
            text_content=item["text_content"]
        )
    
    raise HTTPException(status_code=404, detail=f"Audio file not found for language: {language}")

@app.post("/api/audio", response_model=AudioFile)
async def create_audio_file(audio_file: AudioFileCreate):
    """Create a new audio file entry"""
    
    if db_connected and collection:
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
            
            await collection.insert_one(document)
            
            return AudioFile(
                id=document["id"],
                language=document["language"],
                audio_url=document["audio_url"],
                text_content=document["text_content"]
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Database error, using fallback: {e}")
            # Fall through to fallback mode
    
    # Fallback to in-memory storage
    if audio_file.language in fallback_audio_data:
        raise HTTPException(status_code=400, detail=f"Audio file for language '{audio_file.language}' already exists")
    
    document = {
        "id": f"{audio_file.language}_audio",
        "language": audio_file.language,
        "audio_url": audio_file.audio_url,
        "text_content": audio_file.text_content
    }
    
    fallback_audio_data[audio_file.language] = document
    
    return AudioFile(
        id=document["id"],
        language=document["language"],
        audio_url=document["audio_url"],
        text_content=document["text_content"]
    )

@app.put("/api/audio/{language}", response_model=AudioFile)
async def update_audio_file(language: str, audio_file: AudioFileCreate):
    """Update an existing audio file"""
    
    if db_connected and collection:
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
            logger.error(f"Database error, using fallback: {e}")
            # Fall through to fallback mode
    
    # Fallback to in-memory storage
    if language not in fallback_audio_data:
        raise HTTPException(status_code=404, detail=f"Audio file not found for language: {language}")
    
    fallback_audio_data[language].update({
        "audio_url": audio_file.audio_url,
        "text_content": audio_file.text_content
    })
    
    item = fallback_audio_data[language]
    return AudioFile(
        id=item["id"],
        language=item["language"],
        audio_url=item["audio_url"],
        text_content=item["text_content"]
    )

@app.delete("/api/audio/{language}")
async def delete_audio_file(language: str):
    """Delete an audio file by language"""
    
    if db_connected and collection:
        try:
            result = await collection.delete_one({"language": language})
            if result.deleted_count == 0:
                raise HTTPException(status_code=404, detail=f"Audio file not found for language: {language}")
            
            return {"message": f"Audio file for language '{language}' deleted successfully"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Database error, using fallback: {e}")
            # Fall through to fallback mode
    
    # Fallback to in-memory storage
    if language not in fallback_audio_data:
        raise HTTPException(status_code=404, detail=f"Audio file not found for language: {language}")
    
    del fallback_audio_data[language]
    return {"message": f"Audio file for language '{language}' deleted successfully"}

@app.get("/health")
async def health_check():
    """Health check endpoint for deployment monitoring"""
    db_status = "connected" if db_connected else "fallback_mode"
    
    # Test database if connected
    if db_connected and client:
        try:
            await client.admin.command("ping")
            db_status = "connected"
        except Exception as e:
            db_status = "error"
            logger.error(f"Health check failed: {e}")
    
    return {
        "status": "healthy",
        "database": db_status,
        "version": "1.0.0",
        "timestamp": "2025-09-13"
    }

# Root path for deployment
@app.get("/api")
async def api_root():
    """API root endpoint"""
    return {
        "message": "ElevenLabs Clone API",
        "version": "1.0.0",
        "endpoints": {
            "audio": "/api/audio",
            "health": "/health"
        }
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=port, 
        reload=False,  # Disable reload in production
        log_level="info"
    )