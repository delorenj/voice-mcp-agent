"""
agent_core.py

Defines the FunctionAgent class, a LiveKit agent that uses MCP tools from one or more MCP servers. Handles LLM, STT, TTS, and VAD configuration, and customizes tool call behavior for voice interaction.
"""

import os
import logging
import asyncio
from livekit.agents.voice import Agent
from livekit.agents.llm import ChatChunk
from livekit.plugins import openai, silero, elevenlabs
from custom_whisper_stt import CustomWhisperSTT
from typing import Optional, Dict, Any

# Import bridge components - handle case where they're not available
try:
    from agent_bridge import handle_voice_result, get_client_count
    BRIDGE_AVAILABLE = True
except ImportError:
    BRIDGE_AVAILABLE = False
    logging.warning("Bridge components not available - bridge functionality disabled")

class FunctionAgent(Agent):
    """
    A LiveKit agent that uses MCP tools from one or more MCP servers.

    This agent is configured for voice interaction and integrates with MCP tools for task execution.
    It customizes the LLM, STT, TTS, and VAD components, and overrides the llm_node method to provide
    user feedback when a tool call is detected.
    """

    def __init__(self):
        # Load system prompt from file if present, else from env, else use a minimal default
        prompt_path = os.environ.get("AGENT_SYSTEM_PROMPT_FILE", "system_prompt.txt")
        if os.path.exists(prompt_path):
            with open(prompt_path, "r") as f:
                instructions = f.read()
        else:
            instructions = os.environ.get("AGENT_SYSTEM_PROMPT", "You are a helpful assistant communicating through voice. Use the available MCP tools to answer questions.")
        
        # Make LLM model and backend configurable via env var
        llm_model = os.environ.get("AGENT_LLM_MODEL", "gpt-4.1-mini")
        llm_backend = os.environ.get("AGENT_LLM_BACKEND", "openai")  # 'openai' or 'ollama'
        if llm_backend == "ollama":
            llm = openai.LLM.with_ollama(
                model=llm_model,
                base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
            )
        else:
            llm = openai.LLM(model=llm_model, timeout=60)
        
        # Configure STT - use custom Whisper for self-hosted STT
        stt_backend = os.environ.get("AGENT_STT_BACKEND", "whisper")  # "whisper" or "openai"
        
        if stt_backend == "whisper":
            stt_engine = CustomWhisperSTT(
                model_size=os.environ.get("WHISPER_MODEL", "base"),  # base, small, medium, large
                language="en",
                device="cpu",  # Change to "cuda" if GPU available
                compute_type="int8"  # int8 for CPU, float16 for GPU
            )
        else:
            stt_engine = openai.STT()
            
        super().__init__(
            instructions=instructions,
            stt=stt_engine,
            llm=llm,
            tts=elevenlabs.TTS(),
            vad=silero.VAD.load(),
            allow_interruptions=True
        )
        
        # Bridge integration settings
        self.bridge_enabled = BRIDGE_AVAILABLE and os.environ.get("BRIDGE_ENABLED", "true").lower() == "true"
        self.last_transcription = None
        
        if self.bridge_enabled:
            logging.info("Mac Bridge integration enabled")
        else:
            logging.info("Mac Bridge integration disabled")

    async def llm_node(self, chat_ctx, tools, model_settings):
        """Override the llm_node to say a message when a tool call is detected."""
        activity = self._activity
        tool_call_detected = False
        full_response = ""

        # Get the original response from the parent class
        async for chunk in super().llm_node(chat_ctx, tools, model_settings):
            # Check if this chunk contains a tool call
            if isinstance(chunk, ChatChunk) and chunk.delta and chunk.delta.tool_calls and not tool_call_detected:
                # Say the checking message only once when we detect the first tool call
                tool_call_detected = True
                activity.say("Sure, I'll check that for you.")
            
            # Collect response text for bridge
            if isinstance(chunk, ChatChunk) and chunk.delta and chunk.delta.content:
                full_response += chunk.delta.content

            yield chunk
        
        # Send final response to bridge if enabled
        if self.bridge_enabled and full_response and self.last_transcription:
            await self._send_to_bridge(self.last_transcription, full_response, tool_call_detected)

    async def _send_to_bridge(self, transcription: str, response: str, had_tool_calls: bool):
        """Send voice result to Mac bridge"""
        try:
            if not BRIDGE_AVAILABLE:
                return
            
            # Create structured agent response
            agent_response = {
                "action": "type" if not had_tool_calls else "execute",
                "content": response,
                "had_tool_calls": had_tool_calls,
                "params": {}
            }
            
            # Send to bridge
            await handle_voice_result(transcription, agent_response)
            
            logging.debug(f"Sent to bridge - transcription: '{transcription[:50]}...', "
                         f"response: '{response[:50]}...', tool_calls: {had_tool_calls}")
            
        except Exception as e:
            logging.error(f"Error sending to bridge: {e}")

    async def on_speech_final(self, event):
        """Handle final speech recognition result"""
        # Store transcription for bridge integration
        if hasattr(event, 'alternatives') and event.alternatives:
            self.last_transcription = event.alternatives[0].text
            
            # Send simple transcription to bridge if no agent processing needed
            if self.bridge_enabled and self.last_transcription:
                confidence = getattr(event.alternatives[0], 'confidence', None)
                
                # Only send simple transcription if we're not processing with agent
                if not self._should_process_with_agent(self.last_transcription):
                    await self._send_simple_transcription(self.last_transcription, confidence)
        
        # Call parent implementation
        if hasattr(super(), 'on_speech_final'):
            await super().on_speech_final(event)
    
    async def _send_simple_transcription(self, text: str, confidence: Optional[float] = None):
        """Send simple transcription without agent response"""
        try:
            if BRIDGE_AVAILABLE:
                await handle_voice_result(text, confidence=confidence)
                logging.debug(f"Sent simple transcription to bridge: '{text[:50]}...'")
        except Exception as e:
            logging.error(f"Error sending simple transcription to bridge: {e}")
    
    def _should_process_with_agent(self, text: str) -> bool:
        """Determine if text should be processed by agent or just transcribed"""
        # Simple heuristic - process with agent if it looks like a question or command
        question_words = ['what', 'how', 'why', 'when', 'where', 'who', 'can you', 'please', 'help']
        command_words = ['run', 'execute', 'open', 'close', 'find', 'search', 'create', 'delete']
        
        text_lower = text.lower()
        
        # Check for question marks or command patterns
        if '?' in text or any(word in text_lower for word in question_words + command_words):
            return True
            
        # Default to simple transcription for short phrases
        return len(text.split()) > 5
    
    def get_bridge_status(self) -> Dict[str, Any]:
        """Get bridge status information"""
        if not self.bridge_enabled:
            return {"enabled": False, "reason": "Bridge disabled or not available"}
        
        try:
            client_count = get_client_count() if BRIDGE_AVAILABLE else 0
            return {
                "enabled": True,
                "available": BRIDGE_AVAILABLE,
                "connected_clients": client_count
            }
        except Exception as e:
            return {"enabled": True, "available": False, "error": str(e)} 