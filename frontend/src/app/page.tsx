"use client"

import { useState, useRef, useEffect } from "react"
import './globals.css'

interface AudioData {
  id: string
  language: string
  audio_url: string
  text_content: string
}

const tabs = [
  { id: "text-to-speech", label: "TEXT TO SPEECH", icon: "🎤" },
  { id: "agents", label: "AGENTS", icon: "🤖" },
  { id: "music", label: "MUSIC", icon: "🎵" },
  { id: "speech-to-text", label: "SPEECH TO TEXT", icon: "📝" },
  { id: "dubbing", label: "DUBBING", icon: "🎬" },
  { id: "voice-cloning", label: "VOICE CLONING", icon: "👥" },
  { id: "elevenreader", label: "ELEVENREADER", icon: "📚" },
]

const voiceOptions = [
  { name: "Samora", description: "Narrate a story", color: "teal" },
  { name: "2 speakers", description: "Create a dialogue", color: "pink" },
  { name: "Announcer", description: "Voiceover a game", color: "teal" },
  { name: "Sergeant", description: "Play a drill sergeant", color: "purple" },
  { name: "Spuds", description: "Recount an old story", color: "teal" },
  { name: "Jessica", description: "Provide customer support", color: "pink" },
]

const languages = [
  { code: "english", name: "English", flag: "🇺🇸" },
  { code: "arabic", name: "Arabic", flag: "🇸🇦" },
]

// API Configuration
const API_BASE_URL = process.env.NODE_ENV === 'production' 
  ? 'https://elevenlabs-backend-9srp.onrender.com'  // Replace with your deployed backend URL
  : 'http://localhost:8000'

