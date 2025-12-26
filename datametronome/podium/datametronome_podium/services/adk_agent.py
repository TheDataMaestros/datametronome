"""
ADK Agent Service for DataMetronome.

This service integrates with Google's Agent Development Kit (ADK) to provide
an AI assistant that can query and interact with the DataMetronome API.
Supports both Ollama (via LiteLLM) and Gemini models.
"""

import json
import logging
import uuid

from datametronome_podium.core.config import settings

logger = logging.getLogger(__name__)

# HTTP client timeout settings (in seconds)
HTTP_TIMEOUT = 180.0  # 3 minutes for agent operations
HTTP_TIMEOUT_SHORT = 180.0  # Same for tool calls

# Try to import Google ADK - if not available, fall back to HTTP-based approach
try:
    from google.adk import Agent
    from google.adk.models.lite_llm import LiteLlm

    # Try to import context/input classes if available
    try:
        from google.adk import InvocationContext  # type: ignore[attr-defined]

        INVOCATION_CONTEXT_AVAILABLE = True
    except ImportError:
        INVOCATION_CONTEXT_AVAILABLE = False
    ADK_AVAILABLE = True
except ImportError:
    ADK_AVAILABLE = False
    INVOCATION_CONTEXT_AVAILABLE = False
    logger.warning(
        "Google ADK not available. Install with: pip install google-adk. "
        "Falling back to HTTP-based agent."
    )


class ADKAgent:
    """ADK Agent that can query DataMetronome API."""

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        api_url: str | None = None,
    ):
        """Initialize the ADK agent.

        Args:
            model: Model identifier (e.g., 'ollama_chat/qwen2.5' for Ollama)
            api_key: API key (not needed for Ollama, required for Gemini)
            api_url: API endpoint URL (not used for Ollama)
        """
        self.model_name = model or settings.adk_model
        self.api_key = api_key or settings.adk_api_key
        self.api_url = api_url or settings.adk_api_url

        # Use internal API URL - use the same port as the running server
        import os

        # Get port from settings or environment (PODIUM_PORT is used in start script)
        # Check both DATAMETRONOME_PORT and PODIUM_PORT environment variables
        api_port = (
            os.getenv("DATAMETRONOME_PORT")
            or os.getenv("PODIUM_PORT")
            or str(settings.port)
        )
        api_port = int(api_port)  # Ensure it's an integer

        self.api_base_url = os.getenv(
            "DATAMETRONOME_INTERNAL_API_URL", f"http://127.0.0.1:{api_port}/api/v1"
        )
        logger.info(
            f"🔗 ADK Agent API base URL: {self.api_base_url} (using port {api_port})"
        )

        # Initialize ADK agent if available
        self.agent = None
        if ADK_AVAILABLE:
            try:
                # Create LiteLLM model for Ollama
                if self.model_name.startswith("ollama_chat/"):
                    model_obj = LiteLlm(model=self.model_name)
                else:
                    # For Gemini, use the model string directly
                    model_obj = LiteLlm(model=self.model_name)

                # Create the root agent with tools
                # ADK Agent accepts 'instruction' (singular) for system instructions
                self.agent = Agent(
                    model=model_obj,
                    name="datametronome_assistant",
                    description="AI assistant for DataMetronome data quality platform. "
                    "Helps users understand their data quality status, configure checks, "
                    "and troubleshoot issues.",
                    instruction=self._get_system_instructions(),
                    tools=self._get_adk_tools(),
                )
                logger.info(f"✅ ADK Agent initialized with model: {self.model_name}")
                # Log available methods for debugging
                available_methods = [
                    m
                    for m in dir(self.agent)
                    if not m.startswith("_") and callable(getattr(self.agent, m, None))
                ]
                logger.debug(f"ADK Agent available methods: {available_methods}")
            except Exception as e:
                logger.error(f"Failed to initialize ADK agent: {e}", exc_info=True)
                self.agent = None

    def _get_system_instructions(self) -> str:
        """Get system instructions for the agent."""
        return """You are a helpful AI assistant for DataMetronome, a data quality monitoring platform.

DataMetronome is a data quality monitoring platform that helps organizations monitor and ensure the quality of their data.

Your role is to help users understand their data quality status, configure checks, and troubleshoot issues.

Key concepts in DataMetronome:
- Staves: Data sources (databases, data warehouses, etc.) - these are the data sources being monitored
- Clefs: Data quality checks/rules - these define what quality checks to perform on the data
- Checks: Execution results of clefs - these are the actual results from running quality checks

Available tools:
- list_staves: List all data sources (staves) in the system
- get_stave: Get details about a specific data source
- list_stave_tables: List all tables in a specific data source, optionally with their structure/schema
- list_clefs: List all data quality checks (clefs)
- get_clef: Get details about a specific quality check
- list_checks: List check execution results
- get_summary_report: Get a summary report of system status
- get_quality_report: Get a detailed quality report

When users ask questions about DataMetronome, their data sources, tables, checks, or quality status, use the available tools to query the DataMetronome API and provide helpful, accurate answers.

If a user asks about tables in a datasource, use the list_stave_tables tool with the stave_id to show them what tables are available.

Always remember: DataMetronome is the platform you're helping with. It's a real data quality monitoring system, not a hypothetical concept.

Be concise but informative. If a user asks about their data sources, tables, checks, or quality status, use the appropriate tools to get current information."""

    def _get_adk_tools(self):  # type: ignore[return-type]
        """Get ADK tool definitions.

        Returns:
            List of ADK tool definitions
        """
        # ADK tools are defined as functions that the agent can call
        # We'll define them as async functions that the agent can invoke
        return [
            self.list_staves,
            self.get_stave,
            self.list_stave_tables,  # Add table listing tool
            self.list_clefs,
            self.get_clef,
            self.list_checks,
            self.get_summary_report,
            self.get_quality_report,
        ]

    async def list_staves(self, limit: int = 100, skip: int = 0) -> dict[str, object]:
        """List all data sources (staves) in DataMetronome."""
        import httpx

        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SHORT) as client:
            response = await client.get(
                f"{self.api_base_url}/staves/",
                params={"limit": limit, "skip": skip},
            )
            return response.json()

    async def get_stave(self, stave_id: str) -> dict[str, object]:
        """Get details about a specific data source (stave) by ID."""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SHORT) as client:
                response = await client.get(f"{self.api_base_url}/staves/{stave_id}")
                response.raise_for_status()
                return response.json()
        except httpx.ConnectError as e:
            logger.error(f"Failed to connect to API at {self.api_base_url}: {e}")
            return {"error": f"Could not connect to DataMetronome API: {e}"}
        except httpx.HTTPStatusError as e:
            logger.error(f"API error: {e.response.status_code} - {e.response.text}")
            return {"error": f"API error: {e.response.status_code}"}
        except Exception as e:
            logger.error(f"Unexpected error calling API: {e}")
            return {"error": f"Unexpected error: {str(e)}"}

    async def list_stave_tables(
        self, stave_id: str, include_structure: bool = True
    ) -> dict[str, object]:
        """List all tables in a specific data source (stave) by ID.

        This tool allows you to see what tables are available in a datasource,
        and optionally get their structure (columns, data types, etc.).

        Args:
            stave_id: The ID of the stave (data source) to query
            include_structure: Whether to include table structure/schema information (default: True)

        Returns:
            Dictionary with tables list, count, and stave information
        """
        import httpx

        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SHORT) as client:
                response = await client.get(
                    f"{self.api_base_url}/stave-actions/{stave_id}/tables",
                    params={"include_structure": include_structure},
                )
                response.raise_for_status()
                return response.json()
        except httpx.ConnectError as e:
            logger.error(f"Error calling list_stave_tables tool: {e}", exc_info=True)
            return {"error": f"Failed to connect to DataMetronome API: {e}"}
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Error response from list_stave_tables tool: {e}", exc_info=True
            )
            return {
                "error": f"API returned an error: {e.response.status_code} - {e.response.text}"
            }
        except Exception as e:
            logger.error(
                f"Unexpected error in list_stave_tables tool: {e}", exc_info=True
            )
            return {"error": f"Unexpected error: {str(e)}"}

    async def list_clefs(
        self, limit: int = 100, skip: int = 0, stave_id: str | None = None
    ) -> dict[str, object]:
        """List all data quality checks (clefs) in DataMetronome."""
        import httpx

        params = {"limit": limit, "skip": skip}
        if stave_id:
            params["stave_id"] = stave_id
        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SHORT) as client:
                response = await client.get(
                    f"{self.api_base_url}/clefs/", params=params
                )
                response.raise_for_status()
                return response.json()
        except httpx.ConnectError as e:
            logger.error(f"Failed to connect to API at {self.api_base_url}: {e}")
            return {
                "error": f"Could not connect to DataMetronome API: {e}",
                "clefs": [],
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"API error: {e.response.status_code} - {e.response.text}")
            return {"error": f"API error: {e.response.status_code}", "clefs": []}
        except Exception as e:
            logger.error(f"Unexpected error calling API: {e}")
            return {"error": f"Unexpected error: {str(e)}", "clefs": []}

    async def get_clef(self, clef_id: str) -> dict[str, object]:
        """Get details about a specific quality check (clef) by ID."""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SHORT) as client:
                response = await client.get(f"{self.api_base_url}/clefs/{clef_id}")
                response.raise_for_status()
                return response.json()
        except httpx.ConnectError as e:
            logger.error(f"Failed to connect to API at {self.api_base_url}: {e}")
            return {"error": f"Could not connect to DataMetronome API: {e}"}
        except httpx.HTTPStatusError as e:
            logger.error(f"API error: {e.response.status_code} - {e.response.text}")
            return {"error": f"API error: {e.response.status_code}"}
        except Exception as e:
            logger.error(f"Unexpected error calling API: {e}")
            return {"error": f"Unexpected error: {str(e)}"}

    async def list_checks(
        self,
        limit: int = 20,
        status: str | None = None,
        stave_id: str | None = None,
        clef_id: str | None = None,
    ) -> dict[str, object]:
        """List check execution results."""
        import httpx

        params = {"limit": limit}
        if status:
            params["status"] = status
        if stave_id:
            params["stave_id"] = stave_id
        if clef_id:
            params["clef_id"] = clef_id
        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SHORT) as client:
                response = await client.get(
                    f"{self.api_base_url}/checks/", params=params
                )
                response.raise_for_status()
                return response.json()
        except httpx.ConnectError as e:
            logger.error(f"Failed to connect to API at {self.api_base_url}: {e}")
            return {
                "error": f"Could not connect to DataMetronome API: {e}",
                "checks": [],
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"API error: {e.response.status_code} - {e.response.text}")
            return {"error": f"API error: {e.response.status_code}", "checks": []}
        except Exception as e:
            logger.error(f"Unexpected error calling API: {e}")
            return {"error": f"Unexpected error: {str(e)}", "checks": []}

    async def get_summary_report(self) -> dict[str, object]:
        """Get a summary report of DataMetronome system status."""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SHORT) as client:
                response = await client.get(f"{self.api_base_url}/reports/summary")
                response.raise_for_status()
                return response.json()
        except httpx.ConnectError as e:
            logger.error(f"Failed to connect to API at {self.api_base_url}: {e}")
            return {"error": f"Could not connect to DataMetronome API: {e}"}
        except httpx.HTTPStatusError as e:
            logger.error(f"API error: {e.response.status_code} - {e.response.text}")
            return {"error": f"API error: {e.response.status_code}"}
        except Exception as e:
            logger.error(f"Unexpected error calling API: {e}")
            return {"error": f"Unexpected error: {str(e)}"}

    async def get_quality_report(self, days: int = 7) -> dict[str, object]:
        """Get a quality report showing data quality metrics."""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SHORT) as client:
                response = await client.get(
                    f"{self.api_base_url}/reports/quality", params={"days": days}
                )
                response.raise_for_status()
                return response.json()
        except httpx.ConnectError as e:
            logger.error(f"Failed to connect to API at {self.api_base_url}: {e}")
            return {"error": f"Could not connect to DataMetronome API: {e}"}
        except httpx.HTTPStatusError as e:
            logger.error(f"API error: {e.response.status_code} - {e.response.text}")
            return {"error": f"API error: {e.response.status_code}"}
        except Exception as e:
            logger.error(f"Unexpected error calling API: {e}")
            return {"error": f"Unexpected error: {str(e)}"}

    async def process_message(
        self,
        message: str,
        conversation_id: str | None = None,
        context: dict[str, object] | None = None,
    ) -> dict[str, object]:
        """Process a user message using the ADK agent.

        Args:
            message: User's message
            conversation_id: Optional conversation ID for context
            context: Optional additional context

        Returns:
            Response from the agent with message and optional tool calls
        """
        if not ADK_AVAILABLE or not self.agent:
            # Fallback to HTTP-based approach if ADK is not available
            logger.warning(
                "ADK not available or agent not initialized, using HTTP fallback"
            )
            return await self._process_message_http(message, conversation_id, context)

        try:
            logger.info("Using ADK agent to process message")
            # Use ADK agent to process the message
            # ADK run_async expects a Content object, not a plain string
            # Import types from google.genai to create Content objects
            from google.genai import types

            # Create a Content object with the user message
            # Part can be created directly with text attribute
            user_content = types.Content(role="user", parts=[types.Part(text=message)])

            response_text: str = ""
            tool_calls = []
            last_response = None

            # Use Runner for proper session management
            # Agent.run_async() has different signature, so we use Runner instead
            from google.adk import Runner
            from google.adk.sessions import InMemorySessionService

            # Create session service and runner
            session_service = InMemorySessionService()
            runner = Runner(
                agent=self.agent,
                app_name="datametronome",
                session_service=session_service,
            )

            # Create or get session
            session_id = conversation_id or f"session-{uuid.uuid4().hex[:8]}"
            user_id = "default"

            # Try to get existing session, create if it doesn't exist
            try:
                session = await session_service.get_session(
                    app_name="datametronome", user_id=user_id, session_id=session_id
                )
                if session is None:
                    # Session doesn't exist, create it
                    session = await session_service.create_session(
                        app_name="datametronome", user_id=user_id, session_id=session_id
                    )
            except Exception as e:
                # Create new session if get_session fails
                logger.debug(f"Could not get session, creating new one: {e}")
                session = await session_service.create_session(
                    app_name="datametronome", user_id=user_id, session_id=session_id
                )

            if session is None:
                raise RuntimeError("Failed to create or retrieve session")

            # Call run_async on the runner with proper parameters
            async_gen = runner.run_async(
                user_id=user_id, session_id=session.id, new_message=user_content
            )

            # Iterate over the async generator
            # Events from runner.run_async() have a 'content' attribute with 'parts'
            async for event in async_gen:
                last_response = event

                # Extract text from event.content.parts[].text
                if hasattr(event, "content") and event.content:
                    if hasattr(event.content, "parts") and event.content.parts:
                        for part in event.content.parts:
                            if hasattr(part, "text") and part.text:
                                response_text += part.text
                            elif hasattr(part, "function_call"):
                                # This is a tool call, extract it
                                fc = part.function_call
                                tool_calls.append(
                                    {
                                        "id": getattr(
                                            fc, "id", f"call-{len(tool_calls)}"
                                        ),
                                        "name": getattr(fc, "name", ""),
                                        "arguments": getattr(fc, "args", {}),
                                    }
                                )
                    elif hasattr(event.content, "text"):
                        text = getattr(event.content, "text", "")
                        if text:
                            response_text += str(text)

                # Fallback: try direct text attribute
                elif hasattr(event, "text") and event.text:
                    text = getattr(event, "text", "")
                    if text:
                        response_text += str(text)

                # Fallback: try string conversion
                elif isinstance(event, str):
                    response_text += event

                # Collect tool calls from event if available
                if hasattr(event, "tool_calls"):
                    tool_calls_attr = getattr(event, "tool_calls", None)
                    if tool_calls_attr:
                        for tc in tool_calls_attr:
                            tool_calls.append(
                                {
                                    "id": getattr(tc, "id", f"call-{len(tool_calls)}"),
                                    "name": getattr(tc, "name", ""),
                                    "arguments": getattr(tc, "arguments", {}),
                                }
                            )

            # If we didn't get text from events, try to extract from last response
            if not response_text and last_response:
                # Try to extract from event.content.parts[].text
                if hasattr(last_response, "content") and last_response.content:
                    if (
                        hasattr(last_response.content, "parts")
                        and last_response.content.parts
                    ):
                        for part in last_response.content.parts:
                            if hasattr(part, "text") and part.text:
                                response_text += part.text
                    elif hasattr(last_response.content, "text"):
                        text = getattr(last_response.content, "text", "")
                        response_text = str(text) if text else response_text
                elif hasattr(last_response, "messages") and last_response.messages:
                    # Get the last message from the agent
                    last_message = last_response.messages[-1]
                    if hasattr(last_message, "content") and last_message.content:
                        if (
                            hasattr(last_message.content, "parts")
                            and last_message.content.parts
                        ):
                            for part in last_message.content.parts:
                                if hasattr(part, "text") and part.text:
                                    response_text += part.text
                        elif hasattr(last_message.content, "text"):
                            response_text = last_message.content.text
                    elif isinstance(last_message, dict) and "content" in last_message:
                        response_text = last_message["content"]
                elif hasattr(last_response, "text"):
                    text = getattr(last_response, "text", "")
                    response_text = str(text) if text else response_text

            return {
                "message": response_text or "I've processed your request.",
                "toolCalls": tool_calls if tool_calls else None,
                "model": self.model_name,  # Include model name in response
                "finishReason": "stop",  # Default finish reason
            }

        except Exception as e:
            logger.error(
                f"Error processing message with ADK agent: {str(e)}", exc_info=True
            )
            # Fallback to HTTP approach on error
            logger.info("Falling back to HTTP-based agent")
            return await self._process_message_http(message, conversation_id, context)

    async def _process_message_http(
        self,
        message: str,
        conversation_id: str | None = None,
        context: dict[str, object] | None = None,
    ) -> dict[str, object]:
        """Fallback HTTP-based message processing (for when ADK is not available)."""
        # This is the original HTTP-based implementation
        # Kept as fallback for when ADK is not installed
        if not self.api_key and not self.model_name.startswith("ollama_chat/"):
            raise ValueError("ADK API key not configured and not using Ollama")

        import httpx

        # For Ollama, use local endpoint
        if self.model_name.startswith("ollama_chat/"):
            # Extract model name (e.g., "qwen2.5" from "ollama_chat/qwen2.5")
            model_name = self.model_name.replace("ollama_chat/", "")
            base_url = "http://localhost:11434/api/chat"

            # Build conversation history
            # Start with system instructions so the model knows about DataMetronome
            messages = [{"role": "system", "content": self._get_system_instructions()}]

            if context and "history" in context:
                for msg in context["history"][-5:]:
                    messages.append(
                        {
                            "role": msg["role"],
                            "content": msg["content"],
                        }
                    )

            messages.append({"role": "user", "content": message})

            request_data = {
                "model": model_name,
                "messages": messages,
                "stream": False,
            }

            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                response = await client.post(base_url, json=request_data)
                if response.status_code != 200:
                    raise Exception(
                        f"Ollama API error: {response.status_code} - {response.text}"
                    )

                result = response.json()
                assistant_message = result.get("message", {}).get("content", "")

                return {
                    "message": assistant_message,
                    "toolCalls": None,  # Ollama doesn't support tool calling via this endpoint
                }
        else:
            # Original Gemini HTTP implementation (kept as fallback)
            raise NotImplementedError(
                "HTTP-based Gemini implementation removed. "
                "Please install google-adk: pip install google-adk"
            )