export default function Home() {
  const [activeTab, setActiveTab] = useState("text-to-speech")
  const [selectedLanguage, setSelectedLanguage] = useState("english")
  const [audioData, setAudioData] = useState<AudioData[]>([])
  const [currentAudio, setCurrentAudio] = useState<AudioData | null>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [textContent, setTextContent] = useState("")
  const [isSelectOpen, setIsSelectOpen] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const audioRef = useRef<HTMLAudioElement>(null)

  // Fetch audio data from API
  useEffect(() => {
    fetchAudioData()
  }, [])

  const fetchAudioData = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await fetch(`${API_BASE_URL}/api/audio`)
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      const data = await response.json()
      setAudioData(data)
      if (data.length > 0) {
        const englishAudio = data.find((audio: AudioData) => audio.language === 'english') || data[0]
        setCurrentAudio(englishAudio)
        setTextContent(englishAudio.text_content)
        setSelectedLanguage(englishAudio.language)
      }
    } catch (error) {
      console.error('Error fetching audio data:', error)
      setError('Failed to load audio data. Please check if the backend server is running.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleLanguageChange = async (language: string) => {
    setSelectedLanguage(language)
    setIsSelectOpen(false)
    setIsLoading(true)
    setError(null)
    
    // Stop current audio if playing
    if (isPlaying && audioRef.current) {
      audioRef.current.pause()
      setIsPlaying(false)
    }
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/audio/${language}`)
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      const data = await response.json()
      setCurrentAudio(data)
      setTextContent(data.text_content)
    } catch (error) {
      console.error('Error fetching audio for language:', error)
      setError(`Failed to load ${language} audio. Please try again.`)
    } finally {
      setIsLoading(false)
    }
  }

  const handlePlay = async () => {
    if (!currentAudio || !audioRef.current) {
      setError('No audio file available to play')
      return
    }

    setError(null)

    try {
      if (isPlaying) {
        audioRef.current.pause()
        setIsPlaying(false)
      } else {
        // Set the audio source
        audioRef.current.src = currentAudio.audio_url
        
        // Add error handling for audio loading
        audioRef.current.addEventListener('loadstart', () => {
          setIsLoading(true)
        })
        
        audioRef.current.addEventListener('canplay', () => {
          setIsLoading(false)
        })
        
        audioRef.current.addEventListener('error', (e) => {
          setIsLoading(false)
          setError('Failed to load audio file. The audio URL may be invalid.')
          console.error('Audio error:', e)
        })
        
        await audioRef.current.play()
        setIsPlaying(true)
      }
    } catch (error) {
      setIsPlaying(false)
      setIsLoading(false)
      setError('Failed to play audio. Please try again.')
      console.error('Play error:', error)
    }
  }

  const handleDownload = () => {
    if (!currentAudio) {
      setError('No audio file available to download')
      return
    }

    try {
      const link = document.createElement('a')
      link.href = currentAudio.audio_url
      link.download = `audio_${selectedLanguage}.wav`
      link.target = '_blank'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
    } catch (error) {
      setError('Failed to download audio file')
      console.error('Download error:', error)
    }
  }

  // Handle audio ended
  useEffect(() => {
    const audio = audioRef.current
    if (audio) {
      const handleEnded = () => setIsPlaying(false)
      const handleError = () => {
        setIsPlaying(false)
        setIsLoading(false)
        setError('Audio playback failed')
      }
      
      audio.addEventListener('ended', handleEnded)
      audio.addEventListener('error', handleError)
      
      return () => {
        audio.removeEventListener('ended', handleEnded)
        audio.removeEventListener('error', handleError)
      }
    }
  }, [])

  const selectedLangData = languages.find(lang => lang.code === selectedLanguage) || languages[0]

  return (
    <div className="main-container">
      {/* Header */}
      <header className="header">
        <div className="logo">11ElevenLabs</div>
        <nav className="nav">
          <div className="nav-item">
            <span>Creative Platform</span>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
              <path d="m6 9 6 6 6-6"/>
            </svg>
          </div>
          <div className="nav-item">
            <span>Agents Platform</span>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
              <path d="m6 9 6 6 6-6"/>
            </svg>
          </div>
          <div className="nav-item">
            <span>Developers</span>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
              <path d="m6 9 6 6 6-6"/>
            </svg>
          </div>
          <div className="nav-item">
            <span>Resources</span>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
              <path d="m6 9 6 6 6-6"/>
            </svg>
          </div>
          <span className="nav-item">Enterprise</span>
          <span className="nav-item">Pricing</span>
        </nav>
        <div className="header-buttons">
          <button className="btn btn-ghost">Log in</button>
          <button className="btn btn-primary">Sign up</button>
        </div>
      </header>

      {/* Hero Section */}
      <section className="hero">
        <h1>The most realistic voice AI platform</h1>
        <p>
          AI voice models and products powering millions of developers, creators, and enterprises. From
          low-latency conversational agents to the leading AI voice generator for voiceovers and audiobooks.
        </p>
        <div className="hero-buttons">
          <button className="btn btn-primary btn-lg">SIGN UP</button>
          <button className="btn btn-outline btn-lg">CONTACT SALES</button>
        </div>
      </section>

      {/* Tabs */}
      <div className="container">
        <div className="tabs-container">
          <div className="tabs">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`tab ${activeTab === tab.id ? 'active' : ''}`}
              >
                <span>{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="error-message">
            <div className="error-content">
              <span className="error-icon">⚠️</span>
              <span>{error}</span>
              <button onClick={() => setError(null)} className="error-close">×</button>
            </div>
          </div>
        )}

        {/* Text to Speech Content */}
        {activeTab === "text-to-speech" && (
          <div className={`tts-container fade-in ${isLoading ? 'loading' : ''}`}>
            <div className="tts-content">
              {/* Text Editor */}
              <div className="text-editor">
                <textarea
                  value={textContent}
                  onChange={(e) => setTextContent(e.target.value)}
                  placeholder="Enter your text here..."
                  aria-label="Text content for speech synthesis"
                  disabled={isLoading}
                />
                {isLoading && (
                  <div className="loading-overlay">
                    <div className="spinner"></div>
                  </div>
                )}
              </div>

              {/* Voice Options */}
              <div className="voice-options">
                {voiceOptions.map((voice, index) => (
                  <div key={index} className="voice-option">
                    <div className={`voice-color ${voice.color}`}></div>
                    <span className="voice-name">{voice.name}</span>
                    <span className="voice-description">{voice.description}</span>
                  </div>
                ))}
              </div>

              {/* Controls */}
              <div className="controls">
                <div className="select">
                  <div className="select-trigger"
                    onClick={() => !isLoading && setIsSelectOpen(!isSelectOpen)}
                    role="button"
                    tabIndex={0}
                    aria-expanded={isSelectOpen}
                    aria-haspopup="listbox"
                    aria-label="Select language"
                    onKeyDown={(e) => {
                      if (!isLoading && (e.key === 'Enter' || e.key === ' ')) {
                        e.preventDefault()
                        setIsSelectOpen(!isSelectOpen)
                      }
                    }}
                  >
                    <span className="flag">{selectedLangData.flag}</span>
                    <span>{selectedLangData.name}</span>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                      <path d="m6 9 6 6 6-6"/>
                    </svg>
                  </div>
                  <div className={`select-content ${isSelectOpen ? 'open' : ''}`} role="listbox">
                    {languages.map((language) => (
                      <button key={language.code}
                        className="select-item"
                        onClick={() => handleLanguageChange(language.code)}
                        role="option"
                        aria-selected={language.code === selectedLanguage}
                        title={`Select ${language.name}`}
                        aria-label={`Select ${language.name}`}
                        disabled={isLoading} 
                      >
                        <span className="flag">{language.flag}</span>
                        <span>{language.name}</span>
                      </button>
                    ))}
                  </div>
                </div>

                <div className="controls-right">
                  <button 
                    onClick={handlePlay} 
                    className="btn btn-primary btn-icon" 
                    aria-label={isPlaying ? "Pause audio" : "Play audio"}
                    disabled={isLoading || !currentAudio}
                  >
                    {isLoading ? (
                      <div className="btn-spinner"></div>
                    ) : (
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                        {isPlaying ? (
                          <>
                            <rect width="6" height="10" x="9" y="7"/>
                            <rect width="6" height="10" x="15" y="7"/>
                          </>
                        ) : (
                          <polygon points="6,3 20,12 6,21"/>
                        )}
                      </svg>
                    )}
                    {isLoading ? "LOADING..." : (isPlaying ? "PAUSE" : "PLAY")}
                  </button>
                  <button 
                    onClick={handleDownload} 
                    className="btn btn-outline btn-round" 
                    title="Download audio file" 
                    aria-label="Download audio file"
                    disabled={isLoading || !currentAudio}
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                      <polyline points="7,10 12,15 17,10"/>
                      <line x1="12" x2="12" y1="15" y2="3"/>
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Other Tab Contents (Empty) */}
        {activeTab !== "text-to-speech" && (
          <div className="empty-state fade-in">
            <h3>{tabs.find(tab => tab.id === activeTab)?.label}</h3>
            <p>This feature is coming soon.</p>
          </div>
        )}
      </div>

      {/* Bottom CTA */}
      <section className="bottom-cta">
        <div className="cta-card">
          <p>Powered by Eleven v3 (alpha)</p>
          <h2>EXPERIENCE THE FULL AUDIO AI PLATFORM</h2>
          <button className="btn btn-primary btn-lg">SIGN UP</button>
        </div>
      </section>

      {/* Hidden Audio Element */}
      <audio
        ref={audioRef}
        preload="metadata"
      />
    </div>
  )
}